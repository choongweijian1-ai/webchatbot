const chatbox = document.getElementById("chatbox");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");

function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = "msg " + sender;

  if (sender === "bot") {
    div.textContent = `Bot:\n${text}`;
  } else {
    div.textContent = `You: ${text}`;
  }

  chatbox.appendChild(div);
  chatbox.scrollTop = chatbox.scrollHeight;
}

sendBtn.onclick = async () => {
  const message = msgInput.value.trim();
  if (!message) return;

  addMessage(message, "you");
  msgInput.value = "";

  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });

  const data = await response.json();
  addMessage(data.reply, "bot");
};

clearBtn.onclick = () => {
  chatbox.innerHTML = "";
};
