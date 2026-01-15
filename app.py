from flask import Flask, request, jsonify, render_template
import json
import random
import os
import math
import re

app = Flask(__name__)

# ------------------- Load intents.json safely -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENTS_PATH = os.path.join(BASE_DIR, "intents.json")

with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

intents = data.get("intents", [])
noanswer_intent = next(
    (i for i in intents if i.get("tag") == "noanswer"),
    {"responses": ["Sorry, I didn't understand."]}
)

# ------------------- Load QUIZ.json safely -------------------
QUIZ_PATH = os.path.join(BASE_DIR, "QUIZ.json")
quiz_data = {}

try:
    with open(QUIZ_PATH, "r", encoding="utf-8") as f:
        quiz_data = json.load(f)
except FileNotFoundError:
    quiz_data = {"quizzes": {}, "error": "QUIZ.json not found in repo root."}
except json.JSONDecodeError:
    quiz_data = {"quizzes": {}, "error": "QUIZ.json is not valid JSON (check commas/quotes)."}


def get_bot_response(user_text: str) -> str:
    """Simple longest-pattern-first matcher (substring + equality)."""
    user_text = (user_text or "").lower().strip()
    pattern_list = []

    for intent in intents:
        for pattern in intent.get("patterns", []):
            pattern_list.append((pattern.lower().strip(), intent))

    # Prefer longer patterns first so "series circuit" beats "series"
    pattern_list.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern_lower, intent in pattern_list:
        if not pattern_lower:
            continue

        if (
            user_text == pattern_lower
            or pattern_lower in user_text
            or user_text in pattern_lower
        ):
            return random.choice(intent.get("responses", [])) if intent.get("responses") else "OK."

    return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."]))


# ------------------- Pages -------------------
@app.route("/")
def home():
    return render_template("index.html")


# ------------------- Explain commands -------------------
EXPLAIN_TOPICS = {"ohm", "and", "or", "not"}

def parse_explain_command(msg: str):
    if not msg:
        return None
    m = re.match(r"^\s*explain\s+([a-zA-Z']+)\s*$", msg.strip().lower())
    if not m:
        return None
    topic = m.group(1).replace("'", "")
    return topic if topic in EXPLAIN_TOPICS else None


# ------------------- Quiz command parsing (prevents mixing with intents) -------------------
# Commands:
#   /quiz                           -> list categories
#   /quiz <category>                -> show question 1
#   /quiz <category> random         -> random question
#   /quiz <category> <number>       -> question number (1-based)
def parse_quiz_command(msg: str):
    if not msg:
        return None

    msg = msg.strip()
    if not msg.lower().startswith("/quiz"):
        return None

    parts = msg.strip().split()
    # parts[0] is "/quiz"
    if len(parts) == 1:
        return {"mode": "list"}

    category = parts[1].strip().lower()

    if len(parts) >= 3 and parts[2].strip().lower() == "random":
        return {"mode": "random", "category": category}

    if len(parts) >= 3:
        # try parse question number
        try:
            qnum = int(parts[2])
            return {"mode": "number", "category": category, "qnum": qnum}
        except Exception:
            # unknown third argument
            return {"mode": "category", "category": category}

    return {"mode": "category", "category": category}


def format_question_text(category: str, q_obj: dict, index_1based: int) -> str:
    q = q_obj.get("q", "")
    choices = q_obj.get("choices", [])
    lines = [f"📘 Quiz: {category}", f"Q{index_1based}. {q}"]
    for i, c in enumerate(choices, start=1):
        lines.append(f"{i}) {c}")
    lines.append("")  # spacer
    lines.append("Tip: Use /quiz <category> <number> to go to another question, or /quiz <category> random.")
    return "\n".join(lines)


# ------------------- Chat API -------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = payload.get("message", "")

    # 1) Explain commands first
    topic = parse_explain_command(msg)
    if topic:
        return jsonify({"type": "explain", "topic": topic})

    # 2) Quiz commands next (so they DON'T get handled by intents)
    quiz_cmd = parse_quiz_command(msg)
    if quiz_cmd:
        quizzes = quiz_data.get("quizzes", {}) if isinstance(quiz_data, dict) else {}

        # Handle load errors gracefully
        if "error" in quiz_data and not quizzes:
            return jsonify({"type": "chat", "text": f"Quiz error: {quiz_data['error']}"})

        if quiz_cmd["mode"] == "list":
            if not quizzes:
                return jsonify({"type": "chat", "text": "No quiz categories found in QUIZ.json."})
            cat_list = "\n- " + "\n- ".join(sorted(quizzes.keys()))
            return jsonify({"type": "chat", "text": f"✅ Available quiz categories:{cat_list}\n\nStart one like:\n/quiz number_systems"})

        category = quiz_cmd.get("category", "")
        if category not in quizzes:
            available = ", ".join(sorted(quizzes.keys())) if quizzes else "(none)"
            return jsonify({"type": "chat", "text": f"❌ Unknown quiz category: {category}\nAvailable: {available}\n\nTry:\n/quiz"})

        questions = quizzes[category]
        if not questions:
            return jsonify({"type": "chat", "text": f"No questions found in category: {category}."})

        if quiz_cmd["mode"] == "random":
            q_obj = random.choice(questions)
            # Find its index for display (optional)
            idx = questions.index(q_obj) + 1
            return jsonify({"type": "chat", "text": format_question_text(category, q_obj, idx)})

        if quiz_cmd["mode"] == "number":
            qnum = quiz_cmd.get("qnum", 1)
            if qnum < 1 or qnum > len(questions):
                return jsonify({"type": "chat", "text": f"Question number out of range. Pick 1 to {len(questions)}."})
            q_obj = questions[qnum - 1]
            return jsonify({"type": "chat", "text": format_question_text(category, q_obj, qnum)})

        # default: show first question
        q_obj = questions[0]
        return jsonify({"type": "chat", "text": format_question_text(category, q_obj, 1)})

    # 3) Otherwise normal chatbot
    reply = get_bot_response(msg)
    return jsonify({"type": "chat", "text": reply})


# ------------------- Ohm's Law API -------------------
def _to_float(x):
    try:
        if x is None:
            return None
        s = str(x).strip()
        if not s:
            return None
        return float(s)
    except Exception:
        return None


@app.route("/api/ohm", methods=["POST"])
def api_ohm():
    payload = request.get_json(silent=True) or {}
    V = _to_float(payload.get("V"))
    I = _to_float(payload.get("I"))
    R = _to_float(payload.get("R"))

    provided = [v is not None for v in (V, I, R)].count(True)

    if provided < 2:
        return jsonify({"result": "Please enter any TWO values (V, I, R) to calculate the third."})

    if provided > 2:
        return jsonify({"result": "Please provide ONLY two values. Clear the third box and try again."})

    if V is None:
        Vcalc = I * R
        return jsonify({"result": f"Using V = I × R\nV = {I} × {R} = {Vcalc:.4g} V"})
    if I is None:
        if R == 0:
            return jsonify({"result": "R cannot be 0 for I = V/R."})
        Icalc = V / R
        return jsonify({"result": f"Using I = V ÷ R\nI = {V} ÷ {R} = {Icalc:.4g} A"})

    if I == 0:
        return jsonify({"result": "I cannot be 0 for R = V/I."})
    Rcalc = V / I
    return jsonify({"result": f"Using R = V ÷ I\nR = {V} ÷ {I} = {Rcalc:.4g} Ω"})


# ------------------- Resistor API -------------------
def parse_resistor_values(values: str):
    if not values:
        return []
    parts = [p.strip() for p in str(values).split(",")]
    nums = []
    for p in parts:
        if not p:
            continue
        try:
            nums.append(float(p))
        except Exception:
            return None
    return nums


def series_resistance(rs):
    return sum(rs)


def parallel_resistance(rs):
    if any(r == 0 for r in rs):
        return math.inf
    inv_sum = sum(1.0 / r for r in rs)
    if inv_sum == 0:
        return math.inf
    return 1.0 / inv_sum


@app.route("/api/resistors", methods=["POST"])
def api_resistors():
    payload = request.get_json(silent=True) or {}
    values = payload.get("values", "")
    rs = parse_resistor_values(values)

    if rs is None:
        return jsonify({"result": "Please enter numbers separated by commas (example: 10,5,20)."})
    if len(rs) < 2:
        return jsonify({"result": "Please enter at least TWO resistor values (example: 10,5,20)."})
    if any(r < 0 for r in rs):
        return jsonify({"result": "Resistor values should be 0 or positive."})

    s = series_resistance(rs)
    p = parallel_resistance(rs)

    rs_str = ", ".join(f"{r:g}" for r in rs)

    out = [f"Resistors: {rs_str} (Ω)"]
    out.append(f"Series total: {s:.4g} Ω")
    if math.isinf(p):
        out.append("Parallel total: ∞ (invalid because one resistor is 0 Ω)")
    else:
        out.append(f"Parallel total: {p:.4g} Ω")

    return jsonify({"result": "\n".join(out)})


# ------------------- Quiz API (optional, still useful for debugging) -------------------
@app.route("/api/quiz/categories", methods=["GET"])
def quiz_categories():
    quizzes = quiz_data.get("quizzes", {})
    return jsonify({"categories": sorted(list(quizzes.keys()))})


@app.route("/api/quiz/<category>", methods=["GET"])
def quiz_by_category(category):
    quizzes = quiz_data.get("quizzes", {})
    category = category.lower().strip()
    if category not in quizzes:
        return jsonify({"error": "Unknown quiz category", "available": sorted(list(quizzes.keys()))}), 404
    return jsonify({"category": category, "questions": quizzes[category]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
