// ------------------- Chat UI -------------------
const chatBox = document.getElementById("chatBox");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

const explainText = document.getElementById("explainText");

// Opening message shown on load and after clearing chat
const OPENING_MESSAGE = `👋 Hi! Quick tips:
- /quiz  (list categories)
- Type a number after /quiz (example: 6)
- /clear (reset quiz)
Ask about Ohm’s law, logic gates, or resistors anytime.`;

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
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ message: msg })
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
    showExplanation(data.topic);
    addLine("Bot", `Opened explanation for ${String(data.topic || "").toUpperCase()}.`);
    return;
  }

  addLine("Bot", data.text);
}

sendBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

// ✅ Clear chat but keep opening message
clearBtn.addEventListener("click", clearChat);

async function clearChat() {
  // Keep only opening message in UI
  chatBox.textContent = `Bot: ${OPENING_MESSAGE}\n`;

  // Tell backend to clear quiz/session state
  try {
    await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ message: "/clear" })
    });
  } catch (err) {
    console.error(err);
  }

  chatInput.value = "";
  chatInput.focus();
}

// ------------------- Calculators -------------------

// ✅ Ohm Calculate
document.getElementById("calcOhmBtn").addEventListener("click", async () => {
  const V = document.getElementById("V").value;
  const I = document.getElementById("I").value;
  const R = document.getElementById("R").value;

  const res = await fetch("/api/ohm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ V, I, R })
  });

  const data = await res.json();
  document.getElementById("ohmResult").textContent = data.result;
});

// ✅ Ohm Clear
document.getElementById("clearOhmBtn").addEventListener("click", () => {
  document.getElementById("V").value = "";
  document.getElementById("I").value = "";
  document.getElementById("R").value = "";
  document.getElementById("ohmResult").textContent = "";
  document.getElementById("V").focus();
});

// ✅ Resistor Calculate
document.getElementById("calcResBtn").addEventListener("click", async () => {
  const values = document.getElementById("resistors").value;

  const res = await fetch("/api/resistors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ values })
  });

  const data = await res.json();
  document.getElementById("resResult").textContent = data.result;
});

// ✅ Resistor Clear (works only if index.html has clearResBtn)
const clearResBtn = document.getElementById("clearResBtn");
if (clearResBtn) {
  clearResBtn.addEventListener("click", () => {
    document.getElementById("resistors").value = "";
    document.getElementById("resResult").textContent = "";
    document.getElementById("resistors").focus();
  });
}

// ------------------- Canvas drawings -------------------
const canvas = document.getElementById("diagramCanvas");
const ctx = canvas.getContext("2d");

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/**
 * Wrap any drawing in a clean, isolated canvas state.
 * Prevents "zoom"/style leaks after drawing gates.
 */
function withCanvas(drawFn) {
  ctx.save();
  clearCanvas();

  // baseline defaults for everything
  ctx.setTransform(1, 0, 0, 1, 0, 0); // just in case transforms ever get used later
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#000";
  ctx.fillStyle = "#d9d9d9";
  ctx.font = "14px Arial";
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";

  drawFn();
  ctx.restore();
}

// ---- Helper primitives (each isolates its own state too) ----
function line(x1, y1, x2, y2, w = 2) {
  ctx.save();
  ctx.lineWidth = w;
  ctx.strokeStyle = "#000";
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.restore();
}

function rect(x, y, w, h, fill = "#d9d9d9") {
  ctx.save();
  ctx.fillStyle = fill;
  ctx.strokeStyle = "#000";
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);
  ctx.restore();
}

function label(x, y, t, align = "left", size = 14) {
  ctx.save();
  ctx.fillStyle = "#000";
  ctx.font = `${size}px Arial`;
  ctx.textAlign = align;
  ctx.fillText(t, x, y);
  ctx.restore();
}

// -------- Circuits --------
function drawSeriesCircuit() {
  withCanvas(() => {
    line(50, 130, 470, 130);

    rect(170, 110, 60, 40);
    label(190, 105, "R1", "left");

    rect(290, 110, 60, 40);
    label(310, 105, "R2", "left");

    line(470, 130, 470, 190);
    line(470, 190, 50, 190);
    line(50, 190, 50, 130);

    label(10, 20, "Series Circuit", "left");
  });
}

function drawParallelCircuit() {
  withCanvas(() => {
    // rails
    line(60, 90, 460, 90);
    line(60, 210, 460, 210);

    // branch x positions
    const x1 = 200;
    const x2 = 320;

    // vertical resistor dimensions
    const rw = 28;
    const rh = 70;

    // R1 branch
    line(x1, 90, x1, 120);
    rect(x1 - rw / 2, 120, rw, rh);
    line(x1, 190, x1, 210);
    label(x1, 110, "R1", "center");

    // R2 branch
    line(x2, 90, x2, 120);
    rect(x2 - rw / 2, 120, rw, rh);
    line(x2, 190, x2, 210);
    label(x2, 110, "R2", "center");

    label(10, 20, "Parallel Circuit", "left");
  });
}

// -------- Gates --------
function drawAND() {
  withCanvas(() => {
    // inputs
    line(70, 90, 150, 90);
    line(70, 170, 150, 170);

    // body
    line(150, 60, 230, 60);
    line(150, 200, 230, 200);
    line(150, 60, 150, 200);

    // arc
    ctx.save();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#000";
    ctx.beginPath();
    ctx.arc(230, 130, 70, -Math.PI / 2, Math.PI / 2);
    ctx.stroke();
    ctx.restore();

    // output + label
    line(300, 130, 470, 130);
    label(210, 135, "AND", "left");
  });
}

function drawOR() {
  withCanvas(() => {
    // inputs
    line(70, 90, 140, 90);
    line(70, 170, 140, 170);

    ctx.save();
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;

    // inner curve
    ctx.beginPath();
    ctx.moveTo(140, 60);
    ctx.quadraticCurveTo(220, 130, 140, 200);
    ctx.stroke();

    // outer curve
    ctx.beginPath();
    ctx.moveTo(140, 60);
    ctx.quadraticCurveTo(260, 60, 300, 130);
    ctx.quadraticCurveTo(260, 200, 140, 200);
    ctx.stroke();

    ctx.restore();

    // output + label
    line(300, 130, 470, 130);
    label(230, 135, "OR", "left");
  });
}

function drawNOT() {
  withCanvas(() => {
    line(70, 130, 160, 130);

    // triangle
    ctx.save();
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
    ctx.restore();

    // bubble
    ctx.save();
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.arc(292, 130, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // output + label
    line(298, 130, 470, 130);
    label(210, 105, "NOT", "left");
  });
}

// ✅ NAND = AND + bubble
function drawNAND() {
  withCanvas(() => {
    // inputs
    line(70, 90, 150, 90);
    line(70, 170, 150, 170);

    // AND body
    line(150, 60, 230, 60);
    line(150, 200, 230, 200);
    line(150, 60, 150, 200);

    // AND arc
    ctx.save();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#000";
    ctx.beginPath();
    ctx.arc(230, 130, 70, -Math.PI / 2, Math.PI / 2);
    ctx.stroke();
    ctx.restore();

    // label
    label(210, 135, "NAND", "center", 16);

    // inversion bubble
    ctx.save();
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.arc(300, 130, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // output line
    line(306, 130, 470, 130);
  });
}

// ✅ NOR = OR + bubble
function drawNOR() {
  withCanvas(() => {
    // inputs
    line(70, 90, 140, 90);
    line(70, 170, 140, 170);

    ctx.save();
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;

    // OR inner curve
    ctx.beginPath();
    ctx.moveTo(140, 60);
    ctx.quadraticCurveTo(220, 130, 140, 200);
    ctx.stroke();

    // OR outer curve
    ctx.beginPath();
    ctx.moveTo(140, 60);
    ctx.quadraticCurveTo(260, 60, 300, 130);
    ctx.quadraticCurveTo(260, 200, 140, 200);
    ctx.stroke();

    ctx.restore();

    // label
    label(230, 135, "NOR", "center", 16);

    // inversion bubble
    ctx.save();
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.arc(300, 130, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // output line
    line(306, 130, 470, 130);
  });
}

// ✅ XOR = OR + extra input curve
function drawXOR() {
  withCanvas(() => {
    // inputs
    line(70, 90, 140, 90);
    line(70, 170, 140, 170);

    ctx.save();
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;

    // extra XOR curve
    ctx.beginPath();
    ctx.moveTo(125, 60);
    ctx.quadraticCurveTo(205, 130, 125, 200);
    ctx.stroke();

    // OR inner curve
    ctx.beginPath();
    ctx.moveTo(140, 60);
    ctx.quadraticCurveTo(220, 130, 140, 200);
    ctx.stroke();

    // OR outer curve
    ctx.beginPath();
    ctx.moveTo(140, 60);
    ctx.quadraticCurveTo(260, 60, 300, 130);
    ctx.quadraticCurveTo(260, 200, 140, 200);
    ctx.stroke();

    ctx.restore();

    // output + label
    line(300, 130, 470, 130);
    label(230, 135, "XOR", "left");
  });
}

function drawGate(name) {
  const g = (name || "").toLowerCase().trim();
  if (g === "and") drawAND();
  else if (g === "or") drawOR();
  else if (g === "not") drawNOT();
  else if (g === "nand") drawNAND();
  else if (g === "nor") drawNOR();
  else if (g === "xor") drawXOR();
}

// Circuit buttons
document.querySelectorAll("[data-diagram]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const type = btn.getAttribute("data-diagram");
    if (type === "series") drawSeriesCircuit();
    if (type === "parallel") drawParallelCircuit();
  });
});

// Gate dropdown button
document.getElementById("showGateBtn").addEventListener("click", () => {
  const gate = document.getElementById("gateSelect").value;
  drawGate(gate);
});

// ------------------- Explanations -------------------
function showExplanation(topic) {
  topic = (topic || "").toLowerCase().trim(); // ✅ normalize first

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

  } else if (topic === "nand") {
    explainText.textContent =
`🔴 NAND Gate:
Inverse of AND. Output is 0 only when BOTH inputs are 1.

0 0 → 1
0 1 → 1
1 0 → 1
1 1 → 0`;
    drawNAND();

  } else if (topic === "nor") {
    explainText.textContent =
`🔴 NOR Gate:
Output is 1 only when BOTH inputs are 0.

0 0 → 1
0 1 → 0
1 0 → 0
1 1 → 0`;
    drawNOR();

  } else if (topic === "xor") {
    explainText.textContent =
`🔴 XOR Gate:
Output is 1 only when inputs are DIFFERENT.

0 0 → 0
0 1 → 1
1 0 → 1
1 1 → 0`;
    drawXOR();
  }
}

// initial drawing + show opening message once
window.addEventListener("DOMContentLoaded", () => {
  drawSeriesCircuit();
  addLine("Bot", OPENING_MESSAGE);
});
