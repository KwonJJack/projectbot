#!/usr/bin/env bash

set -e

# ==============================
# 경로 설정
# ==============================

SERVER_DIR="/home/robot/project_robot/ros2_ws/server"
ROS2_WS_DIR="/home/robot/project_robot/ros2_ws"
LOG_DIR="$ROS2_WS_DIR/logs"

mkdir -p "$LOG_DIR"

# ==============================
# 터틀봇 설정
# ==============================

ROBOT_USER="ubuntu"
ROBOT_IP="터틀봇_IP"

TURTLEBOT_MODEL="burger"
ROS_DOMAIN_ID_VALUE="30"

SERVER_PID=""

# ==============================
# 종료 처리
# ==============================

cleanup() {
    echo ""
    echo "종료 중..."

    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi

    echo "종료 완료"
}

trap cleanup EXIT INT TERM

echo "======================================"
echo " TurtleBot3 AI Assistant Demo Launcher"
echo "======================================"
echo ""

# ==============================
# 1. TurtleBot bringup 실행
# ==============================

echo "[1/3] TurtleBot bringup 실행"

if [ "$ROBOT_IP" = "터틀봇_IP" ]; then
    echo "ROBOT_IP가 아직 설정되지 않았음."
    echo "server/run_demo.sh 파일에서 ROBOT_IP를 실제 터틀봇 IP로 바꿔야 함."
    echo "예: ROBOT_IP=\"192.168.0.20\""
    echo ""
else
    ssh -o StrictHostKeyChecking=accept-new "$ROBOT_USER@$ROBOT_IP" "
        export ROS_DOMAIN_ID=$ROS_DOMAIN_ID_VALUE
        export ROS_LOCALHOST_ONLY=0

        source /opt/ros/humble/setup.bash
        source ~/turtlebot3_ws/install/setup.bash 2>/dev/null || true

        export TURTLEBOT3_MODEL=$TURTLEBOT_MODEL

        ros2 launch turtlebot3_bringup robot.launch.py
    " > "$LOG_DIR/bringup.log" 2>&1 &

    echo "TurtleBot bringup 실행 요청 완료"
    echo "로그: $LOG_DIR/bringup.log"
    sleep 6
fi

# ==============================
# 2. FastAPI 서버 실행
# ==============================

echo ""
echo "[2/3] FastAPI server 실행"

cd "$SERVER_DIR"

export ROS_DOMAIN_ID=$ROS_DOMAIN_ID_VALUE
export ROS_LOCALHOST_ONLY=0

source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=$TURTLEBOT_MODEL

python3 server.py > "$LOG_DIR/server.log" 2>&1 &

SERVER_PID=$!

sleep 5

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "server.py 실행 실패"
    echo ""
    echo "---- server.log ----"
    cat "$LOG_DIR/server.log"
    exit 1
fi

echo "FastAPI server 실행됨. PID: $SERVER_PID"
echo "로그: $LOG_DIR/server.log"

# ==============================
# 3. Cloudflare Tunnel 실행
# ==============================

echo ""
echo "[3/3] Cloudflare Tunnel 실행"
echo ""
echo "아래에 나오는 https://xxxxx.trycloudflare.com 주소를 휴대폰에서 열면 됨."
echo "이 터미널은 끄지 말고 유지해야 함."
echo ""

cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2

