
# MoodMelody - AI-Powered Music Recommendation App

MoodMelody is a Flask-based web application that uses OpenAI's GPT-4o-mini model to provide personalized music recommendations. The application also integrates with the Spotify API to create playlists based on the recommendations.

## Project Overview

MoodMelody allows users to receive song recommendations based on their mood or specific criteria. Users can then create a Spotify playlist with the recommended songs and listen to it immediately.

## Features

- AI-powered song recommendations using OpenAI's GPT-4o-mini model.
- Integration with Spotify API to create and manage playlists.
- Session management for tracking user interactions.

## Prerequisites

- Python 3.12 or higher
- PostgreSQL
- Git

## Setup Instructions

### Fork and Clone the Repository

1. **Fork the repository** on GitHub.
2. **Clone the repository** to your local machine.

```sh
git clone https://github.com/your-username/mood_melody_backend.git
cd mood_melody_backend
```

### Create and Activate Virtual Environment

1. **Create a virtual environment**:

```sh
python3 -m venv venv
```

2. **Activate the virtual environment**:

- On macOS and Linux:

```sh
source venv/bin/activate
```

- On Windows:

```sh
venv\Scripts\activate
```

### Install Dependencies

1. **Install the required packages**:

```sh
pip install -r requirements.txt
```

### Set Up the Database

1. **Install PostgreSQL** (if not already installed).

2. **Create the development and test databases**:

```sh
psql
CREATE DATABASE mood_melody_dev;
CREATE DATABASE mood_melody_test;
CREATE USER m_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE mood_melody_dev TO m_user;
GRANT ALL PRIVILEGES ON DATABASE mood_melody_test TO m_user;
\q
```

### Configure Environment Variables

1. **Create a `.env` file** in the root directory with the following content:

```plaintext
SQLALCHEMY_DATABASE_URI=postgresql://m_user:password@localhost/mood_melody_dev
SQLALCHEMY_TEST_DATABASE_URI=postgresql://m_user:password@localhost/mood_melody_test
OPENAI_API_KEY=your_openai_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=your_spotify_redirect_uri
```

### Apply Database Migrations

1. **Initialize and apply migrations**:

```sh
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Running the Application

1. **Run the Flask application**:

```sh
flask run
```

The application should now be running at `http://127.0.0.1:5000/`.

## Checking the Application with Postman

1. **Open Postman**.

2. **Create a new POST request**:

- **URL**: `http://127.0.0.1:5000/recommendations`
- **Headers**: Add a `Session-Id` header with a unique value (optional).
- **Body**: Set to JSON and include a `description` field, for example:

```json
{
  "description": "upbeat pop song with a happy vibe"
}
```

3. **Send the request** and you should receive a JSON response with a song recommendation.

## License

This project is licensed under the MIT License.
```