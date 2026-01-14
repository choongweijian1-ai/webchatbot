from flask import Flask, request, jsonify, render_template
import json
import random
import os

app = Flask(__name__)

# ---------------------------
# Load intents.json safely
# ---------------------------
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

        # 1) Exact match
        if user_text == pattern_lower:
            return random.choice(intent.get("responses", []))

        # 2) Partial match (only if pattern longer than 3 chars)
        if len(pattern_lower) > 3 and pattern_lower in user_text:
            return random.choice(intent.get("responses", []))

    # 3) Fallback
    return random.choice(
        noanswer_intent.get("responses", ["Sorry, I didn't understand that."])
    )


# ---------------------------
# Load quiz_data.json safely
# ---------------------------
QUIZ_PATH = os.path.join(BASE_DIR, "QUIZ.json")

with open(QUIZ_PATH, "r", encoding="utf-8") as f:
    quiz_data = json.load(f)["quizzes"]

# Simple quiz state (single-user demo)
quiz_state = {
    "active": False,
    "topic": None,
    "index": 0,
    "score": 0
}


def format_question(qobj, qnum, total):
    lines = [f"Quiz ({qnum}/{total})", qobj["q"]]
    for i, c in enumerate(qobj["choices"], start=1):
        lines.append(f"{i}. {c}")
    lines.append("Reply with 1, 2, 3, or 4.")
    return "\n".join(lines)


# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = payload.get("message", "")
    reply = get_bot_response(msg)
    return jsonify({"reply": reply})

@app.route("/quiz/list", methods=["GET"])
def list_quizzes():
    topics = sorted(list(quiz_data.keys()))
    if not topics:
        return jsonify({"reply": "No quizzes available right now."})

    lines = ["Available quizzes:"]
    for i, t in enumerate(topics, start=1):
        lines.append(f"{i}. {t}")
    lines.append("\nType: quiz <topic>")
    lines.append("Example: quiz number_systems")

    return jsonify({"reply": "\n".join(lines), "topics": topics})

@app.route("/quiz/start", methods=["POST"])
def start_quiz():
    payload = request.get_json(silent=True) or {}
    topic = payload.get("topic", "number_systems")

    if topic not in quiz_data:
        return jsonify({"reply": "Sorry, that quiz topic is not available."})

    quiz_state["active"] = True
    quiz_state["topic"] = topic
    quiz_state["index"] = 0
    quiz_state["score"] = 0

    questions = quiz_data[topic]
    qobj = questions[0]

    reply = "Quiz started!\n\n" + format_question(qobj, 1, len(questions))
    return jsonify({"reply": reply})


@app.route("/quiz/answer", methods=["POST"])
def answer_quiz():
    if not quiz_state["active"]:
        return jsonify({"reply": "No quiz is active. Type 'start quiz' to begin."})

    payload = request.get_json(silent=True) or {}
    ans = str(payload.get("answer", "")).strip()

    if ans not in {"1", "2", "3", "4"}:
        return jsonify({"reply": "Please reply with 1, 2, 3, or 4."})

    topic = quiz_state["topic"]
    questions = quiz_data[topic]
    idx = quiz_state["index"]
    qobj = questions[idx]

    user_index = int(ans) - 1
    correct_index = qobj["answer_index"]

    if user_index == correct_index:
        quiz_state["score"] += 1
        feedback = f"✅ Correct!\nExplanation: {qobj['explain']}"
    else:
        correct_text = qobj["choices"][correct_index]
        feedback = f"❌ Incorrect.\nCorrect answer: {correct_text}\nExplanation: {qobj['explain']}"

    # Next question or finish
    quiz_state["index"] += 1

    if quiz_state["index"] >= len(questions):
        total = len(questions)
        score = quiz_state["score"]
        quiz_state["active"] = False
        reply = f"{feedback}\n\n🎉 Quiz finished!\nScore: {score}/{total}"
        return jsonify({"reply": reply})

    next_q = questions[quiz_state["index"]]
    reply = f"{feedback}\n\n" + format_question(next_q, quiz_state["index"] + 1, len(questions))
    return jsonify({"reply": reply})


# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


