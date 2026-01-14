const chatbox = document.getElementById("chatbox");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");

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

msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});
