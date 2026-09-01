# 对比检测结果
import time


def check_detection_stability(buffer, latest_n=5):
    """
    检查最新几帧的检测结果是否趋于稳定（只检测类别数量一致）
    
    参数:
        buffer: DetectionBuffer缓冲区实例
        latest_n: 要检查的最近帧数(默认5帧)
        
    返回:
        如果稳定: 返回最新一帧所有检测结果
        如果不稳定: 返回None, 并打印相关信息
    """
    # 获取全部检测结果
    latest_detections = buffer.get_all()
    
    # 如果没有足够的数据
    if len(latest_detections) < latest_n:
        print(f"警告: 只有{len(latest_detections)}个结果，不足{latest_n}个")
        return None
    
    # 按时间戳分组（假设同一时间戳的检测属于同一帧）
    frames = {}
    for det in latest_detections:
        if det['timestamp'] not in frames:
            frames[det['timestamp']] = []
        frames[det['timestamp']].append(det)
    
    # 获取按时间排序的帧列表（从旧到新）
    sorted_frames = sorted(frames.values(), key=lambda x: x[0]['timestamp'])[-latest_n:]
    
    # 检查每帧的类别数量是否一致
    class_counts = [len(set(det['class_name'] for det in frame)) for frame in sorted_frames]
    
    # 如果所有帧的类别数量相同
    if len(set(class_counts)) == 1:
        print(f"检测已稳定，最近{latest_n}帧每帧都检测到{class_counts[0]}类物体")
        return sorted_frames[-1]  # 返回最新一帧的所有检测结果
    else:
        # 打印不稳定的详细信息
        print("检测不稳定，最近各帧检测到的类别数量变化:")
        for i, (frame, count) in enumerate(zip(sorted_frames, class_counts)):
            frame_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(frame[0]['timestamp']))
            classes = ', '.join(str(set(det['class_name'] for det in frame)))
            print(f"第{i+1}帧({frame_time}): {count}类 - [{classes}]")
        
        return None


# def check_detection_stability(buffer, latest_n=5):
#     # 获取并分组全部检测结果
#     frames = {}
#     for det in buffer.get_all():
#         frames.setdefault(det['timestamp'], []).append(det)
    
#     # 按时间排序并取最近latest_n帧
#     sorted_frames = sorted(frames.values(), key=lambda x: x[0]['timestamp'])[-latest_n:]
    
#     if len(sorted_frames) < latest_n:
#         print(f"警告: 只有{len(sorted_frames)}个有效帧，不足{latest_n}个")
#         return None
    
#     # 检查类别数量一致性
#     class_counts = [len(set(det['class_name'] for det in frame)) for frame in sorted_frames]
    
#     if len(set(class_counts)) == 1:
#         print(f"检测已稳定，最近{latest_n}帧每帧都检测到{class_counts[0]}类物体")
#         return sorted_frames[-1]
#     else:
#         print("检测不稳定，最近各帧检测到的类别数量变化:")
#         for i, (frame, count) in enumerate(zip(sorted_frames, class_counts)):
#             frame_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(frame[0]['timestamp']))
#             classes = ', '.join(set(str(det['class_name']) for det in frame))
#             print(f"第{i+1}帧({frame_time}): {count}类 - [{classes}]")
#         return None

