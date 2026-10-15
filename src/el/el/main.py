# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Image
# from cv_bridge import CvBridge
# import time
# import numpy as np
# from std_msgs.msg import Bool 
# import traceback
# import random 
# from el.consts import CubeType, Cube, Action
# from el.modules.camera import RealSenseCamera
# from el.modules.detector import CubeDetector, CubeClassifier, CubeConverter
# from el.modules.planning import TetrisSolver
# from el.modules.routing import CoordBuilder
# from el.modules.xarm.wrapper import XArmAPI
# import cv2
# ARM_IP = "192.168.1.242"
# RUNNING_HEIGHT = 130
# HOME_POS = (343.2, -2.4, 546, 180, 0, 0)
# SPEED = 1000
# MVACC = 50000
# Radius=500

# class ImageProcessingNode(Node):
#     def __init__(self):
#         super().__init__('image_processing_node')
#         self.bridge = CvBridge()
#         self.subscription = self.create_subscription(
#             Image, 'camera/image_raw', self.image_callback, 10)
#         self.publisher = self.create_publisher(
#             Bool, 'image_received_signal', 10)
#         self.latest_image = None
#         self.receive_image = None
#         self.get_logger().info("Subscribed to 'camera/image_raw'")
#         self.image_received = False

#     def image_callback(self, msg):
#         try:
#             self.latest_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
#             if self.latest_image is not None:
#                 self.receive_image = self.latest_image
#                 self.image_received = True
#                 self.get_logger().info("节点接收到有效图片")
#                 msg_to_publish = Bool(); msg_to_publish.data = True
#                 self.publisher.publish(msg_to_publish)
#         except Exception as e:
#             self.get_logger().error(f'等待接收图片: {e}')

# def main(args=None):
#     rclpy.init(args=args)
#     image_processing_node = ImageProcessingNode()

#     arm = XArmAPI(ARM_IP); arm.clean_warn(); arm.clean_error()
#     arm.motion_enable(enable=True); arm.set_mode(0); arm.set_state(state=0)
#     arm.set_cgpio_digital(0, 1); time.sleep(0.5)
#         # 规划与识别相关模块
#     detector = CubeDetector()
#     classifier = CubeClassifier()
#     converter = CubeConverter()
#     builder = CoordBuilder()
#     arm.set_position(*HOME_POS, radius=Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)
#     # time.sleep(3)
#     confirm_mode = False
#     final_frame = None

#     while rclpy.ok():
#         rclpy.spin_once(image_processing_node, timeout_sec=0.01)

#         if image_processing_node.latest_image is None:
#             continue

#         if not confirm_mode:
#             frame = image_processing_node.latest_image.copy()

#             result = detector.fine_cubes(frame)
#             cubes = classifier.recognize_cubes(result)
#             cubes = converter.convert(cubes)
#             for cube in cubes:
#                 if cube.category == CubeType.UNKNOWN:
#                     continue
#                 box = cv2.boxPoints((cube.vertice, (int(cube.width), int(cube.height)), cube.angle))
#                 box = box.astype(int)
#                 cv2.drawContours(frame, [box], -1, (255, 255, 255), 1)
#                 cv2.drawMarker(frame, (int(cube.catch_point[0]), int(cube.catch_point[1])), (0, 255, 0),
#                             markerType=cv2.MARKER_DIAMOND, markerSize=10)
#                 cv2.putText(frame, f"{cube.category}", (int(cube.catch_point[0]), int(cube.catch_point[1]) - 10),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

#             cv2.imshow("frame", frame)
#             key = cv2.waitKey(1) & 0xFF

#             if key in [ord('q'), ord('Q'), ord(' ')]:
#                 final_frame = frame.copy()
#                 confirm_mode = True
#                 image_processing_node.get_logger().info("按 Y 确认，按 N 重新采集")
#         else:
#             cv2.imshow("frame", final_frame)
#             key = cv2.waitKey(1) & 0xFF
#             if key in [ord('y'), ord('Y')]:
#                 image_processing_node.receive_image = final_frame.copy()
#                 image_processing_node.image_received = True
#                 cv2.destroyWindow("frame")
#                 break
#             elif key in [ord('n'), ord('N')]:
#                 confirm_mode = False
#                 image_processing_node.get_logger().info("重新采集中...")

#     # image_processing_node.receive_image = None
#     try:
#         # while rclpy.ok() and not image_processing_node.image_received:
#         #     rclpy.spin_once(image_processing_node)
        
#         if image_processing_node.receive_image is None:
#             print("未能接收到图像"); return
        
#         result = CubeDetector().fine_cubes(image_processing_node.receive_image)
#         cubes_from_camera = CubeClassifier().recognize_cubes(result)
#         cubes_from_camera = CubeConverter().convert(cubes_from_camera)
        
#         print("正在创建求解器...")
#         #beam_width为搜索支数
#         solver = TetrisSolver(10, beam_width=50) 
        
#         # 定义抓取顺序
#         placement_order = [
            
#             CubeType.T,
#             CubeType.L,
#             CubeType.J,
#             CubeType.S,
#             CubeType.Z,
#             CubeType.O,
#             CubeType.I,
#             ]
#         solver.set_placement_order(placement_order)

#         print("正在规划摆-放策略...")
#         solution_cubes = solver.solve(cubes_from_camera)

#         if solution_cubes:
#             print(f"\n规划成功，共找到 {len(solution_cubes)} 个方块的摆放位置。")
            
#             if solver.solution: 
#                 final_board_for_display = np.zeros((solver.height, solver.column), dtype=np.int8)
#                 for action in solver.solution:

#                     final_board_for_display = solver.place(
#                         row=action.row, 
#                         col=action.col, 
#                         category=action.category, 
#                         rotation=action.rotation, 
#                         board=final_board_for_display
#                     )
                
#                 solver.print_board(final_board_for_display, len(solver.solution), "Final Layout")

#             print("\n正在计算机械臂坐标...")
            
#             try:

#                 final_cubes_with_coords = CoordBuilder().compute(solution_cubes)

#                 if not final_cubes_with_coords:
#                     print("警告: CoordBuilder 未能返回任何有效的机械臂坐标！")

#                 print("开始执行机械臂动作...")
#                 for cube in final_cubes_with_coords:
#                     start_pos = cube.arm_from.copy(); start_x, start_y, start_z = start_pos
#                     end_pos = cube.arm_to.copy(); end_x, end_y, end_z = end_pos
#                     rot = cube.arm_rot; rot1 = -rot / 2; rot2 = rot / 2
#                     print(cube)
#                     arm.set_position(start_x, start_y, RUNNING_HEIGHT, 180, 0, rot1, Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)
#                     arm.set_cgpio_digital(0, 1); time.sleep(0.2)
#                     arm.set_position(start_x, start_y, z=start_z, yaw=rot1, speed=SPEED, mvacc=MVACC, wait=True); time.sleep(0.2)
#                     arm.set_position(z=RUNNING_HEIGHT, yaw=rot1 + (rot2 / 10), speed=SPEED, mvacc=MVACC, wait=True)
#                     arm.set_position(end_x, end_y, RUNNING_HEIGHT, 180, 0, rot2, radius=Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2); time.sleep(0.2)
#                     arm.set_position(end_x, end_y, z=end_z, yaw=rot2, speed=SPEED, mvacc=MVACC, wait=True);time.sleep(0.2)
#                     arm.set_cgpio_digital(0, 0); time.sleep(0.2)
#                     arm.set_position(z=RUNNING_HEIGHT, yaw=rot2, radius=Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)
#                     print()
            
#             except Exception as e:
#                 print("\n" + "="*20 + "\n!! 在坐标转换或机械臂执行阶段发生严重错误 !!\n" + "="*20)
#                 print(f"错误类型: {type(e).__name__}\n错误信息: {e}")
#                 print("--- 错误追溯 (Traceback) ---"); traceback.print_exc(); print("="*20 + "\n")
                
#         else:
#             print("\n规划失败，求解器未返回任何可行的摆放方案。")
            
#         arm.set_position(*HOME_POS, radius=Radius,speed=SPEED, mvacc=MVACC, wait=True,motion_type=2)

#     except KeyboardInterrupt:
#         pass
#     finally:
#         image_processing_node.get_logger().info('Shutting down...')
#         image_processing_node.destroy_node()
#         rclpy.shutdown()

# if __name__ == '__main__':
#     t0 = time.time()
#     main()
#     time_seconds = time.time() - t0
#     print(f"任务完成，用时 {time_seconds:.2f} 秒, 合 {time_seconds // 60:.0f} 分 {time_seconds % 60:.0f} 秒")
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import time
import numpy as np
from std_msgs.msg import Bool 
import traceback
from el.consts import CubeType
from el.modules.camera import RealSenseCamera
from el.modules.detector import CubeDetector, CubeClassifier, CubeConverter
from el.modules.planning import TetrisSolver
from el.modules.routing import CoordBuilder
from el.modules.xarm.wrapper import XArmAPI
import cv2

ARM_IP = "192.168.1.241"
RUNNING_HEIGHT = 130
# HOME_POS = (343.2, -2.4, 546, 180, 0, 0)
HOME_POS = (393.7,-90.8,608,180,0,0)

# SPEED = 1000
# MVACC = 50000
SPEED = 1000
MVACC = 20000
Radius=500


class ImageProcessingNode(Node):
    def __init__(self):
        super().__init__('image_processing_node')
        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Image, 'camera/image_raw', self.image_callback, 10)
        self.publisher = self.create_publisher(
            Bool, 'image_received_signal', 10)
        self.latest_image = None
        self.receive_image = None
        self.get_logger().info("Subscribed to 'camera/image_raw'")
        self.image_received = False

    def image_callback(self, msg):
        try:
            self.latest_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            if self.latest_image is not None:
                self.get_logger().debug("收到一帧图像")
        except Exception as e:
            self.get_logger().error(f'等待接收图片: {e}')


def main(args=None):
    rclpy.init(args=args)
    image_processing_node = ImageProcessingNode()

    # 初始化机械臂
    arm = XArmAPI(ARM_IP)
    arm.clean_warn()
    arm.clean_error()
    arm.motion_enable(enable=True)
    arm.set_mode(0)
    arm.set_state(state=0)
    arm.set_cgpio_digital(0, 1)
    time.sleep(0.5)

    # 规划与识别相关模块
    detector = CubeDetector()
    classifier = CubeClassifier()
    converter = CubeConverter()
    builder = CoordBuilder()
    solver = TetrisSolver(10, beam_width=400)

    arm.set_position(*HOME_POS, radius=Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)

    # # ============= 图像采集与确认 =============
    confirm_mode = False
    final_frame = None

    while rclpy.ok():
        rclpy.spin_once(image_processing_node, timeout_sec=0.01)

        if image_processing_node.latest_image is None:
            continue

        if not confirm_mode:
            frame = image_processing_node.latest_image.copy()

            result = detector.fine_cubes(frame)
            cubes = classifier.recognize_cubes(result)
            cubes = converter.convert(cubes)

            for cube in cubes:
                if cube.category == CubeType.UNKNOWN:
                    continue
                box = cv2.boxPoints((cube.vertice, (int(cube.width), int(cube.height)), cube.angle))
                box = box.astype(int)
                cv2.drawContours(frame, [box], -1, (255, 255, 255), 1)
                cv2.drawMarker(frame, (int(cube.catch_point[0]), int(cube.catch_point[1])), (0, 255, 0),
                            markerType=cv2.MARKER_DIAMOND, markerSize=10)
                cv2.putText(frame, f"{cube.category}", (int(cube.catch_point[0]), int(cube.catch_point[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            cv2.imshow("frame", frame)
            key = cv2.waitKey(1) & 0xFF

            if key in [ord('q'), ord('Q'), ord(' ')]:
                final_frame = frame.copy()
                confirm_mode = True
                image_processing_node.get_logger().info("按 Y 确认，按 N 重新采集")
        else:
            cv2.imshow("frame", final_frame)
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('y'), ord('Y')]:
                image_processing_node.receive_image = final_frame.copy()
                image_processing_node.image_received = True
                cv2.destroyWindow("frame")
                break
            elif key in [ord('n'), ord('N')]:
                confirm_mode = False
                image_processing_node.get_logger().info("重新采集中...")

    # ============= 图像处理与机械臂执行 =============
    try:
        if image_processing_node.receive_image is None:
            print("未能接收到图像")
            return

        result = detector.fine_cubes(image_processing_node.receive_image)
        cubes_from_camera = classifier.recognize_cubes(result)
        cubes_from_camera = converter.convert(cubes_from_camera)

        print("正在创建求解器...")
        placement_order = [
                           CubeType.T,
                           CubeType.L, 
                           CubeType.J,
                           CubeType.S,
                           CubeType.Z, 
                           CubeType.O, 
                           CubeType.I,
                           ]
        solver.set_placement_order(placement_order)

        print("正在规划摆放策略...")
        solution_cubes = solver.solve(cubes_from_camera)

        if solution_cubes:
            print(f"\n规划成功，共找到 {len(solution_cubes)} 个方块的摆放位置。")

            final_cubes_with_coords = builder.compute(solution_cubes)
            if not final_cubes_with_coords:
                print("警告: CoordBuilder 未能返回任何有效的机械臂坐标！")

            print("开始执行机械臂动作...")
            for cube in final_cubes_with_coords:
                start_pos = cube.arm_from.copy()
                start_x, start_y, start_z = start_pos
                end_pos = cube.arm_to.copy()
                end_x, end_y, end_z = end_pos
                rot = cube.arm_rot
                rot1 = -rot / 2
                rot2 = rot / 2
                print(cube)

                arm.set_position(start_x, start_y, RUNNING_HEIGHT, 180, 0, rot1,
                                 Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)
                arm.set_cgpio_digital(0, 0); time.sleep(0.2)
                arm.set_position(start_x, start_y, z=start_z, yaw=rot1, speed=SPEED, mvacc=MVACC, wait=True)
                time.sleep(0.2)
                arm.set_position(z=RUNNING_HEIGHT, yaw=rot1 + (rot2 / 10),
                                 speed=SPEED, mvacc=MVACC, wait=True)
                arm.set_position(end_x, end_y, RUNNING_HEIGHT, 180, 0, rot2,
                                 radius=Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)
                time.sleep(0.2)
                arm.set_position(end_x, end_y, z=end_z, yaw=rot2,
                                 speed=SPEED, mvacc=MVACC, wait=True)
                time.sleep(0.2)
                arm.set_cgpio_digital(0, 1); time.sleep(0.2)
                arm.set_position(z=RUNNING_HEIGHT, yaw=rot2,
                                 radius=Radius, speed=SPEED, mvacc=MVACC, wait=True, motion_type=2)
                print()

        else:
            print("\n规划失败，求解器未返回任何可行的摆放方案。")

        arm.set_position(*HOME_POS, radius=Radius, speed=SPEED,
                         mvacc=MVACC, wait=True, motion_type=2)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("\n" + "="*20 + "\n!! 在坐标转换或机械臂执行阶段发生严重错误 !!\n" + "="*20)
        print(f"错误类型: {type(e).__name__}\n错误信息: {e}")
        print("--- 错误追溯 (Traceback) ---")
        traceback.print_exc()
        print("="*20 + "\n")
    finally:
        image_processing_node.get_logger().info('Shutting down...')
        image_processing_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    t0 = time.time()
    main()
    time_seconds = time.time() - t0
    print(f"任务完成，用时 {time_seconds:.2f} 秒, 合 {time_seconds // 60:.0f} 分 {time_seconds % 60:.0f} 秒")
