# Voice Assistant TurtleBot ROS2 Project

## 1. 프로젝트 개요

본 프로젝트는 Raspberry Pi 4 기반 TurtleBot에 음성 인식 기반 제어
시스템을 구현하는 것을 목표로 한다.

사용자는 웹 브라우저를 통해 로봇 제어 페이지에 접속하고, 음성 입력 또는
수동 버튼 입력으로 TurtleBot을 제어할 수 있다.

음성 입력은 Whisper.cpp 기반 STT(Speech-To-Text)를 통해 한국어 음성을
텍스트로 변환하고, 변환된 명령어를 분석하여 ROS2 `/cmd_vel` 토픽으로
이동 명령을 전달한다.

------------------------------------------------------------------------

## 2. 주요 기능

### 2.1 웹 기반 로봇 제어

-   웹 브라우저 기반 제어 UI 제공
-   WebSocket 통신을 통한 실시간 명령 전달
-   전진 / 후진 / 좌회전 / 우회전 / 정지 버튼 제공
-   비상 정지 기능 구현

### 2.2 음성 제어

-   웹 브라우저 마이크 입력 사용
-   WebM 음성 데이터 서버 전송
-   FFmpeg를 이용한 WAV 변환
-   Whisper.cpp 기반 음성 인식 수행
-   한국어 명령 분석 후 로봇 이동 명령 변환

지원 명령:

  음성 명령       ROS2 Command
  --------------- --------------
  앞으로 가       forward
  뒤로 가         backward
  왼쪽으로 가     left
  오른쪽으로 가   right
  멈춰            stop

------------------------------------------------------------------------

## 3. 시스템 구성

    [Mobile / PC Browser]
              |
              | HTTP + WebSocket
              |
          [FastAPI Server]
              |
              |
       +------+------+
       |             |
    Whisper.cpp    ROS2 Node
    (STT)          (/cmd_vel)
                      |
                      |
                 TurtleBot Drive Node
                      |
                      |
                  Motor Controller

------------------------------------------------------------------------

## 4. 사용 기술

### Hardware

-   Raspberry Pi 4 Model B 4GB
-   TurtleBot 플랫폼
-   DC Motor Driver

### Software

-   Ubuntu Linux
-   ROS2 Humble
-   FastAPI
-   WebSocket
-   Whisper.cpp
-   FFmpeg
-   Python

------------------------------------------------------------------------

## 5. AI 기술 적용

본 프로젝트에서는 OpenAI API 대신 Raspberry Pi 환경에서 동작 가능한
Whisper.cpp를 사용하였다.

### 사용 모델

-   Whisper Tiny Model (`ggml-tiny.bin`)

### AI 처리 과정

    음성 입력
        |
        v
    Web Browser Recording
        |
        v
    FastAPI Server
        |
        v
    FFmpeg 변환
        |
        v
    Whisper.cpp STT
        |
        v
    Command Parsing
        |
        v
    ROS2 /cmd_vel
        |
        v
    Robot Movement

------------------------------------------------------------------------

## 6. 실행 방법

### 1) ROS2 환경 실행

``` bash
source /opt/ros/humble/setup.bash
```

### 2) TurtleBot Bringup 실행

``` bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py
```

### 3) Voice Assistant Server 실행

``` bash
cd ~/voice_assistant/server
python3 server.py
```

실행 후:

    http://<RaspberryPi_IP>:8000

접속하여 웹 제어 화면 사용

------------------------------------------------------------------------

## 7. 프로젝트 목표

-   ROS2 기반 로봇 제어 구조 이해
-   웹 인터페이스와 ROS2 통신 연동
-   음성 인식 AI 기술 적용
-   실제 로봇 이동 제어 구현
-   임베디드 환경에서 AI 모델 경량화 적용
