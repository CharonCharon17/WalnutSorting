import serial
import time

def check_serial_port(port="/dev/serial0", baudrate=9600, timeout=2):
    """检测串口设备是否可用"""
    try:
        # 尝试打开串口
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            print(f"串口设备 {port} 检测成功")
            print(f"   波特率: {baudrate}")
            print(f"   设备状态: 就绪")
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
    print(f"📤 发送数据包: {packet_data.hex(' ')}")
    
    # 等待并读取回复
    time.sleep(0.2)  # 给STM32足够的响应时间
    
    if ser.in_waiting > 0:
        received_data = ser.read(ser.in_waiting)
        hex_data = received_data.hex(' ')
        print(f"📥 接收: {hex_data}")
        
        # 检查是否收到完整的数据包回复
        if received_data == packet_data:
            print("✅ 数据包通信成功！")
            return True
        else:
            print("❌ 回传内容不匹配")
            return False
    else:
        print("❌ 未收到回复")
        return False

def main_communication(ser):
    """主通信函数"""
    print("开始主通信...")
    
    # 定义要发送的二进制数据包
    data_packet = bytes([0xFF, 0x01, 0x00, 0x00, 0x00, 0xFE])
    
    try:
        while True:
            print("\n" + "="*40)
            
            # 选项1：发送完整数据包
            print("1. 发送完整数据包 FF 01 00 00 00 FE")
            send_data_packet(ser, data_packet)
            
            # 选项2：也可以保留原来的字符串发送方式（可选）
            # message = b"01\n"
            # ser.write(message)
            # print(f"发送字符串: {message.decode().strip()}")
            # time.sleep(0.1)
            # if ser.in_waiting > 0:
            #     received_data = ser.read(ser.in_waiting)
            #     hex_data = received_data.hex(' ')
            #     print(f"接收: {hex_data}")
            
            time.sleep(1)  # 每秒通信一次
            
    except KeyboardInterrupt:
        print("\n通信已停止")

def main():
    """主函数"""
    port = "/dev/serial0"
    baudrate = 9600
    
    print("🔍 正在检测串口设备...")
    
    # 第一步：检测串口设备
    if not check_serial_port(port, baudrate):
        print("程序退出")
        return
    
    # 第二步：建立通信连接
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            print("串口连接已建立")
            print("-" * 40)
            
            # 清空缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # 第三步：开始主通信
            main_communication(ser)
            
    except Exception as e:
        print(f"通信错误: {e}")

if __name__ == "__main__":
    main()