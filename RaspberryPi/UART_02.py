import serial
import serial.tools.list_ports
import time

class HexSerialCommunicator:
    # 预定义的帧头帧尾
    HEADER = 0xFF
    FOOTER = 0xFE
    
    def __init__(self, port=None, baudrate=9600, timeout=0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.rx_buffer = bytearray()  # 接收缓冲区
        self.last_rx_frame = None    # 最后接收到的完整帧

    def find_port(self, target_vid=None, target_pid=None):
        """通过VID/PID查找设备"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(f"检测到设备: {port.device} | VID: {hex(port.vid) if port.vid else 'None'} | PID: {hex(port.pid) if port.pid else 'None'}")
            
            if (target_vid is None or port.vid == target_vid) and \
               (target_pid is None or port.pid == target_pid):
                self.port = port.device
                print(f"找到目标设备: {self.port}")
                return True
        return False

    def open_port(self):
        """打开串口"""
        if self.port and not self.ser:
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                print(f"串口 {self.port} 已打开，波特率 {self.baudrate}")
                return True
            except serial.SerialException as e:
                print(f"串口错误: {e}")
        return False

    def close_port(self):
        """关闭串口"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")

    def send_frame(self, hex_data):
        """
        发送带帧头帧尾的数据帧
        :param hex_data: 16进制字符串，如 "01 A2 FF" 或 "01A2FF"
        """
        if not self.ser or not self.ser.is_open:
            print("错误：串口未打开")
            return False

        try:
            # 清理输入数据
            hex_str = hex_data.replace(' ', '')
            if not all(c in '0123456789ABCDEFabcdef' for c in hex_str):
                raise ValueError("包含非16进制字符")
            
            # 构造完整帧：HEADER + DATA + FOOTER
            data_bytes = bytes.fromhex(hex_str)
            frame = bytes([self.HEADER]) + data_bytes + bytes([self.FOOTER])
            
            [(self.ser.write(frame), time.sleep(0.2)) for _ in range(1)]
            print(f"发送帧: {frame.hex(' ').upper()}")
            return True
            
        except Exception as e:
            print(f"发送错误: {e}")
            return False

    def receive_frame(self):
        """
        接收并解析数据帧
        返回: 成功返回(True, 数据字节), 失败返回(False, None)
        """
        if not self.ser or not self.ser.is_open:
            return False, None

        # 读取所有可用数据
        data = self.ser.read(self.ser.in_waiting or 1)
        if not data:
            return False, None
        
        # 将新数据添加到缓冲区
        self.rx_buffer.extend(data)
        
        # 查找完整帧
        while len(self.rx_buffer) >= 2:
            # 查找帧头位置
            try:
                header_pos = self.rx_buffer.index(self.HEADER)
            except ValueError:
                # 没有找到帧头，清空无效数据
                self.rx_buffer.clear()
                return False, None
            
            # 移除帧头之前的所有数据
            if header_pos > 0:
                del self.rx_buffer[:header_pos]
                continue
                
            # 查找帧尾位置（从帧头后开始找）
            if len(self.rx_buffer) < 2:
                break
                
            try:
                footer_pos = self.rx_buffer[1:].index(self.FOOTER) + 1
            except ValueError:
                # 没有找到帧尾，等待更多数据
                break
                
            # 提取完整帧（HEADER + DATA + FOOTER）
            frame = self.rx_buffer[:footer_pos+1]
            del self.rx_buffer[:footer_pos+1]
            
            # 验证帧结构
            if len(frame) >= 3 and frame[0] == self.HEADER and frame[-1] == self.FOOTER:
                payload = frame[1:-1]  # 去除头尾
                self.last_rx_frame = payload.hex(' ').upper()
                print(f"收到帧: {frame.hex(' ').upper()} | 有效数据: {self.last_rx_frame}")
                return True, self.last_rx_frame
        
        return False, None

def main():
    comm = HexSerialCommunicator(baudrate=9600)
    target_vid = 0x1A86  # CH340 VID
    target_pid = 0x7523  # CH340 PID

    if comm.find_port(target_vid=target_vid, target_pid=target_pid):
        if comm.open_port():
            try:
                # num_good, num_bad, num_unripe = 12, 34, 56
                # data_to_send = f'0b{0:02x}{0:02x}{0:02x}FEFF0c{num_good:02x}{num_bad:02x}{num_unripe:02x}'
                # comm.send_frame(data_to_send)
                while True:
                    # # 用户交互
                    # cmd = input("\n1. 发送数据帧\n2. 手动接收检查\n3. 自动接收测试\nexit. 退出\n选择操作: ").lower()
                    
                    # if cmd == 'exit':
                    #     break
                    # elif cmd == '1':
                    #     hex_data = input("输入16进制数据 (如 '01 02 FF'): ")
                    #     comm.send_frame(hex_data)
                    # elif cmd == '2':
                    #     success, data = comm.receive_frame()
                    #     if success:
                    #         print(f"收到有效数据: {data.hex(' ').upper()}")
                    #     else:
                    #         print("未收到完整数据帧")
                    # elif cmd == '3':
                    #     print("自动接收测试中（5秒），按Ctrl+C中断...")
                    #     end_time = time.time() + 5
                    #     while time.time() < end_time:
                    #         comm.receive_frame()
                    #         time.sleep(0.01)
                    flag, data = comm.receive_frame()
                    if flag:
                        print('UART RT <-- ', data)
                    #     if data == '01 00 00 00':
                    #         print('=================')
                    #         comm.send_frame('01 23 45 56')
                    #         break
            finally:
                comm.close_port()
    else:
        print("未找到目标设备")

if __name__ == "__main__":
    main()
