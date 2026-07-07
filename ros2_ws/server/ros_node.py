#!/usr/bin/env python3

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

        # 현재 명령
        self.current_cmd = "stop"

        # 긴급정지 여부
        self.emergency = False

        # 현재 상태
        self.robot_state = "IDLE"

        # 속도 (발표용으로 약간 낮춤)
        self.linear_speed = 0.12
        self.angular_speed = 0.8

        # 10Hz 주기로 cmd_vel 발행
        self.timer = self.create_timer(
            0.1,
            self.publish_cmd
        )

        self.get_logger().info("WebControlNode Started")

    # --------------------------------------------------

    def set_command(self, command):

        if self.emergency:
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

    def emergency_stop(self):

        self.emergency = True

        self.current_cmd = "stop"

        self.robot_state = "EMERGENCY STOP"

        self.publish_zero()

        self.get_logger().warn("EMERGENCY STOP")

    # --------------------------------------------------

    def release_emergency(self):

        self.emergency = False

        self.current_cmd = "stop"

        self.robot_state = "IDLE"

        self.publish_zero()

        self.get_logger().info("Emergency Released")

    # --------------------------------------------------

    def publish_zero(self):

        msg = Twist()

        msg.linear.x = 0.0
        msg.angular.z = 0.0

        self.cmd_pub.publish(msg)

    # --------------------------------------------------

    def publish_cmd(self):

        msg = Twist()

        if self.emergency:

            self.publish_zero()

            return

        # ===== 방향 수정 =====
        # 현재 터틀봇이 반대로 움직이므로
        # forward/backward를 반전

        if self.current_cmd == "forward":

            msg.linear.x = -self.linear_speed

        elif self.current_cmd == "backward":

            msg.linear.x = self.linear_speed

        elif self.current_cmd == "left":

            msg.angular.z = self.angular_speed

        elif self.current_cmd == "right":

            msg.angular.z = -self.angular_speed

        else:

            msg.linear.x = 0.0
            msg.angular.z = 0.0

        self.cmd_pub.publish(msg)

    # --------------------------------------------------

    def get_status(self):

        return {

            "robot_state": self.robot_state,

            "emergency": self.emergency

        }
