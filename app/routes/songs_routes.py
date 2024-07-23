# from flask import Blueprint, jsonify, request, abort, make_response
# from ..db import db
# from ..models.user import User
# from ..models.openai_response import OpenAIResponse
# from sqlalchemy import func, union, except_
# import openai
# from openai import OpenAI

# app/routes/songs_routes.py
# app/routes/songs_routes.py

from flask import Blueprint, request, jsonify, g
from ..db import db
from ..models.openai_response import OpenAIResponse
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

bp = Blueprint('songs', __name__)

# Load OpenAI API key from environment variable

@bp.route('/songs', methods=['GET'])
def get_songs():
    # Example route
    return jsonify({"message": "Songs route"})

@bp.route('/recommendations', methods=['POST'])
def get_recommendation():
    data = request.json
    session_id = g.session_id  # Use session ID from middleware

    # Create input message for OpenAI
    input_message = f"Please recommend one song based on the following description: {data['description']}. Provide the recommendation in the format 'Song Title by Artist'."

    try:
        # Send request to OpenAI API
        response = client.chat.completions.create(model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a music recommendation assistant."},
            {"role": "user", "content": input_message}
        ],
        max_tokens=150)

        # Extract song recommendation from response
        song_recommendation = response.choices[0].message.content.strip()

        # Comment out the database session part for testing
        # openai_response = OpenAIResponse(
        #     request_text=data['description'],
        #     response_text=song_recommendation,
        #     songs=[{"title": song_recommendation}],
        #     session_id=session_id
        # )
        # db.session.add(openai_response)
        # db.session.commit()

        return jsonify({'response': song_recommendation, 'songs': [{"title": song_recommendation}]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



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