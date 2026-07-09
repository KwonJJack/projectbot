#!/usr/bin/env python3


class MessageRouter:

    def __init__(self, ros_node):

        self.ros = ros_node

    # -------------------------------------------------
    # Common status response
    # -------------------------------------------------

    def status_response(self, message=""):

        status = self.ros.get_status()

        return {
            "type": "status",
            "robot_state": status["robot_state"],
            "current_cmd": status["current_cmd"],
            "emergency": status["emergency"],
            "message": message
        }

    # -------------------------------------------------
    # Message handler
    # -------------------------------------------------

    def handle(self, message):

        msg_type = message.get("type", "")

        # ------------------------------
        # Button control
        # ------------------------------
        if msg_type == "control":

            command = message.get("command", "stop")

            self.ros.set_command(command)

            return self.status_response(
                message=f"Command: {command}"
            )

        # ------------------------------
        # Emergency stop
        # ------------------------------
        if msg_type == "emergency":

            self.ros.emergency_stop()

            return self.status_response(
                message="Emergency Stop"
            )

        # ------------------------------
        # Emergency release
        # ------------------------------
        if msg_type == "release":

            self.ros.release_emergency()

            return self.status_response(
                message="Emergency Released"
            )

        # ------------------------------
        # Status request
        # ------------------------------
        if msg_type == "status":

            return self.status_response(
                message="Status"
            )

        # ------------------------------
        # Voice text message
        # 현재 음성 파일 처리는 server.py의 /voice API에서 담당
        # WebSocket으로 텍스트만 들어오는 경우 표시용으로만 응답
        # ------------------------------
        if msg_type == "voice":

            text = message.get("text", "")

            return {
                "type": "voice",
                "stt": text,
                "message": "Voice text received"
            }

        # ------------------------------
        # Unknown message
        # ------------------------------
        return {
            "type": "error",
            "message": "Unknown Message Type"
        }
