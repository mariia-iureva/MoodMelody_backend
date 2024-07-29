# tests/conftest.py
import os
from dotenv import load_dotenv
import pytest
from app import create_app
import requests
from unittest.mock import patch
from app import db

# Load environment variables from .env file
load_dotenv()

@pytest.fixture(scope='module')
def client():
    test_config = {
        'TESTING': True,
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'SQLALCHEMY_DATABASE_URI': os.getenv('SQLALCHEMY_TEST_DATABASE_URI', 'sqlite:///:memory:')  # Default to in-memory SQLite if not set
    }
    app = create_app(test_config)
    
    with app.test_client() as client:
            with app.app_context():
                # Create tables
                db.create_all()
                yield client
                # Drop tables
                db.drop_all()

@pytest.fixture(autouse=True)
def cleanup():
    yield
    db.session.rollback()
    db.session.remove()

@pytest.fixture
def mock_openai(monkeypatch):
    class MockChatCompletionMessage:
        def __init__(self, content):
            self.content = content
            self.role = 'assistant'
            self.function_call = None
            self.tool_calls = None

    class MockChoice:
        def __init__(self, message):
            self.finish_reason = 'stop'
            self.index = 0
            self.logprobs = None
            self.message = MockChatCompletionMessage(message)

    class MockChatCompletion:
        def __init__(self, choices):
            self.choices = choices
            self.id = 'chatcmpl-9prTPD6mJYRKMU8y6C3gbWtPjEpMv'
            self.created = 1722147307
            self.model = 'gpt-4o-mini-2024-07-18'
            self.object = 'chat.completion'
            self.service_tier = None
            self.system_fingerprint = 'fp_ba606877f9'
            self.usage = {'completion_tokens': 46, 'prompt_tokens': 129, 'total_tokens': 175}

    class MockCompletions:
        def create(self, *args, **kwargs):
            message_content = "{ 'Playlist name': 'MMCat Tunes', 'Songs': ['The Cat Came Back by Fred Penner', 'Stray Cat Strut by Stray Cats', 'Everybody Wants to Be a Cat by Phil Harris'] }"
            choices = [MockChoice(message_content)]
            return MockChatCompletion(choices)

    class MockChat:
        @property
        def completions(self):
            return MockCompletions()

    class MockOpenAIClient:
        @property
        def chat(self):
            return MockChat()

    monkeypatch.setattr('app.routes.get_openai_client', lambda: MockOpenAIClient())

@pytest.fixture
def mock_spotify(monkeypatch):
    # Mock get_spotify_user_id
    def mock_get_spotify_user_id(access_token):
        return 'mock_user_id'
    monkeypatch.setattr('app.routes.get_spotify_user_id', mock_get_spotify_user_id)

    # Mock requests.get
    def mock_requests_get(url, headers):
        class MockResponse:
            def json(self):
                return {
                    'tracks': {
                        'items': [
                            {'uri': 'spotify:track:mock_uri'}
                        ]
                    }
                }
        return MockResponse()
    monkeypatch.setattr(requests, 'get', mock_requests_get)

    # Mock requests.post
    def mock_requests_post(url, json, headers):
        class MockResponse:
            def json(self):
                if 'playlists' in url:
                    return {'id': 'mock_playlist_id'}
                return {}
        return MockResponse()
    monkeypatch.setattr(requests, 'post', mock_requests_post)