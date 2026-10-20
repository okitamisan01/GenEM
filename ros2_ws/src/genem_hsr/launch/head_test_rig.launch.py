"""Two-joint commissioning rig using real JTC + GenericSystem, NOT Gazebo HSR."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory('genem_hsr'))
    description = (share / 'config/head_test_rig.urdf').read_text()
    config = str(share / 'config/head_test_rig_controllers.yaml')
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description}]),
        Node(package='controller_manager', executable='ros2_control_node',
             parameters=[config], output='screen'),
        Node(package='controller_manager', executable='spawner',
             arguments=['joint_state_broadcaster', '--controller-manager-timeout', '30']),
        Node(package='controller_manager', executable='spawner',
             arguments=['head_trajectory_controller', '--controller-manager-timeout', '30']),
    ])
