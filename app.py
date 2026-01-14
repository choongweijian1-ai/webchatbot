from flask import Flask, request, jsonify, render_template
import json, os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load quiz data
QUIZ_PATH = os.path.join(BASE_DIR, "quiz_data.json")
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

@app.route("/")
def home():
    return render_template("index.html")

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
