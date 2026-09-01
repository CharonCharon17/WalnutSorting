import sys
import cv2
import time
#from rknnpool import rknnPoolExecutor
from onnx_detector import ONNX_RUN_ultralytics

from rich import print as rprint

import serial
import time

from 环形缓冲 import DetectionBuffer
from 稳定性检测 import check_detection_stability
from 坐标转换 import pixel_to_arm
from 抓取 import get_ht, put_left, put_right


# 本地默认显示
import os
os.environ["DISPLAY"] = ":0"  

from serial.tools import list_ports
import pydobot

# ******************************************************************************
# 
#                               初始化配置部分
# 
# ******************************************************************************

def check_serial_port(port="/dev/serial0", baudrate=9600, timeout=2):
    """检测串口设备是否可用"""
    try:
        # 尝试打开串口
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            print(f"串口设备 {port} 检测成功")
            print(f"波特率: {baudrate}")
            print(f"设备状态: 就绪")
            return True
    except serial.SerialException as e:
        print(f"串口设备 {port} 检测失败: {e}")
        return False
    except PermissionError:
        print(f"权限不足，请尝试: sudo chmod 666 {port}")
        return False
    except FileNotFoundError:
        print(f"串口设备 {port} 不存在")
        print("请检查: ls /dev/serial*")
        return False

def send_data_packet(ser, packet_data):
    """发送完整的数据包并处理回复"""
    # 发送完整的二进制数据包
    ser.write(packet_data)
    print(f"发送数据包: {packet_data.hex(' ')}")
    
    # 等待并读取回复
    time.sleep(0.2)  # 给STM32足够的响应时间
    
    if ser.in_waiting > 0:
        received_data = ser.read(ser.in_waiting)
        hex_data = received_data.hex(' ')
        print(f"接收: {hex_data}")
        
        # 检查是否收到完整的数据包回复
        if received_data == packet_data:
            print("数据包通信成功！")
            return True
        else:
            print("回传内容不匹配")
            return False
    else:
        print("未收到回复")
        return False

def wait_for_stm32_ready(ser):
    """等待STM32发送就绪信号"""
    print("等待STM32就绪信号...")
    
    # 定义STM32就绪数据包
    ready_packet = bytes([0xFF, 0x01, 0x00, 0x00, 0x00, 0xFE])
    
    try:
        while True:
            # 检查是否有数据
            if ser.in_waiting > 0:
                received_data = ser.read(ser.in_waiting)
                hex_data = received_data.hex(' ')
                print(f"接收: {hex_data}")
                
                # 检查是否收到就绪数据包
                if  ready_packet in received_data:
                    print("STM32已就绪！")
                    return True
                else:
                    print(f"收到其他数据: {hex_data}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("等待被用户中断")
        return False

# 初始化摄像头
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("无法打开摄像头，请检查设备连接")
    sys.exit(-1)

# 设置分辨率
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 宽度
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 高度
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # type: ignore # 编码格式

# 初始化ONNX推理器
model_path = "./best.onnx"
detector = ONNX_RUN_ultralytics(model_path, classes=None)
print("ONNX推理器初始化完成")

# 初始化串口通信
port = "/dev/serial0"
baudrate = 9600

print("正在检测串口设备...")
if not check_serial_port(port, baudrate):
    print("串口初始化失败，程序退出")
    sys.exit(-1)

try:
    CH340_device = serial.Serial(port, baudrate, timeout=1)
    print("串口连接已建立")
    # 清空缓冲区
    CH340_device.reset_input_buffer()
    CH340_device.reset_output_buffer()
except Exception as e:
    print(f"串口连接错误: {e}")
    sys.exit(-1)

# 列出所有可用端口
available_ports = list_ports.comports()
cp210x_ports = [
    port for port in available_ports 
    if 'CP210' in port.description or 'Dobot' in port.description
]   # 筛选出 CP210X 设备

if not cp210x_ports:
    print("未找到 CP210X 设备！")
    exit()

# 选择第一个 CP210X 设备
port = cp210x_ports[0].device
print(f"连接到 CP210X 设备: {port}")

# 初始化 Dobot
device = pydobot.Dobot(port=port, verbose=False)
device.speed(velocity=2000, acceleration=2000)
device.suck(False)      # 吸盘关闭
device.move_to(240, 0, 140, r=60, wait=True)    # 移动到初始位置

# 创建缓冲区实例
buffer = DetectionBuffer(size=1000)

cv2.namedWindow('YOLOv8', cv2.WINDOW_NORMAL)  # 必须使用WINDOW_NORMAL
cv2.resizeWindow('YOLOv8', width=1280, height=720)  # 设置初始尺寸
cv2.moveWindow('YOLOv8', 20, 20)

png = cv2.imread('chinese_char.png')
cv2.imshow('YOLOv8', png)
cv2.waitKey(1)

# ******************************************************************************
# 
#                               主循环
# 
# ******************************************************************************

while cap.isOpened():
    # *************************************
    #           等待STM32就绪
    # *************************************
    cv2.imshow('YOLOv8', png)
    cv2.waitKey(1)
    print('开始运行')
    
    # 等待STM32就绪信号
    if not wait_for_stm32_ready(CH340_device):
        break
    
    rprint('*' * 100 , '\nSTM32 就绪')
    
    # *************************************
    #               目标检测
    # *************************************
    data = None
    detection_start_time = time.time()
    detection_timeout = 30  # 30秒检测超时
    
    while time.time() - detection_start_time < detection_timeout:
        t1 = time.time()

        # 读取摄像头帧
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        # 填充区域
        frame[0:720, 0:400] = [128, 128, 128]
        frame[0:720, 880:1280] = [128, 128, 128]
        
        # 使用detector进行推理
        try:
            results = detector.RUN_ONNX(frame, conf_threshold=0.45, iou_threshold=0.25)
            
            # 处理结果
            if results['classes'] is not None:
                # 准备结果字典
                detection_result = {
                    'cl': results['classes'],
                    'xy': results['zxd'],
                    'xyxy': results['box'],
                    'conf': results['score'],
                    'img': frame,
                    'img_draw': results['draw_img'],
                    'use_time': time.time() - t1
                }
                
                # 将结果存入缓冲区
                buffer.add_detection(detection_result)
                
                # 显示结果图像
                img = results['draw_img']
                
                # 计算并显示帧率
                t2 = time.time()
                fps = 1 / (t2 - t1)
                cv2.putText(img, f"FPS: {fps:6.2f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # 显示检测结果信息
                info_text = f"Detected: {len(results['classes'])} objects"
                cv2.putText(img, info_text, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
            else:
                # 没有检测到目标时使用原图
                img = frame
                cv2.putText(img, "No detection", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
        except Exception as e:
            print(f"推理异常: {e}")
            img = frame
            continue

        # 显示结果
        cv2.imshow('YOLOv8', img)

        # 按下Q键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        # 稳定性检测
        data = check_detection_stability(buffer, latest_n=5)
        if data is not None:
            print('结果稳定')
            sorted_data = sorted(data, key=lambda x: x['center_xy'][1])
            break
            
        time.sleep(0.01)
    
    # 检查是否超时
    if data is None:
        print("检测超时，未找到稳定目标")
        # 发送超时信号给STM32
        timeout_packet = bytes([0xFF, 0xEE, 0xEE, 0xEE, 0xEE, 0xFE])
        CH340_device.write(timeout_packet)
        continue

    # *************************************
    #           结果稳定，开始抓取
    # *************************************
    num_good, num_bad, num_unripe = 0, 0, 0
    item = sorted_data[-1]
    rprint(item)

    print(f"最右边的检测结果:")
    pixel_x = item['center_xy'][0]
    pixel_y = item['center_xy'][1]

    # 转换到机械臂坐标
    arm_x, arm_y = pixel_to_arm(pixel_x, pixel_y)
    rprint(f'最右边的目标, 转换后的机械臂坐标: ({arm_x}, {arm_y})')
    
    # 根据分类执行相应操作
    if item['class_name'] == 0:
        rprint('GOOD', item['center_xy'], '放那')
        num_good += 1
    elif item['class_name'] == 1:
        rprint('BAD', item['center_xy'], '扔左边')
        get_ht(device, arm_x, arm_y)
        put_left(device)
        num_bad += 1
    elif item['class_name'] == 2:
        rprint('UNRIPE', item['center_xy'], '扔右边')
        get_ht(device, arm_x, arm_y)
        put_right(device)
        num_unripe += 1
    else:
        rprint('未知目标，跳过')
        continue

    # 发送结果数据给STM32
    try:
        # 构建数据包: FF + 类型 + 数量 + FE
        result_packet = bytes([0xFF, 0x02, num_good, num_bad, num_unripe, 0xFE])
        CH340_device.write(result_packet)
        print(f"发送结果数据包: {result_packet.hex(' ')}")
    except Exception as e:
        print(f"发送数据失败: {e}")

    # 清空缓冲区和数据
    data = None
    buffer.clear()
    print('一轮处理完毕，进入下一轮')

# 释放资源
cap.release()
cv2.destroyAllWindows()
CH340_device.close()
print("程序正常退出")
