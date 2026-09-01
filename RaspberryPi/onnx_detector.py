
import time

import cv2
import numpy as np
import onnxruntime as ort

from typing import Any, Union, Tuple, List, Optional, Dict
# from rich import print


class ONNX_RUN_ultralytics:
    """
    YOLOv8 ONNX推理类
    
    功能：
    - 加载YOLOv8 ONNX模型
    - 执行图像预处理和后处理
    - 进行目标检测推理
    - 支持自定义置信度和IOU阈值
    
    属性：
    - model_path: ONNX模型路径
    - classes: 类别名称列表（可选）
    - session: ONNX Runtime会话
    - input_name: 模型输入名称
    """
    
    def __init__(self, model_path: str, classes: Optional[List[str]] = None):
        """
        初始化YOLOv8 ONNX推理器
        
        参数:
        - model_path: ONNX模型文件路径
        - classes: 类别名称列表，如果为None则使用默认的数字编号
        """
        self.model_path = model_path
        self.classes = classes
        
        # 如果没有指定类别，使用数字编号作为默认类别
        if self.classes is None or len(self.classes) == 0:
            self.classes = [str(i + 1).zfill(3) for i in range(1000)]
        
        # 执行提供者配置（默认：CPU）
        providers = [
            'CUDAExecutionProvider',  # GPU加速（如果可用）
            'CPUExecutionProvider'    # CPU后备
        ]
        
        session_options = ort.SessionOptions()
        session_options.log_severity_level = 3      # 设置日志级别

        # 初始化ONNX Runtime会话
        self.session = ort.InferenceSession(
            self.model_path, 
            providers=providers, 
            sess_options=session_options
        )
        self.input_name = self.session.get_inputs()[0].name

        # 预热模型
        self._model_warmup(self.session, num_warmups=3)

    def _model_warmup(self, session, imgsz=640, num_warmups=10):
        """针对YOLOv8模型的预热"""
        input_name = session.get_inputs()[0].name
        input_shape = session.get_inputs()[0].shape
        
        # YOLOv8通常期望 [1, 3, H, W] 格式的输入
        if len(input_shape) == 4 and input_shape[1] == 3:
            dummy_input = np.random.randn(1, 3, imgsz, imgsz).astype(np.float32)
        else:
            dummy_input = np.random.randn(*input_shape).astype(np.float32)
        
        print("预热YOLOv8模型...")
        for _ in range(num_warmups):
            session.run(None, {input_name: dummy_input})
        print("预热完成！")


    def _letterbox(
        self, 
        im: np.ndarray, 
        new_shape: Union[int, Tuple[int, int]] = (640, 640),
        color: Tuple[int, int, int] = (114, 114, 114)
    ) -> Tuple[np.ndarray, Tuple[float, float], Tuple[float, float]]:
        """
        将图像填充为指定形状，保持宽高比（内部方法）
        """
        shape = im.shape[:2]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)
        
        # 计算缩放比例
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
        dw /= 2
        dh /= 2
        
        # 调整图像大小
        if shape[::-1] != new_unpad:
            im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
        
        # 填充图像
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        
        return im, (r, r), (left, top)
    
    def _preprocess_image(self, image: Union[str, np.ndarray], img_size: int = 640):
        """
        图像预处理（内部方法）
        """
        # 读取图像
        if isinstance(image, str):
            image = cv2.imread(image)
            assert isinstance(image, np.ndarray), "OpenCV未能正确读取图像"
        elif not isinstance(image, np.ndarray):
            raise TypeError("输入必须是numpy数组或图像路径字符串")

        original_size = image.shape[:2]  # (height, width)
        
        # 颜色空间转换 BGR → RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 保持宽高比的resize
        image, ratio, (dw, dh) = self._letterbox(image, new_shape=(img_size, img_size))
        
        # 归一化到0-1范围
        image = image.astype(np.float32) / 255.0
        
        # 通道顺序转换 HWC → CHW
        image = np.transpose(image, (2, 0, 1))  # [H, W, C] → [C, H, W]
        
        # 添加batch维度
        image = np.expand_dims(image, axis=0)   # [C, H, W] → [1, C, H, W]
        
        # 确保内存连续性
        if not image.flags.contiguous:
            image = np.ascontiguousarray(image)
        
        return image, original_size, ratio, (dw, dh)
    
    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float):
        """
        非极大值抑制实现（内部方法）
        """
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1 + 1e-5) * (y2 - y1 + 1e-5)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        return keep
    
    def _parse_yolov8_output(
        self, 
        predictions: np.ndarray, 
        conf_threshold: float = 0.25, 
        iou_threshold: float = 0.45
    ) -> List[List[float]]:
        """
        解析YOLOv8输出（内部方法）
        """
        # 转换输出格式
        predictions = np.squeeze(predictions)   # 去除batch维度 [84, 8400]
        predictions = predictions.transpose()   # 转置为 [8400, 84]
        
        # 分离边界框和类别分数
        boxes = predictions[:, :4]              # 边界框 [8400, 4] (cx, cy, w, h)
        class_scores = predictions[:, 4:]       # 类别分数 [8400, 80]
        
        # 计算每个框的置信度和类别
        max_scores = np.max(class_scores, axis=1)      # 每个框的最大分数 [8400]
        class_ids = np.argmax(class_scores, axis=1)    # 每个框的类别ID [8400]
        
        # 应用置信度阈值过滤
        keep_indices = max_scores > conf_threshold
        boxes = boxes[keep_indices]
        max_scores = max_scores[keep_indices]
        class_ids = class_ids[keep_indices]
        
        if len(boxes) == 0:
            return []
        
        # 转换边界框格式 (cx, cy, w, h) → (x1, y1, x2, y2)
        x1 = boxes[:, 0] - boxes[:, 2] / 2  # cx - w/2
        y1 = boxes[:, 1] - boxes[:, 3] / 2  # cy - h/2
        x2 = boxes[:, 0] + boxes[:, 2] / 2  # cx + w/2
        y2 = boxes[:, 1] + boxes[:, 3] / 2  # cy + h/2
        
        boxes_xyxy = np.column_stack([x1, y1, x2, y2])
        
        # 应用NMS非极大值抑制
        keep_indices = self._nms(boxes_xyxy, max_scores, iou_threshold)
        
        # 整理最终结果
        final_boxes = boxes_xyxy[keep_indices]
        final_scores = max_scores[keep_indices]
        final_class_ids = class_ids[keep_indices]
        
        # 组合结果: [x1, y1, x2, y2, confidence, class_id]
        results = []
        for i in range(len(final_boxes)):
            result = [
                float(final_boxes[i][0]),  # x1
                float(final_boxes[i][1]),  # y1
                float(final_boxes[i][2]),  # x2
                float(final_boxes[i][3]),  # y2
                float(final_scores[i]),    # confidence
                int(final_class_ids[i])    # class_id
            ]
            results.append(result)
        
        return results
    
    def _map_to_original_coordinates(
        self, 
        detections: List[List[float]], 
        original_size: Tuple[int, int], 
        ratio: Tuple[float, float], 
        padding: Tuple[float, float]
    ) -> List[List[float]]:
        """
        将检测框坐标映射回原始图像坐标系（内部方法）
        """
        original_height, original_width = original_size
        ratio_w, ratio_h = ratio
        padding_left, padding_top = padding
        
        mapped_detections = []
        
        for det in detections:
            x1, y1, x2, y2, confidence, class_id = det
            
            # 去除填充偏移量
            x1_unpadded = x1 - padding_left
            y1_unpadded = y1 - padding_top
            x2_unpadded = x2 - padding_left
            y2_unpadded = y2 - padding_top
            
            # 根据缩放比例还原到原始尺寸
            x1_original = x1_unpadded / ratio_w
            y1_original = y1_unpadded / ratio_h
            x2_original = x2_unpadded / ratio_w
            y2_original = y2_unpadded / ratio_h
            
            # 确保坐标在图像范围内
            x1_original = max(0, min(x1_original, original_width - 1))
            y1_original = max(0, min(y1_original, original_height - 1))
            x2_original = max(0, min(x2_original, original_width - 1))
            y2_original = max(0, min(y2_original, original_height - 1))
            
            mapped_detections.append([
                x1_original, y1_original, x2_original, y2_original,
                confidence, class_id
            ])
        
        return mapped_detections
    
    # 中心点坐标求取
    def _get_center_point(self, box):
        '''计算边界框中心点坐标
        输入：[top, left, right, bottom]
        [x1, y1, x2, y2]
        返回值：[center_x, center_y]
        '''
        # 解析中心坐标
        center_x = (box[0] + box[2]) / 2
        center_y = (box[1] + box[3]) / 2
        return (center_x, center_y)
    
    def onnx_run(
        self, 
        image: Union[str, np.ndarray], 
        conf_threshold: float = 0.25, 
        iou_threshold: float = 0.45
    ) -> List[List[float]]:
        """
        执行ONNX推理
        
        参数:
        - image: 输入图像（路径字符串或numpy数组）
        - conf_threshold: 置信度阈值，默认0.25
        - iou_threshold: IOU阈值，默认0.45
        
        返回:
        - List[List[float]]: 检测结果列表，每个元素为 [x1, y1, x2, y2, confidence, class_id]
        """

        # 图像预处理
        input_image, original_size, ratio, padding = self._preprocess_image(image)
        # ONNX推理
        outputs = self.session.run(None, {self.input_name: input_image})
        predictions = outputs[0]  # 形状 [1, 84, 8400]
        max_conf = np.max(predictions[0, 4:, :])

        # 所有结果置信度均小于阈值
        if conf_threshold > max_conf:
            return []
        # 解析输出
        detections = self._parse_yolov8_output(predictions, conf_threshold, iou_threshold)
        
        # 映射到原始坐标
        original_detections = self._map_to_original_coordinates(
            detections, original_size, ratio, padding
        )
        return original_detections
    
    def visualize_results(
        self, 
        image: Union[str, np.ndarray], 
        detections: List[List[float]], 
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """
        可视化检测结果
        
        参数:
        - image: 原始图像（路径字符串或numpy数组）
        - detections: 检测结果列表
        - output_path: 输出图像保存路径（可选）
        
        返回:
        - np.ndarray: 带有检测框的图像
        """
        # 读取图像
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image.copy()
        
        # 绘制检测框和标签
        for det in detections:
            x1, y1, x2, y2, conf, cls_id = det
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            
            # 构建标签文本
            if cls_id < len(self.classes):
                class_name = self.classes[cls_id]
            else:
                class_name = str(cls_id)
            
            label = f"Class{cls_id}_{class_name}: {conf:.2f}"
            cv2.putText(img, label, (int(x1), int(y1)-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 保存结果（如果指定了输出路径）
        if output_path:
            cv2.imwrite(output_path, img)
        
        return img

    def RUN_ONNX(
            self, 
            image: Union[str, np.ndarray], 
            conf_threshold: float = 0.25, 
            iou_threshold: float = 0.45
        ) -> Dict[str, Any]:
            '''
            执行完整的ONNX推理流程，包括图像读取、推理、结果解析和可视化
            
            参数:
            - image: 输入图像，可以是文件路径字符串或numpy数组
            - conf_threshold: 置信度阈值，用于过滤低置信度的检测结果，默认0.25
            - iou_threshold: IOU阈值，用于非极大值抑制，默认0.45
            
            返回:
            - Dict[str, Any]: 包含检测结果的字典，包含以下键值：
                - 'img': np.ndarray - 原始图像数组
                - 'classes': Optional[List[int]] - 检测到的类别ID列表，如果没有检测结果则为None
                - 'box': Optional[List[List[float]]] - 检测框坐标列表，格式为[[x1, y1, x2, y2], ...]，如果没有检测结果则为None
                - 'score': Optional[List[float]] - 检测置信度分数列表，如果没有检测结果则为None
                - 'zxd': Optional[List[Tuple[float, float]]] - 检测框中心点坐标列表，格式为[(center_x, center_y), ...]，如果没有检测结果则为None
                - 'draw_img': np.ndarray - 绘制了检测结果的可视化图像
            
            异常:
            - TypeError: 当输入图像类型不是字符串或numpy数组时抛出
            - FileNotFoundError: 当图像路径不存在时抛出（通过cv2.imread返回None判断）
            '''
            start_time = time.time()
            # 读取图像
            if isinstance(image, str):
                image = cv2.imread(image)
                if image is None:
                    raise FileNotFoundError(f"图片加载失败，请检查路径: {image}")
            elif isinstance(image, np.ndarray):
                pass
            else:
                raise TypeError("参数必须是numpy数组或路径字符串")

            img = image.copy()
            results = self.onnx_run(image, conf_threshold=conf_threshold, iou_threshold=iou_threshold)

            t2 = time.time()
            if len(results) > 0:
                draw_image = self.visualize_results(img, results)   # 绘制检测结果
                cls, boxes, scores, zxd = [], [], [], []
                for det in results:
                    x1, y1, x2, y2, conf, cls_id = det
                    (center_x, center_y) = self._get_center_point([x1, y1, x2, y2])
                    print(f"类别 {cls_id}: 置信度 {conf:.2f}, 边界框 [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}], 中心点 {center_x, center_y}")
                    
                    cls.append(cls_id)
                    boxes.append([x1, y1, x2, y2])
                    scores.append(conf)
                    zxd.append((center_x, center_y))
                
                end_time = time.time()
                print(f'用时：{end_time - start_time} s')

                # 返回检测结果
                return {
                    'img': img,                 # 原始图像
                    'classes': cls,             # 类别列表
                    'box': boxes,               # 检测框 [x1, y1, x2, y2]
                    'score': scores,            # 置信度列表
                    'zxd': zxd,                 # 中心点坐标列表
                    'draw_img': draw_image      # 结果绘制图像
                }
            else:
                # 检测结果为空
                end_time = time.time()
                print(f'用时：{end_time - start_time} s    ===当前帧未检测到目标===')
                return {
                    'img': img, 
                    'classes': None, 
                    'box': None, 
                    'score': None, 
                    'zxd': None, 
                    'draw_img': img
                }



# 使用示例
if __name__ == '__main__':
    
    # 初始化推理器
    model_path = '/home/pwq/Desktop/YOLO模型测试/yolo11n.onnx'
    classes = None

    detector = ONNX_RUN_ultralytics(model_path, classes)
    

    # 执行推理
    input_img = '/home/pwq/py/yolo/ultralytics_yolov8_rknn/bus.jpg'
    results = detector.RUN_ONNX(input_img, conf_threshold=0.5, iou_threshold=0.45)

    input_img = '/home/pwq/py/yolo/ultralytics_yolov8_rknn/0.jpg'
    results = detector.RUN_ONNX(input_img, conf_threshold=0.5, iou_threshold=0.45)

    input_img = '/home/pwq/py/yolo/ultralytics_yolov8_rknn/zidane.jpg'
    results = detector.RUN_ONNX(input_img, conf_threshold=0.5, iou_threshold=0.45)


    # print(results)

    # cv2.imwrite('/home/pwq/py/results_img.jpg', results['img'])
    # cv2.imwrite('/home/pwq/py/results_draw_img.jpg', results['draw_img'])


