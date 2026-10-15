import logging
from copy import deepcopy
from typing import List, Tuple
from typing import Union
import cv2
import numpy as np

from el.consts import CubeType, Cube


class CoordBuilder:
    def __init__(self):
        self.logger = logging.getLogger("Tetris.CoordBuilder")
        self.logger.setLevel("INFO")

        # (垂直, 水平)位置映射
        self.position_map: dict[CubeType, tuple[float, float]] = {
            CubeType.I: (1 / 2, 1 / 2),
            CubeType.J: (1 / 4, 5 / 6),
            CubeType.L: (1 / 4, 1 / 6),
            CubeType.O: (1 / 2, 1 / 2),
            CubeType.S: (1 / 2, 1 / 2),
            CubeType.T: (1 / 4, 1 / 2),
            CubeType.Z: (1 / 2, 1 / 2),
        }

        # 相机->机械臂 透视变换矩阵
        self.camera_perspective_matrix = (
            np.array(
                # [[-2.26935651e-02 ,-5.59732403e-01, -7.01586028e-03],
                # [-5.63255768e-01 , 2.29278832e-02 ,-1.66140409e-02],
                # [ 5.97550732e+02 , 3.78641415e+02 , 8.89571507e+01],]
                # [[-1.80394951e-02, -5.64491979e-01 ,-5.41323691e-03],
                # [-5.64222176e-01 , 2.07732634e-02 ,-1.52097716e-02],
                # [ 5.97085119e+02,  3.85810176e+02 , 8.39388967e+01],]

                # [[-1.98601324e-02 ,-5.67440804e-01 ,-5.71690892e-03],
                # [-5.61494119e-01 , 2.22862873e-02 ,-1.54755233e-02],
                # [ 5.98781826e+02 , 3.85177199e+02 , 8.40461322e+01],]

                [[-7.32460368e-03, -6.39587362e-01 , 1.29204956e-03],
 [-6.38495868e-01 , 5.68792972e-03 ,-1.13123657e-02],
 [ 6.71949527e+02  ,3.54297374e+02 , 9.01853537e+01]]
            )
        )

        # 棋盘->机械臂 透视变换矩阵
        self.broad_perspective_matrix = (
            np.array(
                # [[-1.77678680e-01 , 1.99780256e+01 , 1.05879283e-14],
                # [ 2.00457330e+01 , 1.09360182e-01 , 0.00000000e+00],
                # [ 1.93732146e+02 , 3.08503637e+02 , 9.00000000e+01],]
                [[-5.68578684e-02 , 2.01793965e+01  ,9.91730883e-15],
                [ 2.01027406e+01  ,1.27005455e-01 ,-3.55271368e-15],
                [ 2.19058550e+02  ,2.69905260e+02  ,9.10000000e+01]]
            )
        )

        self.catch_coeffs = np.array(
            [9.81226746e+01,  2.03531762e-02,  1.86649910e-05,
             -2.75464548e-02, -6.07496015e-06, 5.37042629e-05]
        )
        self.place_coeffs = np.array(
            [110, 0., 0.,
             0.,  0., 0.]
        )

        self.broad_pixel_angle_offset = 180

        self.distance_limit = 700
        self.height_limit = 92.5

    @staticmethod
    def transform_point(point: Tuple[float, float], matrix: np.ndarray) -> np.ndarray:
        # Convert the point to a numpy array and reshape it to (1, 1, 2) for cv2.perspectiveTransform
        point_array = np.array([[point]], dtype=np.float32)

        # Apply the perspective transform
        transformed_point_array = cv2.perspectiveTransform(point_array, matrix)

        # Extract the transformed point from the result
        transformed_point = transformed_point_array[0][0]

        return transformed_point

    def legality_check(self, arm_point:Union[Tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray]) -> bool:
        x, y, _ = arm_point
        distance = np.sqrt(x ** 2 + y ** 2)
        if distance > self.distance_limit:
            return False
        return True

    def compute(self, cubes: List[Cube]) -> List[Cube]:
        cubes = deepcopy(cubes)
        new_cubes = []
        for cube in cubes:
            # 过滤未处理的方块
            if cube.category == CubeType.UNKNOWN or cube.broad_point is None or cube.catch_angle is None:
                continue

            rotate = cube.broad_angle + cube.catch_angle + self.broad_pixel_angle_offset

            rotate = (rotate + 180) % 360 - 180

            if cube.category in [CubeType.Z, CubeType.S, CubeType.I]:
                rotate = (rotate + 90) % 180 - 90
            elif cube.category == CubeType.O:
                rotate = (rotate + 45) % 90 - 45

            # 更新机械臂旋转角度
            cube.arm_rot = rotate

            # 计算始坐标(从像素坐标)
            matrix = self.camera_perspective_matrix
            pos = cube.catch_point
            
            pos = np.array([pos[0], pos[1], 1])
            coord = pos @ matrix
            coord[2] = np.clip(coord[2], self.height_limit, coord[2])
            if not self.legality_check(coord):
                self.logger.warning(f"对于位于像素位置 {pos} 的方块 {cube.category} 所转换获得的机械臂抓取坐标 {coord} "
                                    f"位于机械臂规划范围/安全范围之外,已跳过")
                continue
            cube.arm_from = coord

            # 计算末坐标(从棋盘坐标)
            matrix = self.broad_perspective_matrix
            pos = cube.broad_point
            pos = np.array([pos[0], pos[1], 1])
            coord = pos @ matrix
            coord[2] = np.clip(coord[2], self.height_limit, coord[2] - 0.25)
            if not self.legality_check(coord):
                self.logger.warning(f"对于位于棋盘位置 {pos} 的方块 {cube.category} 所转换获得的机械臂放置坐标 {coord} "
                                    f"位于机械臂规划范围/安全范围之外,已跳过")
                continue
            cube.arm_to = coord
            new_cubes.append(cube)

        return new_cubes
