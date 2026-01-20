from flask import Flask, request, jsonify, render_template, session, send_file
import json
import random
import os
import math
import re
from io import BytesIO

import fitz  # PyMuPDF

app = Flask(__name__)

# ✅ REQUIRED for Flask session storage
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_change_me")

# ------------------- Base directory -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------- PDF path -------------------
PDF_PATH = os.path.join(BASE_DIR, "pdfs", "logic_gates.pdf")

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

# ------------------- Load QUIZ.json safely (still loaded, but commands disabled) -------------------
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

# ------------------- Topic menu (like quiz menu) -------------------
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
    # quiz state (kept for safety, even though quiz commands are disabled)
    session.pop("quiz_active", None)
    session.pop("quiz_category", None)
    session.pop("quiz_index", None)
    session.pop("quiz_correct", None)
    session.pop("quiz_answered", None)
    session.pop("awaiting_quiz_pick", None)

    # topic state
    session.pop("awaiting_topic_pick", None)

    # formula state
    clear_formula_state()

# ------------------- Text normalization + safe matching -------------------
def normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def has_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None

# ------------------- Bot matcher -------------------
def _match_intent(user_text: str):
    user_text = normalize_text(user_text)

    pattern_list = []
    for intent in intents:
        for pattern in intent.get("patterns", []):
            p = normalize_text(pattern)
            if p:
                pattern_list.append((p, intent))
    pattern_list.sort(key=lambda x: len(x[0]), reverse=True)

    # exact match first
    for pattern_lower, intent in pattern_list:
        if user_text == pattern_lower:
            responses = intent.get("responses", [])
            return (random.choice(responses) if responses else "OK."), intent.get("tag", "noanswer")

    if len(user_text) <= 2:
        return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."])), "noanswer"

    # word-boundary match
    for pattern_lower, intent in pattern_list:
        if has_term(user_text, pattern_lower):
            responses = intent.get("responses", [])
            return (random.choice(responses) if responses else "OK."), intent.get("tag", "noanswer")

    return random.choice(noanswer_intent.get("responses", ["Sorry, I didn't understand."])), "noanswer"

# ------------------- Pages -------------------
@app.route("/")
def home():
    return render_template("index.html")

# ------------------- Serve PDF pages as images -------------------
@app.route("/pdf/page/<int:page_num>.png")
def pdf_page_png(page_num: int):
    """
    page_num is 1-based (human-friendly)
    """
    if page_num < 1:
        return "Invalid page", 400

    if not os.path.exists(PDF_PATH):
        return "PDF not found on server", 404

    doc = fitz.open(PDF_PATH)
    if page_num > doc.page_count:
        doc.close()
        return "Invalid page", 400

    page = doc.load_page(page_num - 1)  # 0-based
    pix = page.get_pixmap(dpi=120)
    doc.close()

    return send_file(BytesIO(pix.tobytes("png")), mimetype="image/png")

# ------------------- Chat API -------------------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    msg = (payload.get("message", "") or "")

    # ✅ RAW command check FIRST (before normalize_text)
    msg_raw = msg.strip().lower()

    # Clear everything
    if msg_raw == "/clear":
        clear_state()
        return jsonify({"type": "chat", "text": "🧹 Cleared state."})

    # ✅ ONLY /topic opens topic menu
    if msg_raw == "/topic":
        session["awaiting_topic_pick"] = True
        return jsonify({"type": "chat", "text": format_topic_menu()})

    # ✅ normalize after raw commands
    msg_clean = normalize_text(msg)

    # ------------------- yes/no after formula prompt -------------------
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
            return jsonify({"type": "chat", "text": "Alright. You may type /topic to learn more."})

        return jsonify({
            "type": "chat",
            "text": "Please reply with yes or no.\n\n📘 Would you like to see more formulas? (yes / no)"
        })

    # ------------------- Topic selection mode (after /topic) -------------------
    if session.get("awaiting_topic_pick"):

        # ✅ Special: show PDF pages 41–57 for "logic gates"
        if msg_clean == "logic gates":
            images = [f"/pdf/page/{p}.png" for p in range(41, 58)]  # 41..57
            session["awaiting_topic_pick"] = False
            return jsonify({
                "type": "chat",
                "text": "📘 Logic Gates (Slides 41–57)",
                "images": images
            })

        # number selection
        if msg_clean.isdigit():
            topic_phrase = TOPIC_MENU.get(msg_clean)
            if not topic_phrase:
                return jsonify({"type": "chat", "text": "❌ Invalid selection. Type /topic to see the menu again."})

            session["awaiting_topic_pick"] = False
            reply, _tag = _match_intent(topic_phrase)
            return jsonify({"type": "chat", "text": reply})

        # topic name selection
        normalized_menu = {normalize_text(v): v for v in TOPIC_MENU.values()}
        if msg_clean in normalized_menu:
            session["awaiting_topic_pick"] = False
            reply, _tag = _match_intent(normalized_menu[msg_clean])
            return jsonify({"type": "chat", "text": reply})

        return jsonify({
            "type": "chat",
            "text": "❌ Please reply with a topic number (example: 6) or type the topic name.\nType /topic to see the menu again."
        })

    # ------------------- Normal chatbot (uses intents.json) -------------------
    reply, _tag = _match_intent(msg)
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

