const chatbox = document.getElementById("chatbox");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");

// Track if quiz is active on the client side
let quizActive = false;

// Quiz topic selection mode (after showing quiz list)
let quizSelectMode = false;     // true when user is choosing a quiz from the list
let lastQuizTopics = [];        // topics from /quiz/list in the same order displayed

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

async function startQuiz(topic = "number_systems") {
  const data = await postJSON("/quiz/start", { topic });
  quizActive = true;
  return data;
}

async function answerQuiz(answer) {
  const data = await postJSON("/quiz/answer", { answer });

  if (typeof data.reply === "string") {
    const r = data.reply.toLowerCase();
    if (r.includes("quiz finished")) quizActive = false;
    if (r.includes("no quiz is active")) quizActive = false;
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
    // ✅ 0) Show quiz list and enable number selection mode
    if (
      lower === "quiz" ||
      lower === "quiz list" ||
      lower === "list quiz" ||
      lower === "list quizzes"
    ) {
      const data = await getQuizList();
      addMessage(data.reply, "bot");

      if (Array.isArray(data.topics) && data.topics.length > 0) {
        quizSelectMode = true;
        lastQuizTopics = data.topics;
        addMessage("Reply with the quiz number to start it (e.g., 1).", "bot");
      } else {
        quizSelectMode = false;
        lastQuizTopics = [];
      }
      return;
    }

    // ✅ 0b) If user is choosing a quiz topic, allow number selection
    // Important: This only runs when NOT currently taking a quiz.
    if (!quizActive && quizSelectMode && /^\d+$/.test(message)) {
      const choiceNum = parseInt(message, 10);

      if (choiceNum >= 1 && choiceNum <= lastQuizTopics.length) {
        const topic = lastQuizTopics[choiceNum - 1];
        quizSelectMode = false; // exit selection mode
        const data = await startQuiz(topic);
        addMessage(data.reply, "bot");
      } else {
        addMessage(`Please enter a number between 1 and ${lastQuizTopics.length}.`, "bot");
      }
      return;
    }

    // ✅ 1) Start quiz command: "start quiz"
    if (lower === "start quiz") {
      quizSelectMode = false;
      const data = await startQuiz("number_systems");
      addMessage(data.reply, "bot");
      return;
    }

    // ✅ 1b) Start quiz by topic: "quiz <topic>"
    if (lower.startsWith("quiz ")) {
      quizSelectMode = false;
      const topic = lower.replace("quiz ", "").trim();
      const data = await startQuiz(topic || "number_systems");
      addMessage(data.reply, "bot");
      return;
    }

    // ✅ 2) If quiz is active AND user typed 1-4, treat as answer
    if (quizActive && ["1", "2", "3", "4"].includes(message)) {
      const data = await answerQuiz(message);
      addMessage(data.reply, "bot");
      return;
    }

    // ✅ 3) Default: normal chatbot endpoint
    const data = await postJSON("/chat", { message });
    addMessage(data.reply, "bot");
  } catch (err) {
    addMessage("Error: could not reach the server. Please try again.", "bot");
  }
};

clearBtn.onclick = () => {
  chatbox.innerHTML = "";
  quizActive = false;
  quizSelectMode = false;
  lastQuizTopics = [];
};

msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});
