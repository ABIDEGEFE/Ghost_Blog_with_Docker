from flask import Flask, request, jsonify, redirect, make_response
from TTS.api import TTS
from urllib.parse import quote
import requests
import subprocess
import jwt
import time
import os

app = Flask(__name__)

# Load TTS model (Note: This may take a moment on startup)
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

GHOST_URL = "http://localhost:2368"
CONTENT_API_KEY = "4076763c15f0f6f4d648483771"

GHOST_ADMIN_API = "http://localhost:2368/ghost/api/admin"
ADMIN_API_KEY = "69b8fa07941dc23a009ebff0:18342f97c02a85dee2db4515e48826da2053a1adc27a1a332e9e72cb43542833"


def generate_ghost_token():
    key_id, secret = ADMIN_API_KEY.split(":")

    iat = int(time.time())
    exp = iat + 5 * 60  # 5 minutes

    payload = {
        "iat": iat,
        "exp": exp,
        "aud": "/admin/"
    }

    token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers={"kid": key_id})

    return token


def invite_user(email, role):
    token = generate_ghost_token()

    headers = {
        "Authorization": f"Ghost {token}",
        "Content-Type": "application/json"
    }

    role_map = {
        "admin": "Administrator",
        "editor": "Editor",
        "author": "Author"
    }

    ghost_role_name = role_map.get(role, "Author")
    print("this is current user role............***********####### ", ghost_role_name)
    role_id = get_role_id(ghost_role_name)

    if not role_id:
        print("Role not found:", ghost_role_name)
        return

    data = {
        "invites": [{
            "email": email,
            "role_id": role_id  
        }]
    }

    url = f"{GHOST_ADMIN_API}/invites/"
    res = requests.post(url, json=data, headers=headers)

    print("Invite response:", res.status_code, res.text)


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

def get_roles():
    token = generate_ghost_token()

    headers = {
        "Authorization": f"Ghost {token}"
    }

    url = f"{GHOST_ADMIN_API}/roles/"
    res = requests.get(url, headers=headers).json()

    roles = res.get("roles", [])

    for r in roles:
        print(r["name"], "→", r["id"])

    return roles

def get_role_id(role_name):
    roles = get_roles()

    for r in roles:
        if r["name"].lower() == role_name.lower():
            return r["id"]

    return None

@app.route("/sync-user", methods=["GET"])
def sync_user():
    email = request.headers.get("X-Auth-Request-Email")
    roles = request.headers.get("X-Auth-Request-Groups", "")
    print("req................ppp", request.headers)
    print("Email:", email)
    print("Raw Roles:", roles)

    # Convert roles string → list
    role_list = [r.strip() for r in roles.split(",")]

    # Filter only meaningful roles
    allowed_roles = ["admin", "editor", "author"]

    user_role = None
    for r in role_list:
        if r in allowed_roles:
            user_role = r
            break
    print("Filtered Role:", user_role)
   
    if email and user_role:
        invite_user(email, user_role)
    if user_role in allowed_roles:
        response = make_response(redirect("/ghost"))
    else:
        response = make_response(redirect("/"))
    response.set_cookie("synced", "true", max_age=300)  # 5 min

    return response


if __name__ == "__main__":
    # Use threaded=True to prevent the UI from freezing during TTS generation
    app.run(port=5000, debug=False, threaded=True)

