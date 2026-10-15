import launch
import launch_ros.actions

def generate_launch_description():
    return launch.LaunchDescription([
        # 启动 RealSenseCameraNode
        launch_ros.actions.Node(
            package='el',  # 替换为你的包名
            executable='camera_node',  # 替换为你的节点的可执行文件名
            name='camera_node',
            output='screen',
            parameters=[],
            remappings=[],
        ),
        # 启动 ImageProcessingNode
        launch_ros.actions.Node(
            package='el',  # 替换为你的包名
            executable='main',  # 替换为你的节点的可执行文件名
            name='image_processing_node',
            output='screen',
            parameters=[],
            remappings=[],
        ),
    ])

