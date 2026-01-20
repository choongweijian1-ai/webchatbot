from flask import Flask, request, jsonify, render_template, session, send_file
import json
import random
import os
import math
import re
from io import BytesIO
import fitz  # PyMuPDF

app = Flask(__name__)
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

# ------------------- Load circuits.json (series/parallel) -------------------
CIRCUITS_PATH = os.path.join(BASE_DIR, "circuits.json")
try:
    with open(CIRCUITS_PATH, "r", encoding="utf-8") as f:
        circuits_data = json.load(f)
except Exception:
    circuits_data = {}

# ------------------- Load QUIZ.json safely -------------------
QUIZ_FILENAME = "QUIZ.json"
QUIZ_PATH = os.path.join(BASE_DIR, QUIZ_FILENAME)

quiz_data = {}
quiz_menu = {}
quiz_error = None

try:
    with open(QUIZ_PATH, "r", encoding="utf-8") as f:
        quiz_file = json.load(f)
    quiz_data = quiz_file.get("quizzes", {})
    quiz_menu = quiz_file.get("quiz_menu", {})
except FileNotFoundError:
    quiz_error = f"{QUIZ_FILENAME} not found in repo root."
except json.JSONDecodeError as e:
    quiz_error = f"{QUIZ_FILENAME} is not valid JSON: {e}"

# ------------------- Topic menu -------------------
TOPIC_MENU = {
    "1": "analog signals",
    "2": "digital signal",
    "3": "logic levels",
    "4": "number systems",
    "5": "decimal number system",
    "6": "binary number system",
    "7": "hexadecimal number system",
    "8": "combinational logic circuits",
    "9": "sum of products",
    "10": "product of sums",
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

def format_topic_menu() -> str:
    lines = ["📘 Available Topics:"]
    for k in sorted(TOPIC_MENU.keys(), key=lambda x: int(x)):
        lines.append(f"{k}. {TOPIC_MENU[k].title()}")
    lines.append("")
    lines.append("Reply with a number (example: 6) to continue.")
    lines.append('Or type the topic name (example: "binary number system").')
    return "\n".join(lines)

# ------------------- Formula follow-up states -------------------
YES_WORDS = {"yes", "y", "yeah", "yup", "sure", "ok", "okay"}
NO_WORDS = {"no", "n", "nope", "nah"}
FORMULA_PROMPT = "\n\n📘 Would you like to learn more? (yes / no)"

def set_formula_state(key: str):
    session["awaiting_formula_choice"] = True
    session["last_formula_key"] = key

def clear_formula_state():
    session.pop("awaiting_formula_choice", None)
    session.pop("last_formula_key", None)

def clear_state():
    session.pop("quiz_active", None)
    session.pop("quiz_category", None)
    session.pop("quiz_index", None)
    session.pop("quiz_correct", None)
    session.pop("quiz_answered", None)
    session.pop("awaiting_quiz_pick", None)
    session.pop("awaiting_topic_pick", None)
    clear_formula_state()

# ------------------- Text normalization + safe matching -------------------
def normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def has_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None

# ------------------- Bot matcher (intents.json) -------------------
def _match_intent(user_text: str):
    user_text = normalize_text(user_text)

    pattern_list = []
    for intent in intents:
        for pattern in intent.get("patterns", []):
            p = normalize_text(pattern)
            if p:
                pattern_list.append((p, intent))
    pattern_list.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern_lower, intent in pattern_list:
        if user_text == pattern_lower:
            responses = intent.get("responses", [])
            return (random.choice(responses) if responses else "OK."), intent.get("tag", "noanswer")

    if len(user_text) <= 2:
        return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."])), "noanswer"

    for pattern_lower, intent in pattern_list:
        if has_term(user_text, pattern_lower):
            responses = intent.get("responses", [])
            return (random.choice(responses) if responses else "OK."), intent.get("tag", "noanswer")

    return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."])), "noanswer"

# ------------------- Explain command -------------------
EXPLAIN_TOPICS = {"ohm", "and", "or", "not", "nand", "nor", "xor"}

def parse_explain_command(msg_clean: str):
    parts = msg_clean.split()
    if len(parts) == 2 and parts[0] == "explain":
        topic = parts[1]
        if topic in EXPLAIN_TOPICS:
            return topic
    return None

# ------------------- Circuits formatting -------------------
def format_circuit_text(key: str) -> str:
    c = circuits_data.get(key)
    if not c:
        return "❌ Circuit topic not found."

    lines = [f"📘 {c.get('title','')}", "", c.get("description",""), ""]
    if c.get("key_points"):
        lines.append("Key Points:")
        for p in c["key_points"]:
            lines.append(f"• {p}")
        lines.append("")

    if c.get("formulas"):
        lines.append("Formulas:")
        for f in c["formulas"]:
            lines.append(f"• {f}")
        lines.append("")

    if c.get("examples"):
        lines.append("Examples:")
        for e in c.get("examples", []):
            lines.append(f"• {e}")

    return "\n".join(lines)

# ------------------- Logic gates query -------------------
def is_logic_gates_query(msg_clean: str) -> bool:
    s = msg_clean.replace(" ", "")
    return (
        msg_clean in {"logic gate", "logic gates"} or
        s in {"logicgate", "logicgates"} or
        msg_clean.startswith("logic gate") or
        msg_clean.startswith("logic gates")
    )

# ------------------- Analogue electronics query -------------------
def is_analog_electronics_query(msg_clean: str) -> bool:
    s = msg_clean.replace(" ", "")
    return (
        msg_clean in {"analog electronics", "analogue electronics"} or
        s in {"analogelectronics", "analogueelectronics"} or
        msg_clean.startswith("analog") or
        msg_clean.startswith("analogue")
    )

# ------------------- Better series/parallel detection -------------------
def is_series_query(msg_clean: str) -> bool:
    s = msg_clean.replace(" ", "")
    return msg_clean in {"series", "series circuit"} or s in {"series", "seriescircuit"} or msg_clean.startswith("series")

def is_parallel_query(msg_clean: str) -> bool:
    s = msg_clean.replace(" ", "")
    return msg_clean in {"parallel", "parallel circuit"} or s in {"parallel", "parallelcircuit"} or msg_clean.startswith("parallel")

# ------------------- Pages -------------------
@app.route("/")
def home():
    return render_template("index.html")

# ------------------- Serve PDF pages (ANY pdf in /pdfs) as images -------------------
@app.route("/pdf/<pdf_name>/page/<int:page_num>.png")
def pdf_page_png(pdf_name: str, page_num: int):
    if page_num < 1:
        return "Invalid page", 400

    safe_name = os.path.basename(pdf_name)  # security: blocks ../ tricks
    pdf_path = os.path.join(BASE_DIR, "pdfs", safe_name)

    if not safe_name.lower().endswith(".pdf"):
        return "Invalid file", 400
    if not os.path.exists(pdf_path):
        return "PDF not found on server", 404

    with fitz.open(pdf_path) as doc:
        if page_num > doc.page_count:
            return "Invalid page", 400
        page = doc.load_page(page_num - 1)
        pix = page.get_pixmap(dpi=150)

    return send_file(BytesIO(pix.tobytes("png")), mimetype="image/png")

# ------------------- Quiz helpers -------------------
def format_quiz_menu() -> str:
    lines = ["✅ Available quiz categories:"]
    if isinstance(quiz_menu, dict) and quiz_menu:
        for k in sorted(quiz_menu.keys(), key=lambda x: int(x)):
            lines.append(f"{k}. {quiz_menu[k]}")
    else:
        keys = sorted(list(quiz_data.keys()))
        for i, k in enumerate(keys, start=1):
            lines.append(f"{i}. {k}")

    lines.append("")
    lines.append("Reply with a number (example: 1) to start.")
    return "\n".join(lines)

def format_question_text(category: str, q_obj: dict, index_1based: int) -> str:
    q = q_obj.get("q", "")
    choices = q_obj.get("choices", [])
    lines = [f"📘 Quiz: {category}", f"Q{index_1based}. {q}"]
    for i, c in enumerate(choices, start=1):
        lines.append(f"{i}) {c}")
    lines.append("")
    lines.append("Tip: reply 1–4")
    return "\n".join(lines)

def is_quiz_answer(msg: str) -> bool:
    if not msg:
        return False
    s = msg.strip()
    return s.isdigit() and 1 <= int(s) <= 4

def get_correct_option_number(q_obj: dict):
    choices = q_obj.get("choices", [])
    ans_i = q_obj.get("answer_index", None)
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
        return {"type": "chat", "text": "❌ This question has no valid 'answer_index' in QUIZ.json."}

    user_opt = user_msg.strip()

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
        return {"type": "chat", "text": status + explain_block + f"\n\n{grade_line}\n\n🏁 End of quiz."}

    session["quiz_index"] = next_idx0
    next_q = questions[next_idx0]
    q_text = format_question_text(category, next_q, next_idx0 + 1)
    return {"type": "chat", "text": status + explain_block + "\n\n" + q_text}

# ------------------- Chat API -------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = (payload.get("message", "") or "")
    msg_raw = msg.strip().lower()

    # Clear everything
    if msg_raw == "/clear":
        clear_state()
        return jsonify({"type": "chat", "text": "🧹 Cleared state."})

    # /topic opens topic menu
    if msg_raw == "/topic":
        session["awaiting_topic_pick"] = True
        return jsonify({"type": "chat", "text": format_topic_menu()})

    # /quiz opens quiz menu
    if msg_raw == "/quiz":
        if quiz_error and not quiz_data:
            return jsonify({"type": "chat", "text": f"Quiz error: {quiz_error}"})
        if not quiz_data:
            return jsonify({"type": "chat", "text": "No quiz categories found."})
        session["awaiting_quiz_pick"] = True
        return jsonify({"type": "chat", "text": format_quiz_menu()})

    msg_clean = normalize_text(msg)

    # picking quiz category
    if session.get("awaiting_quiz_pick") and msg_clean.isdigit():
        session["awaiting_quiz_pick"] = False
        category = quiz_menu.get(msg_clean) if isinstance(quiz_menu, dict) else None

        if not category:
            keys = sorted(list(quiz_data.keys()))
            idx = int(msg_clean) - 1
            category = keys[idx] if 0 <= idx < len(keys) else None

        if not category or category not in quiz_data:
            return jsonify({"type": "chat", "text": "❌ Invalid selection. Type /quiz to see the menu again."})

        questions = quiz_data.get(category, [])
        if not questions:
            clear_state()
            return jsonify({"type": "chat", "text": f"No questions found in category: {category}."})

        start_quiz_state(category, 0)
        q_obj = questions[0]
        return jsonify({"type": "chat", "text": format_question_text(category, q_obj, 1)})

    # quiz active: answer 1-4
    if session.get("quiz_active") and is_quiz_answer(msg):
        return jsonify(grade_quiz_answer(msg))

    # explain
    explain_topic = parse_explain_command(msg_clean)
    if explain_topic:
        return jsonify({"type": "explain", "topic": explain_topic})

    # logic gates pdf
    if is_logic_gates_query(msg_clean):
        images = [
            f"/pdf/logic_gates.pdf/page/{p}.png"
            for p in range(41, 57)
            if p not in {42, 43}
        ]
        session["awaiting_topic_pick"] = False
        return jsonify({
            "type": "chat",
            "text": "📘 Logic Gates (Slides 41–57, excluding 42 & 43)",
            "images": images
        })

    # analogue electronics pdf
    if is_analog_electronics_query(msg_clean):
        images = [
            f"/pdf/ANALOGUE_ELECTRONICS.pdf/page/{p}.png"
            for p in range(1, 13)
        ]
        session["awaiting_topic_pick"] = False
        return jsonify({
            "type": "chat",
            "text": "📘 BJT(Bipolar Junction Transistor), (Slides 1–12)",
            "images": images
        })

    # series/parallel (works anytime, even after /topic)
    if is_series_query(msg_clean):
        set_formula_state("series")
        return jsonify({"type": "chat", "text": format_circuit_text("series") + FORMULA_PROMPT})

    if is_parallel_query(msg_clean):
        set_formula_state("parallel")
        return jsonify({"type": "chat", "text": format_circuit_text("parallel") + FORMULA_PROMPT})

    # formula yes/no
    if session.get("awaiting_formula_choice"):
        ans = msg_clean

        if ans in YES_WORDS:
            key = session.get("last_formula_key")
            clear_formula_state()

            imgs = []
            if key and key in circuits_data:
                imgs = circuits_data[key].get("formula_images", []) or []

            if imgs:
                return jsonify({"type": "chat", "text": "Here are the formulas:", "images": imgs})

            return jsonify({"type": "chat", "text": "Sorry, currently no formula available."})

        if ans in NO_WORDS:
            clear_formula_state()
            return jsonify({"type": "chat", "text": "Alright. You may type /topic or /quiz to learn more."})

        return jsonify({"type": "chat", "text": "Please reply with yes or no.\n\n📘 Would you like to learn more? (yes / no)"})

    # topic selection mode
    if session.get("awaiting_topic_pick"):
        if msg_clean.isdigit():
            topic_phrase = TOPIC_MENU.get(msg_clean)
            if not topic_phrase:
                return jsonify({"type": "chat", "text": "❌ Invalid selection. Type /topic to see the menu again."})
            session["awaiting_topic_pick"] = False
            reply, _tag = _match_intent(topic_phrase)
            return jsonify({"type": "chat", "text": reply})

        normalized_menu = {normalize_text(v): v for v in TOPIC_MENU.values()}
        if msg_clean in normalized_menu:
            session["awaiting_topic_pick"] = False
            reply, _tag = _match_intent(normalized_menu[msg_clean])
            return jsonify({"type": "chat", "text": reply})

        return jsonify({"type": "chat", "text": "❌ Please reply with a topic number or name.\nType /topic to see the menu again."})

    # normal intents
    reply, _tag = _match_intent(msg)
    return jsonify({"type": "chat", "text": reply})

# ------------------- APIs -------------------
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

