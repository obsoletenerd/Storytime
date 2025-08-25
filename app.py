import os
import time
import requests
from datetime import datetime
import re
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
You are a masterful storyteller creating an engaging bedtime story for a child.
If the age of the child is mentioned in the input, adapt the story to suit.
If no age is mentioned, assume the child is around 8 years old.

STORY REQUIREMENTS:
- Write a complete story that's 8-12 paragraphs long (aim for about 800-1200 words)
- The story should be gentle, positive, funny, engaging, and adventurous
- Include a clear beginning, middle with multiple events/challenges, and satisfying ending

STORY STRUCTURE - Choose ONE of these varied formats:
1. Quest Adventure: Character goes on a journey with 3-4 different challenges/discoveries
2. Mystery Story: Character discovers something puzzling and solves it through multiple clues
3. Friendship Tale: Character meets new friends and they have several adventures together
4. Magic Discovery: Character finds something magical that leads to multiple magical experiences
5. Problem-Solving Story: Character faces a problem that requires several creative attempts to solve
6. Exploration Adventure: Character explores a new place and has multiple discoveries/encounters

VARIETY ELEMENTS - Include 2-3 of these to make each story unique:
- Talking animals with distinct personalities
- A magical object or ability
- A helpful mentor figure
- A silly misunderstanding that gets resolved
- A creative invention or solution
- A celebration or festival
- Weather that affects the adventure
- A map, riddle, or puzzle to solve
- An unexpected ally
- A cozy hideout or special place

PACING:
- Spend 2-3 paragraphs setting up the character and situation
- Include 4-6 paragraphs of main adventure with multiple events
- Use 2-3 paragraphs for a satisfying conclusion that ties everything together
- Add sensory details (what characters see, hear, smell, feel) to make scenes vivid
- Include dialogue to bring characters to life

Here is what the user gave you to try and use in the story.
Don't feel like you need to use all of it, but weave in what you can naturally.

"""


IMAGE_SUMMARY_PROMPT = """
Based on the following story, create a brief description for an image that would be perfect to accompany this story.
The image should be child-friendly and capture the main scene or feeling of the story.
Keep the description under 200 characters and focus on visual elements that would delight a 6-12 year old (not toddler).
Do not include any text or words in the image.
Do not include any children in the picture, but instead focus on characters and elements of the story so they can imagine themselves in it.

Story:
"""

TITLE_EXTRACTION_PROMPT = """
Based on the following bedtime story, create a short, catchy title that captures the essence of the story.
The title should be:
- 3-8 words long
- Child-friendly and engaging
- Capture the main adventure or theme
- Suitable for a bedtime story

Only respond with the title, nothing else.

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

def extract_story_title(provider_name: str, story: str) -> str:
    """
    Uses the selected LLM provider to extract a concise title from the story.
    """
    full_prompt = TITLE_EXTRACTION_PROMPT + story
    title = generate_story(provider_name, full_prompt).strip()

    # Clean the title to make it filename-safe
    # Remove quotes if the AI wrapped the title in them
    title = title.strip('"\'')
    # Replace problematic characters with safe ones
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces with underscores and limit length
    title = title.replace(' ', '_')[:50]

    return title if title else "Untitled_Story"

def save_story_to_file(story: str, provider_name: str) -> str:
    """
    Saves the story to a markdown file with date and AI-generated title.
    Returns the filename of the saved file.
    """
    # Create stories directory if it doesn't exist
    stories_dir = "stories"
    if not os.path.exists(stories_dir):
        os.makedirs(stories_dir)

    # Get current date
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Extract title from story
    title = extract_story_title(provider_name, story)

    # Create filename
    filename = f"{date_str}_{title}.md"
    filepath = os.path.join(stories_dir, filename)

    # Create markdown content
    markdown_content = f"# {title.replace('_', ' ')}\n\n"
    markdown_content += f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n"
    markdown_content += f"*Using provider: {provider_name}*\n\n"
    markdown_content += "---\n\n"
    markdown_content += story

    # Save to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Story saved to: {filepath}")
        return filename
    except Exception as e:
        print(f"Error saving story: {e}")
        return None

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
    Also saves the story to a local file.
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

    # Save the story to a file
    saved_filename = save_story_to_file(story, provider_name)
    if saved_filename:
        session["saved_filename"] = saved_filename

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
