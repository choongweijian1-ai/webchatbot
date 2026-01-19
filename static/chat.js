// =================== chat.js (FULL FIXED VERSION) ===================

window.addEventListener("DOMContentLoaded", () => {

  // ------------------- Chat UI -------------------
  const chatBox = document.getElementById("chatBox");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const clearBtn = document.getElementById("clearBtn");
  const explainText = document.getElementById("explainText");

  if (!chatBox || !chatInput || !sendBtn || !clearBtn) {
    console.error("Chat UI elements missing:", { chatBox, chatInput, sendBtn, clearBtn });
    alert("Chat UI failed to load (missing elements). Check IDs in index.html.");
    return;
  }

  // Opening message shown on load and after clearing chat
  const OPENING_MESSAGE = `👋 Hi! Quick tips:
- /quiz  (list categories)
- Type a number after /quiz (example: 6)
- /topic (list topics)
- Type a number after /topic (example: 6)
- /clear (reset quiz/topic)
Ask about Ohm’s law, logic gates, or resistors anytime.`;

  function addLine(who, text) {
    const role = (who || "").toLowerCase(); // "you" or "bot"
    const safeText = String(text).replace(/</g, "&lt;").replace(/>/g, "&gt;");

    chatBox.innerHTML +=
      `<span class="chat-name ${role}">${who}:</span> ${safeText}<br>`;

    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // ✅ Render one or multiple images from server
  function addImages(images) {
    if (!images) return;

    // allow single string or array
    const list = Array.isArray(images) ? images : [images];

    list.forEach((url) => {
      if (!url) return;
      const safeUrl = String(url).replace(/"/g, "&quot;");
      chatBox.innerHTML += `<img src="${safeUrl}" class="formula-img" alt="formula"><br>`;
    });

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
        credentials: "include", // ✅ IMPORTANT: keep Flask session
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

    // Explain (panel)
    if (data.type === "explain") {
      if (typeof showExplanation === "function") {
        showExplanation(data.topic, explainText);
      }
      addLine("Bot", `Opened explanation for ${String(data.topic || "").toUpperCase()}.`);
      return;
    }

    // Normal chat text
    addLine("Bot", data.text || "");

    // ✅ show images if provided by Flask
    if (data.images) addImages(data.images);
    if (data.image) addImages(data.image);
  }

  async function clearChat() {
    chatBox.innerHTML =
      `<span class="chat-name bot">Bot:</span> ${OPENING_MESSAGE.replace(/\n/g, "<br>")}<br>`;

    try {
      await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ message: "/clear" })
      });
    } catch (err) {
      console.error(err);
    }

    chatInput.value = "";
    chatInput.focus();
  }

  sendBtn.addEventListener("click", sendChat);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChat();
  });

  clearBtn.addEventListener("click", clearChat);

  // ------------------- Calculators -------------------

  // ✅ Ohm Calculate
  const calcOhmBtn = document.getElementById("calcOhmBtn");
  if (calcOhmBtn) {
    calcOhmBtn.addEventListener("click", async () => {
      const V = document.getElementById("V").value;
      const I = document.getElementById("I").value;
      const R = document.getElementById("R").value;

      const res = await fetch("/api/ohm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ V, I, R })
      });

      const data = await res.json();
      document.getElementById("ohmResult").textContent = data.result;
    });
  }

  // ✅ Ohm Clear
  const clearOhmBtn = document.getElementById("clearOhmBtn");
  if (clearOhmBtn) {
    clearOhmBtn.addEventListener("click", () => {
      document.getElementById("V").value = "";
      document.getElementById("I").value = "";
      document.getElementById("R").value = "";
      document.getElementById("ohmResult").textContent = "";
      document.getElementById("V").focus();
    });
  }

  // ✅ Resistor Calculate
  const calcResBtn = document.getElementById("calcResBtn");
  if (calcResBtn) {
    calcResBtn.addEventListener("click", async () => {
      const values = document.getElementById("resistors").value;

      const res = await fetch("/api/resistors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ values })
      });

      const data = await res.json();
      document.getElementById("resResult").textContent = data.result;
    });
  }

  // ✅ Resistor Clear
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
  const ctx = canvas ? canvas.getContext("2d") : null;

  function clearCanvas() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  function withCanvas(drawFn) {
    if (!ctx || !canvas) return;
    ctx.save();
    clearCanvas();

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#000";
    ctx.fillStyle = "#d9d9d9";
    ctx.font = "14px Arial";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";

    drawFn();
    ctx.restore();
  }

  function line(x1, y1, x2, y2, w = 2) {
    if (!ctx) return;
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
    if (!ctx) return;
    ctx.save();
    ctx.fillStyle = fill;
    ctx.strokeStyle = "#000";
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
    ctx.restore();
  }

  function label(x, y, t, align = "left", size = 14) {
    if (!ctx) return;
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
      line(60, 90, 460, 90);
      line(60, 210, 460, 210);

      const x1 = 200;
      const x2 = 320;

      const rw = 28;
      const rh = 70;

      const labelOffset = 50;
      const labelY = 155;

      line(x1, 90, x1, 120);
      rect(x1 - rw / 2, 120, rw, rh);
      line(x1, 190, x1, 210);
      label(x1 - labelOffset, labelY, "R1", "right");

      line(x2, 90, x2, 120);
      rect(x2 - rw / 2, 120, rw, rh);
      line(x2, 190, x2, 210);
      label(x2 - labelOffset, labelY, "R2", "right");

      label(10, 20, "Parallel Circuit", "left");
    });
  }

  // -------- Gates --------
  function drawAND() {
    withCanvas(() => {
      line(70, 90, 150, 90);
      line(70, 170, 150, 170);

      line(150, 60, 230, 60);
      line(150, 200, 230, 200);
      line(150, 60, 150, 200);

      ctx.save();
      ctx.beginPath();
      ctx.arc(230, 130, 70, -Math.PI / 2, Math.PI / 2);
      ctx.stroke();
      ctx.restore();

      line(300, 130, 470, 130);
      label(210, 135, "AND", "left");
    });
  }

  function drawOR() {
    withCanvas(() => {
      line(70, 90, 140, 90);
      line(70, 170, 140, 170);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(140, 60);
      ctx.quadraticCurveTo(220, 130, 140, 200);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(140, 60);
      ctx.quadraticCurveTo(260, 60, 300, 130);
      ctx.quadraticCurveTo(260, 200, 140, 200);
      ctx.stroke();
      ctx.restore();

      line(300, 130, 470, 130);
      label(230, 135, "OR", "left");
    });
  }

  function drawNOT() {
    withCanvas(() => {
      line(70, 130, 160, 130);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(160, 90);
      ctx.lineTo(160, 170);
      ctx.lineTo(280, 130);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.restore();

      ctx.save();
      ctx.fillStyle = "#000";
      ctx.beginPath();
      ctx.arc(292, 130, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      line(298, 130, 470, 130);
      label(210, 105, "NOT", "left");
    });
  }

  function drawNAND() {
    withCanvas(() => {
      line(70, 90, 150, 90);
      line(70, 170, 150, 170);

      line(150, 60, 230, 60);
      line(150, 200, 230, 200);
      line(150, 60, 150, 200);

      ctx.save();
      ctx.beginPath();
      ctx.arc(230, 130, 70, -Math.PI / 2, Math.PI / 2);
      ctx.stroke();
      ctx.restore();

      label(210, 135, "NAND", "center", 16);

      ctx.save();
      ctx.fillStyle = "#000";
      ctx.beginPath();
      ctx.arc(300, 130, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      line(306, 130, 470, 130);
    });
  }

  function drawNOR() {
    withCanvas(() => {
      line(70, 90, 140, 90);
      line(70, 170, 140, 170);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(140, 60);
      ctx.quadraticCurveTo(220, 130, 140, 200);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(140, 60);
      ctx.quadraticCurveTo(260, 60, 300, 130);
      ctx.quadraticCurveTo(260, 200, 140, 200);
      ctx.stroke();
      ctx.restore();

      label(230, 135, "NOR", "center", 16);

      ctx.save();
      ctx.fillStyle = "#000";
      ctx.beginPath();
      ctx.arc(300, 130, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      line(306, 130, 470, 130);
    });
  }

  function drawXOR() {
    withCanvas(() => {
      line(70, 90, 140, 90);
      line(70, 170, 140, 170);

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(125, 60);
      ctx.quadraticCurveTo(205, 130, 125, 200);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(140, 60);
      ctx.quadraticCurveTo(220, 130, 140, 200);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(140, 60);
      ctx.quadraticCurveTo(260, 60, 300, 130);
      ctx.quadraticCurveTo(260, 200, 140, 200);
      ctx.stroke();
      ctx.restore();

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

  document.querySelectorAll("[data-diagram]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const type = btn.getAttribute("data-diagram");
      if (type === "series") drawSeriesCircuit();
      if (type === "parallel") drawParallelCircuit();
    });
  });

  const showGateBtn = document.getElementById("showGateBtn");
  if (showGateBtn) {
    showGateBtn.addEventListener("click", () => {
      const gate = document.getElementById("gateSelect").value;
      drawGate(gate);
    });
  }

  // =================== IMAGE MODAL (POP OUT) ===================
  const imgModal = document.getElementById("imgModal");
  const imgModalContent = document.getElementById("imgModalContent");
  const imgClose = document.getElementById("imgClose");

  if (imgModal && imgModalContent && imgClose) {
    // open modal by clicking formula image
    document.addEventListener("click", (e) => {
      if (e.target.classList && e.target.classList.contains("formula-img")) {
        imgModal.style.display = "flex";
        imgModalContent.src = e.target.src;
      }
    });

    // close button
    imgClose.addEventListener("click", () => {
      imgModal.style.display = "none";
      imgModalContent.src = "";
    });

    // click outside image closes
    imgModal.addEventListener("click", (e) => {
      if (e.target === imgModal) {
        imgModal.style.display = "none";
        imgModalContent.src = "";
      }
    });

    // ESC closes
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        imgModal.style.display = "none";
        imgModalContent.src = "";
      }
    });
  }

  // initial
  drawSeriesCircuit();
  clearChat();
});

// ------------------- Explanations -------------------
function showExplanation(topic, explainTextEl) {
  const t = (topic || "").toLowerCase().trim();
  if (!explainTextEl) return;

  if (t === "ohm") {
    explainTextEl.textContent =
`📘 Ohm's Law:
V = I × R
Voltage (V) = push of electrons
Current (I) = flow of electrons
Resistance (R) = opposition to flow
Enter any two values to calculate the third.`;

  } else if (t === "and") {
    explainTextEl.textContent =
`🔵 AND Gate:
Outputs 1 only if BOTH inputs are 1.

Truth table:
0 0 → 0
0 1 → 0
1 0 → 0
1 1 → 1`;

  } else if (t === "or") {
    explainTextEl.textContent =
`🟢 OR Gate:
Outputs 1 if ANY input is 1.

Truth table:
0 0 → 0
0 1 → 1
1 0 → 1
1 1 → 1`;

  } else if (t === "not") {
    explainTextEl.textContent =
`🔴 NOT Gate:
Outputs the opposite of the input.

0 → 1
1 → 0`;

  } else if (t === "nand") {
    explainTextEl.textContent =
`🔴 NAND Gate:
Inverse of AND. Output is 0 only when BOTH inputs are 1.

0 0 → 1
0 1 → 1
1 0 → 1
1 1 → 0`;

  } else if (t === "nor") {
    explainTextEl.textContent =
`🔴 NOR Gate:
Output is 1 only when BOTH inputs are 0.

0 0 → 1
0 1 → 0
1 0 → 0
1 1 → 0`;

  } else if (t === "xor") {
    explainTextEl.textContent =
`🔴 XOR Gate:
Output is 1 only when inputs are DIFFERENT.

0 0 → 0
0 1 → 1
1 0 → 1
1 1 → 0`;
  }
}
