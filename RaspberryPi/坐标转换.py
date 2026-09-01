# 转换像素坐标到机械臂(平面)坐标

def pixel_to_arm(pixel_x, pixel_y,
                pixel_init_x=494, pixel_init_y=129,   # 参考点像素坐标
                arm_init_x=213, arm_init_y=-40,       # 参考点对应的机械臂坐标
                x_scale=0.2324, y_scale=0.1681,         # 缩放比例
                x_direction=-1, y_direction=1,         # 坐标轴方向
                swap_axes=False):                      # 交换轴
    """
    将像素坐标转换为机械臂坐标（支持独立缩放、轴交换和方向调整）
    
    参数:
        pixel_x, pixel_y: 要转换的像素坐标
        pixel_init_x, pixel_init_y: 参考点在像素坐标系中的坐标
        arm_init_x, arm_init_y: 参考点在机械臂坐标系中的坐标
        x_direction: x轴方向(1或-1)
        y_direction: y轴方向(1或-1)
        swap_axes: 是否交换x和y轴(True/False)
    
    返回:
        (arm_x, arm_y): 转换后的机械臂坐标
    """
    # 参数检查
    # print(pixel_x, pixel_y, pixel_init_x, pixel_init_y, arm_init_x, arm_init_y, x_scale, y_scale, x_direction, y_direction, swap_axes)
    
    # 计算相对于参考点的偏移量
    delta_pixel_x = pixel_x - pixel_init_x
    delta_pixel_y = pixel_y - pixel_init_y
    
    # 应用缩放和方向
    if swap_axes:
        # 交换x和y轴
        delta_arm_x = delta_pixel_y * x_scale * x_direction
        delta_arm_y = delta_pixel_x * y_scale * y_direction
    else:
        # 不交换轴
        delta_arm_x = delta_pixel_x * x_scale * x_direction
        delta_arm_y = delta_pixel_y * y_scale * y_direction
    
    # 计算机械臂绝对坐标
    arm_x = arm_init_x + delta_arm_x
    arm_y = arm_init_y + delta_arm_y
    
    return arm_x, arm_y


if __name__ == "__main__":
    pass

    print(pixel_to_arm(494, 129))
    print(pixel_to_arm(808, 593))

    print(pixel_to_arm(649, 366))
    