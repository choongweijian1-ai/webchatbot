from flask import Flask, request, jsonify, render_template
import json
import random
import os

app = Flask(__name__)

# Load intents.json safely
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENTS_PATH = os.path.join(BASE_DIR, "intents.json")

with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

intents = data["intents"]
noanswer_intent = next(i for i in intents if i["tag"] == "noanswer")


def get_bot_response(user_text: str) -> str:
    user_text = user_text.lower().strip()
    pattern_list = []

    # Build pattern list
    for intent in intents:
        for pattern in intent.get("patterns", []):
            pattern_list.append((pattern.lower().strip(), intent))

    # Sort longest patterns first (more specific first)
    pattern_list.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern_lower, intent in pattern_list:
        if not pattern_lower:
            continue

        # 1️⃣ Exact match (best match)
        if user_text == pattern_lower:
            return random.choice(intent.get("responses", []))

        # 2️⃣ Partial match ONLY for longer patterns
        if len(pattern_lower) > 3 and pattern_lower in user_text:
            return random.choice(intent.get("responses", []))

    # 3️⃣ Fallback
    return random.choice(
        noanswer_intent.get("responses", ["Sorry, I didn't understand that."])
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = payload.get("message", "")
    reply = get_bot_response(msg)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
