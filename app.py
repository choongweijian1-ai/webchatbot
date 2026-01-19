from flask import Flask, request, jsonify, render_template, session
import json
import random
import os
import math
import re

app = Flask(__name__)

# ✅ REQUIRED for Flask session storage (quiz/topic state)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_change_me")

# Optional but recommended on Render (HTTPS)
# app.config.update(
#     SESSION_COOKIE_SAMESITE="Lax",
#     SESSION_COOKIE_SECURE=True,
# )

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

# ------------------- Load QUIZ.json safely -------------------
QUIZ_FILENAME = "QUIZ.json"  # must match exact case on Render
QUIZ_PATH = os.path.join(BASE_DIR, QUIZ_FILENAME)

quiz_data = {}
quiz_menu = {}
quiz_error = None

try:
    with open(QUIZ_PATH, "r", encoding="utf-8") as f:
        quiz_file = json.load(f)

    quiz_data = quiz_file.get("quizzes", {})
    quiz_menu = quiz_file.get("quiz_menu", {})  # ✅ IMPORTANT

except FileNotFoundError:
    quiz_error = f"{QUIZ_FILENAME} not found in repo root."
    quiz_menu = {}
    quiz_data = {}
except json.JSONDecodeError as e:
    quiz_error = f"{QUIZ_FILENAME} is not valid JSON: {e}"
    quiz_menu = {}
    quiz_data = {}

# ------------------- Topic menu (like quiz menu) -------------------
# Must match your intents patterns so get_bot_response(topic_name) works well.
TOPIC_MENU = {
    "1": "analog signals",
    "2": "digital signal",
    "3": "logic levels",
    "4": "number systems",
    "5": "decimal number system",
    "6": "binary number system",
    "7": "hexadecimal number system",
    "8": "combinational logic circuits",
    "9": "sum of products",          # matches SOP intent patterns
    "10": "product of sums",         # matches POS intent patterns
    "11": "minterm vs maxterm",
    "12": "truth table conversion",
    "13": "boolean algebra",
    "14": "logic simplification",
    "15": "de morgan's theorem",
    "16": "universal gates",
    "17": "karnaugh map",
    "18": "k-map grouping rules",
    "19": "don't care",
    "20": "seven segment display",
    "21": "common anode vs common cathode",
    "22": "basic binary addition",
    "23": "half adder",
    "24": "full adder",
    "25": "parallel binary adder",
    "26": "ripple carry adder",
    "27": "look-ahead carry adder",
    "28": "signed binary numbers",
    "29": "sign magnitude representation",
    "30": "1's complement",
    "31": "2's complement",
    "32": "2's complement addition",
    "33": "range of signed numbers",
}
# ------------------- Topic -> formula follow-up flow -------------------

NON_TOPIC_TAGS = {
    "greeting", "goodbye", "thanks", "who", "quizes", "topic", "noanswer"
}

FORMULA_PROMPT = "\n\n📘 Would you like to see more formulas? (yes / no)"

YES_WORDS = {"yes", "y", "yeah", "yup", "sure", "ok", "okay", "formula", "formulas"}
NO_WORDS  = {"no", "n", "nope", "nah"}

def append_formula_prompt(text: str) -> str:
    return (text or "") + FORMULA_PROMPT

def set_formula_state(tag: str):
    session["awaiting_formula_choice"] = True
    session["last_topic_tag"] = tag

def clear_formula_state():
    session.pop("awaiting_formula_choice", None)
    session.pop("last_topic_tag", None)

# ------------------- Topic follow-up prompt -------------------
NON_TOPIC_TAGS = {
    "greeting", "goodbye", "thanks", "who", "quizes", "topic", "noanswer"
}

FORMULA_PROMPT = "\n\n📘 Would you like to see the formulas? (yes / no)"

def append_formula_prompt(text: str) -> str:
    return (text or "") + FORMULA_PROMPT


def format_topic_menu() -> str:
    lines = ["📘 Available Topics:"]
    for k in sorted(TOPIC_MENU.keys(), key=lambda x: int(x)):
        # show nicer title-casing, but keep mapping values as patterns
        display = TOPIC_MENU[k]
        lines.append(f"{k}. {display.title()}")
    lines.append("")
    lines.append("Reply with a number (example: 6) to continue.")
    lines.append('Or type the topic name (example: "binary number system").')
    return "\n".join(lines)

# ------------------- Bot response matcher -------------------
def _match_intent(user_text: str):
    """
    Return (reply_text, intent_tag).
    """
    user_text = (user_text or "").lower().strip()

    pattern_list = []
    for intent in intents:
        for pattern in intent.get("patterns", []):
            p = (pattern or "").lower().strip()
            if p:
                pattern_list.append((p, intent))

    pattern_list.sort(key=lambda x: len(x[0]), reverse=True)

    # 1) Exact match
    for pattern_lower, intent in pattern_list:
        if user_text == pattern_lower:
            responses = intent.get("responses", [])
            reply = random.choice(responses) if responses else "OK."
            return reply, intent.get("tag", "noanswer")

    # 2) Very short input -> no substring matching
    if len(user_text) <= 2:
        return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."])), "noanswer"

    # 3) Substring match (pattern inside user_text)
    for pattern_lower, intent in pattern_list:
        if pattern_lower in user_text:
            responses = intent.get("responses", [])
            reply = random.choice(responses) if responses else "OK."
            return reply, intent.get("tag", "noanswer")

    return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."])), "noanswer"


def get_bot_response(user_text: str) -> str:
    reply, _tag = _match_intent(user_text)
    return reply

# ------------------- Pages -------------------
@app.route("/")
def home():
    return render_template("index.html")

# ------------------- Explain commands -------------------
EXPLAIN_TOPICS = {"ohm", "and", "or", "not", "nand", "nor", "xor"}

def parse_explain_command(msg: str):
    if not msg:
        return None
    m = re.match(r"^\s*explain\s+([a-zA-Z']+)\s*$", msg.strip().lower())
    if not m:
        return None
    topic = m.group(1).replace("'", "")
    return topic if topic in EXPLAIN_TOPICS else None

# ------------------- Quiz command parsing -------------------
def parse_quiz_command(msg: str):
    """
    Commands:
      /quiz
      /quiz <category>
      /quiz <category> random
      /quiz <category> <number>
    """
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
    lines = [
        f"📘 Quiz: {category}",
        f"Q{index_1based}. {q}"
    ]
    for i, c in enumerate(choices, start=1):
        lines.append(f"{i}) {c}")
    lines.append("")
    lines.append("Tip: reply 1-4")
    return "\n".join(lines)

# ------------------- Quiz answer handling -------------------
def is_quiz_answer(msg: str) -> bool:
    if not msg:
        return False
    s = msg.strip().lower()
    if s in {"a", "b", "c", "d"}:
        return True
    return s.isdigit() and 1 <= int(s) <= 9

def normalize_answer(msg: str) -> str:
    s = msg.strip().lower()
    mapping = {"a": "1", "b": "2", "c": "3", "d": "4"}
    return mapping.get(s, s)

def get_correct_option_number(q_obj: dict):
    choices = q_obj.get("choices", [])
    ans_i = q_obj.get("answer_index", None)

    if ans_i is None:
        return None

    try:
        ans_i = int(ans_i)
    except Exception:
        return None

    if ans_i < 0 or ans_i >= len(choices):
        return None

    return str(ans_i + 1)

def start_quiz_state(category: str, q_index_0based: int):
    session["quiz_active"] = True
    session["quiz_category"] = category
    session["quiz_index"] = int(q_index_0based)
    session["quiz_correct"] = 0
    session["quiz_answered"] = 0

def clear_state():
    # quiz state
    session.pop("quiz_active", None)
    session.pop("quiz_category", None)
    session.pop("quiz_index", None)
    session.pop("quiz_correct", None)
    session.pop("quiz_answered", None)
    session.pop("awaiting_quiz_pick", None)

    # topic state
    session.pop("awaiting_topic_pick", None)

    # formula follow-up state
    session.pop("awaiting_formula_choice", None)
    session.pop("last_topic_tag", None)

def grade_quiz_answer(user_msg: str):
    category = session.get("quiz_category")
    idx0 = session.get("quiz_index")

    if not category or category not in quiz_data or idx0 is None:
        clear_state()
        return {"type": "chat", "text": "❌ Quiz session lost. Start again with:\n/quiz"}

    questions = quiz_data.get(category, [])
    if not questions or idx0 < 0 or idx0 >= len(questions):
        clear_state()
        return {"type": "chat", "text": "❌ Quiz question not found. Start again with:\n/quiz"}

    q_obj = questions[idx0]
    correct_opt = get_correct_option_number(q_obj)
    if not correct_opt:
        return {"type": "chat", "text": "❌ This question has no valid 'answer_index' field in QUIZ.json."}

    user_opt = normalize_answer(user_msg)

    answered = int(session.get("quiz_answered", 0)) + 1
    correct = int(session.get("quiz_correct", 0))

    is_correct = (user_opt == correct_opt)
    if is_correct:
        correct += 1

    session["quiz_answered"] = answered
    session["quiz_correct"] = correct

    explain = (q_obj.get("explain") or "").strip()
    explain_block = f"\n\nExplanation:\n{explain}" if explain else ""

    status = "✅ Correct!" if is_correct else "❌ Incorrect."
    next_idx0 = idx0 + 1

    if next_idx0 >= len(questions):
        percent = (correct / answered) * 100 if answered else 0.0
        grade_line = f"Grade: {correct}/{answered} ({percent:.0f}%)"
        clear_state()
        return {
            "type": "chat",
            "text": status + explain_block + f"\n\n{grade_line}\n\n🏁 End of quiz."
        }

    session["quiz_index"] = next_idx0
    next_q = questions[next_idx0]
    q_text = format_question_text(category, next_q, next_idx0 + 1)

    return {"type": "chat", "text": status + explain_block + "\n\n" + q_text}

# ------------------- Chat API -------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = payload.get("message", "")
    msg_clean = (msg or "").strip().lower()

    # /clear clears quiz + topic state
    if msg_clean == "/clear":
        clear_state()
        return jsonify({"type": "chat", "text": "🧹 Cleared quiz/topic state."})

        # ------------------- yes/no after topic formula prompt -------------------
    if session.get("awaiting_formula_choice"):
        ans = msg_clean

        if ans in YES_WORDS:
            clear_formula_state()
            return jsonify({
                "type": "chat",
                "text": "Sorry, currently no formula available."
            })

        if ans in NO_WORDS:
            clear_formula_state()
            return jsonify({
                "type": "chat",
                "text": "Alright. You may type /topic to learn more."
            })

        # If user typed something else, gently remind
        return jsonify({
            "type": "chat",
            "text": "Please reply with **yes** or **no**.\n\n📘 Would you like to see more formulas? (yes / no)"
        })


    # ------------------- /topic menu -------------------
    if msg_clean in {"/topic", "topic", "topics", "show topics", "topic menu"}:
        # entering topic menu cancels pending quiz pick only (optional)
        session["awaiting_topic_pick"] = True
        return jsonify({"type": "chat", "text": format_topic_menu()})

    # ✅ Handle numeric topic selection after /topic
    if session.get("awaiting_topic_pick") and msg_clean.isdigit():
        session["awaiting_topic_pick"] = False

        topic_phrase = TOPIC_MENU.get(msg_clean)
        if not topic_phrase:
            return jsonify({"type": "chat", "text": "❌ Invalid selection. Type /topic to see the menu again."})

        # Use existing intents by passing a phrase that matches patterns
        reply, tag = _match_intent(topic_phrase)
        
        # Append formula prompt only for real topic intents
        if tag not in NON_TOPIC_TAGS:
            reply = append_formula_prompt(reply)
            set_formula_state(tag)
        
        return jsonify({"type": "chat", "text": reply})


    # ------------------- Quiz pick (numeric) after /quiz -------------------
    if session.get("awaiting_quiz_pick") and msg_clean.isdigit():
        session["awaiting_quiz_pick"] = False

        category = quiz_menu.get(msg_clean) if isinstance(quiz_menu, dict) else None
        if not category or category not in quiz_data:
            return jsonify({"type": "chat", "text": "❌ Invalid selection. Type /quiz to see the menu again."})

        questions = quiz_data.get(category, [])
        if not questions:
            clear_state()
            return jsonify({"type": "chat", "text": f"No questions found in category: {category}."})

        start_quiz_state(category, 0)
        q_obj = questions[0]
        if not get_correct_option_number(q_obj):
            return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer_index' field in QUIZ.json."})
        return jsonify({"type": "chat", "text": format_question_text(category, q_obj, 1)})

    # Intercept quiz answers
    if session.get("quiz_active") and is_quiz_answer(msg):
        return jsonify(grade_quiz_answer(msg))

    # Explain commands
    topic = parse_explain_command(msg)
    if topic:
        return jsonify({"type": "explain", "topic": topic})

    # Quiz commands
    quiz_cmd = parse_quiz_command(msg)
    if quiz_cmd:
        if quiz_error and not quiz_data:
            return jsonify({"type": "chat", "text": f"Quiz error: {quiz_error}"})

        if quiz_cmd["mode"] == "list":
            # don't wipe topic menu unless you want to
            session["awaiting_quiz_pick"] = True

            if not quiz_data:
                return jsonify({"type": "chat", "text": "No quiz categories found."})

            if isinstance(quiz_menu, dict) and quiz_menu:
                lines = ["✅ Available quiz categories:"]
                for k in sorted(quiz_menu.keys(), key=lambda x: int(x)):
                    lines.append(f"{k}. {quiz_menu[k]}")
                lines.append("")
                lines.append("Reply with a number (example: 6) to start.")
                lines.append("Or type: /quiz number_systems")
                return jsonify({"type": "chat", "text": "\n".join(lines)})

            cat_list = "\n- " + "\n- ".join(sorted(quiz_data.keys()))
            return jsonify({
                "type": "chat",
                "text": f"✅ Available quiz categories:{cat_list}\n\nStart one like:\n/quiz number_systems"
            })

        category = quiz_cmd.get("category", "")
        if category not in quiz_data:
            available = ", ".join(sorted(quiz_data.keys())) if quiz_data else "(none)"
            return jsonify({
                "type": "chat",
                "text": f"❌ Unknown quiz category: {category}\nAvailable: {available}\n\nTry:\n/quiz"
            })

        questions = quiz_data[category]
        if not questions:
            return jsonify({"type": "chat", "text": f"No questions found in category: {category}."})

        if quiz_cmd["mode"] == "random":
            q_obj = random.choice(questions)
            idx0 = questions.index(q_obj)
            start_quiz_state(category, idx0)
            if not get_correct_option_number(q_obj):
                return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer_index' field in QUIZ.json."})
            return jsonify({"type": "chat", "text": format_question_text(category, q_obj, idx0 + 1)})

        if quiz_cmd["mode"] == "number":
            qnum = quiz_cmd.get("qnum", 1)
            if qnum < 1 or qnum > len(questions):
                return jsonify({"type": "chat", "text": f"Question number out of range. Pick 1 to {len(questions)}."})
            idx0 = qnum - 1
            q_obj = questions[idx0]
            start_quiz_state(category, idx0)
            if not get_correct_option_number(q_obj):
                return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer_index' field in QUIZ.json."})
            return jsonify({"type": "chat", "text": format_question_text(category, q_obj, qnum)})

        q_obj = questions[0]
        start_quiz_state(category, 0)
        if not get_correct_option_number(q_obj):
            return jsonify({"type": "chat", "text": "❌ This question has no valid 'answer_index' field in QUIZ.json."})
        return jsonify({"type": "chat", "text": format_question_text(category, q_obj, 1)})

    # Normal chatbot
    reply, tag = _match_intent(msg)
    
    if tag not in NON_TOPIC_TAGS:
        reply = append_formula_prompt(reply)
        set_formula_state(tag)
    else:
        # if user asks something else, cancel any pending formula prompt
        clear_formula_state()
    
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



