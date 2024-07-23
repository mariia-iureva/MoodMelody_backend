# app/__init__.py

import os
from flask import Flask, request, g
from .routes.songs_routes import bp
from .db import db, migrate
from .models import User, OpenAIResponse  # Ensure models are imported
import openai
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)

    # Determine which database to use
    if test_config:
        db_to_use = os.environ.get("SQLALCHEMY_TEST_DATABASE_URI")
    else:
        db_to_use = os.environ.get("SQLALCHEMY_DATABASE_URI")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = db_to_use

    # Initialize the database and migration
    db.init_app(app)
    migrate.init_app(app, db)

    # Set OpenAI API key from environment variable

    # Middleware to generate session ID
    @app.before_request
    def ensure_session_id():
        session_id = request.headers.get('Session-Id')
        if not session_id:
            session_id = str(uuid.uuid4())
            g.session_id = session_id
            user = User(session_id=session_id)
            db.session.add(user)
            db.session.commit()
        else:
            g.session_id = session_id

    # Register the blueprint
    app.register_blueprint(bp)

    return app
