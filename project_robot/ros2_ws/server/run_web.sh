#!/usr/bin/env bash

set -e

BASE_DIR="/home/robot/project_robot/ros2_ws"
SERVER_DIR="$BASE_DIR/server"
LOG_DIR="$BASE_DIR/logs"

ROS_DOMAIN_ID_VALUE="31"
TURTLEBOT_MODEL="burger"
LDS_MODEL_VALUE="LDS-01"

mkdir -p "$LOG_DIR"

SERVER_PID=""

cleanup() {
    echo ""
    echo "run_web.sh 종료됨."

    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi

    echo "FastAPI server 종료 처리 완료"
}

trap cleanup EXIT INT TERM

echo "======================================"
echo " TurtleBot3 Web Server Launcher"
echo "======================================"
echo ""

cd "$SERVER_DIR"

export ROS_DOMAIN_ID=$ROS_DOMAIN_ID_VALUE
export ROS_LOCALHOST_ONLY=0
export TURTLEBOT3_MODEL=$TURTLEBOT_MODEL
export LDS_MODEL=$LDS_MODEL_VALUE

source /opt/ros/humble/setup.bash

echo "[SERVER] ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "[SERVER] ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY"
echo "[SERVER] TURTLEBOT3_MODEL=$TURTLEBOT3_MODEL"
echo "[SERVER] LDS_MODEL=$LDS_MODEL"
echo ""

pkill -f "python3 server.py" 2>/dev/null || true
sleep 1

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
echo ""

echo "서버 상태 확인:"
curl -s http://127.0.0.1:8000/health || true
echo ""
echo ""

echo "Cloudflare Tunnel 실행"
echo "아래 https://xxxxx.trycloudflare.com 주소를 휴대폰에서 열면 됨."
echo ""

cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2

