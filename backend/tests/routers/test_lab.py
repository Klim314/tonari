
import pytest
from unittest.mock import MagicMock, patch

def test_stream_lab_translation(client):
    # Mock get_model_info to ensure we have a valid model/provider
    with patch("app.routers.lab.get_model_info") as mock_get_info:
        mock_info = MagicMock()
        mock_info.provider = "openai"
        mock_get_info.return_value = mock_info

        # Mock the TranslationAgent
        with patch("app.routers.lab.TranslationAgent") as MockAgent:
            # User instance mock
            mock_instance = MockAgent.return_value
            
            # Async generator mock for stream_segment
            async def mock_stream(text, preceding_segments=None):
                yield "Hello "
                yield "World"
                
            mock_instance.stream_segment.side_effect = mock_stream
            
            payload = {
                "text": "こんにちは",
                "model": "test-model",
                "template": "Translate this.",
                "params": {}
            }
            
            response = client.post("/lab/stream", json=payload)
            
            assert response.status_code == 200
            # TestClient handles stream consumption
            assert response.text == "Hello World"
            
            # Verify agent was initialized correctly
            MockAgent.assert_called_once()
            call_kwargs = MockAgent.call_args.kwargs
            assert call_kwargs["model"] == "test-model"
            assert call_kwargs["system_prompt"] == "Translate this."
            assert call_kwargs["context_window"] == 0
            assert call_kwargs["provider"] == "openai"

def test_stream_lab_translation_invalid_model(client):
    with patch("app.routers.lab.get_model_info") as mock_get_info:
        mock_get_info.return_value = None
        
        payload = {
            "text": "test",
            "model": "invalid-model",
            "template": "template"
        }
        
        response = client.post("/lab/stream", json=payload)
        assert response.status_code == 400
