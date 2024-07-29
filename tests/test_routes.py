import json
import pytest
from app.routes import openai_recommendation
from app.routes import store_tokens_in_db, spotify_playlist
# from app.routes import store_tokens_in_db, retrieve_tokens_from_db, spotify_playlist
from app.models import User
from app import db
from unittest.mock import patch, MagicMock
from flask import jsonify

@pytest.fixture(autouse=True)
def clear_db():
    yield
    db.session.query(User).delete()
    db.session.commit()

def test_check_openai_route(client, mock_openai):
    response = client.post('/check_openai', 
        data=json.dumps({'description': 'happy summer vibes'}),
        content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'recommendation' in data
    assert 'Playlist name' in data['recommendation']
    assert 'Songs' in data['recommendation']
    assert len(data['recommendation']['Songs']) == 3
    assert data['recommendation']['Playlist name'].startswith('MM')

def test_spotify_playlist(client, mock_spotify):

    # Store mock tokens in the database
    session_id = 'mock_session_id'
    token_info = {
        'access_token': 'mock_access_token',
        'refresh_token': 'mock_refresh_token'
    }
    store_tokens_in_db(session_id, token_info)

    # Define the recommendation dictionary
    recommendation_dict = {
        'Playlist name': 'Test Playlist',
        'Songs': ['Song1 by Artist1', 'Song2 by Artist2', 'Song3 by Artist3']
    }

    # Perform the spotify_playlist function call
    result = spotify_playlist(recommendation_dict, session_id)

    # Check the result
    assert result == 'https://open.spotify.com/playlist/mock_playlist_id'

# Test case when no tracks are found
def test_spotify_playlist_no_tracks_found(client, mock_spotify):
    # Mock the requests.get to return no tracks
    def mock_requests_get_no_tracks(url, headers):
        class MockResponse:
            def json(self):
                return {'tracks': {'items': []}}
        return MockResponse()

    with patch('requests.get', mock_requests_get_no_tracks):
        session_id = 'mock_session_id'
        token_info = {
            'access_token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token'
        }
        store_tokens_in_db(session_id, token_info)

        recommendation_dict = {
            'Playlist name': 'Test Playlist',
            'Songs': ['Nonexistent Song by No Artist']
        }

        result = spotify_playlist(recommendation_dict, session_id)
        assert result == {"error": "No tracks found."}

# Test case when playlist creation fails
def test_spotify_playlist_creation_failed(client, mock_spotify):
    # Mock the requests.post to return failure for playlist creation
    def mock_requests_post_fail_playlist(url, json, headers):
        class MockResponse:
            def json(self):
                return {}
        return MockResponse()

    with patch('requests.post', mock_requests_post_fail_playlist):
        session_id = 'mock_session_id'
        token_info = {
            'access_token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token'
        }
        store_tokens_in_db(session_id, token_info)

        recommendation_dict = {
            'Playlist name': 'Test Playlist',
            'Songs': ['Song1 by Artist1', 'Song2 by Artist2', 'Song3 by Artist3']
        }

        result = spotify_playlist(recommendation_dict, session_id)
        assert result == {"error": "Failed to create playlist."}

# Test successful authentication
# Test successful authentication
def test_callback_success(client):
    # Mock the requests.post to simulate Spotify's response
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def json(self):
                return {
                    'access_token': 'mock_access_token',
                    'refresh_token': 'mock_refresh_token'
                }
        return MockResponse()

    with patch('requests.post', mock_requests_post):
        with patch('app.routes.get_session_id', return_value='new_session_id'):
            # Setting the cookie in the client's cookie jar
            client.set_cookie(key='session_id', value='mock_session_id')
            
            response = client.get('/auth/callback?code=mock_code')
            assert response.status_code == 302
            assert response.location == 'http://localhost:3000?session_id=mock_session_id'
            
            # Verify that tokens are stored in the database
            token_info = User.query.filter_by(session_id='mock_session_id').first()
            assert token_info is not None
            assert token_info.access_token == 'mock_access_token'
            assert token_info.refresh_token == 'mock_refresh_token'

# Test callback with missing session ID
def test_callback_no_session_id(client):
    # Mock the requests.post to simulate Spotify's response
    def mock_requests_post(url, headers, data):
        class MockResponse:
            def json(self):
                return {
                    'access_token': 'mock_access_token',
                    'refresh_token': 'mock_refresh_token'
                }
        return MockResponse()

    with patch('requests.post', mock_requests_post):
        # Ensure no cookie is set to simulate missing session ID
        client.delete_cookie('session_id')
        
        response = client.get('/auth/callback?code=mock_code')
        assert response.status_code == 302
        
        # Extract the new session_id from the redirection URL
        new_session_id = response.location.split('session_id=')[-1]
        assert new_session_id != ''
        assert response.location == f'http://localhost:3000?session_id={new_session_id}'
        
        # Verify that tokens are stored in the database
        token_info = User.query.filter_by(session_id=new_session_id).first()
        assert token_info is not None
        assert token_info.access_token == 'mock_access_token'
        assert token_info.refresh_token == 'mock_refresh_token'


# Mock OpenAI Recommendation
def mock_openai_recommendation(user_text):
    return {
        'Playlist name': 'MMTest Playlist',
        'Songs': ['Song1 by Artist1', 'Song2 by Artist2', 'Song3 by Artist3']
    }

# Mock Spotify Playlist Creation
def mock_spotify_playlist(recommendation_dict, session_id):
    return "https://open.spotify.com/playlist/mock_playlist_id"

# Mock Token Retrieval
def mock_retrieve_tokens_from_db(session_id):
    if session_id == "mock_session_id":
        return {'access_token': 'mock_access_token', 'refresh_token': 'mock_refresh_token'}
    return None

def test_recommend_no_session_id(client):
    response = client.post('/recommend', json={'description': 'happy songs'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['authorized'] == False
    assert "No session ID found" in data['message']
    assert "auth_url" in data

def test_recommend_user_not_authorized(client):
    with patch('app.routes.retrieve_tokens_from_db', side_effect=mock_retrieve_tokens_from_db):
        response = client.post('/recommend?session_id=invalid_session_id', json={'description': 'happy songs'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['authorized'] == False
        assert "User not authorized" in data['message']
        assert "auth_url" in data

def test_recommend_success(client):
    with patch('app.routes.retrieve_tokens_from_db', side_effect=mock_retrieve_tokens_from_db):
        with patch('app.routes.openai_recommendation', side_effect=mock_openai_recommendation):
            with patch('app.routes.spotify_playlist', side_effect=mock_spotify_playlist):
                client.set_cookie(key='session_id', value='mock_session_id')
                response = client.post('/recommend', json={'description': 'happy songs'})
                assert response.status_code == 200
                data = response.get_json()
                assert data['authorized'] == True
                assert 'recommendation' in data
                assert 'spotify_link' in data
                assert data['recommendation'] == ['Song1 by Artist1', 'Song2 by Artist2', 'Song3 by Artist3']
                assert data['spotify_link'] == "https://open.spotify.com/playlist/mock_playlist_id"