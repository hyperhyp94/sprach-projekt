import os
import json
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__, static_folder=".", static_url_path="")

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "vocab_de.json")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "data", "progress.json")

os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)


def load_vocab():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {}
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def initial_state():
    return {
        "next_review": datetime.now(timezone.utc).isoformat(),
        "ease_factor": 2.5,
        "interval_days": 0,
        "repetitions": 0,
        "last_review": None,
    }


def compute_sm2(state, q):
    """Apply SM-2 algorithm. q is 0 (Again), 2 (Hard), 3 (Good), or 5 (Easy)."""
    now = datetime.now(timezone.utc)
    ef = state["ease_factor"]
    n = state["repetitions"]
    interval = state["interval_days"]

    if q == 0:
        # Wiederholen: reset, 10 minutes, EF unchanged
        new_n = 0
        new_ef = ef
        new_interval = 10 / 1440  # 10 minutes expressed as fraction of a day
        next_review = now + timedelta(minutes=10)

    elif q == 2:
        # Schwer: reset, 1 day, EF -0.2
        new_n = 0
        new_ef = max(1.3, ef - 0.2)
        new_interval = 1
        next_review = now + timedelta(days=1)

    elif q == 3:
        # Gut: apply EF formula, interval based on repetition count
        new_ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
        new_n = n + 1
        if n == 0:
            new_interval = 1
        elif n == 1:
            new_interval = 6
        else:
            new_interval = interval * ef
        next_review = now + timedelta(days=new_interval)

    elif q == 5:
        # Leicht: like Gut, but EF +0.15 and interval × 1.3
        new_ef = max(1.3, ef + 0.15)
        new_n = n + 1
        if n == 0:
            new_interval = 1 * 1.3
        elif n == 1:
            new_interval = 6 * 1.3
        else:
            new_interval = interval * ef * 1.3
        next_review = now + timedelta(days=new_interval)

    else:
        return state  # invalid rating, return unchanged

    return {
        "next_review": next_review.isoformat(),
        "ease_factor": round(new_ef, 4),
        "interval_days": round(new_interval, 4),
        "repetitions": new_n,
        "last_review": now.isoformat(),
    }


def parse_dt(s):
    """Parse an ISO datetime string, always returning a UTC-aware datetime."""
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/vocab")
def api_vocab():
    lang = request.args.get("lang", "es")
    category = request.args.get("category", "all")

    if lang not in ("es", "tr"):
        return jsonify({"error": "Invalid language. Use 'es' or 'tr'."}), 400

    vocab = load_vocab()
    lang_data = vocab.get(lang, {})

    if category == "all":
        result = []
        for cat, words in lang_data.items():
            for w in words:
                result.append({"word": w["word"], "translation": w["translation"], "category": cat})
    else:
        if category not in lang_data:
            return jsonify({"error": f"Category '{category}' not found."}), 404
        result = [
            {"word": w["word"], "translation": w["translation"], "category": category}
            for w in lang_data[category]
        ]

    return jsonify(result)


@app.route("/api/categories")
def api_categories():
    lang = request.args.get("lang", "es")

    if lang not in ("es", "tr"):
        return jsonify({"error": "Invalid language. Use 'es' or 'tr'."}), 400

    vocab = load_vocab()
    lang_data = vocab.get(lang, {})
    categories = list(lang_data.keys())

    return jsonify(categories)


@app.route("/api/progress", methods=["GET"])
def api_progress_get():
    lang = request.args.get("lang", "es")

    if lang not in ("es", "tr"):
        return jsonify({"error": "Invalid language"}), 400

    vocab = load_vocab()
    lang_data = vocab.get(lang, {})
    progress = load_progress()
    lang_progress = progress.get(lang, {})

    # Ensure all words have an initial state
    changed = False
    for cat, words in lang_data.items():
        for w in words:
            word = w["word"]
            if word not in lang_progress:
                lang_progress[word] = initial_state()
                changed = True

    if changed:
        progress[lang] = lang_progress
        save_progress(progress)

    return jsonify(lang_progress)


@app.route("/api/progress", methods=["POST"])
def api_progress_post():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    lang = data.get("lang")
    word = data.get("word")
    rating = data.get("rating")

    if lang not in ("es", "tr"):
        return jsonify({"error": "Invalid language"}), 400
    if not word:
        return jsonify({"error": "Missing word"}), 400
    if rating not in (0, 2, 3, 5):
        return jsonify({"error": "Invalid rating. Use 0, 2, 3, or 5."}), 400

    progress = load_progress()
    lang_progress = progress.get(lang, {})
    state = lang_progress.get(word, initial_state())
    new_state = compute_sm2(state, rating)
    lang_progress[word] = new_state
    progress[lang] = lang_progress
    save_progress(progress)

    return jsonify(new_state)


@app.route("/api/due")
def api_due():
    lang = request.args.get("lang", "es")
    category = request.args.get("category", "all")

    if lang not in ("es", "tr"):
        return jsonify({"error": "Invalid language"}), 400

    vocab = load_vocab()
    lang_data = vocab.get(lang, {})
    progress = load_progress()
    lang_progress = progress.get(lang, {})

    now = datetime.now(timezone.utc)

    # Build list of all words in current filter
    all_words = []
    if category == "all":
        for cat, words in lang_data.items():
            for w in words:
                all_words.append({"word": w["word"], "translation": w["translation"], "category": cat})
    else:
        if category not in lang_data:
            return jsonify({"error": f"Category '{category}' not found."}), 404
        for w in lang_data[category]:
            all_words.append({"word": w["word"], "translation": w["translation"], "category": category})

    due_cards = []
    new_cards = []
    next_due_dt = None
    reviewed_count = 0

    for card in all_words:
        word = card["word"]
        state = lang_progress.get(word, initial_state())
        repetitions = state.get("repetitions", 0)
        last_review = state.get("last_review")
        next_review_dt = parse_dt(state.get("next_review")) or now

        is_new = repetitions == 0 and last_review is None
        is_due = next_review_dt <= now

        if is_new:
            new_cards.append(card)

        if not is_new:
            reviewed_count += 1

        if is_due or is_new:
            due_cards.append({**card, "_next_review_dt": next_review_dt, "state": state})
        else:
            # Track the soonest upcoming review
            if next_due_dt is None or next_review_dt < next_due_dt:
                next_due_dt = next_review_dt

    # Sort due cards: oldest next_review first
    due_cards.sort(key=lambda x: x["_next_review_dt"])

    # Strip internal field before returning
    result_cards = [
        {"word": c["word"], "translation": c["translation"], "category": c["category"], "state": c["state"]}
        for c in due_cards
    ]

    return jsonify({
        "due": result_cards,
        "new_cards": new_cards,
        "stats": {
            "due_count": len(due_cards),
            "new_count": len(new_cards),
            "total_count": len(all_words),
            "reviewed_count": reviewed_count,
            "next_due": next_due_dt.isoformat() if next_due_dt else None,
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("TOOL_PORT", "5111"))
    app.run(host="0.0.0.0", port=port, debug=False)
