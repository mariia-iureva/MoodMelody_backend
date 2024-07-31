from flask import Blueprint, redirect, request, jsonify, session, url_for
import os
import requests
import base64
import uuid
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

bp = Blueprint("main", __name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def search_spotify_track(track_title, track_artist, access_token):
    search_url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": f"track:{track_title} artist:{track_artist}",
        "type": "track",
        "limit": 1,
    }

    response = requests.get(search_url, headers=headers, params=params)
    response_json = response.json()
    if response_json["tracks"]["items"]:
        return response_json["tracks"]["items"][0]["external_urls"]["spotify"]
    return None


@bp.route("/auth/login")
def login():
    auth_url = get_spotify_authorization()
    return redirect(auth_url)


@bp.route("/auth/callback")
def callback():
    auth_code = request.args.get("code")
    if not auth_code:
        return (
            jsonify(
                {
                    "error": "missing_authorization_code",
                    "error_description": "Authorization code not found in request",
                }
            ),
            400,
        )

    token_info = get_spotify_token(auth_code)
    print("Token Info:", token_info)
    if "access_token" in token_info:
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id

        session["access_token"] = token_info["access_token"]
        session["refresh_token"] = token_info["refresh_token"]

        print(f"Got the auth token {session['access_token']}")
        print("Session after storing access token:", dict(session))
        # Redirect back to the frontend with the access token
        return redirect(
            f"http://localhost:3000?access_token={token_info['access_token']}"
        )
    else:
        return jsonify(token_info), 400


def get_spotify_authorization():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    scopes = "playlist-modify-public playlist-modify-private"

    auth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?response_type=code&client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}"
    )
    return auth_url


def get_spotify_token(auth_code):
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

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


@bp.route("/recommendations", methods=["POST"])
def get_recommendation():
    print("call received")
    data = request.json
    # Print the user text received from frontend
    print("User Text:", data["description"])
    # token = request.headers.get('Authorization')
    # if not token:
    #     return jsonify({"error": "Authorization token is missing"}), 401

    # access_token = token.split(" ")[1]

    # Create input message for OpenAI
    input_message = f"Please recommend one song based on the following description: {data['description']}. Provide the recommendation in the format 'Song Title by Artist'."

    try:
        # Send request to OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a music recommendation assistant.",
                },
                {"role": "user", "content": input_message},
            ],
            max_tokens=150,
        )

        # Extract song recommendation from response
        song_recommendation = response.choices[0].message.content.strip()
        print("Song Recommendation from OpenAI:", song_recommendation)
        song_title, song_artist = song_recommendation.split(" by ")

        # Search for the track on Spotify
        track_link = search_spotify_track(song_title, song_artist, access_token)
        if not track_link:
            return jsonify({"error": "Song not found on Spotify"}), 404

        return jsonify({"response": song_recommendation, "spotify_link": track_link})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500


@bp.route("/check_session", methods=["GET"])
def check_session():
    session_id = session.get("session_id")
    access_token = session.get("access_token")
    print(
        "Check session endpoint called. Session ID:",
        session_id,
        "Access Token:",
        access_token,
    )
    return jsonify({"session_id": session_id, "access_token": access_token})
