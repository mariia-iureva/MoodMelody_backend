import json
import pytest
from app.routes import openai_recommendation
from app.routes import store_tokens_in_db, spotify_playlist,format_openai_response, get_spotify_user_id
from app.routes import get_session_id, save_search_history, refresh_spotify_token, retrieve_user_info_from_db
from app.routes import openai_recommendation, MAX_RETRIES
from app.routes import retrieve_user_info_from_db

# from app.routes import store_tokens_in_db, retrieve_user_info_from_db, spotify_playlist
from app.models import User, SearchHistory
from app import db
from unittest.mock import patch, MagicMock
from flask import jsonify
import ast

from flask import json
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def clear_db():
    yield
    db.session.query(SearchHistory).delete()
    db.session.query(User).delete()
    db.session.commit()

def test_welcome_route(client):
    """Test the welcome route."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.data.decode('utf-8') == "Welcome to the Mood Melody Backend!"

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

def test_callback_success(client, mock_spotify_user_id, caplog):
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def json(self):
                return {
                    "access_token": "mock_access_token",
                    "refresh_token": "mock_refresh_token",
                }
            @property
            def text(self):
                return "Mock response text"
        return MockResponse()

    with patch("requests.post", mock_requests_post):
        with patch("app.routes.get_session_id", return_value="new_session_id"):
            with patch("app.routes.get_spotify_user_id", return_value=mock_spotify_user_id):
                client.set_cookie(key="session_id", value="mock_session_id")
                
                response = client.get("/auth/callback?code=mock_code")
                
                # Print response data for debugging
                print(f"Response Status Code: {response.status_code}")
                print(f"Response Data: {response.get_data(as_text=True)}")
                
                # Print logs
                print("Logs:")
                for record in caplog.records:
                    print(f"{record.levelname}: {record.getMessage()}")
                
                assert response.status_code == 302, f"Expected 302, got {response.status_code}"
                assert response.location == "http://localhost:3000/home?session_id=mock_session_id"
                
                token_info = User.query.filter_by(session_id="mock_session_id").first()
                assert token_info is not None
                assert token_info.access_token == "mock_access_token"
                assert token_info.refresh_token == "mock_refresh_token"
                assert token_info.spotify_user_id == mock_spotify_user_id

def test_callback_no_session_id(client, mock_spotify_user_id, caplog):
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def json(self):
                return {
                    "access_token": "mock_access_token",
                    "refresh_token": "mock_refresh_token",
                }
            @property
            def text(self):
                return "Mock response text"
        return MockResponse()

    with patch("requests.post", mock_requests_post):
        with patch("app.routes.get_spotify_user_id", return_value=mock_spotify_user_id):
            with patch("app.routes.get_session_id", return_value="new_session_id"):
                client.delete_cookie("session_id")
                
                response = client.get("/auth/callback?code=mock_code")
                
                # Print response data for debugging
                print(f"Response Status Code: {response.status_code}")
                print(f"Response Data: {response.get_data(as_text=True)}")
                
                # Print logs
                print("Logs:")
                for record in caplog.records:
                    print(f"{record.levelname}: {record.getMessage()}")
                
                assert response.status_code == 302, f"Expected 302, got {response.status_code}"
                
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

def test_callback_spotify_error(client):
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def __init__(self):
                self.status_code = 400
                self.text = "Error from Spotify"
        return MockResponse()

    with patch("requests.post", mock_requests_post):
        response = client.get("/auth/callback?code=mock_code")
        
        assert response.status_code == 400
        assert "Failed to obtain access token from Spotify" in response.get_json()["error"]

def test_callback_unexpected_error(client):
    with patch("requests.post", side_effect=Exception("Unexpected error")):
        response = client.get("/auth/callback?code=mock_code")
        
        assert response.status_code == 500
        assert "An unexpected error occurred during authentication" in response.get_json()["error"]

def test_get_spotify_user_id_success(mock_spotify_user_id):
    def mock_requests_get(url, headers):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                self.text = '{"id": "' + mock_spotify_user_id + '"}'
            def json(self):
                return {"id": mock_spotify_user_id}
        return MockResponse()

    with patch("requests.get", mock_requests_get):
        user_id = get_spotify_user_id("mock_access_token")
        assert user_id == mock_spotify_user_id

def test_get_spotify_user_id_error():
    def mock_requests_get(url, headers):
        class MockResponse:
            def __init__(self):
                self.status_code = 400
                self.text = "Error from Spotify"
        return MockResponse()

    with patch("requests.get", mock_requests_get):
        with pytest.raises(ValueError, match="Could not retrieve user profile from Spotify"):
            get_spotify_user_id("mock_access_token")

def test_get_spotify_user_id_error():
    def mock_requests_get(url, headers):
        class MockResponse:
            def __init__(self):
                self.status_code = 400
                self.text = "Error from Spotify"
        return MockResponse()

    with patch("requests.get", mock_requests_get):
        with pytest.raises(ValueError, match="Could not retrieve user profile from Spotify"):
            get_spotify_user_id("mock_access_token")

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
def mock_retrieve_user_info_from_db(session_id):
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
        "app.routes.retrieve_user_info_from_db", side_effect=mock_retrieve_user_info_from_db
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
    def mock_retrieve_user_info_from_db(session_id):
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
        "app.routes.retrieve_user_info_from_db", side_effect=mock_retrieve_user_info_from_db
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

# def test_format_openai_response_incomplete_json():
#     # Test an incomplete JSON-like string
#     incomplete_json_string = '{"Playlist name": "MMSpring Vibes", "Songs": ["Here Comes the Sun by The Beatles", "Bloom by The Paper Kites", "Budapest by George Ezra"]'
#     result = format_openai_response(incomplete_json_string)
#     expected = {
#         "Playlist name": "MMSpring Vibes",
#         "Songs": [
#             "Here Comes the Sun by The Beatles",
#             "Bloom by The Paper Kites",
#             "Budapest by George Ezra",
#         ],
#     }
#     assert result == expected


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

def test_get_session_id():
    session_id = get_session_id()
    assert isinstance(session_id, str)
    assert len(session_id) == 36  # UUID4 should be 36 characters long

def test_save_search_history(client, clear_db):
    # The client fixture provides the app context
    spotify_user_id = "test_user"
    search_query = "happy summer vibes"
    spotify_link = "https://open.spotify.com/playlist/123456"
    
    save_search_history(spotify_user_id, search_query, spotify_link)
    
    # Verify the entry was saved
    entry = SearchHistory.query.filter_by(spotify_user_id=spotify_user_id).first()
    assert entry is not None
    assert entry.search_query == search_query
    assert entry.spotify_link == spotify_link

@patch('requests.post')
def test_refresh_spotify_token_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_access_token"}
    mock_post.return_value = mock_response

    new_token = refresh_spotify_token("old_refresh_token")
    assert new_token == "new_access_token"

@patch('requests.post')
def test_refresh_spotify_token_failure(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Error refreshing token"
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="Failed to refresh access token from Spotify."):
        refresh_spotify_token("old_refresh_token")

def test_store_tokens_in_db(client, clear_db):
    session_id = "test_session"
    token_info = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token"
    }
    spotify_user_id = "test_user_id"
    
    store_tokens_in_db(session_id, token_info, spotify_user_id)
    
    # Verify the tokens were stored
    user = User.query.filter_by(session_id=session_id).first()
    assert user is not None
    assert user.access_token == "test_access_token"
    assert user.refresh_token == "test_refresh_token"
    assert user.spotify_user_id == "test_user_id"

def test_retrieve_user_info_from_db(client, clear_db):
    # First, store some test data
    session_id = "test_session"
    user = User(session_id=session_id, access_token="test_access", refresh_token="test_refresh", spotify_user_id="test_user")
    db.session.add(user)
    db.session.commit()
    
    # Now retrieve and check
    user_info = retrieve_user_info_from_db(session_id)
    assert user_info is not None
    assert user_info["access_token"] == "test_access"
    assert user_info["refresh_token"] == "test_refresh"
    assert user_info["spotify_user_id"] == "test_user"
    
    # Test with non-existent session
    assert retrieve_user_info_from_db("non_existent_session") is None

@patch('app.routes.requests.get')
def test_get_playlist_tracks(mock_get, client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "track": {
                    "id": "track1",
                    "name": "Song 1",
                    "artists": [{"name": "Artist 1"}],
                    "album": {"name": "Album 1"},
                    "duration_ms": 200000,
                    "preview_url": "http://example.com/preview1"
                }
            }
        ]
    }
    mock_get.return_value = mock_response

    # Mock the retrieve_user_info_from_db function
    with patch('app.routes.retrieve_user_info_from_db', return_value={"access_token": "test_token"}):
        response = client.get('/playlist/test_playlist_id/tracks?session_id=test_session')
        
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Song 1"
    assert data["items"][0]["artist"] == "Artist 1"

@patch('app.routes.retrieve_user_info_from_db')
def test_get_access_token(mock_retrieve, client):
    mock_retrieve.return_value = {"access_token": "test_access_token"}
    
    response = client.get('/get_access_token?session_id=test_session')
        
    assert response.status_code == 200
    assert response.get_json() == {"access_token": "test_access_token"}

@patch('app.routes.retrieve_user_info_from_db')
def test_get_access_token_no_session(mock_retrieve, client):
    mock_retrieve.return_value = None
    
    response = client.get('/get_access_token')
        
    assert response.status_code == 401
    assert "No session ID found" in response.get_json()["error"]

def test_get_history_success(client, clear_db):
    # Setup: Create a user and some search history
    user = User(session_id="test_session", spotify_user_id="test_user", access_token="test_token", refresh_token="test_refresh")
    db.session.add(user)
    
    # Add some search history entries
    for i in range(15):  # Add 15 entries to test the limit of 10
        history = SearchHistory(
            spotify_user_id="test_user",
            search_query=f"Test query {i}",
            spotify_link=f"https://open.spotify.com/playlist/test{i}"
        )
        db.session.add(history)
        # Simulate time passing between entries
        db.session.flush()
        history.timestamp = datetime.now() - timedelta(minutes=i)
    
    db.session.commit()

    # Test the route
    response = client.get('/history?session_id=test_session')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert len(data) == 10  # Should only return the latest 10 entries
    assert data[0]['description'] == "Test query 0"  # Most recent entry
    assert "spotifyLink" in data[0]
    assert "timestamp" in data[0]

def test_get_history_invalid_session_id(client):
    response = client.get('/history?session_id=invalid_session')
    assert response.status_code == 401
    assert json.loads(response.data)['error'] == "User not authorized."

def test_get_history_empty(client, clear_db):
    # Setup: Create a user but no search history
    user = User(session_id="test_session", spotify_user_id="test_user", access_token="test_token", refresh_token="test_refresh")
    db.session.add(user)
    db.session.commit()

    response = client.get('/history?session_id=test_session')
    assert response.status_code == 200
    assert json.loads(response.data) == []

from unittest.mock import patch

@patch('app.routes.retrieve_user_info_from_db')
def test_get_history_db_error(mock_retrieve, client):
    mock_retrieve.side_effect = Exception("Database error")
    
    response = client.get('/history?session_id=test_session')
    assert response.status_code == 500
    assert "error" in json.loads(response.data)