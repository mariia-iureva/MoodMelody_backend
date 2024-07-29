# tests/conftest.py
import os
from dotenv import load_dotenv
import pytest
from app import create_app


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
            yield client

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
