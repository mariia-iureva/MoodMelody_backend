# Flask configuration
FLASK_SECRET_KEY=your_secret_key_here

# Database configuration
SQLALCHEMY_DATABASE_URI=postgresql://mood_user:password@localhost:5432/mood_m
SQLALCHEMY_TEST_DATABASE_URI=postgresql://mood_user:password@localhost:5432/mood_m_test

# OpenAI configuration
OPENAI_API_KEY=your_openai_api_key_here

# Spotify configuration
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:5000/auth/callback
SPOTIFY_ACCESS_TOKEN="for hardcoded token only"