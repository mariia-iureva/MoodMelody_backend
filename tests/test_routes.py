import json
import pytest
from app.routes import openai_recommendation
from app.routes import store_tokens_in_db, spotify_playlist,format_openai_response

# from app.routes import store_tokens_in_db, retrieve_tokens_from_db, spotify_playlist
from app.models import User, SearchHistory
from app import db
from unittest.mock import patch, MagicMock
from flask import jsonify
import ast

@pytest.fixture(autouse=True)
def clear_db():
    yield
    db.session.query(SearchHistory).delete()
    db.session.query(User).delete()
    db.session.commit()


def test_check_openai_route(client, mock_openai):
    response = client.post(
        "/check_openai",
        data=json.dumps({"description": "happy summer vibes"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "recommendation" in data
    assert "Playlist name" in data["recommendation"]
    assert "Songs" in data["recommendation"]
    assert len(data["recommendation"]["Songs"]) == 3
    assert data["recommendation"]["Playlist name"].startswith("MM")


def test_spotify_playlist(client, mock_spotify, mock_spotify_user_id):
    # Store mock tokens and user ID in the database
    session_id = "mock_session_id"
    token_info = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
    }
    store_tokens_in_db(session_id, token_info, mock_spotify_user_id)

    # Define the recommendation dictionary
    recommendation_dict = {
        "Playlist name": "Test Playlist",
        "Songs": ["Song1 by Artist1", "Song2 by Artist2", "Song3 by Artist3"],
    }

    # Perform the spotify_playlist function call
    user_id, spotify_link = spotify_playlist(recommendation_dict, session_id)

    # Check the result
    assert spotify_link == "https://open.spotify.com/playlist/mock_playlist_id"
    assert user_id == mock_spotify_user_id

def test_spotify_playlist_no_tracks_found(client, mock_spotify, mock_spotify_user_id):
    # Mock the requests.get to return no tracks
    def mock_requests_get_no_tracks(url, headers):
        class MockResponse:
            def json(self):
                return {"tracks": {"items": []}}

        return MockResponse()

    with patch("requests.get", mock_requests_get_no_tracks):
        session_id = "mock_session_id"
        token_info = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
        }
        store_tokens_in_db(session_id, token_info, mock_spotify_user_id)

        recommendation_dict = {
            "Playlist name": "Test Playlist",
            "Songs": ["Nonexistent Song by No Artist"],
        }
        print(f"!!!!!!!!!!! {spotify_playlist(recommendation_dict, session_id)}")

        result = spotify_playlist(recommendation_dict, session_id)
        assert result == {"error": "No tracks found."}

def test_spotify_playlist_creation_failed(client, mock_spotify, mock_spotify_user_id):

    # Mock the requests.post to return failure for playlist creation
    def mock_requests_post_fail_playlist(url, json, headers):
        class MockResponse:
            def json(self):
                return {}

        return MockResponse()

    with patch("requests.post", mock_requests_post_fail_playlist):
        session_id = "mock_session_id"
        token_info = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
        }
        store_tokens_in_db(session_id, token_info, mock_spotify_user_id)

        recommendation_dict = {
            "Playlist name": "Test Playlist",
            "Songs": ["Song1 by Artist1", "Song2 by Artist2", "Song3 by Artist3"],
        }

        result = spotify_playlist(recommendation_dict, session_id)
        assert result == {"error": "Failed to create playlist."}

# Test successful authentication
def test_callback_success(client, mock_spotify_user_id):
    # Mock the requests.post to simulate Spotify's token response
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def json(self):
                return {
                    "access_token": "mock_access_token",
                    "refresh_token": "mock_refresh_token",
                }

        return MockResponse()

    with patch("requests.post", mock_requests_post):
        with patch("app.routes.get_session_id", return_value="new_session_id"):
            # Patch get_spotify_user_id to return mock_spotify_user_id
            with patch("app.routes.get_spotify_user_id", return_value=mock_spotify_user_id):
                # Setting the cookie in the client's cookie jar
                client.set_cookie(key="session_id", value="mock_session_id")

                response = client.get("/auth/callback?code=mock_code")
                assert response.status_code == 302
                assert (
                    response.location == "http://localhost:3000/home?session_id=mock_session_id"
                )

                # Verify that tokens and user_id are stored in the database
                token_info = User.query.filter_by(session_id="mock_session_id").first()
                assert token_info is not None
                assert token_info.access_token == "mock_access_token"
                assert token_info.refresh_token == "mock_refresh_token"
                assert token_info.spotify_user_id == mock_spotify_user_id


# Test callback with missing session ID
def test_callback_no_session_id(client, mock_spotify_user_id):
    # Mock the requests.post to simulate Spotify's token response
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def json(self):
                return {
                    "access_token": "mock_access_token",
                    "refresh_token": "mock_refresh_token",
                }

        return MockResponse()

    with patch("requests.post", mock_requests_post):
        with patch("app.routes.get_spotify_user_id", return_value=mock_spotify_user_id):
            # Ensure no cookie is set to simulate missing session ID
            client.delete_cookie("session_id")

            response = client.get("/auth/callback?code=mock_code")
            assert response.status_code == 302

            # Extract the new session_id from the redirection URL
            new_session_id = response.location.split("session_id=")[-1]
            assert new_session_id != ""
            assert response.location == f"http://localhost:3000/home?session_id={new_session_id}"

            # Verify that tokens and user_id are stored in the database
            token_info = User.query.filter_by(session_id=new_session_id).first()
            assert token_info is not None
            assert token_info.access_token == "mock_access_token"
            assert token_info.refresh_token == "mock_refresh_token"
            assert token_info.spotify_user_id == mock_spotify_user_id



# Mock OpenAI Recommendation
def mock_openai_recommendation(user_text):
    return {
        "Playlist name": "MMTest Playlist",
        "Songs": ["Song1 by Artist1", "Song2 by Artist2", "Song3 by Artist3"],
    }


# Mock Spotify Playlist Creation
def mock_spotify_playlist(recommendation_dict, session_id):
    return "https://open.spotify.com/playlist/mock_playlist_id"


# Mock Token Retrieval
def mock_retrieve_tokens_from_db(session_id):
    if session_id == "mock_session_id":
        return {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
        }
    return None


def test_recommend_no_session_id(client):
    response = client.post("/recommend", json={"description": "happy songs"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["authorized"] == False
    assert "No session ID found" in data["message"]
    assert "auth_url" in data


def test_recommend_user_not_authorized(client):
    with patch(
        "app.routes.retrieve_tokens_from_db", side_effect=mock_retrieve_tokens_from_db
    ):
        response = client.post(
            "/recommend?session_id=invalid_session_id",
            json={"description": "happy songs"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["authorized"] == False
        assert "User not authorized" in data["message"]
        assert "auth_url" in data



def test_recommend_success(client, mock_spotify, mock_spotify_user_id):
    def mock_retrieve_tokens_from_db(session_id):
        return {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "spotify_user_id": mock_spotify_user_id
        }

    def mock_openai_recommendation(user_text):
        return {
            "Playlist name": "Mock Playlist",
            "Songs": [
                "Song1 by Artist1",
                "Song2 by Artist2",
                "Song3 by Artist3",
            ]
        }

    # Create a mock user in the database
    mock_user = User(
        session_id="mock_session_id",
        access_token="mock_access_token",
        refresh_token="mock_refresh_token",
        spotify_user_id=mock_spotify_user_id
    )
    db.session.add(mock_user)
    db.session.commit()

    with patch(
        "app.routes.retrieve_tokens_from_db", side_effect=mock_retrieve_tokens_from_db
    ):
        with patch(
            "app.routes.openai_recommendation", side_effect=mock_openai_recommendation
        ):
            client.set_cookie(key="session_id", value="mock_session_id")
            response = client.post(
                "/recommend", json={"description": "happy songs"}
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["authorized"] == True
            assert "recommendation" in data
            assert "spotify_link" in data
            assert "user_id" in data
            assert data["recommendation"] == [
                "Song1 by Artist1",
                "Song2 by Artist2",
                "Song3 by Artist3",
            ]
            assert data["spotify_link"] == f"https://open.spotify.com/playlist/mock_playlist_id"
            assert data["user_id"] == mock_spotify_user_id

def test_format_openai_response_json():
    # Test a properly formatted JSON string
    json_string = '{"Playlist name": "MMSpring Vibes", "Songs": ["Here Comes the Sun by The Beatles", "Bloom by The Paper Kites", "Budapest by George Ezra"]}'
    result = format_openai_response(json_string)
    expected = {
        "Playlist name": "MMSpring Vibes",
        "Songs": [
            "Here Comes the Sun by The Beatles",
            "Bloom by The Paper Kites",
            "Budapest by George Ezra",
        ],
    }
    assert result == expected

def test_format_openai_response_fallback_to_string():
    # Test a string that cannot be parsed as JSON or a dictionary
    invalid_string = "Invalid response string"
    result = format_openai_response(invalid_string)
    assert result == invalid_string

def test_format_openai_response_incomplete_json():
    # Test an incomplete JSON-like string
    incomplete_json_string = '{"Playlist name": "MMSpring Vibes", "Songs": ["Here Comes the Sun by The Beatles", "Bloom by The Paper Kites", "Budapest by George Ezra"]'
    result = format_openai_response(incomplete_json_string)
    expected = {
        "Playlist name": "MMSpring Vibes",
        "Songs": [
            "Here Comes the Sun by The Beatles",
            "Bloom by The Paper Kites",
            "Budapest by George Ezra",
        ],
    }
    assert result == expected


def test_format_openai_response_raises_value_error():
    # Test a string that raises an exception
    invalid_dict_string = '{"Playlist name": "MMSpring Vibes", "Songs": [Here Comes the Sun by The Beatles", "Bloom by The Paper Kites", "Budapest by George Ezra"]}'
    with pytest.raises(ValueError):
        format_openai_response(invalid_dict_string)

def test_format_openai_response_dict():
    # Test a string that can be parsed as a dictionary
    dict_string = "{'Playlist name': 'MMSpring Vibes', 'Songs': ['Here Comes the Sun by The Beatles', 'Bloom by The Paper Kites', 'Budapest by George Ezra']}"
    result = format_openai_response(dict_string)
    expected = {
        "Playlist name": "MMSpring Vibes",
        "Songs": [
            "Here Comes the Sun by The Beatles",
            "Bloom by The Paper Kites",
            "Budapest by George Ezra",
        ],
    }
    assert result == expected