#!/usr/bin/env python3

from threading import Lock

from geometry_msgs.msg import Twist
from rclpy.node import Node


class WebControlNode(Node):

    def __init__(self):

        super().__init__("web_control_node")

        # Publisher
        self.cmd_pub = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        # Thread safety
        self.lock = Lock()

        # Current command
        self.current_cmd = "stop"

        # Emergency stop flag
        self.emergency = False

        # Robot state
        self.robot_state = "IDLE"

        # Speed values
        self.linear_speed = 0.12
        self.angular_speed = 0.8

        # 실제 터틀봇이 전후 반대로 움직이면 True
        # 일반 ROS 기준이면 False
        self.invert_linear = True

        # 10Hz cmd_vel publish
        self.timer = self.create_timer(
            0.1,
            self.publish_cmd
        )

        self.get_logger().info("WebControlNode started")

    # --------------------------------------------------
    # Command validation
    # --------------------------------------------------

    def normalize_command(self, command):

        if command is None:
            return "stop"

        command = str(command).lower().strip()

        valid_commands = [
            "forward",
            "backward",
            "left",
            "right",
            "stop"
        ]

        if command not in valid_commands:
            self.get_logger().warn(f"Unknown command: {command}")
            return "stop"

        return command

    # --------------------------------------------------
    # Set command
    # --------------------------------------------------

    def set_command(self, command):

        command = self.normalize_command(command)

        with self.lock:

            if self.emergency:
                self.get_logger().warn(
                    f"Command ignored during emergency: {command}"
                )
                return

            self.current_cmd = command

            if command == "forward":
                self.robot_state = "FORWARD"

            elif command == "backward":
                self.robot_state = "BACKWARD"

            elif command == "left":
                self.robot_state = "LEFT"

            elif command == "right":
                self.robot_state = "RIGHT"

            else:
                self.robot_state = "IDLE"

        self.get_logger().info(f"CMD : {command}")

    # --------------------------------------------------
    # Emergency stop
    # --------------------------------------------------

    def emergency_stop(self):

        with self.lock:

            self.emergency = True
            self.current_cmd = "stop"
            self.robot_state = "EMERGENCY_STOP"

        self.publish_zero()

        self.get_logger().warn("EMERGENCY STOP")

    # --------------------------------------------------
    # Release emergency stop
    # --------------------------------------------------

    def release_emergency(self):

        with self.lock:

            self.emergency = False
            self.current_cmd = "stop"
            self.robot_state = "IDLE"

        self.publish_zero()

        self.get_logger().info("EMERGENCY RELEASE")

    # --------------------------------------------------
    # Publish zero velocity
    # --------------------------------------------------

    def publish_zero(self):

        msg = Twist()
        msg.linear.x = 0.0
        msg.angular.z = 0.0

        self.cmd_pub.publish(msg)

    # --------------------------------------------------
    # Publish cmd_vel
    # --------------------------------------------------

    def publish_cmd(self):

        with self.lock:

            current_cmd = self.current_cmd
            emergency = self.emergency

        if emergency:
            self.publish_zero()
            return

        msg = Twist()

        if current_cmd == "forward":

            linear = self.linear_speed

            if self.invert_linear:
                linear = -linear

            msg.linear.x = linear

        elif current_cmd == "backward":

            linear = -self.linear_speed

            if self.invert_linear:
                linear = -linear

            msg.linear.x = linear

        elif current_cmd == "left":

            msg.angular.z = self.angular_speed

        elif current_cmd == "right":

            msg.angular.z = -self.angular_speed

        else:

            msg.linear.x = 0.0
            msg.angular.z = 0.0

        self.cmd_pub.publish(msg)

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def get_status(self):

        with self.lock:

            return {
                "robot_state": self.robot_state,
                "current_cmd": self.current_cmd,
                "emergency": self.emergency
            }
