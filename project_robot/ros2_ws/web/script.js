// ===========================================
// TurtleBot3 AI Assistant
// Manual Control + Voice Control + YOLO Person Follow
// ===========================================


// ===========================================
// WebSocket
// ===========================================

const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const ws = new WebSocket(wsProtocol + window.location.host + "/ws");


// ===========================================
// UI Elements
// ===========================================

const connection = document.getElementById("connection");
const robotState = document.getElementById("robotState");
const followModeText = document.getElementById("followModeText");

const voiceText = document.getElementById("voiceText");
const aiText = document.getElementById("aiText");
const logBox = document.getElementById("logBox");

const btnForward = document.getElementById("forward");
const btnBackward = document.getElementById("backward");
const btnLeft = document.getElementById("left");
const btnRight = document.getElementById("right");
const btnStop = document.getElementById("stop");

const btnEmergency = document.getElementById("emergency");
const btnRelease = document.getElementById("release");

const recordBtn = document.getElementById("recordBtn");

const webcam = document.getElementById("webcam");
const cameraState = document.getElementById("cameraState");
const detectResult = document.getElementById("detectResult");

const startCameraBtn = document.getElementById("startCameraBtn");
const startDetectBtn = document.getElementById("startDetectBtn");
const stopDetectBtn = document.getElementById("stopDetectBtn");


// ===========================================
// Log
// ===========================================

function addLog(text) {
    const now = new Date();

    const time =
        now.getHours().toString().padStart(2, "0") + ":" +
        now.getMinutes().toString().padStart(2, "0") + ":" +
        now.getSeconds().toString().padStart(2, "0");

    const div = document.createElement("div");
    div.className = "log-item";
    div.innerHTML = `[${time}] ${text}`;

    logBox.prepend(div);
}


// ===========================================
// Follow Mode UI
// ===========================================

function updateFollowModeUI(isOn) {
    if (isOn) {
        followModeText.innerHTML = "Follow Mode: ON";
    } else {
        followModeText.innerHTML = "Follow Mode: OFF";
    }
}


// ===========================================
// WebSocket Send
// ===========================================

function sendJSON(data) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    } else {
        addLog("WebSocket is not connected");
    }
}


// ===========================================
// WebSocket Events
// ===========================================

ws.onopen = () => {
    connection.innerHTML = "🟢 Connected";
    addLog("Connected");

    sendJSON({
        type: "status"
    });
};

ws.onclose = () => {
    connection.innerHTML = "🔴 Disconnected";
    addLog("Disconnected");
};

ws.onerror = () => {
    connection.innerHTML = "🔴 WebSocket Error";
    addLog("WebSocket Error");
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "status") {
        if (msg.robot_state) {
            robotState.innerHTML = msg.robot_state;
        }

        if (typeof msg.follow_mode !== "undefined") {
            updateFollowModeUI(msg.follow_mode);
        }

        if (msg.message) {
            addLog(msg.message);
        }
    }

    else if (msg.type === "voice") {
        if (msg.stt) {
            voiceText.innerHTML = msg.stt;
        }

        if (msg.ai) {
            aiText.innerHTML = msg.ai;
        }

        addLog("Voice: " + msg.stt);
    }

    else if (msg.type === "error") {
        addLog("ERROR: " + msg.message);
    }
};


// ===========================================
// Manual Control
// ===========================================

function control(command) {
    sendJSON({
        type: "control",
        command: command
    });
}


// 방향 버튼은 누르고 있는 동안 이동, 떼면 정지
function holdButton(button, command) {
    function start(e) {
        e.preventDefault();
        control(command);
    }

    function stop(e) {
        e.preventDefault();
        control("stop");
    }

    button.addEventListener("mousedown", start);
    button.addEventListener("mouseup", stop);
    button.addEventListener("mouseleave", stop);

    button.addEventListener("touchstart", start, { passive: false });
    button.addEventListener("touchend", stop, { passive: false });
    button.addEventListener("touchcancel", stop, { passive: false });
}

holdButton(btnForward, "forward");
holdButton(btnBackward, "backward");
holdButton(btnLeft, "left");
holdButton(btnRight, "right");

btnStop.onclick = () => {
    control("stop");
};


// ===========================================
// Emergency
// ===========================================

btnEmergency.onclick = () => {
    sendJSON({
        type: "emergency"
    });

    updateFollowModeUI(false);
    addLog("Emergency Stop");
};

btnRelease.onclick = () => {
    sendJSON({
        type: "release"
    });

    updateFollowModeUI(false);
    addLog("Emergency Released");
};


// ===========================================
// Voice Recording
// ===========================================

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

recordBtn.onclick = async () => {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true
            });

            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => {
                audioChunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, {
                    type: "audio/webm"
                });

                const formData = new FormData();
                formData.append("file", audioBlob, "voice.webm");

                addLog("Sending audio...");

                try {
                    const res = await fetch("/voice", {
                        method: "POST",
                        body: formData
                    });

                    if (!res.ok) {
                        throw new Error(await res.text());
                    }

                    const data = await res.json();

                    voiceText.innerHTML = data.speech;
                    aiText.innerHTML = data.command;

                    if (typeof data.follow_mode !== "undefined") {
                        updateFollowModeUI(data.follow_mode);
                    }

                    if (data.message) {
                        addLog(data.message);
                    }

                    addLog("STT: " + data.speech);
                    addLog("CMD: " + data.command);
                }

                catch (err) {
                    addLog("Voice Error: " + err);
                }
            };

            mediaRecorder.start();
            isRecording = true;

            recordBtn.innerHTML = "⏹ 녹음 중지";
            addLog("Recording started");
        }

        catch (err) {
            addLog("Mic Error: " + err);
        }
    }

    else {
        mediaRecorder.stop();
        isRecording = false;

        recordBtn.innerHTML = "🎤 음성 입력";
        addLog("Recording stopped");
    }
};


// ===========================================
// Camera / YOLO Detection
// ===========================================

let cameraStream = null;
let detectTimer = null;
let isDetecting = false;

const DETECT_INTERVAL_MS = 700;
const JPEG_QUALITY = 0.75;


startCameraBtn.onclick = async () => {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: "environment"
            },
            audio: false
        });

        webcam.srcObject = cameraStream;

        await new Promise((resolve) => {
            webcam.onloadedmetadata = () => {
                resolve();
            };
        });

        cameraState.innerHTML = "✅ 카메라 준비 완료";
        addLog("Camera started");
    }

    catch (err) {
        cameraState.innerHTML = "❌ 카메라 시작 실패";
        addLog("Camera error: " + err);
    }
};


startDetectBtn.onclick = () => {
    if (!cameraStream) {
        addLog("Camera is not started");
        detectResult.innerHTML = "카메라를 먼저 시작하세요.";
        return;
    }

    if (isDetecting) {
        return;
    }

    isDetecting = true;
    cameraState.innerHTML = "✅ 실시간 인식 중";
    addLog("YOLO detection started");

    detectTimer = setInterval(() => {
        sendFrameToServer();
    }, DETECT_INTERVAL_MS);
};


stopDetectBtn.onclick = () => {
    stopDetectionLoop();
};


function stopDetectionLoop() {
    if (detectTimer !== null) {
        clearInterval(detectTimer);
        detectTimer = null;
    }

    isDetecting = false;
    cameraState.innerHTML = "⏸ 실시간 인식 중지";
    detectResult.innerHTML = "탐지 중지됨";

    addLog("YOLO detection stopped");
}


async function sendFrameToServer() {
    if (!webcam || webcam.readyState < 2) {
        return;
    }

    const canvas = document.createElement("canvas");

    const width = webcam.videoWidth;
    const height = webcam.videoHeight;

    if (width === 0 || height === 0) {
        return;
    }

    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(webcam, 0, 0, width, height);

    canvas.toBlob(async (blob) => {
        if (!blob) {
            return;
        }

        const formData = new FormData();
        formData.append("file", blob, "frame.jpg");

        try {
            const res = await fetch("/detect", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                throw new Error(await res.text());
            }

            const data = await res.json();

            updateFollowModeUI(data.follow_mode);

            if (data.robot_state) {
                robotState.innerHTML = data.robot_state;
            }

            if (data.detected) {
                const confidence = (data.confidence * 100).toFixed(1);
                const center = (data.center_x_ratio * 100).toFixed(1);
                const heightRatio = (data.height_ratio * 100).toFixed(1);

                detectResult.innerHTML =
                    "사람 감지 / " +
                    "명령: " + data.command +
                    " / 신뢰도: " + confidence + "%" +
                    " / 위치: " + center + "%" +
                    " / 크기: " + heightRatio + "%";
            }

            else {
                detectResult.innerHTML =
                    "사람 미감지 / 명령: " + data.command;
            }
        }

        catch (err) {
            detectResult.innerHTML = "탐지 오류";
            addLog("Detect Error: " + err);
        }

    }, "image/jpeg", JPEG_QUALITY);
}
