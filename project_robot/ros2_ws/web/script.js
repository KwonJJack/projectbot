// ==============================
// DOM
// ==============================

const connectionEl = document.getElementById("connection");
const robotState = document.getElementById("robotState");
const followModeText = document.getElementById("followModeText");

const voiceText = document.getElementById("voiceText");
const aiText = document.getElementById("aiText");
const recordBtn = document.getElementById("recordBtn");

const webcam = document.getElementById("webcam");
const cameraState = document.getElementById("cameraState");
const detectResult = document.getElementById("detectResult");

const startCameraBtn = document.getElementById("startCameraBtn");
const startDetectBtn = document.getElementById("startDetectBtn");
const stopCameraBtn = document.getElementById("stopCameraBtn");

const forwardBtn = document.getElementById("forward");
const backwardBtn = document.getElementById("backward");
const leftBtn = document.getElementById("left");
const rightBtn = document.getElementById("right");
const stopBtn = document.getElementById("stop");

const emergencyBtn = document.getElementById("emergency");
const releaseBtn = document.getElementById("release");

const logBox = document.getElementById("logBox");

// ==============================
// State
// ==============================

let ws = null;

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

let cameraStream = null;
let detectTimer = null;
let isDetecting = false;
let isSendingFrame = false;

const DETECT_INTERVAL_MS = 700;
const DETECT_IMAGE_WIDTH = 320;

const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");

// ==============================
// Utils
// ==============================

function addLog(message) {
    const item = document.createElement("div");
    item.className = "log-item";
    item.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;

    logBox.appendChild(item);
    logBox.scrollTop = logBox.scrollHeight;
}

function updateFollowMode(value) {
    const isOn = value === true || value === "true" || value === "ON";

    followModeText.innerText = isOn
        ? "Follow Mode: ON"
        : "Follow Mode: OFF";

    followModeText.style.color = isOn ? "#009688" : "#333";
}

function updateStatus(data) {
    if (!data) {
        return;
    }

    if (data.robot_state !== undefined) {
        robotState.innerText = data.robot_state;
    }

    if (data.follow_mode !== undefined) {
        updateFollowMode(data.follow_mode);
    }
}

function getSpeechText(data) {
    return data.speech || data.stt || data.text || data.voice_text || "";
}

// ==============================
// WebSocket
// ==============================

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsUrl = protocol + window.location.host + "/ws";

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        connectionEl.innerText = "🟢 Connected";
        connectionEl.style.color = "#2e7d32";
        addLog("WebSocket connected");

        sendJSON({
            type: "status"
        });
    };

    ws.onclose = () => {
        connectionEl.innerText = "🔴 Disconnected";
        connectionEl.style.color = "#d32f2f";
        addLog("WebSocket disconnected");

        setTimeout(connectWebSocket, 1500);
    };

    ws.onerror = () => {
        connectionEl.innerText = "🔴 Error";
        connectionEl.style.color = "#d32f2f";
        addLog("WebSocket error");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            updateStatus(data);

            if (data.message) {
                addLog(data.message);
            }

        } catch (error) {
            addLog("WebSocket parse error");
        }
    };
}

function sendJSON(data) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        addLog("WebSocket not connected");
        return;
    }

    ws.send(JSON.stringify(data));
}

// ==============================
// Control
// ==============================

function control(command) {
    sendJSON({
        type: "control",
        command: command
    });
}

function bindHoldButton(button, command) {
    button.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        control(command);
    });

    button.addEventListener("pointerup", (event) => {
        event.preventDefault();
        control("stop");
    });

    button.addEventListener("pointerleave", () => {
        control("stop");
    });

    button.addEventListener("touchcancel", () => {
        control("stop");
    });
}

bindHoldButton(forwardBtn, "forward");
bindHoldButton(backwardBtn, "backward");
bindHoldButton(leftBtn, "left");
bindHoldButton(rightBtn, "right");

stopBtn.onclick = () => {
    control("stop");
};

emergencyBtn.onclick = () => {
    stopDetectionLoop();
    sendJSON({
        type: "emergency"
    });
};

releaseBtn.onclick = () => {
    sendJSON({
        type: "release"
    });
};

// ==============================
// Camera / Detection
// ==============================

startCameraBtn.onclick = async () => {
    await startCamera();
};

startDetectBtn.onclick = async () => {
    await startDetectionLoop();
};

stopCameraBtn.onclick = () => {
    stopCamera();
};

async function startCamera() {
    if (cameraStream) {
        cameraState.innerHTML = "✅ 카메라 이미 켜짐";
        addLog("Camera already started");
        return true;
    }

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: {
                    ideal: "environment"
                },
                width: {
                    ideal: 640
                },
                height: {
                    ideal: 480
                }
            },
            audio: false
        });

        webcam.srcObject = cameraStream;
        await webcam.play();

        cameraState.innerHTML = "✅ 카메라 켜짐";
        detectResult.innerHTML = "카메라 준비 완료. “사람 따라가” 음성 명령 시 자동 인식 시작.";

        addLog("Camera started");

        return true;

    } catch (error) {
        cameraState.innerHTML = "❌ 카메라 오류";
        detectResult.innerHTML = "카메라 시작 실패. 권한을 확인하세요.";

        addLog("Camera error: " + error.message);

        return false;
    }
}

async function startDetectionLoop() {
    if (!cameraStream) {
        cameraState.innerHTML = "⚠️ 카메라를 먼저 시작하세요";
        detectResult.innerHTML = "카메라 시작 후 다시 시도하세요.";
        addLog("Detection start failed: camera is off");
        return;
    }

    if (isDetecting) {
        detectResult.innerHTML = "이미 실시간 인식 중";
        return;
    }

    isDetecting = true;

    cameraState.innerHTML = "🟢 실시간 인식 중";
    detectResult.innerHTML = "YOLO 사람 인식 중...";

    addLog("YOLO detection started");

    await sendFrameToServer();

    detectTimer = setInterval(() => {
        sendFrameToServer();
    }, DETECT_INTERVAL_MS);
}

function stopDetectionLoop() {
    if (detectTimer !== null) {
        clearInterval(detectTimer);
        detectTimer = null;
    }

    isDetecting = false;

    if (cameraStream) {
        cameraState.innerHTML = "✅ 카메라 켜짐 / 인식 중지";
        detectResult.innerHTML = "탐지 중지됨";
    } else {
        cameraState.innerHTML = "🔌 카메라 꺼짐";
        detectResult.innerHTML = "카메라 비활성화됨";
    }

    addLog("YOLO detection stopped");
}

function stopCamera() {
    stopDetectionLoop();

    if (cameraStream) {
        cameraStream.getTracks().forEach((track) => {
            track.stop();
        });

        cameraStream = null;
    }

    webcam.srcObject = null;

    cameraState.innerHTML = "🔌 카메라 꺼짐";
    detectResult.innerHTML = "카메라 비활성화됨";

    control("stop");

    addLog("Camera stopped");
}

async function sendFrameToServer() {
    if (!cameraStream || !isDetecting || isSendingFrame) {
        return;
    }

    if (!webcam || webcam.readyState < 2) {
        return;
    }

    isSendingFrame = true;

    try {
        const videoWidth = webcam.videoWidth || 640;
        const videoHeight = webcam.videoHeight || 480;

        const targetWidth = DETECT_IMAGE_WIDTH;
        const targetHeight = Math.round(videoHeight * (targetWidth / videoWidth));

        canvas.width = targetWidth;
        canvas.height = targetHeight;

        ctx.drawImage(webcam, 0, 0, targetWidth, targetHeight);

        const blob = await new Promise((resolve) => {
            canvas.toBlob(resolve, "image/jpeg", 0.55);
        });

        if (!blob) {
            return;
        }

        const formData = new FormData();
        formData.append("file", blob, "frame.jpg");

        const response = await fetch("/detect", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        updateStatus(data);

        if (data.detected) {
            const confidence = Math.round((data.confidence || 0) * 100);
            const command = data.command || "-";

            detectResult.innerHTML =
                `사람 감지 / 신뢰도 ${confidence}% / 명령: ${command}`;
        } else {
            detectResult.innerHTML = "사람 미감지 / 정지";
        }

    } catch (error) {
        detectResult.innerHTML = "인식 요청 실패";
        addLog("Detect error: " + error.message);

    } finally {
        isSendingFrame = false;
    }
}

// ==============================
// Voice
// ==============================

recordBtn.onclick = async () => {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
};

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        audioChunks = [];

        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach((track) => {
                track.stop();
            });

            await sendVoiceToServer();
        };

        mediaRecorder.start();

        isRecording = true;

        recordBtn.innerHTML = "⏹ 녹음 중지";
        voiceText.innerHTML = "듣는 중...";
        aiText.innerHTML = "분석 대기";

        addLog("Voice recording started");

    } catch (error) {
        voiceText.innerHTML = "마이크 오류";
        addLog("Microphone error: " + error.message);
    }
}

function stopRecording() {
    if (!mediaRecorder || !isRecording) {
        return;
    }

    mediaRecorder.stop();

    isRecording = false;

    recordBtn.innerHTML = "🎤 음성 입력";

    addLog("Voice recording stopped");
}

async function sendVoiceToServer() {
    try {
        const audioBlob = new Blob(audioChunks, {
            type: "audio/webm"
        });

        const formData = new FormData();
        formData.append("file", audioBlob, "voice.webm");

        voiceText.innerHTML = "분석 중...";
        aiText.innerHTML = "서버 전송 중...";

        const response = await fetch("/voice", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = data.detail || "voice request failed";
            throw new Error(detail);
        }

        const speech = getSpeechText(data);
        const command = data.command || "-";

        voiceText.innerHTML = speech || "(인식 결과 없음)";
        aiText.innerHTML = command;

        updateStatus(data);

        addLog(`Voice: ${speech} → ${command}`);

        if (command === "follow_person" || data.follow_mode === true) {
            updateFollowMode(true);

            if (cameraStream) {
                detectResult.innerHTML = "사람 따라가기 음성 인식됨. 실시간 인식 자동 시작.";
                await startDetectionLoop();
            } else {
                detectResult.innerHTML = "사람 따라가기 ON. 카메라 시작 후 다시 말하거나 인식 시작을 누르세요.";
                cameraState.innerHTML = "⚠️ 카메라 꺼짐";
                addLog("Follow mode ON, but camera is off");
            }

            return;
        }

        if (
            command === "stop" ||
            command === "follow_stop"
        ) {
            updateFollowMode(false);
            stopDetectionLoop();
        }

    } catch (error) {
        voiceText.innerHTML = "음성 처리 실패";
        aiText.innerHTML = "-";
        addLog("Voice error: " + error.message);
    }
}

// ==============================
// Safety
// ==============================

window.addEventListener("beforeunload", () => {
    if (cameraStream) {
        cameraStream.getTracks().forEach((track) => {
            track.stop();
        });
    }

    control("stop");
});

// ==============================
// Start
// ==============================

connectWebSocket();
