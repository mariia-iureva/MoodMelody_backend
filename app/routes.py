from flask import Blueprint, request, jsonify, redirect, session, url_for, make_response, current_app
import os
from openai import OpenAI
from flask_cors import CORS
import requests
import base64
from app.models.user import User
from app.models.search_history import SearchHistory
from .db import db
import uuid
import logging
import ast
import re
import json
from datetime import datetime
import sys



# Use the environment variable to set the React app URL
REACT_APP_URL = os.getenv("REACT_APP_URL")

# Retries attempts for OpenAI to respond with correctly formatted response if we fail to parse it.
MAX_RETRIES = 2

# Set up logging
# Create a directory for logs if it doesn't exist
log_directory = "logging"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Configure logging
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(log_directory, log_filename)),
        logging.StreamHandler(sys.stdout)  # If you also want to output to the console
    ]
)

logger = logging.getLogger()

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
SPOTIFY_ACCESS_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN")

# Helper functions

def get_session_id():
    print("I'm in session id")
    session_id = str(uuid.uuid4())
    return session_id


def store_tokens_in_db(session_id, token_info, spotify_user_id):
    access_token = token_info["access_token"]
    refresh_token = token_info["refresh_token"]
    user = User(
        session_id=session_id, access_token=access_token, refresh_token=refresh_token, spotify_user_id=spotify_user_id
    )
    db.session.add(user)
    db.session.commit()
    print(f"Successfully stored session ID {session_id} and token info")


def retrieve_user_info_from_db(session_id):
    user = User.query.filter_by(session_id=session_id).first()
    if user:
        return {
            "access_token": user.access_token,
            "refresh_token": user.refresh_token,
            "spotify_user_id": user.spotify_user_id,
        }
    return None

def save_search_history(spotify_user_id, search_query, spotify_link):
    """
    Save a search history entry to the database.
    
    :param spotify_user_id: Spotify user ID
    :param search_query: The search query or playlist name
    :param spotify_link: The Spotify playlist link
    """
    search_history_entry = SearchHistory(
        spotify_user_id=spotify_user_id,
        search_query=search_query,
        spotify_link=spotify_link
    )
    db.session.add(search_history_entry)
    db.session.commit()

def format_openai_response(response_string):
    """
    Formats the OpenAI response string to ensure it is a valid dictionary format.
    """
    try:
        # First, try to parse the entire string as JSON
        try:
            return json.loads(response_string)
        except json.JSONDecodeError:
            pass

        # If that fails, try to extract JSON-like content
        match = re.search(r'\{.*\}', response_string, re.DOTALL)
        if match:
            json_string = match.group(0)
            print("JSON String:", json_string)

            # Count occurrences of opening and closing braces and brackets
            open_braces = json_string.count('{')
            close_braces = json_string.count('}')
            open_brackets = json_string.count('[')
            close_brackets = json_string.count(']')

            print("Closing Braces:", close_braces)
            print("Closing Brackets:", close_brackets)

            # Add missing closing braces and brackets
            if open_braces > close_braces:
                json_string += '}' * (open_braces - close_braces)
            if open_brackets > close_brackets:
                json_string += ']' * (open_brackets - close_brackets)
            print("JSON String with Closing Braces:", json_string)

            try:
                return json.loads(json_string)
            except json.JSONDecodeError:
                return ast.literal_eval(json_string)

        # If all else fails, return the original string
        logger.warning("Could not parse as JSON or dict, returning original string")
        return response_string

    except Exception as e:
        logger.error("Failed to format OpenAI response: %s", response_string)
        logger.error("Error details: %s", str(e))
        raise ValueError("Could not parse the OpenAI response.")
    
def openai_recommendation(user_text):
    retries = 0
    while retries <= MAX_RETRIES:
        try: 
            logger.info(f"Attempt {retries + 1}: Asking OpenAI to recommend some songs")

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
            logger.warning(f"Attempt {retries + 1} failed: ValueError: %s", str(e))
            retries += 1
            if retries > MAX_RETRIES:
                logger.error("Max retries reached. Unable to parse the recommendation.")
                return jsonify({"error": "Unable to parse the recommendation after multiple attempts. Please try again later."}), 500

        except Exception as e:
            logger.error(f"Attempt {retries + 1} failed: Unexpected error: %s", str(e))
            return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

    # This line should never be reached due to the return statements in the loop,
    # but it's here for completeness
    return jsonify({"error": "Unable to generate a recommendation. Please try again later."}), 500


def get_spotify_user_id(access_token):
    try:
        user_profile_url = "https://api.spotify.com/v1/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(user_profile_url, headers=headers)
        
        # Log and print the response status code and text for debugging
        logger.info("User profile request response status: %s", response.status_code)
        logger.info("User profile request response text: %s", response.text)

        if response.status_code != 200:
            logger.error("Failed to fetch user profile: %s", response.text)
            raise ValueError("Could not retrieve user profile from Spotify.")

        user_profile = response.json()
        return user_profile["id"]
    
    except requests.exceptions.RequestException as e:
        logger.error("RequestException in get_spotify_user_id: %s", str(e))
        raise ValueError("Request to Spotify failed.")
    
    except KeyError as e:
        logger.error("KeyError in get_spotify_user_id: %s", str(e))
        raise ValueError("User ID not found in Spotify response.")
    
    except json.JSONDecodeError as e:
        logger.error("JSONDecodeError in get_spotify_user_id: %s", str(e))
        raise ValueError("Invalid JSON received from Spotify.")


def spotify_playlist(recommendation_dict, session_id):
    # Uncomment the following line to use a hardcoded token for testing
    # access_token = SPOTIFY_ACCESS_TOKEN

    token_info = retrieve_user_info_from_db(session_id)
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

    spotify_link_result = f"https://open.spotify.com/playlist/{playlist_id}"

    return user_id, spotify_link_result


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

    token_info = retrieve_user_info_from_db(session_id)
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

    # Create Spotify playlist and get user ID
    user_id, spotify_link = spotify_playlist(recommendation_dict, session_id)
    print("Spotify Link:", spotify_link)

    # Extract playlist ID from spotify_link
    playlist_id = spotify_link.split('/')[-1]

    # Save the search history using the helper function
    if spotify_link and not isinstance(spotify_link, dict):  # Ensure spotify_link is not an error dictionary
        save_search_history(user_id, user_text, spotify_link)

    return jsonify(
        {
            "authorized": True,
            "recommendation": recommendation_dict["Songs"],
            "spotify_link": spotify_link,
            "playlist_id": playlist_id,
            "user_id": user_id
        }
    )


@bp.route("/auth/login", methods=["GET"])
def login():
    scope = [
        "playlist-modify-public",
        "playlist-modify-private",
        "user-read-private",
        "user-read-email"
    ]
    
    query_parameters = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": " ".join(scope),
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        # "show_dialog": "true"  # Forces the user to approve the app again
    }
    
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode(query_parameters)
    return redirect(auth_url)


@bp.route("/auth/callback", methods=["GET"])
def callback():
    try:
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
        
        # Log and print the response status code and text for debugging
        logger.info("Token request response status: %s", response.status_code)
        logger.info("Token request response text: %s", response.text)

        # Check for a successful response
        if response.status_code != 200:
            logger.error("Failed to get token: %s", response.text)
            return jsonify({"error": "Failed to obtain access token from Spotify."}), 400

        response_data = response.json()

        session_id = request.cookies.get("session_id")
        logger.info("Session ID from Cookie: %s", session_id)
        if not session_id:
            session_id = get_session_id()
        logger.info("Final Session ID: %s", session_id)

        token_info = {
            "access_token": response_data["access_token"],
            "refresh_token": response_data["refresh_token"],
        }

        # Get the Spotify user ID
        spotify_user_id = get_spotify_user_id(token_info["access_token"])
        store_tokens_in_db(session_id, token_info, spotify_user_id)

        # Redirect back to React app with session ID in URL
        logger.info("Access Token: %s", response_data["access_token"])
        logger.info("Authorization successful! You can now use Spotify API.")

        react_app_url = f"{REACT_APP_URL}/home?session_id={session_id}"
        return redirect(react_app_url)

    except requests.exceptions.RequestException as e:
        logger.error("RequestException: %s", str(e))
        return jsonify({"error": "Request to Spotify failed. Please try again later."}), 500

    except KeyError as e:
        logger.error("KeyError: Missing expected data in response. Details: %s", str(e))
        return jsonify({"error": "Unexpected response format from Spotify."}), 500

    except json.JSONDecodeError as e:
        logger.error("JSONDecodeError: Failed to parse JSON. Details: %s", str(e))
        return jsonify({"error": "Received invalid JSON response from Spotify."}), 500

    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return jsonify({"error": "An unexpected error occurred during authentication."}), 500

@bp.route("/history", methods=["GET"])
def get_history():
    session_id = request.args.get("session_id")
    if not session_id:
        session_id = request.cookies.get("session_id")

    if not session_id:
        return jsonify({"error": "No session ID found."}), 401

    user_info = retrieve_user_info_from_db(session_id)
    if not user_info:
        return jsonify({"error": "User not authorized."}), 401

    user_id = user_info["spotify_user_id"]
    history = (
        SearchHistory.query.filter_by(spotify_user_id=user_id)
        .order_by(SearchHistory.timestamp.desc())
        .limit(10)  # Fetch the latest 10 records
        .all()
    )

    return jsonify([{
        "description": entry.search_query,
        "spotifyLink": entry.spotify_link,
        "timestamp": entry.timestamp.isoformat()
    } for entry in history])
    # return jsonify([{
    #     "description": entry.search_query,
    #     "spotifyLink": entry.spotify_link,
    #     "timestamp": entry.timestamp.isoformat(),
    #     "playlistId": entry.spotify_link.split('/')[-1]
    # } for entry in history])


@bp.route("/playlist/<playlist_id>/tracks", methods=["GET"])
def get_playlist_tracks(playlist_id):
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "No session ID found."}), 401

    token_info = retrieve_user_info_from_db(session_id)
    if not token_info:
        return jsonify({"error": "User not authorized."}), 401

    access_token = token_info["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    playlist_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    response = requests.get(playlist_tracks_url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch playlist tracks."}), response.status_code

    tracks_data = response.json()
    simplified_tracks = [
        {
            "id": item["track"]["id"],
            "name": item["track"]["name"],
            "artist": item["track"]["artists"][0]["name"],
            "album": item["track"]["album"]["name"],
            "duration_ms": item["track"]["duration_ms"],
            "preview_url": item["track"]["preview_url"]
        }
        for item in tracks_data["items"]
    ]

    return jsonify({"items": simplified_tracks})


@bp.route("/get_access_token", methods=["GET"])
def get_access_token():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "No session ID found."}), 401

    token_info = retrieve_user_info_from_db(session_id)
    if not token_info:
        return jsonify({"error": "User not authorized."}), 401

    return jsonify({"access_token": token_info["access_token"]})