# TurtleBot3 AI 음성인식 비서

이 프로젝트는 웹 브라우저와 음성 명령을 이용해 TurtleBot3를 제어하는 ROS2 기반 프로젝트입니다.
휴대폰 웹 브라우저에서 버튼 제어, 음성 제어, YOLO 기반 사람 추적 기능을 사용할 수 있습니다.

---

## 1. 프로젝트 구조

```text
ros2_ws/
├── server/
│   ├── server.py
│   ├── ros_node.py
│   ├── message.py
│   └── run_demo.sh
│
├── web/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 2. GitHub에 포함하지 않는 파일

다음 파일들은 용량이 크기 때문에 GitHub에 포함하지 않습니다.

```text
server/whisper.cpp/
server/yolo11n.pt
server/yolov8n.pt
server/best.pt
web/tfjs_model/
logs/
__pycache__/
build/
install/
log/
```

Whisper 모델과 YOLO 모델은 실행 전에 직접 설치 또는 다운로드해야 합니다.

---

## 3. Python 패키지 설치

프로젝트 폴더로 이동합니다.

```bash
cd ~/project_robot/ros2_ws
```

필요한 Python 패키지를 설치합니다.

```bash
python3 -m pip install -r requirements.txt
```

`requirements.txt` 예시는 다음과 같습니다.

```text
fastapi
uvicorn[standard]
python-multipart
ultralytics
opencv-python
pillow
numpy
```

---

## 4. Whisper.cpp 설치

음성 인식을 위해 `server/` 폴더 안에 `whisper.cpp`를 설치합니다.

```bash
cd ~/project_robot/ros2_ws/server
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build -j$(nproc)
```

Whisper 모델 파일을 다운로드합니다.

```bash
bash models/download-ggml-model.sh tiny
```

설치 후 다음 파일들이 존재해야 합니다.

```text
server/whisper.cpp/build/bin/whisper-cli
server/whisper.cpp/models/ggml-tiny.bin
```

확인 명령어:

```bash
ls ~/project_robot/ros2_ws/server/whisper.cpp/build/bin/whisper-cli
ls ~/project_robot/ros2_ws/server/whisper.cpp/models/ggml-tiny.bin
```

---

## 5. YOLO 모델 준비

사람 인식을 위해 Ultralytics YOLO를 사용합니다.

YOLO 모델은 처음 실행할 때 자동으로 다운로드될 수 있습니다.
수동으로 확인하려면 다음 명령어를 실행합니다.

```bash
python3 - <<'EOF'
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
print("YOLO model loaded")
EOF
```

정상적으로 실행되면 `yolo11n.pt` 모델이 준비된 상태입니다.

---

## 6. TurtleBot3 bringup 실행

TurtleBot3의 Raspberry Pi에 SSH로 접속합니다.

```bash
ssh ubuntu@터틀봇_IP
```

예시:

```bash
ssh ubuntu@192.168.0.10
```

SSH 접속 후 TurtleBot3 bringup을 실행합니다.

```bash
export ROS_DOMAIN_ID=31
export ROS_LOCALHOST_ONLY=0

source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash 2>/dev/null || true

export TURTLEBOT3_MODEL=burger

ros2 launch turtlebot3_bringup robot.launch.py
```

이 터미널은 종료하지 않고 계속 켜둡니다.

---

## 7. 웹 서버 실행

새 터미널에서 서버 폴더로 이동합니다.

```bash
cd ~/project_robot/ros2_ws/server
```

ROS2 환경을 불러옵니다.

```bash
export ROS_DOMAIN_ID=31
export ROS_LOCALHOST_ONLY=0

source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
```

FastAPI 서버를 실행합니다.

```bash
python3 server.py
```

정상 실행 시 다음과 비슷한 로그가 출력됩니다.

```text
Uvicorn running on http://0.0.0.0:8000
```

---

## 8. 휴대폰 접속용 Cloudflare Tunnel 실행

휴대폰에서 카메라와 마이크를 사용하려면 HTTPS 접속이 필요합니다.
이를 위해 Cloudflare Tunnel을 사용합니다.

새 터미널에서 다음 명령어를 실행합니다.

```bash
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2
```

실행 후 다음과 같은 주소가 출력됩니다.

```text
https://xxxxx.trycloudflare.com
```

이 주소를 휴대폰 크롬 브라우저에서 열면 됩니다.

---

## 9. 자동 실행 스크립트 사용

`server/run_demo.sh`를 사용하면 서버와 Cloudflare Tunnel을 한 번에 실행할 수 있습니다.

먼저 파일 안의 TurtleBot IP를 수정합니다.

```bash
cd ~/project_robot/ros2_ws/server
code run_demo.sh
```

아래 부분을 실제 TurtleBot IP로 수정합니다.

```bash
ROBOT_IP="192.168.0.10"
```

실행 권한을 부여합니다.

```bash
chmod +x run_demo.sh
```

실행합니다.

```bash
./run_demo.sh
```

실행 후 출력되는 `https://xxxxx.trycloudflare.com` 주소를 휴대폰에서 접속합니다.

단, TurtleBot bringup이 자동으로 되지 않는 경우에는 SSH로 TurtleBot에 직접 접속하여 bringup을 먼저 실행하는 것이 안정적입니다.

---

## 10. 휴대폰 사용 순서

휴대폰에서 웹페이지에 접속한 뒤 다음 순서로 사용합니다.

```text
1. Connection이 Connected 상태인지 확인
2. 카메라 시작
3. 실시간 인식 시작
4. 음성 입력 버튼 클릭
5. “사람 따라가”라고 말하기
6. 다시 음성 입력 버튼을 눌러 녹음 종료
7. Follow Mode: ON 확인
8. 카메라에 사람을 비추기
```

사람이 화면 왼쪽에 있으면 TurtleBot이 왼쪽으로 회전하고, 오른쪽에 있으면 오른쪽으로 회전합니다.
사람이 중앙에 있고 멀리 있으면 전진하며, 가까우면 정지합니다.

---

## 11. 음성 명령 예시

```text
앞으로
뒤로
왼쪽
오른쪽
정지
사람 따라가
추적 중지
```

---

## 12. 동작 방식

```text
휴대폰 브라우저
→ FastAPI 서버
→ Whisper.cpp 음성 인식
→ 명령어 변환
→ ROS2 /cmd_vel 발행
→ TurtleBot3 이동
```

사람 추적 기능은 다음과 같이 동작합니다.

```text
휴대폰 카메라
→ 서버로 이미지 프레임 전송
→ YOLO가 사람 탐지
→ 사람의 위치와 크기 계산
→ forward / left / right / stop 명령 결정
→ ROS2 /cmd_vel 발행
```

---

## 13. 주의사항

* `whisper.cpp` 폴더와 YOLO 모델 파일은 GitHub에 포함하지 않습니다.
* 실행 전에 `Whisper.cpp`와 `ggml-tiny.bin` 모델을 직접 설치해야 합니다.
* TurtleBot3와 서버 PC는 같은 ROS_DOMAIN_ID를 사용해야 합니다.
* 본 프로젝트에서는 `ROS_DOMAIN_ID=31`을 사용합니다.
* 휴대폰 카메라와 마이크를 사용하려면 HTTPS 주소로 접속하는 것이 안정적입니다.
* Cloudflare Tunnel 주소는 임시 주소이므로 실행할 때마다 바뀔 수 있습니다.
