// ===========================================
// TurtleBot3 AI Assistant - v0.3
// Voice + Manual Control Integrated
// ===========================================

// ----------------------------
// WebSocket
// ----------------------------

const wsProtocol =
    window.location.protocol === "https:" ? "wss://" : "ws://";

const ws = new WebSocket(
    wsProtocol + window.location.host + "/ws"
);

// ----------------------------
// UI Elements
// ----------------------------

const connection = document.getElementById("connection");
const robotState = document.getElementById("robotState");
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

// ----------------------------
// Log
// ----------------------------

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

// ----------------------------
// WebSocket send
// ----------------------------

function sendJSON(data) {

    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// ----------------------------
// WebSocket Events
// ----------------------------

ws.onopen = () => {
    connection.innerHTML = "🟢 Connected";
    addLog("Connected");
};

ws.onclose = () => {
    connection.innerHTML = "🔴 Disconnected";
    addLog("Disconnected");
};

ws.onmessage = (event) => {

    const msg = JSON.parse(event.data);

    if (msg.type === "status") {

        if (msg.robot_state) {
            robotState.innerHTML = msg.robot_state;
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

        addLog(`Voice: ${msg.stt}`);
    }

    else if (msg.type === "error") {
        addLog("ERROR: " + msg.message);
    }
};

// ----------------------------
// Manual Control
// ----------------------------

function control(command) {

    sendJSON({
        type: "control",
        command: command
    });
}

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
    button.addEventListener("touchend", stop);
}

holdButton(btnForward, "forward");
holdButton(btnBackward, "backward");
holdButton(btnLeft, "left");
holdButton(btnRight, "right");

btnStop.onclick = () => {
    control("stop");
};

// ----------------------------
// Emergency
// ----------------------------

btnEmergency.onclick = () => {
    sendJSON({ type: "emergency" });
    addLog("Emergency Stop");
};

btnRelease.onclick = () => {
    sendJSON({ type: "release" });
    addLog("Emergency Released");
};

// ----------------------------
// 🎤 Voice Recording (NEW)
// ----------------------------

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

recordBtn.onclick = async () => {

    if (!isRecording) {

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

            addLog("🎤 Sending audio...");

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

                addLog("STT: " + data.speech);
                addLog("CMD: " + data.command);

            } catch (err) {
                addLog("Voice Error: " + err);
            }
        };

        mediaRecorder.start();
        isRecording = true;

        recordBtn.innerHTML = "⏹ Stop Recording";

        addLog("🎤 Recording started");

    } else {

        mediaRecorder.stop();
        isRecording = false;

        recordBtn.innerHTML = "🎤 Voice Input";

        addLog("🛑 Recording stopped");
    }
};

// ----------------------------
// Init request
// ----------------------------

ws.addEventListener("open", () => {
    sendJSON({ type: "status" });
});
