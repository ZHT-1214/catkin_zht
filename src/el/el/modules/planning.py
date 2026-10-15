import logging
import time
import random
import numpy as np
import numba as nb
from copy import deepcopy
from typing import Dict, Tuple, List
from el.consts import CubeType, Cube, Action

# 使用Numba加速关键函数
@nb.njit(nb.int8[:,:](nb.int8[:,:], nb.int8), cache=True)
def numba_rotate_mask(mask, rotations):
    """使用Numba优化的旋转函数"""
    for _ in range(rotations):
        mask = np.rot90(mask)
    return mask

@nb.njit(nb.int8(nb.int8[:,:], nb.int8[:,:], nb.int64), cache=True)
def numba_find_drop_row(board, mask, start_col):
    """使用Numba优化的下落位置查找函数"""
    mask_h, mask_w = mask.shape
    board_h, board_w = board.shape
    
    # 检查边界
    if start_col < 0 or start_col + mask_w > board_w:
        return -1
    
    # 查找最低位置
    for row in range(board_h - mask_h, -1, -1):
        valid = True
        for r in range(mask_h):
            for c in range(mask_w):
                if mask[r, c] == 1 and board[row + r, start_col + c] != 0:
                    valid = False
                    break
            if not valid:
                break
        if valid:
            return row
    return -1

@nb.njit(nb.float64(nb.int8[:,:], nb.int64, nb.int64), cache=True)
def numba_calculate_score(board, height, width):
    """使用Numba优化的评分函数"""
    if np.count_nonzero(board) == 0:
        return 0.0
    
    # 权重系数
    w_lines = 500.0
    w_holes = -800.0
    w_height = -100.0
    w_bumpiness = -150.0
    
    # 计算列高度
    col_heights = np.zeros(width, dtype=np.int64)
    for c in range(width):
        for r in range(height):
            if board[r, c] != 0:
                col_heights[c] = height - r
                break
    
    # 计算消除的行数
    lines_cleared = 0
    for r in range(height):
        full = True
        for c in range(width):
            if board[r, c] == 0:
                full = False
                break
        if full:
            lines_cleared += 1
    
    # 计算空洞
    holes = 0
    for c in range(width):
        if col_heights[c] > 0:
            start_row = height - col_heights[c]
            for r in range(start_row, height):
                if board[r, c] == 0:
                    holes += 1
    
    # 计算凹凸度
    bumpiness = 0
    for c in range(width - 1):
        bumpiness += abs(col_heights[c] - col_heights[c + 1])
    
    # 计算总分
    return (w_lines * lines_cleared +
            w_holes * holes +
            w_height * np.sum(col_heights) +
            w_bumpiness * bumpiness)

class TetrisSolver:
    def __init__(self, column: int, height: int = 14, beam_width: int = 10):
        self.column = column
        self.height = height
        self.beam_width = beam_width
        
        # 方块定义
        self.mask_map: Dict[CubeType, np.ndarray] = {
            CubeType.O: np.array(((1, 1), (1, 1)), dtype=np.int8),
            CubeType.I: np.array(((1, 1, 1, 1),), dtype=np.int8),
            CubeType.T: np.array(((1, 1, 1), (0, 1, 0)), dtype=np.int8),
            CubeType.L: np.array(((1, 1, 1), (1, 0, 0)), dtype=np.int8),
            CubeType.J: np.array(((1, 1, 1), (0, 0, 1)), dtype=np.int8),
            CubeType.S: np.array(((0, 1, 1), (1, 1, 0)), dtype=np.int8),
            CubeType.Z: np.array(((1, 1, 0), (0, 1, 1)), dtype=np.int8),
        }
        
        self.id_map: Dict[CubeType, int] = {
            CubeType.O: 1, CubeType.I: 2, CubeType.T: 3, 
            CubeType.J: 4, CubeType.L: 5, CubeType.S: 6, CubeType.Z: 7
        }
        
        # 旋转配置
        self.rotation_map: Dict[CubeType, Tuple[int, ...]] = {
            CubeType.O: (0,),
            CubeType.I: (0, 1),
            CubeType.T: (0, 1, 2, 3),
            CubeType.J: (0, 1, 2, 3),
            CubeType.L: (0, 1, 2, 3),
            CubeType.S: (0, 1),
            CubeType.Z: (0, 1),
        }
        
        # 锚点配置
        self.anchor_map: Dict[CubeType, Tuple[int, ...]] = {
            CubeType.O: (0,),
            CubeType.I: (0, 0),
            CubeType.T: (0, 0, 1, 1),
            CubeType.L: (0, 0, 2, 0),
            CubeType.J: (0, 0, 0, 1),
            CubeType.Z: (0, 1),
            CubeType.S: (1, 0),
        }
        
        # 方块中心偏移
        self.offset_map: Dict[CubeType, Tuple[Tuple[float, float], ...]] = {
            CubeType.O: ((0.5, 0.5),),
            CubeType.I: ((1.5, 0.0), (0.0, 1.5)),
            CubeType.T: ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)),
            CubeType.L: ((0.0, 0.0), (0.0, 2.0), (2.0, 1.0), (1.0, 0.0)),
            CubeType.J: ((2.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 2.0)),
            CubeType.Z: ((1.0, 0.5), (0.5, 1.0)),
            CubeType.S: ((1.0, 0.5), (0.5, 1.0)),
        }
        
        self.fixed_placement_order: List[CubeType] = []
        self.solution = None
        
        self.char_map = {0: '.'}
        for cube_type, cube_id in self.id_map.items():
            self.char_map[cube_id] = cube_type.name[0]

    def set_placement_order(self, order: List[CubeType]):
        """设置方块放置顺序"""
        self.fixed_placement_order = order

    def _find_drop_row(self, board, mask, start_col):
        """使用Numba优化的下落位置查找"""
        return numba_find_drop_row(board, mask, start_col)

    def place(self, row: int, col: int, category: CubeType, rotation: int, board: np.ndarray):
        """放置方块到棋盘"""
        # 获取旋转后的方块
        rotated_mask = numba_rotate_mask(self.mask_map[category].copy(), rotation)
        anchor = self.anchor_map[category][rotation]
        
        # 计算实际放置位置
        start_col = col - anchor
        mask_h, mask_w = rotated_mask.shape
        
        # 更新棋盘
        for r in range(mask_h):
            for c in range(mask_w):
                if rotated_mask[r, c] == 1:
                    board[row + r, start_col + c] = self.id_map[category]
                    
        return board
    
    def calculate_score(self, board: np.ndarray) -> float:
        """使用Numba优化的评分函数"""
        return numba_calculate_score(board, self.height, self.column)

    def print_board(self, board, step, msg):
        """打印棋盘状态"""
        print(f"\n--- {msg} (Step: {step}) ---")
        flipped_board = np.flipud(board)
        for r_idx, row in enumerate(flipped_board):
            row_str = " ".join([self.char_map.get(c, '?') for c in row])
            print(f"Row {r_idx:2d} | {row_str} |")
        print("-" * (board.shape[1] * 2 + 7))

    def solve(self, cubes: List[Cube]) -> List[Cube]:
        """求解方块布局问题"""
        # 初始化方块统计
        initial_count_dict = {}
        for cube in cubes:
            cat_val = cube.category.value
            initial_count_dict[cat_val] = initial_count_dict.get(cat_val, 0) + 1

        # 初始化棋盘
        initial_board = np.zeros((self.height, self.column), dtype=np.int8)
        beams = [(self.calculate_score(initial_board), initial_board, [], initial_count_dict)]
        best_partial_solution = []
        total_pieces_to_place = len(cubes)
        
        for placed_count in range(total_pieces_to_place):
            next_beams = []
            
            for _, current_board, current_solution, current_counts in beams:
                # 确定下一个要放置的方块类型
                type_to_place = next(
                    (c_type for c_type in self.fixed_placement_order 
                     if current_counts.get(c_type.value, 0) > 0), 
                    None
                )
                if type_to_place is None: 
                    continue

                for rotation in self.rotation_map[type_to_place]:
                    # 获取旋转后的方块
                    mask = numba_rotate_mask(self.mask_map[type_to_place].copy(), rotation)
                    mask_h, mask_w = mask.shape
                    
                    # 遍历所有可能的放置列
                    for start_col in range(self.column - mask_w + 1):
                        final_row = self._find_drop_row(current_board, mask, start_col)
                        
                        if final_row >= 0:
                            # 创建新状态
                            new_board = current_board.copy()
                            anchor = self.anchor_map[type_to_place][rotation]
                            placement_col = start_col + anchor
                            
                            # 放置方块
                            self.place(final_row, placement_col, type_to_place, rotation, new_board)
                            
                            # 更新方块计数
                            new_counts = current_counts.copy()
                            new_counts[type_to_place.value] -= 1
                            
                            # 更新解决方案
                            new_solution = current_solution.copy()
                            new_solution.append(
                                Action(type_to_place, final_row, placement_col, rotation)
                            )
                            
                            # 计算新分数
                            score = self.calculate_score(new_board)
                            next_beams.append((score, new_board, new_solution, new_counts))
                            
            # 如果没有找到新状态，跳出循环
            if not next_beams: 
                self.solution = best_partial_solution 
                break

            # 过滤重复状态
            unique_boards = {}
            for state in next_beams:
                score, board, solution, counts = state
                board_bytes = board.tobytes()
                if board_bytes not in unique_boards or score > unique_boards[board_bytes][0]:
                    unique_boards[board_bytes] = (score, board, solution, counts)
            
            # 选择最优的状态
            sorted_states = sorted(unique_boards.values(), key=lambda x: x[0], reverse=True)
            beams = sorted_states[:self.beam_width]
            
            if not beams: 
                self.solution = best_partial_solution
                break
                
            best_partial_solution = beams[0][2]
            
            # 更新最终解决方案
            if placed_count == total_pieces_to_place - 1:
                self.solution = best_partial_solution
        
        # 打印最终棋盘状态
        if beams:
            self.print_board(beams[0][1], len(best_partial_solution), "Final Board")
        
        if self.solution is None:
            self.solution = best_partial_solution

        return self._post_process(self.solution, cubes)

    def _post_process(self, actions: List[Action], cubes: List[Cube]) -> List[Cube]:
        """将内部解决方案转换为物理坐标"""
        output_cubes = []
        unused_cubes = cubes.copy()
        
        for action in actions:
            # 找到匹配类型的方块
            for i, cube in enumerate(unused_cubes):
                if cube.category == action.category:
                    # 计算物理坐标
                    anchor = self.anchor_map[action.category][action.rotation]
                    offset = self.offset_map[action.category][action.rotation]
                    
                    # cube.broad_point = (
                    #     action.col - anchor + offset[0],
                    #     action.row + offset[1]
                    # )
                    # cube.broad_angle = action.rotation * 90.0
                    # 逻辑坐标
                    x = action.col - anchor + offset[0]
                    y = action.row + offset[1]

                    # 旋转 180°：相当于同时做 X/Y 轴翻转
                    x = (self.column - 1) - x
                    y = (self.height - 1) - y

                    cube.broad_point = (x, y)
                    cube.broad_angle = (action.rotation * 90.0 + 180.0) % 360.0
                    output_cubes.append(cube)
                    unused_cubes.pop(i)
                    break
        
        return output_cubes

def emulate():
    solver = TetrisSolver(column=10, height=14, beam_width=400)
    
    cubes = []
    cube_counts = {c: 2 for c in [CubeType.I, CubeType.O, CubeType.T, CubeType.L, CubeType.J, CubeType.S, CubeType.Z]}
    for category, count in cube_counts.items():
        for _ in range(count):
            cube = Cube()
            cube.category = category
            cubes.append(cube)
    random.shuffle(cubes)

    placement_order = [
        CubeType.I,
        CubeType.L, 
        CubeType.J, 
        CubeType.O, 
        CubeType.T, 
        CubeType.S, 
        CubeType.Z,
    ]
    
    solver.set_placement_order(placement_order)

    print(f"Total Cubes to place: {sum(cube_counts.values())}")
    t1 = time.time()
    solution_cubes = solver.solve(cubes)
    print(f"\nTime Consumed: {(time.time() - t1) * 1000:.2f} ms")
    
    if solution_cubes:
        print(f"\nFound a solution with {len(solution_cubes)} cubes placed:")
        for solved_cube in solution_cubes:
            print(solved_cube)
    else:
        print("\nNo solution was found.")

if __name__ == "__main__":
    # 运行测试
    emulate()