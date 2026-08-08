"""
Unit tests for Remote STT Server API endpoints and transcription service.
"""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.stt import STTService, stt_service

client = TestClient(app)


def test_health_endpoint():
    """
    Test GET /health returns OK status and model info.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data
    assert "device" in data


def test_stt_service_transcribe():
    """
    Test STTService directly with numpy array input.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    audio = np.zeros(1600, dtype=np.float32)
    text = stt.transcribe(audio, language="en")
    assert isinstance(text, str)


def test_websocket_transcribe_flow():
    """
    Test WebSocket /transcribe flow with config message and binary PCM chunk.
    """
    with client.websocket_connect("/transcribe") as websocket:
        # Send initial config message
        websocket.send_json({"type": "config", "language": "en"})

        # Send 0.1 second of PCM bytes
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)

        # Receive JSON response
        response = websocket.receive_json()
        assert "text" in response
        assert isinstance(response["text"], str)


def test_websocket_invalid_json():
    """
    Test WebSocket resilience when receiving invalid JSON config text.
    """
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_text("invalid json")

        # Send audio bytes after invalid json
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)

        response = websocket.receive_json()
        assert "text" in response
        assert isinstance(response["text"], str)


def test_websocket_config_update():
    """
    Test updating config mid-session.
    """
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_json({"type": "config", "language": "es"})
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)
        res1 = websocket.receive_json()
        assert "text" in res1

        websocket.send_json({"type": "config", "language": "en", "task": "translate"})
        websocket.send_bytes(pcm_bytes)
        res2 = websocket.receive_json()
        assert "text" in res2


def test_websocket_invalid_language_and_task():
    """
    Test WebSocket session stability when receiving invalid/unsupported language or task config (DEF-003).
    """
    audio = np.zeros(1600, dtype=np.float32)

    # Direct STTService test with invalid language & task
    text1 = stt_service.transcribe(audio, language="invalid_lang", task="invalid_task")
    assert isinstance(text1, str)

    text2 = stt_service.transcribe(audio, language="english", task="unknown")
    assert isinstance(text2, str)

    # WebSocket integration test
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_json({"type": "config", "language": "invalid_lang", "task": "invalid_task"})
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)
        res1 = websocket.receive_json()
        assert "text" in res1


def test_websocket_odd_length_audio_chunks():
    """
    Test WebSocket handling of odd-length binary audio messages without corrupting alignment (DEF-004).
    """
    with client.websocket_connect("/transcribe") as websocket:
        # Send 1 byte odd message (ignored/trimmed, no response generated since buffer is empty)
        websocket.send_bytes(b"\x01")

        # Send 1001 bytes odd message (trimmed to 1000 bytes)
        websocket.send_bytes(bytes(1001))
        res1 = websocket.receive_json()
        assert "text" in res1

        # Send standard 3200 byte chunk (100ms)
        websocket.send_bytes(bytes(3200))
        res2 = websocket.receive_json()
        assert "text" in res2
