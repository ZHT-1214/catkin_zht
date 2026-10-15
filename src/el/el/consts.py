import enum
from typing import Tuple, Optional
import numpy as np


class CubeType(enum.Enum):
    O, I, T, L, J, S, Z, UNKNOWN = 1, 2, 3, 4, 5, 6, 7, 8

    def __str__(self):
        return self.name

class Cube:
    def __init__(self):

        self.category: CubeType = CubeType.UNKNOWN
        
        self.broad_point: Optional[Tuple[float, float]] = None
        self.broad_angle: Optional[float] = 0.0

        self.arm_from: Optional[Tuple[float, float, float]] = None
        self.arm_to: Optional[Tuple[float, float, float]] = None
        self.arm_rot: Optional[float] = 0.0


    def __str__(self):
        return (f"Cube(category={self.category.name}, "
                f"board_pos={self.broad_point}, board_angle={self.broad_angle}, "
                f"arm_from={self.arm_from}, arm_to={self.arm_to}, arm_rot={self.arm_rot})")

class Action:
    def __init__(self, category: CubeType, row: int, col: int, rotation: int):
        self.category = category
        self.row = row     
        self.col = col     
        self.rotation = rotation

    def __str__(self):
        return f"Action(type={self.category.name}, pos=({self.row},{self.col}), rot={self.rotation})"


def poly2d(xy, *coeffs) -> np.ndarray:
    x, y = xy
    degree = 2
    idx = 0
    z = np.zeros_like(x)
    for i in range(degree + 1):
        for j in range(degree + 1 - i):
            z += coeffs[idx] * x**i * y**j
            idx += 1
    return z
