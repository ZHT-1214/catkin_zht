from setuptools import setup,find_packages
from glob import glob
import os

package_name = 'el'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Resource index for ament
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        
        # Launch files
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        
        # Config files
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        
        # Package XML
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='z',
    maintainer_email='z@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_node = el.camera_node:main',  # 确保 'camera_node.py' 文件中有 'main' 函数
            'main = el.main:main',  # 确保 'image_processing_node.py' 文件中有 'main' 函数
        ],
    },
)

