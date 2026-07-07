#!/usr/bin/env python3

class MessageRouter:

    def __init__(self, ros_node):

        self.ros = ros_node

    # -------------------------------------------------

    def handle(self, message):

        msg_type = message.get("type", "")

        # ------------------------------
        # 버튼 제어
        # ------------------------------

        if msg_type == "control":

            command = message.get("command", "stop")

            self.ros.set_command(command)

            return {

                "type": "status",

                "robot_state": self.ros.robot_state,

                "emergency": self.ros.emergency,

                "message": f"{command}"

            }

        # ------------------------------
        # 긴급정지
        # ------------------------------

        elif msg_type == "emergency":

            self.ros.emergency_stop()

            return {

                "type": "status",

                "robot_state": self.ros.robot_state,

                "emergency": True,

                "message": "Emergency Stop"

            }

        # ------------------------------
        # 긴급정지 해제
        # ------------------------------

        elif msg_type == "release":

            self.ros.release_emergency()

            return {

                "type": "status",

                "robot_state": self.ros.robot_state,

                "emergency": False,

                "message": "Emergency Released"

            }

        # ------------------------------
        # 상태 요청
        # ------------------------------

        elif msg_type == "status":

            status = self.ros.get_status()

            return {

                "type": "status",

                "robot_state": status["robot_state"],

                "emergency": status["emergency"]

            }

        # ------------------------------
        # 음성
        # ------------------------------

        elif msg_type == "voice":

            text = message.get("text", "")

            # 현재는 AI가 없으므로 그대로 표시만 함
            return {

                "type": "voice",

                "stt": text,

                "ai": "AI 준비중"

            }

        # ------------------------------
        # 알 수 없는 메시지
        # ------------------------------

        return {

            "type": "error",

            "message": "Unknown Message Type"

        }
