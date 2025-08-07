import os
import time
import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
from openai import OpenAI
from llm_providers import get_available_providers, get_provider

app = Flask(__name__)
app.secret_key = os.urandom(24)  # <-- change for production

# Load .env file
load_dotenv()

# OpenAI setup for image generation
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Master prompts
MASTER_PROMPT = """
You are a friendly storyteller, writing a bedtime story for a child.
The story should be gentle, positive, and suitable for bedtime.
Make it engaging, keep sentences short, and avoid any scary or disturbing content.

Here is what the user gave you to try and use in the story.
Don't feel like you need to use all of it, but weave in what you can:

"""

IMAGE_SUMMARY_PROMPT = """
Based on the following bedtime story, create a brief description for an image that would be perfect to accompany this story.
The image should be child-friendly, magical, and capture the main scene or feeling of the story.
Keep the description under 200 characters and focus on visual elements that would delight a child.
Do not include any text or words in the image description.
Do not include any children in the picture, but instead focus on characters and elements of the story so they can imagine themselves in it.

Story:
"""

# Helper functions
def generate_story(provider_name: str, prompt: str) -> str:
    """
    Generate a story using the specified LLM provider.
    """
    try:
        provider = get_provider(provider_name)
        return provider.generate_text(prompt)
    except Exception as e:
        return f"[Error with {provider_name}: {e}]"

def generate_image_prompt(provider_name: str, story: str) -> str:
    """
    Uses the selected LLM provider to create a concise image description based on the story.
    """
    full_prompt = IMAGE_SUMMARY_PROMPT + story
    return generate_story(provider_name, full_prompt).strip()

def generate_image_with_openai(prompt: str) -> str:
    """
    Generates an image using OpenAI's DALL-E API and returns the image URL.
    """
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Children's book illustration style: {prompt}. Soft, warm colors, gentle and magical atmosphere, perfect for bedtime.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

# Routes
@app.route("/", methods=["GET"])
def index():
    available_providers = get_available_providers()
    print(available_providers)
    return render_template("index.html", available_providers=available_providers)


@app.route("/start", methods=["POST"])
def start():
    """
    Stores the user data in the session and redirects to the wait page.
    """
    session["name_and_friends"] = request.form.get("names", "")
    session["favourite_things"] = request.form.get("things", "")
    session["topic"] = request.form.get("topic", "")
    session["llm_provider"] = request.form.get("llm_provider", "ollama")
    # Store whether user wants image generation (checkbox returns "on" if checked, None if not)
    session["generate_image"] = request.form.get("generate_image") == "on"
    return redirect(url_for("wait"))

@app.route("/wait")
def wait():
    """
    Shows the "Please wait…" page. The page triggers the story generation.
    """
    return render_template("wait.html")

@app.route("/generate", methods=["POST"])
def generate():
    """
    Generates the story using the selected LLM provider and stores it in the session.
    """
    user_prompt = (
        f"Names: {session.get('name_and_friends', '')}\n"
        f"Favourite things: {session.get('favourite_things', '')}\n"
        f"Topic: {session.get('topic', '')}\n"
    )
    full_prompt = MASTER_PROMPT + user_prompt

    # Generate the story using the selected provider
    provider_name = session.get("llm_provider", "ollama")
    story = generate_story(provider_name, full_prompt)
    session["story"] = story

    return jsonify({"status": "ok"})

@app.route("/result")
def result():
    """
    Display the generated story with optional image generation capability.
    """
    story = session.get("story", "No story generated.")
    should_generate_image = session.get("generate_image", False)
    return render_template("result.html", story=story, generate_image=should_generate_image)

@app.route("/generate_image", methods=["POST"])
def generate_image():
    """
    Generates an image based on the story and returns the image URL.
    """
    story = session.get("story", "")
    if not story:
        return jsonify({"error": "No story found"}), 400

    # Generate image description using the same LLM provider that created the story
    provider_name = session.get("llm_provider", "ollama")
    image_description = generate_image_prompt(provider_name, story)

    # Generate the actual image
    image_url = generate_image_with_openai(image_description)

    if image_url:
        session["image_url"] = image_url
        return jsonify({"status": "success", "image_url": image_url})
    else:
        return jsonify({"error": "Failed to generate image"}), 500

@app.route("/check_image")
def check_image():
    """
    Check if an image has been generated for the current story.
    """
    image_url = session.get("image_url")
    if image_url:
        return jsonify({"status": "ready", "image_url": image_url})
    else:
        return jsonify({"status": "generating"})

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1337, debug=True)
