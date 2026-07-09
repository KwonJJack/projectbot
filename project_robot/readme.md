# TurtleBot3 AI Assistant

TurtleBot3를 웹 브라우저와 음성 명령으로 제어하는 AI Assistant 프로젝트이다.

휴대폰 브라우저에서 웹 페이지에 접속하여 TurtleBot3를 수동 조종할 수 있고, 음성 명령을 통해 전진, 후진, 좌회전, 우회전, 정지 명령을 보낼 수 있다. 또한 YOLO 사람 인식을 이용하여 `"사람 따라가"` 명령을 받으면 사람의 위치에 따라 로봇이 회전, 전진, 정지하도록 구성하였다.

---

## 1. 주요 기능

* 휴대폰 웹 브라우저를 통한 TurtleBot3 원격 조종
* WebSocket 기반 실시간 명령 전송
* `/cmd_vel` 토픽 발행
* Whisper.cpp 기반 한국어 음성 인식
* YOLO 기반 사람 인식
* `"사람 따라가"` 음성 명령을 통한 사람 따라가기 모드
* 긴급 정지 및 해제 기능
* Cloudflare Tunnel을 이용한 휴대폰 외부 접속

---

## 2. 프로젝트 구조

```bash
ros2_ws/
├── server/
│   ├── server.py
│   ├── ros_node.py
│   ├── message.py
│   ├── run_web.sh
│   └── whisper.cpp/          # 직접 설치 필요, GitHub 업로드 제외 권장
│
├── web/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── logs/                     # 실행 로그 저장
└── README.md
```

---

## 3. 실행 환경

이 프로젝트는 다음 환경을 기준으로 작성하였다.

```text
OS: Ubuntu 22.04
ROS 2: Humble
Robot: TurtleBot3 Burger
ROS_DOMAIN_ID: 31
TURTLEBOT3_MODEL: burger
LDS_MODEL: LDS-01
Web Server: FastAPI
STT: whisper.cpp
Object Detection: Ultralytics YOLO
Tunnel: Cloudflare Tunnel
```

---

## 4. 터미널에서 별도로 설치해야 하는 것

### 4-1. 기본 패키지 설치

PC 또는 서버를 실행할 Ubuntu 환경에서 다음 패키지를 설치한다.

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git curl cmake build-essential ffmpeg
```

`ffmpeg`는 웹에서 녹음된 음성 파일을 Whisper가 처리할 수 있는 WAV 형식으로 변환하기 위해 필요하다.

---

### 4-2. Python 패키지 설치

프로젝트 서버에서 사용하는 Python 패키지를 설치한다.

```bash
pip3 install fastapi
pip3 install "uvicorn[standard]"
pip3 install python-multipart
pip3 install pillow
pip3 install ultralytics
```

한 번에 설치하려면 다음 명령어를 사용해도 된다.

```bash
pip3 install fastapi "uvicorn[standard]" python-multipart pillow ultralytics
```

---

### 4-3. Cloudflare Tunnel 설치

휴대폰에서 HTTPS 링크로 접속하기 위해 `cloudflared`가 필요하다.

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings

curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt update
sudo apt install -y cloudflared
```

설치 확인:

```bash
cloudflared --version
```

---

### 4-4. Whisper.cpp 설치

음성 인식을 위해 `server/whisper.cpp` 폴더가 필요하다.
GitHub에는 용량 문제로 올리지 않고, 실행할 PC에서 직접 설치하는 것을 권장한다.

```bash
cd ~/project_robot/ros2_ws/server

git clone https://github.com/ggml-org/whisper.cpp.git

cd whisper.cpp

cmake -B build
cmake --build build -j$(nproc)

bash models/download-ggml-model.sh tiny
```

설치 후 아래 파일들이 있어야 한다.

```bash
ls ~/project_robot/ros2_ws/server/whisper.cpp/build/bin/whisper-cli
ls ~/project_robot/ros2_ws/server/whisper.cpp/models/ggml-tiny.bin
```

정상이라면 두 파일 경로가 출력된다.

---

### 4-5. YOLO 모델 준비

서버 코드에서는 `yolo11n.pt` 모델을 사용한다.

처음 실행 시 인터넷이 연결되어 있으면 Ultralytics가 모델을 자동으로 다운로드할 수 있다.
직접 확인하려면 다음 명령어를 실행한다.

```bash
python3 - <<'EOF'
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
print("YOLO model loaded")
EOF
```

실행 후 현재 디렉터리 또는 캐시 경로에 `yolo11n.pt`가 준비된다.

---

## 5. TurtleBot3 Bringup 실행

`run_web.sh`는 TurtleBot3 bringup을 자동으로 실행하지 않는다.
따라서 TurtleBot3 bringup은 별도 터미널에서 먼저 실행해야 한다.

### 5-1. TurtleBot3에 SSH 접속

```bash
ssh robot@192.168.0.10
```

### 5-2. TurtleBot3 bringup 실행

TurtleBot3에 접속한 터미널에서 다음 명령어를 실행한다.

```bash
export ROS_DOMAIN_ID=31
export ROS_LOCALHOST_ONLY=0

source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash 2>/dev/null || true

export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-01

ros2 launch turtlebot3_bringup robot.launch.py
```

이 터미널은 TurtleBot3 bringup이 실행되는 터미널이므로 끄지 않고 유지한다.

---

## 6. 웹 서버 실행

새 터미널을 열고 PC에서 다음 명령어를 실행한다.

```bash
cd ~/project_robot/ros2_ws/server
chmod +x run_web.sh
./run_web.sh
```

정상적으로 실행되면 다음과 같은 흐름이 출력된다.

```text
TurtleBot3 Web Server Launcher
[SERVER] ROS_DOMAIN_ID=31
[SERVER] ROS_LOCALHOST_ONLY=0
[SERVER] TURTLEBOT3_MODEL=burger
[SERVER] LDS_MODEL=LDS-01
FastAPI server 실행됨
Cloudflare Tunnel 실행
https://xxxxx.trycloudflare.com
```

출력된 `https://xxxxx.trycloudflare.com` 주소를 휴대폰 브라우저에서 열면 웹 조종 화면에 접속할 수 있다.

---

## 7. 휴대폰 사용 방법

### 7-1. 수동 조종

휴대폰에서 Cloudflare 링크에 접속한 뒤 방향 버튼을 누르면 TurtleBot3가 움직인다.

```text
▲ : 전진
▼ : 후진
◀ : 좌회전
▶ : 우회전
■ : 정지
```

긴급 상황에서는 `Emergency Stop` 버튼을 누른다.

---

### 7-2. 음성 명령

웹 화면의 `음성 입력` 버튼을 누르고 명령을 말한 뒤 다시 버튼을 눌러 녹음을 종료한다.

사용 가능한 음성 명령 예시는 다음과 같다.

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

### 7-3. 사람 따라가기 모드

사람 따라가기 모드는 다음 순서로 사용한다.

```text
1. 카메라 시작
2. 음성 입력
3. “사람 따라가” 말하기
4. 음성 입력 종료
5. Follow Mode ON 확인
6. 실시간 인식 시작
7. 사람을 카메라에 비추기
```

YOLO가 사람을 인식하면 사람의 화면 위치에 따라 로봇이 움직인다.

```text
사람이 화면 왼쪽에 있음  → 좌회전
사람이 화면 오른쪽에 있음 → 우회전
사람이 중앙에 있고 멀리 있음 → 전진
사람이 중앙에 있고 가까움 → 정지
사람이 보이지 않음 → 정지
```

---

## 8. 실행 확인 명령어

### 8-1. `/cmd_vel` 발행 확인

PC에서 새 터미널을 열고 다음 명령어를 실행한다.

```bash
export ROS_DOMAIN_ID=31
export ROS_LOCALHOST_ONLY=0

source /opt/ros/humble/setup.bash

ros2 topic echo /cmd_vel
```

휴대폰에서 버튼을 누르면 `/cmd_vel` 값이 출력되어야 한다.

예시:

```yaml
linear:
  x: -0.12
angular:
  z: 0.0
```

또는:

```yaml
linear:
  x: 0.0
angular:
  z: 0.8
```

---

### 8-2. 서버 상태 확인

```bash
curl http://127.0.0.1:8000/health
```

정상이라면 다음과 비슷한 응답이 출력된다.

```json
{
  "server": "ok",
  "ros_initialized": true,
  "follow_mode": false,
  "yolo_available": true,
  "yolo_model": "yolo11n.pt"
}
```

---

### 8-3. 서버 로그 확인

```bash
tail -f ~/project_robot/ros2_ws/logs/server.log
```

음성 인식이나 YOLO 요청이 들어오면 이 로그에서 확인할 수 있다.

---

## 9. 문제 해결

### 9-1. 휴대폰에서 카메라 또는 마이크가 안 될 때

휴대폰 브라우저에서 접속 주소가 반드시 `https://`로 시작해야 한다.

```text
https://xxxxx.trycloudflare.com
```

카메라와 마이크 권한을 허용해야 한다.

Chrome 기준:

```text
주소창 왼쪽 자물쇠 아이콘
→ 사이트 설정
→ 카메라 허용
→ 마이크 허용
```

권한이 꼬인 경우 사이트 권한을 삭제한 뒤 다시 접속한다.

---

### 9-2. 음성 명령이 안 될 때

Whisper.cpp 실행 파일과 모델 파일이 있는지 확인한다.

```bash
ls ~/project_robot/ros2_ws/server/whisper.cpp/build/bin/whisper-cli
ls ~/project_robot/ros2_ws/server/whisper.cpp/models/ggml-tiny.bin
```

`ffmpeg` 설치 여부도 확인한다.

```bash
ffmpeg -version
```

---

### 9-3. YOLO가 안 될 때

Ultralytics 설치 여부를 확인한다.

```bash
python3 - <<'EOF'
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
print("YOLO OK")
EOF
```

---

### 9-4. 웹은 켜졌는데 로봇이 안 움직일 때

먼저 `/cmd_vel`이 발행되는지 확인한다.

```bash
export ROS_DOMAIN_ID=31
export ROS_LOCALHOST_ONLY=0
source /opt/ros/humble/setup.bash

ros2 topic echo /cmd_vel
```

`/cmd_vel`은 나오는데 로봇이 움직이지 않으면 TurtleBot3 bringup, OpenCR, 모터 전원, ROS_DOMAIN_ID 설정을 확인해야 한다.

---

### 9-5. Cloudflare 링크가 매번 바뀌는 이유

현재 프로젝트는 Quick Tunnel 방식을 사용한다.

```bash
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2
```

Quick Tunnel은 실행할 때마다 임시 주소를 생성하므로, `run_web.sh`를 다시 실행하면 휴대폰 접속 링크가 바뀐다.

---

## 10. GitHub 업로드 시 제외 권장 파일

다음 파일과 폴더는 용량이 크거나 실행 환경마다 달라지므로 GitHub 업로드에서 제외하는 것을 권장한다.

```gitignore
__pycache__/
*.pyc

logs/
*.log

build/
install/
log/

server/whisper.cpp/
*.bin

*.pt
*.onnx
*.tflite
*.engine
*.weights

.vscode/
```

특히 아래 파일들은 직접 설치 또는 다운로드하는 방식이 좋다.

```text
server/whisper.cpp/
ggml-tiny.bin
yolo11n.pt
```

---

## 11. 전체 실행 순서 요약

### 터미널 1: TurtleBot3 bringup

```bash
ssh robot@192.168.0.10
```

TurtleBot3 안에서:

```bash
export ROS_DOMAIN_ID=31
export ROS_LOCALHOST_ONLY=0

source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash 2>/dev/null || true

export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-01

ros2 launch turtlebot3_bringup robot.launch.py
```

### 터미널 2: 웹 서버 + Cloudflare Tunnel

PC에서:

```bash
cd ~/project_robot/ros2_ws/server
./run_web.sh
```

### 휴대폰

```text
터미널에 출력된 https://xxxxx.trycloudflare.com 접속
```

---

## 12. 프로젝트 설명 요약

이 프로젝트는 TurtleBot3를 웹 기반으로 제어하고, 음성 인식과 객체 인식을 결합하여 간단한 AI 비서 로봇처럼 동작하도록 구성한 프로젝트이다.

FastAPI 서버가 웹 페이지와 ROS 2 노드를 연결하고, WebSocket을 통해 수동 조종 명령을 전달한다. 음성 명령은 Whisper.cpp를 통해 텍스트로 변환되고, 변환된 문장을 명령어로 해석하여 TurtleBot3의 `/cmd_vel` 토픽으로 발행된다. 또한 YOLO를 이용하여 카메라 영상에서 사람을 탐지하고, 사람의 위치에 따라 로봇이 회전하거나 전진하도록 하였다.
