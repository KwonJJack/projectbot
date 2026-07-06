from setuptools import setup

package_name = 'voice_assistant_robot'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='team5',
    maintainer_email='team5@example.com',
    description='Voice command based ROS 2 assistant robot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'assistant_coordinator = voice_assistant_robot.assistant_coordinator:main',
        ],
    },
)
