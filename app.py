from flask import Flask, request, jsonify, render_template
import json
import random
import os

app = Flask(__name__)

# Load intents.json (safe path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENTS_PATH = os.path.join(BASE_DIR, "intents.json")

with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

intents = data["intents"]
noanswer_intent = next(i for i in intents if i["tag"] == "noanswer")


def get_bot_response(user_text: str) -> str:
    user_text = user_text.lower().strip()
    pattern_list = []

    for intent in intents:
        for pattern in intent.get("patterns", []):
            pattern_list.append((pattern.lower(), intent))

    pattern_list.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern_lower, intent in pattern_list:
        if pattern_lower and (
            user_text == pattern_lower
            or pattern_lower in user_text
            or user_text in pattern_lower
        ):
            return random.choice(intent.get("responses", []))

    return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."]))


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

