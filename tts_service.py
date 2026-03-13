from flask import Flask, request
from TTS.api import TTS
from urllib.parse import quote
import requests
import subprocess
import os

app = Flask(__name__)

# Load TTS model (Note: This may take a moment on startup)
# Using a slightly faster model for your i5 CPU
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

GHOST_URL = "http://localhost:2368"
CONTENT_API_KEY = "4076763c15f0f6f4d648483771"

# Ensure this directory exists
AUDIO_DIR = "/home/abinet/Desktop/ghost-cms/content/themes/ghost-audio-theme/assets/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    data = request.json
    
    # 1. Correctly extract post data from Ghost Webhook structure
    # Ghost wraps the post in ['post']['current']
    current_post = data.get("post", {}).get("current", {})
    
    post_id = current_post.get("id")
    slug = current_post.get("slug")
    title = current_post.get("title")

    print("........................slug", slug)
    
    wav_path = os.path.join(AUDIO_DIR, f"{slug}.wav")
    mp3_path = os.path.join(AUDIO_DIR, f"{slug}.mp3")


    if not post_id:
        print("Error: Could not find post ID in webhook payload")
        return {"status": "failed", "reason": "no_id"}, 400

    print(f"--- Processing: {title} ({post_id}) ---")

    # 2. Fetch full post content using the ID
    # Added formats=plaintext so the TTS has actual content to read
    filter_query = quote(f"id:{post_id}")
    url = f"{GHOST_URL}/ghost/api/content/posts/{post_id}/?key={CONTENT_API_KEY}&formats=plaintext"

    try:
        api_response = requests.get(url).json()
        posts = api_response.get("posts", [])

        if not posts:
            print(f"Ghost API returned no posts for ID: {post_id}")
            return {"status": "failed", "reason": "post_not_found"}, 404

        # 3. Get the actual text content (preferring plaintext over slug)
        # We fall back to the title if the post body is empty
        full_post = posts[0]
        text_to_read = full_post.get("plaintext") or full_post.get("title")

        # 4. Generate Audio
        
        tts.tts_to_file(text=text_to_read, file_path=wav_path)
        subprocess.run([
           "ffmpeg",
           "-y",
           "-i", wav_path,
           "-ar", "22050",      # sample rate
           "-ac", "1",          # mono channel
           "-b:a", "128k",      # audio bitrate
           mp3_path
         ], check=True)
        print(f"Success! Audio saved {mp3_path}")
        return {"status": "success", "file": mp3_path}

    except Exception as e:
        print(f"System Error: {str(e)}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    # Use threaded=True to prevent the UI from freezing during TTS generation
    app.run(port=5000, debug=False, threaded=True)

