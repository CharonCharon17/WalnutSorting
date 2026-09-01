# 机械臂使用CP210X串口，通过pydobot库控制机械臂运动
# .pose() 回读机械臂状态
# .move_to() 控制机械臂运动，参数为(x, y, z, r)，xyz为目标坐标，r为吸盘转动角度（可直接使用回读参数）
# .suck() 吸盘控制，True或False

# pip install pyserial pydobot


# 导入库
from serial.tools import list_ports
import time
import pydobot




# 前往并抓取目标
def get_ht(device, x, y, z=-25, t=5):
    device.move_to(240, 0, 140, r=0, wait=True)     # 先到初始位置
    device.move_to(x, y, 0, r=0, wait=True)     # 移动到目标上方
    device.move_to(x, y, z, r=0, wait=True)     # 放下爪子
    device.suck(True)   # 打开气泵
    time.sleep(t)       # 等待爪子和上
    device.move_to(240, 0, 80, r=0, wait=True)     # 稍微抬起

# 放到左边
def put_left(device):
    device.move_to(160, -150, 100, r=0, wait=True)   # 先移到中间位置
    device.move_to(0, -200, 100, r=0, wait=True)     # 移到收集处上方
    device.move_to(0, -200, 0, r=0, wait=True)      # 放下
    device.suck(False)  # 关闭气泵
    time.sleep(0.5)     # 等待爪子张开
    device.move_to(0, -200, 100, r=0, wait=True)
    device.move_to(160, -150, 100, r=0, wait=True)   # 回到中间位置
    device.move_to(240, 0, 140, r=0, wait=True)     # 回到初始位置

# 放到右边
def put_right(device):
    device.move_to(160, 150, 100, r=0, wait=True)    # 先移到中间位置
    device.move_to(0, 200, 100, r=0, wait=True)      # 移到上方
    device.move_to(0, 200, 0, r=0, wait=True)       # 放下
    device.suck(False)  # 关闭气泵
    time.sleep(0.5)     # 等待爪子张开
    device.move_to(0, 200, 100, r=0, wait=True)
    device.move_to(160, 150, 100, r=0, wait=True)    # 回到中间位置
    device.move_to(240, 0, 140, r=0, wait=True)     # 回到初始位置



if __name__ == '__main__':
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

    from 坐标转换 import pixel_to_arm
    xx, yy = pixel_to_arm(603, 295)
    print(xx, yy)
    get_ht(device, x=xx, y=yy)
    put_left(device)
    get_ht(device, x=xx, y=yy)
    put_right(device)

    # 关闭控制器
    device.close()
