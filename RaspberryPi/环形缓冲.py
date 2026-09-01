from collections import deque
import time

# 使用memory_profiler进行内存分析
from memory_profiler import profile

from 稳定性检测 import check_detection_stability


class DetectionBuffer:
    '''
    环形缓冲区类
    存放检测结果，提供获取最新结果、指定类别结果、所有结果、统计信息等功能
    按每个检测结果存放计数
    '''
    def __init__(self, size):
        """
        初始化检测结果缓冲区
        
        参数:
            size: 缓冲区最大容量
        """
        self.size = size
        self.buffer = deque(maxlen=size)
    
    # @profile    # 内存分析
    def add_detection(self, detection_result):
        """
        添加检测结果到缓冲区
        
        参数:
            detection_result: img_yolo_v8.img_detect()返回的字典结果
        """
        # 为每个检测结果添加时间戳
        timestamp = time.time()
        
        # 将检测结果按对象拆分存储
        for i in range(len(detection_result['cl'])):
            self.buffer.append({
                'timestamp': timestamp,
                'class_name': detection_result['cl'][i],
                'center_xy': detection_result['xy'][i],
                'bbox_xyxy': detection_result['xyxy'][i],
                'confidence': detection_result['conf'][i],
                'inference_time': detection_result['use_time'],
                'frame_index': len(self.buffer)  # 可选: 添加帧序号
            })
    
    def get_latest(self, n=1):
        """
        获取最新的n个检测结果
        
        参数:
            n: 要获取的结果数量
            
        返回:
            包含最新n个检测结果的列表
        """
        return list(self.buffer)[-n:]
    
    def get_by_class(self, class_name):
        """
        获取指定类别的所有检测结果
        
        参数:
            class_name: 要筛选的类别名称
            
        返回:
            包含指定类别检测结果的列表
        """
        return [item for item in self.buffer if item['class_name'] == class_name]
    
    def get_all(self):
        """
        获取所有检测结果
        
        返回:
            包含所有检测结果的列表
        """
        return list(self.buffer)
    
    def clear(self):
        """
        清空缓冲区
        """
        self.buffer.clear()
    
    def is_empty(self):
        """
        检查缓冲区是否为空
        
        返回:
            bool: 缓冲区是否为空
        """
        return len(self.buffer) == 0
    
    def is_full(self):
        """
        检查缓冲区是否已满
        
        返回:
            bool: 缓冲区是否已满
        """
        return len(self.buffer) == self.size
    
    def get_statistics(self):
        """
        获取缓冲区统计信息
        
        返回:
            包含统计信息的字典:
            - total_detections: 总检测数量
            - class_distribution: 类别分布
            - avg_confidence: 平均置信度
            - avg_inference_time: 平均推理时间
        """
        if self.is_empty():
            return None
            
        stats = {
            'total_detections': len(self.buffer),
            'class_distribution': {},
            'total_confidence': 0.0,
            'total_inference_time': 0.0
        }
        
        for item in self.buffer:
            # 统计类别分布
            cls = item['class_name']
            stats['class_distribution'][cls] = stats['class_distribution'].get(cls, 0) + 1
            
            # 累加置信度和推理时间
            stats['total_confidence'] += item['confidence']
            stats['total_inference_time'] += item['inference_time']
        
        # 计算平均值
        stats['avg_confidence'] = stats['total_confidence'] / len(self.buffer)
        stats['avg_inference_time'] = stats['total_inference_time'] / len(self.buffer)
        
        return stats



if __name__ == "__main__":
    # 创建缓冲区实例
    buffer = DetectionBuffer(size=1000)

    import cv2
    from rknnpool import rknnPoolExecutor
    from func import myFunc




    # 初始化RKNN线程池
    model_path = "./ht_v8n_300_3588_.rknn"
    # 线程数
    TPEs = 3
    pool = rknnPoolExecutor(model_path, TPEs, myFunc)

    # 读取图像 (这里用同一张图模拟)
    img = cv2.imread('/home/orangepi/ht_Arm/v1_000026.jpg')

    # 初始化异步所需要的帧
    if img is not None:
        for i in range(TPEs + 1):
            pool.put(img)
    else:
        del pool
        exit(-1)
    
    # 模拟实时检测过程
    for i in range(300):  # 模拟帧检测

        t1 = time.time()
        # 进行检测
        pool.put(img)
        data, flag = pool.get()
        if not flag:
            continue
        else: pass #print('*' * 50 + '\n', data,'\n' + '*' * 50)

        results = {
            'cl': data['classes'],
            'xy': data['zxd'],
            'xyxy': data['box'],
            'conf': data['score'],
            'img': img,
            'img_draw': data['img'],
            'use_time': time.time() - t1
        }
        
        # 将结果存入缓冲区
        buffer.add_detection(results)
        


        # 打印最新检测结果
        latest = buffer.get_latest(1)
        print(f"\n帧 {i+1} 最新检测结果:")
        for det in latest:
            print(f"  类别: {det['class_name']}")
            print(f"  中心坐标: {det['center_xy']}")
            print(f"  边界框: {det['bbox_xyxy']}")
            print(f"  置信度: {det['confidence']:.2f}")
            print(f"  时间戳: {det['timestamp']}")
    
    from rich import print as rprint
    data = check_detection_stability(buffer, latest_n=100)
    rprint(data)
    
    if not data or len(data) <= 0:
        exit()
    
    from 坐标转换 import pixel_to_arm
    for i, item in enumerate(data):
        print(f"\n第{i + 1}个稳定检测结果:")
        pixel_x = item['center_xy'][0]
        pixel_y = item['center_xy'][1]
        # if any([
        #     pixel_x < 300,
        #     pixel_x > 500,
        #     pixel_y < 200,
        #     pixel_y > 400
        # ]):
        #     continue

        arm_x, arm_y = pixel_to_arm(pixel_x, pixel_y)
        rprint(f'第{i+1}个目标, 转换后的机械臂坐标: ({arm_x}, {arm_y})')
        if item['class_name'] == 0:
            rprint('GOOD', item['center_xy'], '放那')
            pass
        elif item['class_name'] == 1:
            rprint('BAD', item['center_xy'], '扔左边')
        elif item['class_name'] == 2:
            rprint('UNRIPE', item['center_xy'], '扔右边')
        else:
            rprint('未知目标，跳过')
            pass

    print('一轮处理完毕，进入下一轮')







    # 获取统计信息
    stats = buffer.get_statistics()
    print("\n缓冲区统计信息:")
    print(f"总检测数: {stats['total_detections']}")
    print(f"类别分布: {stats['class_distribution']}")
    print(f"平均置信度: {stats['avg_confidence']:.2f}")
    print(f"平均推理时间: {stats['avg_inference_time']:.2f}ms")


    pass



    # 释放资源
    cv2.destroyAllWindows()
    pool.release()

