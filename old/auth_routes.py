from flask import Blueprint, redirect, request, session, jsonify
import os
import requests
import base64
import uuid
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    auth_url = get_spotify_authorization()
    return redirect(auth_url)

@auth_bp.route('/callback')
def callback():
    auth_code = request.args.get('code')
    if not auth_code:
        return jsonify({"error": "missing_authorization_code", "error_description": "Authorization code not found in request"}), 400

    token_info = get_spotify_token(auth_code)
    print("Token Info:", token_info)
    if 'access_token' in token_info:
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']

        print(f"Got the auth token {session['access_token']}")
        print("Session after storing access token:", dict(session))
        return jsonify({"message": "Authorization successful! You can now use Spotify API."})
    else:
        return jsonify(token_info), 400

def get_spotify_authorization():
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    scopes = 'playlist-modify-public playlist-modify-private'

    auth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?response_type=code&client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}"
    )
    return auth_url

def get_spotify_token(auth_code):
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.post(token_url, data=payload, headers=headers)
    return response.json()
