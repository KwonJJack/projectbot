import rclpy
from rclpy.node import Node

from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist


class AssistantCoordinator(Node):
    def __init__(self):
        super().__init__('assistant_coordinator')

        # 현재 명령 및 상태
        self.current_cmd = 'STOP'
        self.state = 'IDLE'

        # 속도 설정
        self.linear_speed = 0.15
        self.angular_speed = 0.6

        # 입력 소실 감지용
        self.last_cmd_time = self.get_clock().now()
        self.command_timeout_sec = 1.0

        # Subscriber: 웹앱에서 오는 음성 명령
        self.create_subscription(
            String,
            '/voice_cmd',
            self.voice_cmd_callback,
            10
        )

        # Subscriber: 웹앱 전환/비상 정지
        self.create_subscription(
            Bool,
            '/emergency_stop',
            self.emergency_stop_callback,
            10
        )

        # Publisher: 터틀봇 주행 명령
        self.cmd_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # Publisher: LCD 표시 문구
        self.lcd_pub = self.create_publisher(
            String,
            '/lcd_text',
            10
        )

        # Publisher: 부저 알림
        self.buzzer_pub = self.create_publisher(
            Bool,
            '/buzzer',
            10
        )

        # Publisher: 웹 대시보드 상태 표시
        self.state_pub = self.create_publisher(
            String,
            '/assistant_state',
            10
        )

        # 10Hz timer
        # /cmd_vel은 연속 명령이므로 0.1초마다 계속 발행
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.publish_lcd('READY')
        self.publish_state('IDLE')

        self.get_logger().info('assistant_coordinator started')

    def voice_cmd_callback(self, msg):
        command = msg.data.strip().upper()
        self.last_cmd_time = self.get_clock().now()

        self.get_logger().info(f'Received voice command: {command}')

        valid_commands = [
            'FORWARD',
            'BACKWARD',
            'LEFT',
            'RIGHT',
            'STOP',
            'STATUS'
        ]

        if command not in valid_commands:
            self.current_cmd = 'STOP'
            self.state = 'UNKNOWN_COMMAND'
            self.publish_stop()
            self.publish_lcd('UNKNOWN CMD')
            self.publish_state(self.state)
            self.publish_buzzer()
            return

        if command == 'STATUS':
            self.publish_lcd(f'STATE: {self.state}')
            self.publish_state(self.state)
            self.publish_buzzer()
            return

        self.current_cmd = command

        if command == 'STOP':
            self.state = 'STOPPED'
            self.publish_stop()
            self.publish_lcd('STOPPED')
        else:
            self.state = 'MOVING'
            self.publish_lcd(f'CMD: {command}')

        self.publish_state(self.state)
        self.publish_buzzer()

    def emergency_stop_callback(self, msg):
        if msg.data:
            self.current_cmd = 'STOP'
            self.state = 'EMERGENCY_STOP'

            self.publish_stop()
            self.publish_lcd('EMERGENCY STOP')
            self.publish_state(self.state)
            self.publish_buzzer()

            self.get_logger().warn('Emergency stop activated')

    def timer_callback(self):
        # 입력 소실 안전장치
        elapsed = self.get_elapsed_time_from_last_cmd()

        if self.current_cmd != 'STOP' and elapsed > self.command_timeout_sec:
            self.current_cmd = 'STOP'
            self.state = 'TIMEOUT_STOP'

            self.publish_stop()
            self.publish_lcd('TIMEOUT STOP')
            self.publish_state(self.state)

            self.get_logger().warn('Command timeout: robot stopped')
            return

        # 이동 명령이면 /cmd_vel을 10Hz로 계속 발행
        if self.current_cmd == 'FORWARD':
            self.publish_cmd(self.linear_speed, 0.0)

        elif self.current_cmd == 'BACKWARD':
            self.publish_cmd(-self.linear_speed, 0.0)

        elif self.current_cmd == 'LEFT':
            self.publish_cmd(0.0, self.angular_speed)

        elif self.current_cmd == 'RIGHT':
            self.publish_cmd(0.0, -self.angular_speed)

        else:
            self.publish_stop()

    def get_elapsed_time_from_last_cmd(self):
        now = self.get_clock().now()
        elapsed_ns = (now - self.last_cmd_time).nanoseconds
        return elapsed_ns / 1e9

    def publish_cmd(self, linear_x, angular_z):
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z
        self.cmd_pub.publish(msg)

    def publish_stop(self):
        self.publish_cmd(0.0, 0.0)

    def publish_lcd(self, text):
        msg = String()
        msg.data = text
        self.lcd_pub.publish(msg)

    def publish_buzzer(self):
        msg = Bool()
        msg.data = True
        self.buzzer_pub.publish(msg)

    def publish_state(self, state):
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = AssistantCoordinator()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.publish_stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
