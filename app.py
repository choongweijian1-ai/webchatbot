from flask import Flask, request, jsonify, render_template, session
import json
import random
import os
import math
import re

app = Flask(__name__)

# ✅ REQUIRED for Flask session storage (quiz state)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_change_me")

# ------------------- Base directory -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------- Load intents.json safely -------------------
INTENTS_PATH = os.path.join(BASE_DIR, "intents.json")
with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    intents_file = json.load(f)

intents = intents_file.get("intents", [])
noanswer_intent = next(
    (i for i in intents if i.get("tag") == "noanswer"),
    {"responses": ["Sorry, I didn't understand."]}
)

# ------------------- Load quiz.json safely -------------------
# IMPORTANT: filename must match EXACTLY (case-sensitive on Render)
QUIZ_FILENAME = "QUIZ.json"  # change to "QUIZ.json" if your file is uppercase
QUIZ_PATH = os.path.join(BASE_DIR, QUIZ_FILENAME)

quiz_data = {}   # { "number_systems": [...], "signals": [...], ... }
quiz_error = None

try:
    with open(QUIZ_PATH, "r", encoding="utf-8") as f:
        quiz_file = json.load(f)
    quiz_data = quiz_file.get("quizzes", {})
except FileNotFoundError:
    quiz_error = f"{QUIZ_FILENAME} not found in repo root."
    quiz_data = {}
except json.JSONDecodeError as e:
    quiz_error = f"{QUIZ_FILENAME} is not valid JSON: {e}"
    quiz_data = {}


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


# ------------------- Quiz command parsing -------------------
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

    parts = msg.split()
    if len(parts) == 1:
        return {"mode": "list"}

    category = parts[1].strip().lower()

    if len(parts) >= 3 and parts[2].strip().lower() == "random":
        return {"mode": "random", "category": category}

    if len(parts) >= 3:
        try:
            qnum = int(parts[2])
            return {"mode": "number", "category": category, "qnum": qnum}
        except Exception:
            return {"mode": "category", "category": category}

    return {"mode": "category", "category": category}


def format_question_text(category: str, q_obj: dict, index_1based: int) -> str:
    q = q_obj.get("q", "")
    choices = q_obj.get("choices", [])
    lines = [f"📘 Quiz: {category}", f"Q{index_1based}. {q}"]
    for i, c in enumerate(choices, start=1):
        lines.append(f"{i}) {c}")
    lines.append("")
    lines.append("Tip: /quiz <category> <number>  OR  /quiz <category> random")
    return "\n".join(lines)


# ------------------- Quiz answer handling (STEP 2) -------------------
def is_quiz_answer(msg: str) -> bool:
    if not msg:
        return False
    s = msg.strip().lower()
    return s in {"1", "2", "3", "4", "a", "b", "c", "d"}

def normalize_answer(msg: str) -> str:
    """Map a/b/c/d to 1/2/3/4, keep digits as-is."""
    s = msg.strip().lower()
    mapping = {"a": "1", "b": "2", "c": "3", "d": "4"}
    return mapping.get(s, s)

def get_correct_option_number(q_obj: dict):
    """
    Accepts quiz JSON formats like:
      - "answer": 3         (means option 3)
      - "answer": "3"       (means option 3)
      - "answer": "10"      (means the correct choice text is "10")
      - "answer": "c"       (means option 3)
    Returns: "1"/"2"/"3"/"4" or None if cannot detect
    """
    ans = q_obj.get("answer", None)
    choices = q_obj.get("choices", [])

    if ans is None:
        return None

    # If answer is int (1-4)
    if isinstance(ans, int):
        if 1 <= ans <= len(choices):
            return str(ans)
        return None

    # If answer is string
    if isinstance(ans, str):
        a = ans.strip().lower()

        # 'a'/'b'/'c'/'d'
        if a in {"a", "b", "c", "d"}:
            return normalize_answer(a)

        # "1"/"2"/"3"/"4"
        if a.isdigit():
            # If it's a valid option number (1-4)
            if 1 <= int(a) <= len(choices):
                return a

        # Otherwise treat it as correct choice TEXT, find which option matches
        for idx, c in enumerate(choices, start=1):
            if str(c).strip().lower() == a:
                return str(idx)

    return None

def start_quiz_state(category: str, q_index_0based: int):
    """Store current quiz state in Flask session cookie."""
    session["quiz_active"] = True
    session["quiz_category"] = category
    session["quiz_index"] = int(q_index_0based)

def clear_quiz_state():
    session.pop("quiz_active", None)
    session.pop("quiz_category", None)
    session.pop("quiz_index", None)

def grade_quiz_answer(user_msg: str):
    """
    Grades current quiz answer from session.
    Keeps your strict quiz format.
    """
    category = session.get("quiz_category")
    idx0 = session.get("quiz_index")

    if not category or category not in quiz_data or idx0 is None:
        clear_quiz_state()
        return {"type": "chat", "text": "❌ Quiz session lost. Start again with:\n/quiz"}

    questions = quiz_data.get(category, [])
    if not questions or idx0 < 0 or idx0 >= len(questions):
        clear_quiz_state()
        return {"type": "chat", "text": "❌ Quiz question not found. Start again with:\n/quiz"}

    q_obj = questions[idx0]
    correct_opt = get_correct_option_number(q_obj)

    if not correct_opt:
        # Your quiz JSON lacks a usable "answer"
        return {"type": "chat", "text": "❌ This question has no valid 'answer' field in QUIZ.json."}

    user_opt = normalize_answer(user_msg)

    if user_opt == correct_opt:
        # ✅ Correct -> go next question or end quiz
        next_idx0 = idx0 + 1
        if next_idx0 >= len(questions):
            clear_quiz_state()
            return {"type": "chat", "text": "✅ Correct!\n\n🏁 End of quiz."}

        # move to next question (same category)
        session["quiz_index"] = next_idx0
        next_q = questions[next_idx0]
        q_text = format_question_text(category, next_q, next_idx0 + 1)
        return {"type": "chat", "text": "✅ Correct!\n\n" + q_text}

    # ❌ Wrong -> repeat same question (do NOT exit quiz)
    q_text = format_question_text(category, q_obj, idx0 + 1)
    return {"type": "chat", "text": "❌ Incorrect.\n\n" + q_text}


# ------------------- Chat API -------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = payload.get("message", "")

    # ✅ STEP 2: Intercept quiz answer FIRST (prevents Definition/Use/Why hijack)
    if session.get("quiz_active") and is_quiz_answer(msg):
        result = grade_quiz_answer(msg)
        return jsonify(result)

    # 1) Explain commands
    topic = parse_explain_command(msg)
    if topic:
        return jsonify({"type": "explain", "topic": topic})

    # 2) Quiz commands
    quiz_cmd = parse_quiz_command(msg)
    if quiz_cmd:
        if quiz_error and not quiz_data:
            return jsonify({"type": "chat", "text": f"Quiz error: {quiz_error}"})

        if quiz_cmd["mode"] == "list":
            clear_quiz_state()
            if not quiz_data:
                return jsonify({"type": "chat", "text": "No quiz categories found."})
            cat_list = "\n- " + "\n- ".join(sorted(quiz_data.keys()))
            return jsonify({"type": "chat", "text": f"✅ Available quiz categories:{cat_list}\n\nStart one like:\n/quiz number_systems"})

        category = quiz_cmd.get("category", "")
        if category not in quiz_data:
            clear_quiz_state()
            available = ", ".join(sorted(quiz_data.keys())) if quiz_data else "(none)"
            return jsonify({"type": "chat", "text": f"❌ Unknown quiz category: {category}\nAvailable: {available}\n\nTry:\n/quiz"})

        questions = quiz_data[category]
        if not questions:
            clear_quiz_state()
            return jsonify({"type": "chat", "text": f"No questions found in category: {category}."})

        if quiz_cmd["mode"] == "random":
            q_obj = random.choice(questions)
            idx0 = questions.index(q_obj)
            start_quiz_state(category, idx0)
            # Validate answer exists
            if not get_correct_option_number(q_obj):
                return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer' field in QUIZ.json."})
            return jsonify({"type": "chat", "text": format_question_text(category, q_obj, idx0 + 1)})

        if quiz_cmd["mode"] == "number":
            qnum = quiz_cmd.get("qnum", 1)
            if qnum < 1 or qnum > len(questions):
                return jsonify({"type": "chat", "text": f"Question number out of range. Pick 1 to {len(questions)}."})
            idx0 = qnum - 1
            q_obj = questions[idx0]
            start_quiz_state(category, idx0)
            if not get_correct_option_number(q_obj):
                return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer' field in QUIZ.json."})
            return jsonify({"type": "chat", "text": format_question_text(category, q_obj, qnum)})

        # default: first question
        q_obj = questions[0]
        start_quiz_state(category, 0)
        if not get_correct_option_number(q_obj):
            return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer' field in QUIZ.json."})
        return jsonify({"type": "chat", "text": format_question_text(category, q_obj, 1)})

    # 3) Normal chatbot
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


# ------------------- Quiz API (debug) -------------------
@app.route("/api/quiz/categories", methods=["GET"])
def quiz_categories():
    return jsonify({"categories": sorted(list(quiz_data.keys()))})


@app.route("/api/quiz/<category>", methods=["GET"])
def quiz_by_category(category):
    category = category.lower().strip()
    if category not in quiz_data:
        return jsonify({"error": "Unknown quiz category", "available": sorted(list(quiz_data.keys()))}), 404
    return jsonify({"category": category, "questions": quiz_data[category]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
