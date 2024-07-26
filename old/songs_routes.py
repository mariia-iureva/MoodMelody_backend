# from flask import Blueprint, jsonify, request, abort, make_response
from ..db import db
# from ..models.user import User
# from ..models.openai_response import OpenAIResponse
# from sqlalchemy import func, union, except_
# import openai
# from openai import OpenAI

from flask import Blueprint, request, jsonify, session, redirect, url_for
import os
import requests
from openai import OpenAI
import openai

bp = Blueprint('songs', __name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def search_spotify_track(track_title, track_artist, access_token):
    search_url = "https://api.spotify.com/v1/search"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "q": f"track:{track_title} artist:{track_artist}",
        "type": "track",
        "limit": 1
    }

    response = requests.get(search_url, headers=headers, params=params)
    response_json = response.json()
    if response_json['tracks']['items']:
        return response_json['tracks']['items'][0]['external_urls']['spotify']
    return None

@bp.route('/recommendations', methods=['POST'])
def get_recommendation():
    session_id = session.get('session_id')
    print("Session ID:", session_id)
    if not session_id:
        print("Session ID is missing. Redirecting to login.")
        return redirect(url_for('auth.login'))  # Redirect to login if session ID is missing

    # Retrieve the token from the session
    access_token = session.get('access_token')
    if not access_token:
        print("Spotify access token is missing")
        return jsonify({"error": "Spotify access token is missing"}), 401

    data = request.json

    # Create input message for OpenAI
    input_message = f"Please recommend one song based on the following description: {data['description']}. Provide the recommendation in the format 'Song Title by Artist'."

    try:
        # Send request to OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a music recommendation assistant."},
                {"role": "user", "content": input_message}
            ],
            max_tokens=150
        )

        # Extract song recommendation from response
        song_recommendation = response.choices[0].message.content.strip()
        print("Song Recommendation from OpenAI:", song_recommendation)
        song_title, song_artist = song_recommendation.split(' by ')

        # Search for the track on Spotify
        track_link = search_spotify_track(song_title, song_artist, access_token)
        if not track_link:
            return jsonify({"error": "Song not found on Spotify"}), 404

        return jsonify({'response': song_recommendation, 'spotify_link': track_link})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@bp.route('/check_session', methods=['GET'])
def check_session():
    session_id = session.get('session_id')
    access_token = session.get('access_token')
    return jsonify({
        "session_id": session_id,
        "access_token": access_token
    })

# bp = Blueprint("characters", __name__, url_prefix="/characters")
# # openai.api_key = app.config['OPENAI_API_KEY']
# client = OpenAI()

# @bp.post("")    
# def create_character():

#     request_body = request.get_json()
#     try: 
#         new_character = Character.from_dict(request_body)
#         db.session.add(new_character)
#         db.session.commit()

#         return make_response(new_character.to_dict(), 201)

#     except KeyError as e:
#         abort(make_response({"message": f"missing required value: {e}"}, 400))

# @bp.get("")
# def get_characters():
#     character_query = db.select(Character)

#     characters = db.session.scalars(character_query)
#     response = []

#     for character in characters:
#         response.append(
#             {
#                 "id" : character.id,
#                 "name" : character.name,
#                 "personality" : character.personality,
#                 "occupation" : character.occupation,
#                 "age" : character.age
#             }
#         )

#     return jsonify(response)

# @bp.get("/<char_id>/greetings")
# def get_greetings(char_id):
#     pass

# @bp.post("/<char_id>/generate")
# def add_greetings(char_id):
#     pass
#     # this function will generate greetings for a character

# def generate_greetings(character):

#     input_message = f"I am writing a video game in the style of The Witcher. I have an npc named {character.name} who is {character.age} years old. They are a {character.occupation} who has a {character.personality} personality. Please generate a python style list of 10 stock phrases they might use when the main character talks to them"
#     completion = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "user", "content": input_message}
#         ]
#     )
#     return(completion.choices[0].message.content.split("\n"))

# def validate_model(cls,id):
#     try:
#         id = int(id)
#     except:
#         response =  response = {"message": f"{cls.__name__} {id} invalid"}
#         abort(make_response(response , 400))

#     query = db.select(cls).where(cls.id == id)
#     model = db.session.scalar(query)
#     if model:
#         return model

#     response = {"message": f"{cls.__name__} {id} not found"}
#     abort(make_response(response, 404))