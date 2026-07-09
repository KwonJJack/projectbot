# ROS2 Topic & Communication Interface Definition

## 1. System Communication Overview

본 프로젝트는 Whisper.cpp 기반 음성 인식 시스템과 FastAPI 서버를 이용하여 TurtleBot3를 제어하는 ROS2 기반 음성 제어 시스템입니다.

### 전체 통신 구조

```
User Voice
    ↓
Whisper.cpp (Speech To Text)
    ↓
FastAPI Server
    ↓
ROS2 Node (web_bridge)
    ↓
/cmd_vel Topic
    ↓
TurtleBot3 Drive Controller
    ↓
Robot Motion
```


FastAPI 서버는 ROS2 Node 역할을 수행하며, 음성 명령 및 웹 제어 명령을 ROS2 Topic 메시지로 변환하여 TurtleBot3 구동 노드에 전달합니다.

---

## 2. ROS2 Topic Interface Definition


## Topic List

| 토픽명 | 메시지 타입 | 발행자 | 구독자 | 주기 | 성격 | QoS |
|---|---|---|---|---|---|---|
| `/cmd_vel` | geometry_msgs/msg/Twist | web_bridge | TurtleBot3 Drive Controller | 10Hz | 연속 제어 | RELIABLE |
| `/rosout` | rcl_interfaces/msg/Log | ROS2 Node | rosout | 이벤트 발생 시 | 로그 이벤트 | RELIABLE |
| `/parameter_events` | rcl_interfaces/msg/ParameterEvent | ROS2 Node | Parameter Listener | 이벤트 발생 시 | 파라미터 이벤트 | RELIABLE |


---

## 3. `/cmd_vel` Interface


## Purpose

웹 기반 수동 제어 및 Whisper.cpp 음성 인식 결과를
TurtleBot3 이동 명령으로 전달하기 위한 ROS2 Topic.


---

## Message Type


geometry_msgs/msg/Twist



---

## Publisher


web_bridge



FastAPI 서버 내부 ROS2 Node에서 생성된 이동 명령을
`/cmd_vel` Topic으로 publish 한다.


---

## Subscriber


TurtleBot3 Drive Controller


`/cmd_vel` 메시지를 수신하여
TurtleBot3의 이동 방향 및 속도를 제어한다.


---

## Frequency


10Hz

100ms 주기로 현재 이동 명령 상태를 publish 한다.


---

## Message Field


| Field | Description |
|---|---|
| `linear.x` | 전진 / 후진 속도 |
| `angular.z` | 좌 / 우 회전 속도 |
| `linear.y` | 사용하지 않음 |
| `linear.z` | 사용하지 않음 |
| `angular.x` | 사용하지 않음 |
| `angular.y` | 사용하지 않음 |


---

## 4. `/cmd_vel` Message Example

### Forward
```
linear.x = 0.12
angular.z = 0.0
```

### Backward
```
linear.x = -0.12
angular.z = 0.0
```

### Left Turn
```
linear.x = 0.0
angular.z = 0.8
```

### Right Turn
```
linear.x = 0.0
angular.z = -0.8
```

### Stop
```
linear.x = 0.0
angular.z = 0.0
```

---

## 5. Non-ROS Communication Interface

### WebSocket Interface

FastAPI 서버와 Web Browser 간 실시간 제어 명령 전달을 위해 WebSocket 통신을 사용합니다.

| 항목 | 내용 |
|---|---|
| Protocol | WebSocket |
| Endpoint | /ws |
| Client | Web Browser |
| Server | FastAPI |
| Data Format | JSON |

---

## 6. WebSocket Message Format

### Control Request

Client에서 FastAPI 서버로 전달하는 JSON 형식

**Example:**

```json
{
    "type": "control",
    "command": "forward"
}
```

---

## 7. Supported Command

| Command | Meaning | ROS2 Output |
|---|---|---|
| forward | 전진 | linear.x = 0.12 |
| backward | 후진 | linear.x = -0.12 |
| left | 좌회전 | angular.z = 0.8 |
| right | 우회전 | angular.z = -0.8 |
| stop | 정지 | linear.x = 0.0, angular.z = 0.0 |

---

## 8. Node Interface Definition

### FastAPI ROS2 Bridge Node

**Node Name:** `web_bridge`

**Responsibility:**
- WebSocket Client 요청 처리
- Whisper.cpp 음성 명령 결과 처리
- Command Mapping
- /cmd_vel Publish

### TurtleBot3 Control Node

**Responsibility:**
- /cmd_vel Subscribe
- Differential Drive 계산
- Motor Velocity Control

---

## 9. QoS Policy

### /cmd_vel

| Parameter | Value |
|---|---|
| Reliability | RELIABLE |
| Durability | VOLATILE |
| History | KEEP_LAST |
| Depth | 10 |

연속적인 이동 제어 명령 전달이 목적이므로 신뢰성 있는 전달 방식을 사용합니다.

---

## 10. Hardware Interface

본 프로젝트에서는 다음 인터페이스를 사용하지 않습니다.

| Interface | Usage |
|---|---|
| Camera | Not Used |
| Image Topic | Not Used |
| LCD Display | Not Used |
Arduino MCU	Not Used
Ultrasonic Sensor	Not Used
LiDAR Data Topic (/scan)	Not Used

현재 시스템의 핵심 제어 인터페이스는 다음과 같다.

Whisper.cpp
     ↓
FastAPI
     ↓
web_bridge ROS2 Node
     ↓
/cmd_vel
     ↓
TurtleBot3 Drive Controller
     ↓
Robot Movement
