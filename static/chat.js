const chatbox = document.getElementById("chatbox");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");

// Track if quiz is active on the client side
let quizActive = false;

async function getQuizList() {
  const res = await fetch("/quiz/list");
  return await res.json();
}

function addMessage(text, sender) {
  const msgDiv = document.createElement("div");
  msgDiv.className = "msg";

  const label = document.createElement("span");
  label.className = sender === "bot" ? "bot-label" : "you-label";
  label.textContent = sender === "bot" ? "Bot:" : "You:";

  const content = document.createElement("span");
  content.textContent = sender === "bot" ? `\n${text}` : ` ${text}`;

  msgDiv.appendChild(label);
  msgDiv.appendChild(content);

  chatbox.appendChild(msgDiv);
  chatbox.scrollTop = chatbox.scrollHeight;
}

async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return await res.json();
}

// Optional: start quiz with topic, default is number_systems
async function startQuiz(topic = "number_systems") {
  const data = await postJSON("/quiz/start", { topic });
  quizActive = true;
  return data;
}

async function answerQuiz(answer) {
  const data = await postJSON("/quiz/answer", { answer });

  // If backend says quiz finished, we turn it off on client side too
  if (typeof data.reply === "string" && data.reply.toLowerCase().includes("quiz finished")) {
    quizActive = false;
  }
  // If backend says no quiz active, also turn off
  if (typeof data.reply === "string" && data.reply.toLowerCase().includes("no quiz is active")) {
    quizActive = false;
  }

  return data;
}

sendBtn.onclick = async () => {
  const message = msgInput.value.trim();
  if (!message) return;

  addMessage(message, "you");
  msgInput.value = "";

  const lower = message.toLowerCase();

  try {
    // ✅ INSERTED HERE
    if (
      lower === "quiz" ||
      lower === "quiz list" ||
      lower === "list quiz" ||
      lower === "list quizzes"
    ) {
      const data = await getQuizList();
      addMessage(data.reply, "bot");
      return;
    }

    // 1) Start quiz command
    if (lower === "start quiz") {
      const data = await startQuiz("number_systems");
      addMessage(data.reply, "bot");
      return;
    }

    // 1b) Start quiz by topic
    if (lower.startsWith("quiz ")) {
      const topic = lower.replace("quiz ", "").trim();
      const data = await startQuiz(topic || "number_systems");
      addMessage(data.reply, "bot");
      return;
    }

    // 2) Answer quiz
    if (quizActive && ["1", "2", "3", "4"].includes(message)) {
      const data = await answerQuiz(message);
      addMessage(data.reply, "bot");
      return;
    }

    // 3) Normal chat
    const data = await postJSON("/chat", { message });
    addMessage(data.reply, "bot");

  } catch (err) {
    addMessage("Error: could not reach the server. Please try again.", "bot");
  }
};


clearBtn.onclick = () => {
  chatbox.innerHTML = "";
};

msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});


