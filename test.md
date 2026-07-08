# 단위 테스트 결과표 (TEST.md)

| ID | 대상 | 테스트 내용 | 기대 결과 | 실제 결과 | 판정 | 담당 |
| :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| U-01 | ROS2 | `/web_control_node` 활성화 및 마스터 등록 | ROS2 환경 내 웹 제어 노드가 정상 실행 상태를 유지 | ros2 node list 명령 시 /web_control_node 확인 | ✅ | 김민성 |
| U-02 | 백엔드 | 자연어 파서(parse_command) 키워드 매칭 | 추출된 한글 문장에서 주행 핵심 명령어 매핑 및 분류 | [CMD] forward / [CMD] left 변환 성공 | ✅ | 권재현 |
| U-03 | 웹/백 | 수동 제어 패드 패킷 송수신 테스트 | 버튼 클릭 시 웹소켓을 통해 해당 방향 명령 전달 | CMD : forward/backward/right/left/stop 로그 확인 | ✅ | 박상욱 |
| U-04 | AI | Whisper.cpp 한국어 음성 인식 (STT) | "앞으로가.", "왼쪽으로 가" 발화 시 정확한 텍스트 추출 | [STT] 앞으로가. / [STT] 왼쪽으로 가 확인 | ✅ | 권주원 |
| U-05 | 제어 | 시스템 비상 정지 (EMERGENCY STOP) | 웹앱 비상 정지 버튼 클릭 시 로봇 즉각 감속 및 잠금 | [WARN] EMERGENCY STOP 로그 발생 및 구동 정지 | ✅ | 김동혁 |
