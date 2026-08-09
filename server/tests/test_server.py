"""
Unit tests for Remote STT Server API endpoints and transcription service.
"""
import numpy as np
import pytest
from unittest.mock import patch
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


def test_websocket_ping_pong_keepalive():
    """
    Test ping/pong keepalive messages during WebSocket session.
    """
    with client.websocket_connect("/transcribe") as websocket:
        # Send ping
        websocket.send_json({"type": "ping"})
        res = websocket.receive_json()
        assert res == {"type": "pong"}

        # Send pong back to server (ignored gracefully)
        websocket.send_json({"type": "pong"})

        # Follow up with audio stream
        websocket.send_bytes(bytes(3200))
        res2 = websocket.receive_json()
        assert "text" in res2


def test_websocket_abrupt_disconnect_mid_stream():
    """
    Test server resilience and clean resource shutdown on abrupt WebSocket disconnect mid-stream.
    """
    ws = client.websocket_connect("/transcribe")
    websocket = ws.__enter__()
    websocket.send_json({"type": "config", "language": "en"})
    websocket.send_bytes(bytes(3200))
    # Close connection abruptly mid-stream without explicit disconnect handshake
    ws.__exit__(None, None, None)


def test_websocket_idle_timeout_keepalive(monkeypatch):
    """
    Test server sending periodic ping frame when client is idle.
    """
    monkeypatch.setattr("server.main.KEEPALIVE_TIMEOUT_SECONDS", 0.1)
    with client.websocket_connect("/transcribe") as websocket:
        # Client stays idle; server should send keepalive ping after timeout
        msg = websocket.receive_json()
        assert msg == {"type": "ping"}


def test_stt_service_translate_task_parameter():
    """
    Test that STTService correctly passes task='translate' to faster-whisper model.transcribe.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    audio = np.zeros(1600, dtype=np.float32)

    with patch.object(stt.model, "transcribe", return_value=([], None)) as mock_transcribe:
        # Test default task 'transcribe'
        stt.transcribe(audio, language="es")
        mock_transcribe.assert_called_once()
        _, kwargs1 = mock_transcribe.call_args
        assert kwargs1.get("task") == "transcribe"

        mock_transcribe.reset_mock()

        # Test explicit 'translate' task
        stt.transcribe(audio, language="es", task="translate")
        mock_transcribe.assert_called_once()
        _, kwargs2 = mock_transcribe.call_args
        assert kwargs2.get("task") == "translate"
        assert kwargs2.get("language") == "es"


def test_websocket_translate_task_parameter():
    """
    Test that WebSocket endpoint correctly parses 'task': 'translate' from config message
    and passes task='translate' to STTService.
    """
    with patch.object(stt_service, "transcribe", return_value="hello world") as mock_transcribe:
        with client.websocket_connect("/transcribe") as websocket:
            # Send translation config
            websocket.send_json({"type": "config", "language": "es", "task": "translate"})
            # Send audio bytes
            websocket.send_bytes(bytes(3200))

            res = websocket.receive_json()
            assert res == {"text": "hello world"}
            assert mock_transcribe.called
            _, kwargs = mock_transcribe.call_args
            assert kwargs.get("task") == "translate"
            assert kwargs.get("language") == "es"
