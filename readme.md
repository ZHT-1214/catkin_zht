# 方块视觉识别与机械臂自动摆放

本项目是一个基于 ROS 2 的 Python 工作空间，用 RealSense 彩色相机识别方块，在棋盘上搜索摆放方案，并将方块抓取和放置坐标发送给 xArm 机械臂。
## 演示视频

[点击观看演示视频：俄罗斯方块机器人-我们做的全队](https://www.bilibili.com/video/BV17FJm67EbM/)
## 功能流程

1. 相机节点采集 1280 × 720、30 FPS 的彩色图像，并发布到 `camera/image_raw`。
2. 主节点检测图像中的方块轮廓，识别方块类型并计算抓取点。
3. 操作者在图像窗口中检查识别结果：按 `Space` 或 `Q` 暂停并预览，按 `Y` 确认，按 `N` 重新采集。
4. 求解器按预设顺序搜索 10 列棋盘上的摆放位置。
5. 坐标转换模块将相机和棋盘坐标转换为机械臂坐标；通过范围检查的方案由机械臂执行。

## 项目结构

```text
src/el/
├── el/
│   ├── camera_node.py       # RealSense 相机 ROS 2 节点
│   ├── main.py              # 识别、规划和机械臂执行主程序
│   ├── consts.py            # 方块类型和数据结构
│   └── modules/
│       ├── camera.py        # RealSense 相机封装
│       ├── detector.py      # 方块检测、分类和抓取点计算
│       ├── planning.py      # 棋盘摆放搜索（Numba 加速）
│       ├── routing.py       # 相机/棋盘坐标到机械臂坐标的转换
│       └── xarm/            # xArm Python 控制接口
├── launch/
│   └── robot_launch.py      # 同时启动相机和主节点
├── package.xml
└── setup.py
```

## 环境要求

- ROS 2（支持 `ament_python`）及 `colcon`
- 可用的 RealSense 相机、RealSense SDK 和 Python 模块 `pyrealsense2`
- xArm 机械臂及其控制网络
- Python 依赖：NumPy、OpenCV、Numba，以及 ROS 2 的 `rclpy`、`sensor_msgs`、`std_msgs` 和 `cv_bridge`

请在已配置好 ROS 2、RealSense SDK 和上述 Python/ROS 依赖的终端中构建和运行。当前仓库没有单独的依赖锁定文件。

## 构建与启动

在工作空间根目录执行（将 `<ROS_DISTRO>` 替换为已安装的 ROS 2 发行版名称）：

```bash
source /opt/ros/<ROS_DISTRO>/setup.bash
colcon build --symlink-install --packages-select el
source install/setup.bash
ros2 launch el robot_launch.py
```

启动后，主节点会显示相机图像和识别标记。按上述按键确认图像后，程序会规划并执行机械臂动作。也可以单独运行相机节点进行检查：

```bash
ros2 run el camera_node
```

## 硬件与安全配置

- 主程序当前将 xArm IP 地址写在 [`src/el/el/main.py`](./src/el/el/main.py) 的 `ARM_IP` 常量中（当前值为 `192.168.1.241`）。运行前请确认该地址与实际机械臂网络配置一致。
- 相机到机械臂、棋盘到机械臂的标定矩阵及坐标安全范围在 [`src/el/el/modules/routing.py`](./src/el/el/modules/routing.py) 中。更换相机位置、棋盘位置或机械臂后，必须重新标定并先验证坐标。
- 棋盘列数、搜索宽度和方块摆放顺序在 [`src/el/el/main.py`](./src/el/el/main.py) 中配置；当前搜索宽度为 `400`。增大搜索宽度会增加规划时间。
- 首次运行或修改标定后，请先在机械臂周围清空工作区域，并在低速、可随时急停的条件下确认抓取点、放置点和工具 I/O 行为。请勿在未核对坐标与安全范围时直接运行。

## 备用紧固件

| 用途 | 规格 | 数量 |
| --- | --- | ---: |
| 打印支架 | M6 × 15 mm | 2 |
| 底盘 | M5 × 20 mm（带螺母） | 5 |
| 相机 | M3 × 5 mm | 2 |
