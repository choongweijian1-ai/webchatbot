const chatbox = document.getElementById("chatbox");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");

function addLine(who, text) {
  const div = document.createElement("div");
  div.className = "msg";
  div.innerHTML = `<span class="${who.toLowerCase()}">${who}:</span> ${text}`;
  chatbox.appendChild(div);
  chatbox.scrollTop = chatbox.scrollHeight;
}

async function sendMessage() {
  const text = msgInput.value.trim();
  if (!text) return;

  addLine("You", text);
  msgInput.value = "";

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text })
  });

  const data = await res.json();
  addLine("Bot", data.reply);
}

sendBtn.addEventListener("click", sendMessage);
msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

clearBtn.addEventListener("click", () => {
  chatbox.innerHTML = "";
});
