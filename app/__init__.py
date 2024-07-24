import os
from flask import Flask
from flask_cors import CORS
import redis
from .routes import bp as main_bp
from .db import db, migrate
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Ensure FLASK_SECRET_KEY is set in the .env file
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    if not app.secret_key:
        raise ValueError("No secret key set for Flask application. Please set FLASK_SECRET_KEY in the .env file.")

    # Configure session
    # redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    # app.config['SESSION_TYPE'] = 'redis'
    # app.config['SESSION_PERMANENT'] = False
    # app.config['SESSION_USE_SIGNER'] = True  # To sign the session cookies
    # app.config['SESSION_REDIS'] = redis.from_url(redis_url)
    # # Session(app)

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
    openai.api_key = os.getenv('OPENAI_API_KEY')

    # Register blueprints
    app.register_blueprint(main_bp)

    return app
