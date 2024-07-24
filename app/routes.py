from flask import Blueprint, request, jsonify, redirect, session, url_for
import os
from openai import OpenAI
from flask_cors import CORS
import requests
import base64

bp = Blueprint('main', __name__)
CORS(bp)  # Enable CORS for the blueprint

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Spotify credentials (replace with your client ID and client secret)
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# Hardcoded Spotify access token (replace with actual token)
SPOTIFY_ACCESS_TOKEN = os.getenv('SPOTIFY_ACCESS_TOKEN')

@bp.route('/recommendations', methods=['POST'])
def get_recommendation():
    print("call received")
    data = request.json
    # Print the user text received from frontend
    user_text = data['description']
    print("User Text:", user_text)
    
    # Placeholder response for all requests
    song_recommendation = "'Happy' by Pharrell Williams."
    
    # Commented out OpenAI logic
    # Create the input message for OpenAI
    # input_message = f"Please recommend one song based on the following description: {user_text}. Provide the recommendation in the format 'Song Title by Artist'."
    
    # Send request to OpenAI API
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": "You are a music recommendation assistant."},
    #         {"role": "user", "content": input_message}
    #     ],
    #     max_tokens=50
    # )
    
    # Extract song recommendation from response
    # song_recommendation = response.choices[0].message.content.strip()
    
    print("OpenAI Response:", song_recommendation)
    
    return jsonify({"message": "Received the text", "description": user_text, "recommendation": song_recommendation})

@bp.route('/spotify_link', methods=['POST'])
def get_spotify_link():
    data = request.json
    song_recommendation = data.get('recommendation')
    if not song_recommendation:
        return jsonify({"error": "No song recommendation found"}), 400

    # Search for the song on Spotify
    search_url = "https://api.spotify.com/v1/search"
    search_headers = {
        "Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}"
    }
    search_params = {
        "q": song_recommendation,
        "type": "track",
        "limit": 1
    }
    search_response = requests.get(search_url, headers=search_headers, params=search_params)

    if search_response.status_code == 401:
        # If unauthorized, redirect to login
        auth_url = url_for('main.login', _external=True)
        return jsonify({"redirect_url": auth_url})

    search_results = search_response.json()

    if 'tracks' not in search_results or not search_results['tracks']['items']:
        return jsonify({"error": "No tracks found on Spotify"}), 404

    track_id = search_results['tracks']['items'][0]['id']
    track_link = search_results['tracks']['items'][0]['external_urls']['spotify']
    
    return jsonify({"spotify_link": track_link})

@bp.route('/auth/login', methods=['GET'])
def login():
    auth_url = (
        "https://accounts.spotify.com/authorize"
        "?response_type=code"
        f"&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        "&scope=playlist-modify-public"
    )
    return redirect(auth_url)

@bp.route('/auth/callback', methods=['GET'])
def callback():
    code = request.args.get('code')
    token_url = "https://accounts.spotify.com/api/token"
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.urlsafe_b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI
    }

    response = requests.post(token_url, headers=headers, data=data)
    response_data = response.json()

    session['access_token'] = response_data['access_token']
    session['refresh_token'] = response_data['refresh_token']

    return jsonify({"message": "Authorization successful! You can now use Spotify API.", "access_token": response_data['access_token']})
