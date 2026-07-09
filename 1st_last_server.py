#!/usr/bin/env python3

import os
import json
import tempfile
import threading
import subprocess
import re
import shutil
import asyncio
from sensor_msgs.msg import BatteryState
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import Twist



# ==================================================
# Path
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_DIR = os.path.join(BASE_DIR, "whisper.cpp")
MODEL_PATH = os.path.join(
    WHISPER_DIR,
    "models",
    "ggml-tiny.bin"
)
WEB_DIR = os.path.join(BASE_DIR, "../web")


# ==================================================
# ROS2 Node
# ==================================================

class WebControlNode(Node):

    def __init__(self):

        super().__init__("web_control_node")

        self.cmd_pub = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        self.current_cmd = "stop"

        self.emergency = False

        self.linear_speed = 0.12
        self.angular_speed = 0.8
        self.battery = 0

        self.timer = self.create_timer(
            0.1,
            self.publish_cmd
        )


        self.get_logger().info(
            "WebControlNode started"
        )
        self.create_subscription(
            BatteryState,
            "/battery_state",
            self.battery_callback,
            10
        )

    # ------------------------------
    # command
    # ------------------------------

    def set_command(self, cmd):

        if self.emergency:
            return

        self.current_cmd = cmd

        self.get_logger().info(
            f"CMD : {cmd}"
        )


    # ------------------------------
    # emergency stop
    # ------------------------------

    def emergency_stop(self):

        self.emergency = True

        self.current_cmd = "stop"

        msg = Twist()

        self.cmd_pub.publish(msg)

        self.get_logger().warn(
            "EMERGENCY STOP"
        )


    # ------------------------------
    # release
    # ------------------------------

    def release_emergency(self):

        self.emergency = False

        self.current_cmd = "stop"

        self.get_logger().info(
            "EMERGENCY RELEASE"
        )


    # ------------------------------
    # cmd_vel publish
    # ------------------------------

    def publish_cmd(self):

        msg = Twist()


        if self.emergency:

            self.cmd_pub.publish(msg)
            return


        # 방향 반전 적용
        # 필요하면 여기 숫자만 다시 변경

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

    def battery_callback(self, msg):

        new_value = round(msg.percentage, 1)

        if new_value != self.battery:
            self.battery = new_value
            print(f"BATTERY = {self.battery}%")


def speech_to_text(audio_path):

    wav_path = audio_path.replace(".webm", ".wav")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i",
        audio_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        wav_path
    ], check=True,stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL)

    result = subprocess.run(

        [
            "./build/bin/whisper-cli",
            "-m",
            "models/ggml-tiny.bin",
            "-f",
            wav_path,
            "-l",
            "ko"
        ],

        cwd=WHISPER_DIR,

        capture_output=True,

        text=True
    )
    if result.returncode != 0:
        print(result.stderr)
    output = result.stdout

    text = ""

    for line in output.splitlines():

        if "-->" in line:

            text += line.split("]")[-1].strip()

    return text
def parse_command(text):

    if not text:
        return "stop"

    text = text.lower().strip()
    text = text.replace(" ", "")

    # -------------------------
    # STOP (최우선)
    # -------------------------
    stop_words = [
        "정지", "멈춰", "멈춰라", "멈춤",
        "스톱", "stop", "그만",
        "서", "멈춰줘", "멈춰주세요",
        "중지"
    ]

    for word in stop_words:
        if word in text:
            return "stop"

    # -------------------------
    # LEFT
    # -------------------------
    left_words = [
        "왼쪽", "왼편", "좌측",
        "좌회전", "왼", "좌로"
    ]

    for word in left_words:
        if word in text:
            return "left"

    # -------------------------
    # RIGHT
    # -------------------------
    right_words = [
        "오른쪽", "오른편", "우측",
        "우회전", "오른", "우로"
    ]

    for word in right_words:
        if word in text:
            return "right"

    # -------------------------
    # BACKWARD
    # -------------------------
    backward_words = [
        "뒤로", "뒤쪽",
        "후진", "후퇴",
        "뒤", "빼",
        "물러나"
    ]

    for word in backward_words:
        if word in text:
            return "backward"

    # -------------------------
    # FORWARD
    # -------------------------
    forward_words = [
        "앞으로", "전진", "직진",
        "출발", "이동",
        "가자", "가줘",
        "앞", "전방"
    ]

    for word in forward_words:
        if word in text:
            return "forward"

    # "가" 단독 처리 (가장 마지막)
    if text == "가":
        return "forward"

    return "stop"
# ==================================================
# FastAPI
# ==================================================

app = FastAPI()


ros_node = None



app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static"
)



# ==================================================
# Main Page
# ==================================================

@app.get("/")
def home():

    with open(
        os.path.join(WEB_DIR, "index.html"),
        "r",
        encoding="utf-8"
    ) as f:

        return HTMLResponse(
            f.read()
        )



# ==================================================
# WebSocket
# ==================================================

@app.websocket("/ws")
async def websocket(ws: WebSocket):

    await ws.accept()

    async def send_status_loop():

        while True:
            try:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "status",
                            "robot_state": ros_node.current_cmd,
                            "battery": ros_node.battery
                        }
                    )
                )
            except Exception:
                break

            await asyncio.sleep(1)

    task = asyncio.create_task(send_status_loop())

    try:

        while True:

            data = await ws.receive_text()

            msg = json.loads(data)

            if msg["type"] == "control":

                ros_node.set_command(
                    msg["command"]
                )

            elif msg["type"] == "emergency":

                ros_node.emergency_stop()

            elif msg["type"] == "release":

                ros_node.release_emergency()

    except WebSocketDisconnect:

        pass
    finally:
        task.cancel()
        try:
            await task
        except Exception:
            pass



# ==================================================
# Voice API
# ==================================================

@app.post("/voice")
async def voice(
    file: UploadFile = File(...)
):

    print("[VOICE] received")

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".webm"
    ) as tmp:

        tmp.write(await file.read())
        audio_path = tmp.name

    try:

        text = speech_to_text(audio_path)

        print("[STT]", text)

        command = parse_command(text)

        print("[CMD]", command)

        ros_node.set_command(command)

        return {
            "speech": text,
            "command": command
        }

    finally:

        if os.path.exists(audio_path):
            os.remove(audio_path)

        wav_path = audio_path.replace(".webm", ".wav")

        if os.path.exists(wav_path):
            os.remove(wav_path)

# ==================================================
# Start
# ==================================================

if __name__ == "__main__":


    rclpy.init()


    ros_node = WebControlNode()


    executor = MultiThreadedExecutor()

    executor.add_node(
        ros_node
    )


    def spin():

        executor.spin()



    threading.Thread(
        target=spin,
        daemon=True
    ).start()



    import uvicorn


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=8000

    )
