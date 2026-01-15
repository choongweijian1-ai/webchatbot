const chatBox = document.getElementById("chatBox");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

const explainText = document.getElementById("explainText");


function addLine(who, text) {
  const line = `${who}: ${text}\n`;
  chatBox.textContent += line;
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendChat() {
  const msg = chatInput.value.trim();
  if (!msg) return;

  addLine("You", msg);
  chatInput.value = "";

  let res;
  try {
    res = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin", // 🔑 REQUIRED for Flask sessions (quiz)
      body: JSON.stringify({message: msg})
    });
  } catch (err) {
    console.error(err);
    addLine("Bot", "⚠️ Network error. Please try again.");
    return;
  }

  let data;
  try {
    data = await res.json();
  } catch (err) {
    console.error(err);
    addLine("Bot", "⚠️ Server returned invalid response.");
    return;
  }

  if (data.type === "explain") {
    // Update panel text + draw related gate/circuit if desired
    showExplanation(data.topic);
    addLine("Bot", `Opened explanation for ${data.topic.toUpperCase()}.`);
    return;
  }

  addLine("Bot", data.text);
}

sendBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

async function clearChat() {
  // Clear UI immediately
  chatBox.textContent = "";

  // Tell backend to clear session state
  try {
    await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin",
      body: JSON.stringify({ message: "/clear" })
    });
  } catch (err) {
    console.error(err);
  }

  addLine("Bot", "🧹 Chat cleared. Ask a question or type /quiz to start.");
}

clearBtn.addEventListener("click", clearChat);



// ------------------- Calculators -------------------
document.getElementById("calcOhmBtn").addEventListener("click", async () => {
  const V = document.getElementById("V").value;
  const I = document.getElementById("I").value;
  const R = document.getElementById("R").value;

  const res = await fetch("/api/ohm", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({V, I, R})
  });

  const data = await res.json();
  document.getElementById("ohmResult").textContent = data.result;
});

document.getElementById("calcResBtn").addEventListener("click", async () => {
  const values = document.getElementById("resistors").value;

  const res = await fetch("/api/resistors", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({values})
  });

  const data = await res.json();
  document.getElementById("resResult").textContent = data.result;
});

// ------------------- Canvas drawings -------------------
const canvas = document.getElementById("diagramCanvas");
const ctx = canvas.getContext("2d");

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function line(x1, y1, x2, y2, w=2) {
  ctx.lineWidth = w;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.strokeStyle = "#000";
  ctx.stroke();
}

function rect(x, y, w, h, fill="#d9d9d9") {
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = "#000";
  ctx.strokeRect(x, y, w, h);
}

function text(x, y, t) {
  ctx.fillStyle = "#000";
  ctx.font = "14px Arial";
  ctx.fillText(t, x, y);
}

function drawSeriesCircuit() {
  clearCanvas();
  line(50, 130, 470, 130);

  rect(170, 110, 60, 40);
  text(190, 105, "R1");

  rect(290, 110, 60, 40);
  text(310, 105, "R2");

  line(470, 130, 470, 190);
  line(470, 190, 50, 190);
  line(50, 190, 50, 130);

  text(10, 20, "Series Circuit");
}

function drawParallelCircuit() {
  clearCanvas();
  line(50, 90, 470, 90);
  line(50, 200, 470, 200);

  rect(170, 90, 60, 110);
  text(190, 80, "R1");

  rect(290, 90, 60, 110);
  text(310, 80, "R2");

  // vertical connectors
  line(170, 90, 170, 200);
  line(230, 90, 230, 200);
  line(290, 90, 290, 200);
  line(350, 90, 350, 200);

  text(10, 20, "Parallel Circuit");
}

function drawAND() {
  clearCanvas();
  // inputs
  line(70, 90, 150, 90);
  line(70, 170, 150, 170);
  // left box + half circle style
  line(150, 60, 230, 60);
  line(150, 200, 230, 200);
  line(150, 60, 150, 200);

  // arc (right side)
  ctx.beginPath();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#000";
  ctx.arc(230, 130, 70, -Math.PI/2, Math.PI/2);
  ctx.stroke();

  // output
  line(300, 130, 470, 130);
  text(210, 135, "AND");
}

function drawOR() {
  clearCanvas();
  line(70, 90, 140, 90);
  line(70, 170, 140, 170);

  // rough OR curve
  ctx.strokeStyle = "#000";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(140, 60);
  ctx.quadraticCurveTo(220, 130, 140, 200);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(140, 60);
  ctx.quadraticCurveTo(260, 60, 300, 130);
  ctx.quadraticCurveTo(260, 200, 140, 200);
  ctx.stroke();

  line(300, 130, 470, 130);
  text(230, 135, "OR");
}

function drawNOT() {
  clearCanvas();
  line(70, 130, 160, 130);

  // triangle
  ctx.strokeStyle = "#000";
  ctx.fillStyle = "#d9d9d9";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(160, 90);
  ctx.lineTo(160, 170);
  ctx.lineTo(280, 130);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // bubble
  ctx.beginPath();
  ctx.fillStyle = "#000";
  ctx.arc(292, 130, 6, 0, Math.PI*2);
  ctx.fill();

  line(298, 130, 470, 130);
  text(210, 105, "NOT");
}

function drawGate(name) {
  const g = name.toLowerCase();
  if (g === "and") drawAND();
  else if (g === "or") drawOR();
  else if (g === "not") drawNOT();
}

document.querySelectorAll("[data-diagram]").forEach(btn => {
  btn.addEventListener("click", () => {
    const type = btn.getAttribute("data-diagram");
    if (type === "series") drawSeriesCircuit();
    if (type === "parallel") drawParallelCircuit();
  });
});

document.getElementById("showGateBtn").addEventListener("click", () => {
  const gate = document.getElementById("gateSelect").value;
  drawGate(gate);
});

// ------------------- Explanations -------------------
function showExplanation(topic) {
  if (topic === "ohm") {
    explainText.textContent =
`📘 Ohm's Law:
V = I × R
Voltage (V) = push of electrons
Current (I) = flow of electrons
Resistance (R) = opposition to flow
Enter any two values to calculate the third.`;
    drawSeriesCircuit();
  } else if (topic === "and") {
    explainText.textContent =
`🔵 AND Gate:
Outputs 1 only if BOTH inputs are 1.

Truth table:
0 0 → 0
0 1 → 0
1 0 → 0
1 1 → 1`;
    drawAND();
  } else if (topic === "or") {
    explainText.textContent =
`🟢 OR Gate:
Outputs 1 if ANY input is 1.

Truth table:
0 0 → 0
0 1 → 1
1 0 → 1
1 1 → 1`;
    drawOR();
  } else if (topic === "not") {
    explainText.textContent =
`🔴 NOT Gate:
Outputs the opposite of the input.

0 → 1
1 → 0`;
    drawNOT();
  }
}

// initial drawing
drawSeriesCircuit();
addLine("Bot", "Hi! Ask about Ohm’s law, logic gates, or resistors. Type /quiz to start.");

