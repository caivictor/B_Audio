"""
End-to-End Tests for Remote STT Backend Server (REQUIREMENTS.md Phase 1).

Verifies:
1. GET /health returns 200 OK with model and device info.
2. WebSocket /transcribe endpoint accepts JSON config and binary PCM chunks.
3. WebSocket responds with JSON {"text": "..."}.
4. Error resilience on invalid JSON input.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.main import app

client = TestClient(app)


def test_stt_server_health_check():
    """Verify Remote STT Server /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data
    assert "device" in data


def test_stt_server_websocket_transcribe():
    """Verify Remote STT Server /transcribe WebSocket endpoint flow."""
    with client.websocket_connect("/transcribe") as ws:
        # Send JSON config
        ws.send_json({"type": "config", "language": "es"})

        # Send 1 second of 16kHz 16-bit PCM (32000 bytes)
        pcm_bytes = bytes(32000)
        ws.send_bytes(pcm_bytes)

        # Receive JSON response
        response = ws.receive_json()
        assert "text" in response
        assert isinstance(response["text"], str)


def test_stt_server_websocket_resilience():
    """Verify Remote STT Server handles invalid messages without crashing."""
    with client.websocket_connect("/transcribe") as ws:
        # Send bad text
        ws.send_text("not json")

        # Send valid audio bytes
        pcm_bytes = bytes(32000)
        ws.send_bytes(pcm_bytes)

        response = ws.receive_json()
        assert "text" in response
