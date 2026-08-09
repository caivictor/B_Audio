"""
End-to-End Tests for Phase 1 (Proof of Concept) Pipeline.

Verifies:
1. Chrome Extension connects to Local Client Relay (ws://localhost:8765).
2. Local Client forwards config and audio chunks to Remote STT Backend (ws://127.0.0.1:8000/transcribe).
3. STT Backend processes audio PCM chunks and returns transcribed text JSON.
4. Local Client updates transparent PyQt6 UI Overlay with real-time text.
5. End-to-end failure handling when STT server or extension disconnects.
"""

import sys
import os
import json
import asyncio
import socket
import pytest
import websockets
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.main import RelayServer, CaptionSignalBridge, TransparentOverlayWindow, run_mock_stt_server, parse_speaker_tags


def get_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def qapp():
    """Module-level QApplication fixture for Qt GUI testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.mark.asyncio
async def test_full_e2e_transcription_pipeline_spanish(qapp):
    """
    Test full end-to-end pipeline flow with Spanish configuration:
    Extension -> Local Client Relay -> STT Server -> Local Client -> Overlay UI text update.
    """
    mock_port = get_free_port()
    relay_port = get_free_port()

    # 1. Start STT Server
    mock_server = await run_mock_stt_server(host="127.0.0.1", port=mock_port)

    # 2. Setup Local Client Signal Bridge & Overlay
    bridge = CaptionSignalBridge()
    overlay = TransparentOverlayWindow(initial_text="Initializing")
    
    received_texts = []
    received_statuses = []

    def on_text(txt):
        received_texts.append(txt)
        overlay.set_caption_text(txt)

    def on_status(st):
        received_statuses.append(st)

    bridge.text_received.connect(on_text)
    bridge.status_changed.connect(on_status)

    # 3. Start Local Client Relay Server
    relay = RelayServer(
        host="127.0.0.1",
        port=relay_port,
        remote_url=f"ws://127.0.0.1:{mock_port}/transcribe",
        signal_bridge=bridge
    )
    await relay.start_server()

    try:
        # 4. Simulate Chrome Extension connecting to Local Client on ws://localhost:relay_port
        ext_url = f"ws://127.0.0.1:{relay_port}"
        async with websockets.connect(ext_url) as ext_ws:
            # Send Extension config message (Spanish language selection)
            config = json.dumps({"type": "config", "language": "es"})
            await ext_ws.send(config)

            # Send binary PCM audio chunk (16kHz mono 16-bit PCM = 32000 bytes for 1s)
            pcm_chunk = b"\x00\x00" * 16000
            await ext_ws.send(pcm_chunk)

            # Wait briefly for round-trip processing
            await asyncio.sleep(0.8)

            # Verify transcription text received and updated on overlay window
            assert len(received_texts) > 0, "No transcription text received from pipeline"
            latest_text = received_texts[-1]
            assert "demostración" in latest_text or "Transcripción" in latest_text or "bienvenidos" in latest_text
            assert overlay.label.text() == parse_speaker_tags(latest_text)

    finally:
        mock_server.close()
        await mock_server.wait_closed()
        await relay.stop()


@pytest.mark.asyncio
async def test_full_e2e_transcription_pipeline_english(qapp):
    """
    Test full end-to-end pipeline flow with English configuration.
    """
    mock_port = get_free_port()
    relay_port = get_free_port()

    mock_server = await run_mock_stt_server(host="127.0.0.1", port=mock_port)

    bridge = CaptionSignalBridge()
    overlay = TransparentOverlayWindow(initial_text="Initializing")
    
    received_texts = []
    bridge.text_received.connect(lambda txt: (received_texts.append(txt), overlay.set_caption_text(txt)))

    relay = RelayServer(
        host="127.0.0.1",
        port=relay_port,
        remote_url=f"ws://127.0.0.1:{mock_port}/transcribe",
        signal_bridge=bridge
    )
    await relay.start_server()

    try:
        ext_url = f"ws://127.0.0.1:{relay_port}"
        async with websockets.connect(ext_url) as ext_ws:
            config = json.dumps({"type": "config", "language": "en"})
            await ext_ws.send(config)

            pcm_chunk = b"\x00\x00" * 16000
            await ext_ws.send(pcm_chunk)

            await asyncio.sleep(0.8)

            assert len(received_texts) > 0
            latest_text = received_texts[-1]
            assert "Hello" in latest_text or "demonstration" in latest_text or "Real-time" in latest_text
            assert overlay.label.text() == parse_speaker_tags(latest_text)

    finally:
        mock_server.close()
        await mock_server.wait_closed()
        await relay.stop()


@pytest.mark.asyncio
async def test_extension_connection_when_stt_offline(qapp):
    """
    Test Local Client behavior when extension connects but STT server is offline.
    Local Client should handle connection failure gracefully and update status.
    """
    relay_port = get_free_port()
    unused_stt_port = get_free_port()

    bridge = CaptionSignalBridge()
    received_statuses = []
    bridge.status_changed.connect(received_statuses.append)

    relay = RelayServer(
        host="127.0.0.1",
        port=relay_port,
        remote_url=f"ws://127.0.0.1:{unused_stt_port}/transcribe",
        signal_bridge=bridge
    )
    await relay.start_server()

    try:
        ext_url = f"ws://127.0.0.1:{relay_port}"
        async with websockets.connect(ext_url) as ext_ws:
            config = json.dumps({"type": "config", "language": "es"})
            await ext_ws.send(config)

            await asyncio.sleep(4)

            # Check that status bridge logged error connecting to STT
            assert any("Error connecting to STT server" in st for st in received_statuses)

    finally:
        await relay.stop()
