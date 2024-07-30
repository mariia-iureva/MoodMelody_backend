import os
from flask import Flask
from flask_cors import CORS
from .routes import bp as main_bp
from .db import db, migrate
import openai
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

# Load environment variables from .env file
load_dotenv()
# db = SQLAlchemy()
# migrate = Migrate()

def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Ensure FLASK_SECRET_KEY is set in the .env file
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    if not app.secret_key:
        raise ValueError("No secret key set for Flask application. Please set FLASK_SECRET_KEY in the .env file.")

    if test_config:
        # Use the test configuration if provided
        app.config.update(test_config)
    else:
        # Use the DATABASE_URL from Heroku if it exists, otherwise fall back to local SQLALCHEMY_DATABASE_URI
        database_url = os.getenv('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url or os.getenv('SQLALCHEMY_DATABASE_URI')
        app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    
    # Set common configuration options
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the database and migration
    db.init_app(app)
    migrate.init_app(app, db)

    # Set OpenAI API key from environment variable or test config
    # app.config['OPENAI_API_KEY'] = test_config.get('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY')) if test_config else os.getenv('OPENAI_API_KEY')


    # Set OpenAI API key from environment variable
    # openai.api_key = os.getenv('OPENAI_API_KEY')

    # Register blueprints
    app.register_blueprint(main_bp)

    return app
