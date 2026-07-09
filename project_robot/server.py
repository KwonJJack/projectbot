import os
import json
import tempfile
import threading
import subprocess
import shutil
from io import BytesIO

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import rclpy
from rclpy.executors import MultiThreadedExecutor

from ros_node import WebControlNode
from message import MessageRouter


# ===========================================
# Optional YOLO imports
# ===========================================

try:
    from ultralytics import YOLO
    from PIL import Image
    YOLO_AVAILABLE = True
except Exception as e:
    YOLO_AVAILABLE = False
    YOLO_IMPORT_ERROR = str(e)


# ===========================================
# Paths
# ===========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WHISPER_DIR = os.path.join(BASE_DIR, "whisper.cpp")
WHISPER_BIN = os.path.join(WHISPER_DIR, "build", "bin", "whisper-cli")
MODEL_PATH = os.path.join(WHISPER_DIR, "models", "ggml-tiny.bin")

WEB_DIR = os.path.join(BASE_DIR, "../web")

# YOLO model
YOLO_MODEL_NAME = "yolo11n.pt"


# ===========================================
# FastAPI App
# ===========================================

app = FastAPI()

if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


# ===========================================
# Global State
# ===========================================

ros_node = None
router = None
executor = None
ros_thread = None

yolo_model = None
yolo_lock = threading.Lock()

follow_mode = False
follow_lock = threading.Lock()


# ===========================================
# Follow Mode State
# ===========================================

def set_follow_mode(value: bool):
    global follow_mode

    with follow_lock:
        follow_mode = value


def get_follow_mode() -> bool:
    with follow_lock:
        return follow_mode


# ===========================================
# ROS Init / Shutdown
# ===========================================

def init_ros():
    global ros_node, router, executor, ros_thread

    if not rclpy.ok():
        rclpy.init()

    ros_node = WebControlNode()
    router = MessageRouter(ros_node)

    executor = MultiThreadedExecutor()
    executor.add_node(ros_node)

    ros_thread = threading.Thread(
        target=executor.spin,
        daemon=True
    )

    ros_thread.start()

    print("[ROS] initialized")


def shutdown_ros():
    global ros_node, executor

    try:
        if ros_node is not None:
            ros_node.publish_zero()
            ros_node.destroy_node()

        if executor is not None:
            executor.shutdown()

        if rclpy.ok():
            rclpy.shutdown()

        print("[ROS] shutdown")

    except Exception as e:
        print("[ROS] shutdown error:", e)


@app.on_event("startup")
def on_startup():
    init_ros()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_ros()


# ===========================================
# Whisper STT
# ===========================================

def speech_to_text(audio_path: str) -> str:
    if not os.path.exists(WHISPER_BIN):
        raise RuntimeError(f"whisper-cli not found: {WHISPER_BIN}")

    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Whisper model not found: {MODEL_PATH}")

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not installed")

    wav_path = audio_path + ".wav"

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        audio_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        wav_path
    ]

    subprocess.run(
        ffmpeg_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    whisper_cmd = [
        WHISPER_BIN,
        "-m",
        MODEL_PATH,
        "-f",
        wav_path,
        "-l",
        "ko"
    ]

    result = subprocess.run(
        whisper_cmd,
        cwd=WHISPER_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )

    text_lines = []

    for line in result.stdout.splitlines():
        if "-->" in line and "]" in line:
            text_lines.append(line.split("]", 1)[-1].strip())

    text = " ".join(text_lines).strip()

    return text


# ===========================================
# Command Parser
# ===========================================

def parse_command(text: str) -> str:
    if not text:
        return "stop"

    raw = text.strip().lower()
    compact = raw.replace(" ", "")

    # -------------------------------
    # Follow person mode ON
    # -------------------------------

    follow_on_words = [
        "사람따라가",
        "사람을따라가",
        "사람따라와",
        "사람을따라와",
        "나따라와",
        "나를따라와",
        "따라가",
        "따라와",
        "추적해",
        "사람추적",
        "사람추적해",
        "followperson",
        "followme"
    ]

    for word in follow_on_words:
        if word in compact:
            return "follow_person"

    # -------------------------------
    # Follow person mode OFF
    # -------------------------------

    follow_off_words = [
        "추적중지",
        "따라가기중지",
        "따라오지마",
        "그만따라와",
        "사람그만따라가",
        "사람추적중지",
        "팔로우중지",
        "followstop",
        "stopfollow"
    ]

    for word in follow_off_words:
        if word in compact:
            return "follow_stop"

    # -------------------------------
    # Stop
    # -------------------------------

    stop_words = [
        "정지",
        "멈춰",
        "멈춰라",
        "멈춤",
        "스톱",
        "stop",
        "그만",
        "멈춰줘",
        "멈춰주세요",
        "중지"
    ]

    for word in stop_words:
        if word in compact:
            return "stop"

    # -------------------------------
    # Left
    # -------------------------------

    left_words = [
        "왼쪽",
        "왼편",
        "좌측",
        "좌회전",
        "왼",
        "좌로"
    ]

    for word in left_words:
        if word in compact:
            return "left"

    # -------------------------------
    # Right
    # -------------------------------

    right_words = [
        "오른쪽",
        "오른편",
        "우측",
        "우회전",
        "오른",
        "우로"
    ]

    for word in right_words:
        if word in compact:
            return "right"

    # -------------------------------
    # Backward
    # -------------------------------

    backward_words = [
        "뒤로",
        "뒤쪽",
        "후진",
        "후퇴",
        "뒤",
        "빼",
        "물러나"
    ]

    for word in backward_words:
        if word in compact:
            return "backward"

    # -------------------------------
    # Forward
    # -------------------------------

    forward_words = [
        "앞으로",
        "전진",
        "직진",
        "출발",
        "이동",
        "가자",
        "가줘",
        "앞",
        "전방"
    ]

    if compact == "가":
        return "forward"

    for word in forward_words:
        if word in compact:
            return "forward"

    return "stop"


# ===========================================
# YOLO
# ===========================================

def get_yolo_model():
    global yolo_model

    if not YOLO_AVAILABLE:
        raise RuntimeError(f"YOLO import failed: {YOLO_IMPORT_ERROR}")

    with yolo_lock:
        if yolo_model is None:
            print("[YOLO] loading model:", YOLO_MODEL_NAME)
            yolo_model = YOLO(YOLO_MODEL_NAME)
            print("[YOLO] model loaded")

    return yolo_model


def decide_follow_command(
    person_center_x_ratio: float,
    person_height_ratio: float
) -> str:
    """
    person_center_x_ratio:
        0.0 = 화면 왼쪽 끝
        1.0 = 화면 오른쪽 끝

    person_height_ratio:
        사람 박스 높이 / 전체 화면 높이
        값이 클수록 사람이 가까움
    """

    left_boundary = 0.40
    right_boundary = 0.60

    too_close_height = 0.62

    if person_center_x_ratio < left_boundary:
        return "left"

    if person_center_x_ratio > right_boundary:
        return "right"

    if person_height_ratio >= too_close_height:
        return "stop"

    return "forward"


def detect_person_and_command(image: Image.Image):
    model = get_yolo_model()

    width, height = image.size

    results = model.predict(
        image,
        imgsz=320,
        conf=0.40,
        verbose=False
    )

    result = results[0]

    best_person = None

    if result.boxes is None:
        return {
            "detected": False,
            "command": "stop",
            "reason": "no boxes"
        }

    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        class_name = result.names.get(cls_id, str(cls_id))

        if class_name != "person":
            continue

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        box_width = x2 - x1
        box_height = y2 - y1
        area = box_width * box_height

        if best_person is None or area > best_person["area"]:
            best_person = {
                "class_name": class_name,
                "confidence": conf,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "box_width": box_width,
                "box_height": box_height,
                "area": area
            }

    if best_person is None:
        return {
            "detected": False,
            "command": "stop",
            "reason": "person not found"
        }

    center_x = (best_person["x1"] + best_person["x2"]) / 2.0

    center_x_ratio = center_x / width
    height_ratio = best_person["box_height"] / height

    command = decide_follow_command(
        center_x_ratio,
        height_ratio
    )

    return {
        "detected": True,
        "class_name": "person",
        "confidence": best_person["confidence"],
        "center_x_ratio": center_x_ratio,
        "height_ratio": height_ratio,
        "command": command,
        "box": {
            "x1": best_person["x1"],
            "y1": best_person["y1"],
            "x2": best_person["x2"],
            "y2": best_person["y2"]
        }
    }


# ===========================================
# Routes
# ===========================================

@app.get("/")
def index():
    index_path = os.path.join(WEB_DIR, "index.html")

    if not os.path.exists(index_path):
        raise HTTPException(
            status_code=404,
            detail=f"index.html not found: {index_path}"
        )

    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/health")
def health():
    return {
        "server": "ok",
        "ros_initialized": ros_node is not None,
        "follow_mode": get_follow_mode(),
        "yolo_available": YOLO_AVAILABLE,
        "yolo_model": YOLO_MODEL_NAME
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()

            try:
                msg = json.loads(data)

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                continue

            if router is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "ROS router is not initialized"
                })
                continue

            msg_type = msg.get("type")
            command = msg.get("command")

            # 수동 제어를 하면 사람 추적 모드는 꺼지게 함
            if msg_type == "control":
                set_follow_mode(False)

            if msg_type == "emergency":
                set_follow_mode(False)

            if msg_type == "release":
                set_follow_mode(False)

            response = router.handle(msg)

            if isinstance(response, dict):
                response["follow_mode"] = get_follow_mode()

            await websocket.send_json(response)

    except WebSocketDisconnect:
        if ros_node is not None:
            ros_node.set_command("stop")


@app.post("/voice")
async def voice(file: UploadFile = File(...)):
    global ros_node

    if ros_node is None:
        raise HTTPException(
            status_code=500,
            detail="ROS node is not initialized"
        )

    suffix = ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = speech_to_text(tmp_path)
        command = parse_command(text)

        message = ""

        if command == "follow_person":
            set_follow_mode(True)
            ros_node.set_command("stop")
            message = "Follow person mode ON"

        elif command == "follow_stop":
            set_follow_mode(False)
            ros_node.set_command("stop")
            message = "Follow person mode OFF"

        elif command == "stop":
            set_follow_mode(False)
            ros_node.set_command("stop")
            message = "Stop"

        else:
            set_follow_mode(False)
            ros_node.set_command(command)
            message = f"Manual voice command: {command}"

        status = ros_node.get_status()

        return {
            "speech": text,
            "command": command,
            "message": message,
            "robot_state": status["robot_state"],
            "current_cmd": status["current_cmd"],
            "emergency": status["emergency"],
            "follow_mode": get_follow_mode()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if ros_node is None:
        raise HTTPException(
            status_code=500,
            detail="ROS node is not initialized"
        )

    try:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        result = detect_person_and_command(image)

        current_follow_mode = get_follow_mode()

        if current_follow_mode:
            if result["detected"]:
                ros_node.set_command(result["command"])
            else:
                ros_node.set_command("stop")

        status = ros_node.get_status()

        return {
            "type": "detect",
            "follow_mode": current_follow_mode,
            "detected": result["detected"],
            "command": result["command"],
            "reason": result.get("reason", ""),
            "confidence": result.get("confidence", 0.0),
            "center_x_ratio": result.get("center_x_ratio", 0.0),
            "height_ratio": result.get("height_ratio", 0.0),
            "robot_state": status["robot_state"],
            "current_cmd": status["current_cmd"],
            "emergency": status["emergency"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ===========================================
# Main
# ===========================================

def main():
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )


if __name__ == "__main__":
    main()
