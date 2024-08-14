Here's your updated README with the requested sections and additional details:

---

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

## Frontend Repository

The frontend for this application is available in a separate repository. You can find it [here](https://github.com/abecerrilsalas/MoodMelody_frontend/). Please follow the instructions in that repository to set up and run the frontend.

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
psql -U postgres - #To open the Postgres interactive terminal with a Postgres user named postgres
CREATE DATABASE mood_m;
CREATE DATABASE mood_m_test;
\q
```

### Set Up OpenAI and Spotify Developer Accounts

1. **Create an OpenAI Developer Account**:
   - Visit [OpenAI's website](https://platform.openai.com/signup) and sign up for an API key.
   - Once you have your API key, keep it handy for configuring your environment variables.

2. **Create a Spotify Developer Account**:
   - Go to [Spotify Developer](https://developer.spotify.com/dashboard/login) and log in or create an account.
   - Navigate to the "Dashboard" and click "Create an App".
   - Fill in the required details and click "Create".
   - After creating the app, you will receive a `Client ID` and `Client Secret`.
   - Set the Redirect URI to `http://localhost:5000/auth/callback` (or your deployed backend link).
   - Keep the `Client ID`, `Client Secret`, and `Redirect URI` handy for configuring your environment variables.

### Configure Environment Variables

1. **Create a `.env` file** in the root directory with the following content. Be sure to replace the placeholders with your actual credentials:

```plaintext
SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost/mood_m
SQLALCHEMY_TEST_DATABASE_URI=postgresql://user:password@localhost/mood_m_test
OPENAI_API_KEY="your_openai_api_key"
SPOTIFY_CLIENT_ID="your_spotify_client_id"
SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
SPOTIFY_REDIRECT_URI="http://localhost:5000/auth/callback"  # Or your deployed link
REACT_APP_URL="http://localhost:3000"  # Or your deployed frontend link
FLASK_SECRET_KEY="temporary_secret_key_for_dev"
```

**Important**: Make sure to replace the values like `"your_openai_api_key"`, `"your_spotify_client_id"`, and others with your actual credentials and do not use the values provided above.

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

The application should now be running at `http://127.0.0.1:5000/` or `http://localhost:5000/`.


## Checking the Application with Postman

Since the `/recommend` endpoint requires Spotify authorization, testing it directly with Postman may not be straightforward. Instead, you can test the core functionality of the AI-based recommendation system using the `/check_openai` endpoint.

### Testing the AI Recommendation with Postman

1. **Open Postman**.

2. **Create a new POST request**:

- **URL**: `http://127.0.0.1:5000/check_openai` or `http://localhost:5000/check_openai`
- **Headers**: Set `Content-Type` to `application/json`.
- **Body**: Set to JSON and include a `description` field, for example:

```json
{
  "description": "upbeat pop song with a happy vibe"
}
```

3. **Send the request** and you should receive a JSON response with a song recommendation.

This endpoint will directly utilize OpenAI's GPT-4o-mini model to generate a playlist recommendation based on the provided description. It does not require Spotify authorization and is ideal for testing the core recommendation logic.

### Understanding the `/recommend` Endpoint

The `/recommend` endpoint is where the full functionality of MoodMelody comes into play. Here’s how it works:

1. **Authorization**: When you use the frontend, the app will redirect you to Spotify to authorize your account. Once authorized, Spotify will redirect you back to the MoodMelody app with a session ID.

2. **Making a Recommendation Request**: The frontend will send a request to the `/recommend` endpoint with your mood description and session ID. The backend will use the session ID to create a playlist on Spotify with the recommended songs.

3. **Playlist Creation**: The backend interacts with Spotify's API to create a playlist based on the recommendations generated by OpenAI. The playlist is then returned to the frontend, where you can view and listen to it.

### Why Testing `/recommend` in Postman is Challenging

The `/recommend` endpoint requires that the user is authenticated with Spotify, which involves a redirect-based OAuth flow that isn't easily replicable in Postman. The authentication ensures that the backend can create and manage playlists on behalf of the user. 

### Testing the Full Workflow

To test the full workflow, including Spotify authorization, it's recommended to use the frontend application. The frontend will handle the OAuth flow and make the necessary requests to the `/recommend` endpoint. After authorization, you can generate playlists and see the recommendations in action.

If you want to verify that the backend and frontend are properly communicating, simply run the frontend application and follow the steps to authorize your Spotify account and generate a playlist.


## Troubleshooting

If you encounter issues during setup, consider the following steps:

1. **Check Environment Variables**: Ensure that all environment variables are correctly configured and that you are using your actual credentials.
2. **Database Issues**: If you encounter database connection problems, verify that PostgreSQL is running and that the credentials in your `.env` file are correct.
3. **API Keys**: Ensure that your OpenAI API key and Spotify API credentials are active and correctly entered in your `.env` file.

## License

This project is licensed under the MIT License.