import logging
from typing import List
import sys
from copy import deepcopy

import pyrealsense2 as rs
import numpy as np
import cv2
from typing import Tuple
try:
    sys.path.append(r"../")
    from el.consts import Cube, CubeType
except ImportError:
    print("ImportError: Cannot import Cube from types.py")
    print("Please make sure the path is correct")
    sys.exit(1)


class CubeDetector:
    def __init__(self):
        self.logger = logging.getLogger("Tetris.CubeDetector")
        self.logger.setLevel("INFO")

        # CV parameters
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.filter_d = 9
        self.filter_sigma_color = 75
        self.filter_sigma_space = 75
        self.abs_alpha = 3.
        self.abs_beta = 25

    def _preprocess(self, frame):
        # 使用双边滤波进行平滑处理
        frame = cv2.bilateralFilter(frame, self.filter_d, self.filter_sigma_color, self.filter_sigma_space)

        # 调整对比度和亮度
        adjusted_frame = cv2.convertScaleAbs(frame, alpha=self.abs_alpha, beta=self.abs_beta)

        return adjusted_frame

    def fine_cubes(self, frame):
        image = frame.copy()
        height, width = image.shape[:2]
        # image_round = 2 * (width + height)
        image_pixel = width * height

        # 预处理
        image = self._preprocess(image)

        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 二值化
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # 腐蚀
        erosion = cv2.erode(binary, self.kernel, iterations=2)

        # 轮廓查找
        contours, _ = cv2.findContours(erosion, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) == 0:
            return []
        areas = np.array([cv2.contourArea(cnt) for cnt in contours])
        contours_array = np.array(contours, dtype=object)
        filtered_contours = contours_array[(0.0025 * image_pixel < areas) & (areas < 0.0075 * image_pixel)].tolist()
        if len(filtered_contours) == 0:
            return []
        filtered_contours = list(filtered_contours)
        # 生成结果列表
        results: List[Cube] = []
        for i, contour in enumerate(filtered_contours):
            hull = cv2.convexHull(contour)
            rect = cv2.minAreaRect(hull)
            pos = rect[0]
            w, h = rect[1]
            r = rect[2]
            if w < h:
                w, h = h, w
                r += 90

            # 生成掩膜
            bg = np.zeros((int(h), int(w), 1), dtype=np.uint8)
            matrix = cv2.getRotationMatrix2D(pos, r, 1)
            rotated_contour = cv2.transform(np.array(contour), matrix)
            bg = cv2.fillPoly(bg, [rotated_contour], (255,),
                              offset=(-int(pos[0] - w / 2 + 1),
                                      -int(pos[1] - h / 2 + 1)))

    # 1. 先创建一个空的、符合新定义的 Cube 对象
            new_cube = Cube()
            
            # 2. 然后，再逐个为它的属性进行赋值
            new_cube.contour = contour
            new_cube.hull = hull
            new_cube.vertice = pos
            new_cube.width = w
            new_cube.height = h
            new_cube.angle = r
            new_cube.mask = bg
            
            # 3. 将这个填充好数据的对象，添加到结果列表中
            results.append(new_cube)

        return results


class CubeClassifier:
    def __init__(self):
        self.debug = True

        self.logger = logging.getLogger("Tetris.CubeClassifier")
        self.logger.setLevel("INFO")
        self.rs_pipeline: rs.pipeline = rs.pipeline()

        self.feature_map = dict(
            {
                # J
                # "100"
                # "111": CubeType.J,
                "111"
                "001": CubeType.J,
                # L
                "111"
                "100": CubeType.L,
                # "001"
                # "111": CubeType.L,
                # S
                "011"
                "110": CubeType.S,
                # T
                "111"
                "010": CubeType.T,
                # "010"
                # "111": CubeType.T,
                # Z
                "110"
                "011": CubeType.Z,
            }
        )

    def _classify_by_shape(self, cube: Cube) -> Tuple[CubeType, int]:
        if cube.mask is None:
            return CubeType.UNKNOWN, 0
        rotation = 0  # 逆时针旋转角度
        mask = cube.mask.copy()
        if cube.width < cube.height:
            self.logger.warning("Rotating mask")
            rotation += 90
            mask = np.rot90(mask)

        def _get_category(_mask):
            # 将掩膜平均分割为 6 份（2 行 3 列）
            h_split = np.array_split(_mask, 2, axis=0)  # 按高度分割为 2 份
            parts = [np.array_split(part, 3, axis=1) for part in h_split]  # 每份按宽度分割为 3 份
            # 生成热图
            hot_map = ''
            for i in range(2):
                for j in range(3):
                    if np.sum(parts[i][j] == 255) > 0.6 * parts[i][j].size:
                        hot_map += '1'
                    else:
                        hot_map += '0'
            cube.hot_map = hot_map
            return self.feature_map.get(hot_map, CubeType.UNKNOWN)

        for rotation in [0, 180]:
            category = _get_category(mask)
            if category != CubeType.UNKNOWN:
                return category, rotation
            mask = np.rot90(mask, 2)

        return CubeType.UNKNOWN, 0

    def recognize_cubes(self, cubes: List[Cube]) -> List[Cube]:
        cubes = deepcopy(cubes)
        for cube in cubes:
            h, w = cube.height, cube.width
            aspect_ratio = max(h, w) / min(h, w)
            if aspect_ratio > 2:
                cube.category = CubeType.I
            elif aspect_ratio > 1.2:
                category, rotation = self._classify_by_shape(cube)
                cube.category = category
                cube.angle += rotation
            elif aspect_ratio > 0.8:
                cube.category = CubeType.O
            else:
                cube.category = CubeType.UNKNOWN

        return cubes


class CubeConverter:
    def __init__(self):
        self.logger = logging.getLogger("Tetris.CubeConverter")
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

    def convert(self, cubes: List[Cube]) -> List[Cube]:
        cubes = deepcopy(cubes)
        for cube in cubes:
            # 过滤未识别的方块
            if cube.category == CubeType.UNKNOWN:
                continue

            rotate = cube.angle

            rotate = rotate - 360 if rotate > 180 else rotate

            if cube.category in [CubeType.Z, CubeType.S, CubeType.I]:
                # 将角度转换到 [-90, 90] 范围内
                rotate += -180 if rotate > 90 else 180 if rotate < -90 else 0
            elif cube.category == CubeType.O:
                # 将角度转换到 [-45, 45] 范围内
                rotate += -90 if rotate > 45 else 90 if rotate < -45 else 0

            # 保存抓取角度
            cube.catch_angle = rotate

            # 获取抓取点像素坐标
            pos = self.position_map.get(cube.category, None)
            if pos is None:
                continue
            target_x = cube.vertice[0] - cube.width / 2 + cube.width * pos[1]
            target_y = cube.vertice[1] - cube.height / 2 + cube.height * pos[0]
            target_point = np.array([target_x, target_y, 1])
            rotation_matrix = cv2.getRotationMatrix2D(cube.vertice, -cube.angle, 1.)
            rotation_matrix = np.vstack([rotation_matrix, [0, 0, 1]])
            cube.catch_point = np.dot(rotation_matrix, target_point)[:2]

        return cubes


def main():
    pass


if __name__ == "__main__":
    main()
