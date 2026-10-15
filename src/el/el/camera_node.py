#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import pyrealsense2 as rs
import numpy as np
from el.modules.camera import RealSenseCamera
# class RealSenseCamera:
#     def __init__(self):
#         self.rs_pipeline = rs.pipeline()
#         self.camera_width = 1280
#         self.camera_height = 720
#         self.camera_fps = 30

#     def init(self):
#         config = rs.config()
#         config.enable_stream(rs.stream.color, self.camera_width, self.camera_height, rs.format.bgr8, self.camera_fps)
#         self.rs_pipeline.start(config)

#     def get_frame(self):
#         frames = self.rs_pipeline.wait_for_frames()
#         color_frame = frames.get_color_frame()
#         return np.asanyarray(color_frame.get_data())

#     def stop(self):
#         self.rs_pipeline.stop()

class RealSenseCameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, 'camera/image_raw', 10)
        self.camera = RealSenseCamera()
        self.camera.init()
        self.timer = self.create_timer(1.0 / 30, self.timer_callback)  # 30 Hz
        # 创建订阅者来接收关闭指令
        self.shutdown_subscription = self.create_subscription(
            Bool,
            'image_received_signal',
            self.shutdown_callback,
            10
        )
        self.shutdown_signal_received = False

    def timer_callback(self):
        if self.shutdown_signal_received:
            return
        frame = self.camera.get_frame()
        ros_image = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self.publisher.publish(ros_image)

    def shutdown_callback(self, msg):
        if msg.data:
            self.shutdown_signal_received = True

def main(args=None):
    rclpy.init(args=args)
    node = RealSenseCameraNode()
    try:
        while rclpy.ok():
            rclpy.spin_once(node)
            if node.shutdown_signal_received:  # 你可以根据实际条件设置此标志
                node.get_logger().info('关闭相机节点')
                node.destroy_node()
                rclpy.shutdown()
                break
    except KeyboardInterrupt:
        pass
    finally:
        if not node.shutdown_signal_received:
            node.get_logger().info('Shutting down...')
            node.stop_camera()
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()
