import os
import time
import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)

# ------------------------------------------------------------------
# 1.  Flask app setup
# ------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)  # <-- change for production

# ------------------------------------------------------------------
# 2.  Ollama configuration
# ------------------------------------------------------------------
OLLAMA_HOST = "http://localhost:11434"
MODEL = "mistral:latest"          # ← change to whatever model you are running

# ------------------------------------------------------------------
# 3.  Master prompt (edit this to tweak story behaviour)
# ------------------------------------------------------------------
MASTER_PROMPT = """
You are a friendly storyteller, writing a bedtime story for a child.
The story should be gentle, positive, and suitable for bedtime.
Make it engaging, keep sentences short, and avoid any scary or disturbing content.

Here is what the user gave you to try and use in the story.
Don't feel like you need to use all of it, but weave in what you can:

"""

# ------------------------------------------------------------------
# 4.  Helper – call Ollama
# ------------------------------------------------------------------
def call_ollama(prompt: str) -> str:
    """
    Sends a request to the local Ollama API and returns the generated text.
    """
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,          # we want the full result in one go
    }
    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=60,  # seconds
        )
        r.raise_for_status()
        # Ollama returns a JSON with a `response` key
        return r.json().get("response", "")
    except Exception as e:
        # In production you’d want better error handling/logging
        return f"[Error contacting Ollama: {e}]"

# ------------------------------------------------------------------
# 5.  Routes
# ------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start():
    """
    Stores the user data in the session and redirects to the wait page.
    """
    session["name_and_friends"] = request.form.get("names", "")
    session["favourite_things"] = request.form.get("things", "")
    session["topic"] = request.form.get("topic", "")
    return redirect(url_for("wait"))


@app.route("/wait")
def wait():
    """
    Shows the “Please wait…” page.  The page immediately triggers
    the LLM call via JavaScript, then redirects to /result.
    """
    return render_template("wait.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    This endpoint is called by the JavaScript on the wait page.
    It runs the LLM call and stores the result in the session.
    """
    # Re‑build the user prompt
    user_prompt = (
        f"Names: {session.get('name_and_friends', '')}\n"
        f"Favourite things: {session.get('favourite_things', '')}\n"
        f"Topic: {session.get('topic', '')}\n"
    )
    full_prompt = MASTER_PROMPT + user_prompt

    # Call the LLM
    story = call_ollama(full_prompt)

    # Save result in session so /result can display it
    session["story"] = story

    # Return a small JSON to signal completion
    return jsonify({"status": "ok"})


@app.route("/result")
def result():
    """
    Display the generated story.
    """
    story = session.get("story", "No story generated.")
    return render_template("result.html", story=story)


# ------------------------------------------------------------------
# 6.  Run
# ------------------------------------------------------------------
if __name__ == "__main__":
    # For development – set debug=True
    app.run(host="0.0.0.0", port=1337, debug=True)
