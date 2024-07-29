# tests/test_routes.py
import json
import pytest
from app.routes import openai_recommendation

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
