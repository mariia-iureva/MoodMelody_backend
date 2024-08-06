from flask import Blueprint, request, jsonify, redirect, session, url_for, make_response, current_app
import os
from openai import OpenAI
from flask_cors import CORS
import requests
import base64
from app.models.user import User
from .db import db
import uuid
import logging
import ast
import re
import json

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)
CORS(bp)  # Enable CORS for the blueprint

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_openai_client():
    return OpenAI(api_key=current_app.config["OPENAI_API_KEY"])


# Spotify credentials (replace with your client ID and client secret)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Hardcoded Spotify access token (replace with actual token)
SPOTIFY_ACCESS_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN")

# Helper functions

# def get_session_id():
#     print("I'm in session id")
#     session_id = str(uuid.uuid4())
#     # response = make_response(redirect(url_for('main.login', session_id=session_id)))
#     response.set_cookie('session_id', session_id)
#     return response


def get_session_id():
    print("I'm in session id")
    session_id = str(uuid.uuid4())
    # response = make_response(jsonify({"message": "Session ID created", "session_id": session_id}))
    # response.set_cookie('session_id', session_id)
    # return response
    return session_id


def store_tokens_in_db(session_id, token_info):
    access_token = token_info["access_token"]
    refresh_token = token_info["refresh_token"]
    user = User(
        session_id=session_id, access_token=access_token, refresh_token=refresh_token
    )
    db.session.add(user)
    db.session.commit()
    print(f"Successfully stored session ID {session_id} and token info")


def retrieve_tokens_from_db(session_id):
    user = User.query.filter_by(session_id=session_id).first()
    if user:
        return {"access_token": user.access_token, "refresh_token": user.refresh_token}
    return None

def format_openai_response(response_string):
    """
    Formats the OpenAI response string to ensure it is a valid dictionary format.
    """
    try:
        # Remove any unwanted characters or patterns
        # Example: Remove everything before the first '{' and after the last '}'
        response_string = re.search(r'\{.*\}', response_string).group(0)

        # Try to parse as JSON first (safer than ast.literal_eval)
        try:
            recommendation_dict = json.loads(response_string)
        except json.JSONDecodeError:
            # If JSON parsing fails, fall back to ast.literal_eval
            recommendation_dict = ast.literal_eval(response_string)

        # Convert to a dictionary using ast.literal_eval for safety
        return ast.literal_eval(response_string)
    except Exception as e:
        logger.error("Failed to format OpenAI response: %s", response_string)
        logger.error("Error details: %s", str(e))
        # Return a default dictionary or raise an error
        raise ValueError("Could not parse the OpenAI response.")

def openai_recommendation(user_text):
    try: 
        print("asking openAi to recommend some songs")
        # Placeholder response for all requests
        # song_recommendation = "'Happy' by Pharrell Williams."

        # Create the input message for OpenAI
        input_message = f"Please recommend 3 songs based on the description: {user_text}. Provide the recommendation strictly in the format of a dictionary with keys 'Playlist name' and 'Songs'. The value for 'playlist name' should be a short name based on the user description prefixed with 'MM', and the 'songs' should be an array of 3 song titles and artists in the format ['Song1 by Artist1', 'Song2 by Artist2', 'Song3 by Artist3']. No formatting is needed, don't forget the closing bracket for the array."

        client = get_openai_client()

        # Send request to OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music recommendation assistant."},
                {"role": "user", "content": input_message},
            ],
            max_tokens=50,
        )

        # Extract song recommendation from response
        song_recommendation = response.choices[0].message.content.strip()

        # Format and parse the response
        recommendation_dict = format_openai_response(song_recommendation)

        print("OpenAI Response:", recommendation_dict)

        return recommendation_dict

    except ValueError as e:
        logger.error("ValueError: %s", str(e))
        return jsonify({"error": "Unable to parse the recommendation. Please try again later."}), 500

    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500


def get_spotify_user_id(access_token):
    user_profile_url = "https://api.spotify.com/v1/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(user_profile_url, headers=headers)
    user_profile = response.json()
    return user_profile["id"]


def spotify_playlist(recommendation_dict, session_id):
    # Uncomment the following line to use a hardcoded token for testing
    # access_token = SPOTIFY_ACCESS_TOKEN

    token_info = retrieve_tokens_from_db(session_id)
    print("Token Info from Spotify Playlist:", token_info)
    if not token_info:
        return redirect(url_for("login", session_id=session_id))

    # Uncomment the following line to use the token from the database
    access_token = token_info["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    track_uris = []
    search_url = "https://api.spotify.com/v1/search"

    for recommendation in recommendation_dict["Songs"]:
        query = f"q={recommendation}&type=track&limit=1"
        search_response = requests.get(f"{search_url}?{query}", headers=headers)
        search_results = search_response.json()

        if "tracks" in search_results and search_results["tracks"]["items"]:
            track_uri = search_results["tracks"]["items"][0]["uri"]
            track_uris.append(track_uri)

    if not track_uris:
        return {"error": "No tracks found."}

    user_id = get_spotify_user_id(access_token)
    playlist_url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    playlist_name = recommendation_dict["Playlist name"]
    playlist_body = {
        "name": playlist_name,
        "description": "A playlist created by Mood Melody",
        "public": False,
    }
    playlist_response = requests.post(playlist_url, json=playlist_body, headers=headers)

    # Print the response from Spotify's API for debugging
    print("Playlist Response:", playlist_response.json())

    playlist_data = playlist_response.json()
    if "id" not in playlist_data:
        return {"error": "Failed to create playlist."}

    playlist_id = playlist_response.json()["id"]

    add_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    add_tracks_body = {"uris": track_uris}
    requests.post(add_tracks_url, json=add_tracks_body, headers=headers)

    return f"https://open.spotify.com/playlist/{playlist_id}"


@bp.route("/")
def welcome():
    return "Welcome to the Mood Melody Backend!"


@bp.route("/check_openai", methods=["POST"])
def check_openai():
    data = request.json
    user_text = data["description"]
    recommendation = openai_recommendation(user_text)
    return jsonify({"recommendation": recommendation})


@bp.route("/recommend", methods=["POST"])
def recommend():
    print("call received")
    session_id = request.args.get("session_id")
    if not session_id:
        session_id = request.cookies.get("session_id")
    if not session_id:
        # return get_session_id()
        print("there's no session id in the beginning of recommend")
        return jsonify(
            {
                "authorized": False,
                "message": "No session ID found, please log in to Spotify.",
                "auth_url": url_for("main.login", _external=True),
            }
        )

    token_info = retrieve_tokens_from_db(session_id)
    print("Token Info from recommend:", token_info)
    if not token_info:
        return jsonify(
            {
                "authorized": False,
                "message": "User not authorized, please log in to Spotify.",
                "auth_url": url_for(
                    "main.login", session_id=session_id, _external=True
                ),
            }
        )

    data = request.json
    user_text = data["description"]
    print("User Text:", user_text)

    # Get song recommendations and playlist name from OpenAI
    recommendation_dict = openai_recommendation(user_text)
    # recommendation_dict = {'Playlist name': 'MMHappiness', 'Songs': ['Happy by Pharrell Williams', 'Walking on Sunshine by Katrina and the Waves', 'Good Vibrations by The Beach Boys']}
    # Create Spotify playlist
    spotify_link = spotify_playlist(recommendation_dict, session_id)
    print("Spotify Link:", spotify_link)
    # spotify_link = "example.com"
    # return jsonify({
    #     "authorized": False
    # })

    return jsonify(
        {
            "authorized": True,
            "recommendation": recommendation_dict["Songs"],
            "spotify_link": spotify_link,
        }
    )


@bp.route("/auth/login", methods=["GET"])
def login():
    auth_url = (
        "https://accounts.spotify.com/authorize"
        "?response_type=code"
        f"&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        "&scope=playlist-modify-public playlist-modify-private"
    )
    return redirect(auth_url)


@bp.route("/auth/callback", methods=["GET"])
def callback():
    code = request.args.get("code")
    token_url = "https://accounts.spotify.com/api/token"
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.urlsafe_b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }

    response = requests.post(token_url, headers=headers, data=data)
    response_data = response.json()

    # session['access_token'] = response_data['access_token']
    # session['refresh_token'] = response_data['refresh_token']

    session_id = request.cookies.get("session_id")
    print("Session ID from Cookie:", session_id)
    if not session_id:
        session_id = get_session_id()
    print("Final Session ID:", session_id)
    token_info = {
        "access_token": response_data["access_token"],
        "refresh_token": response_data["refresh_token"],
    }
    store_tokens_in_db(session_id, token_info)

    # Redirect back to React app with session ID in URL

    print("Access Token:", response_data["access_token"])
    print("Authorization successful! You can now use Spotify API.")

    react_app_url = f"http://localhost:3000?session_id={session_id}"
    return redirect(react_app_url)
