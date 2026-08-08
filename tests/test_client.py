"""
Unit tests for WebCaptioner Local Client UI and Relay Server.
"""

import json
import asyncio
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from client.main import TransparentOverlayWindow, CaptionSignalBridge, RelayServer, run_mock_stt_server


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance exists for Qt widget testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_overlay_window_flags_and_properties(qapp):
    """Verify overlay window has required transparent, frameless, always-on-top and click-through flags."""
    overlay = TransparentOverlayWindow(initial_text="Testing Subtitle")

    # Verify Translucent Background attribute
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True

    # Verify Window Flags
    flags = overlay.windowFlags()
    assert bool(flags & Qt.WindowType.FramelessWindowHint) is True
    assert bool(flags & Qt.WindowType.WindowStaysOnTopHint) is True
    assert bool(flags & Qt.WindowType.WindowTransparentForInput) is True

    # Verify label text setting
    assert overlay.label.text() == "Testing Subtitle"

    overlay.set_caption_text("Updated Caption")
    assert overlay.label.text() == "Updated Caption"


def test_caption_signal_bridge(qapp):
    """Verify CaptionSignalBridge emits signals correctly."""
    bridge = CaptionSignalBridge()
    received_texts = []

    bridge.text_received.connect(received_texts.append)
    bridge.text_received.emit("Hello World")

    assert len(received_texts) == 1
    assert received_texts[0] == "Hello World"


def get_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_relay_server_pipeline():
    """
    Integration test for RelayServer pipeline:
    Extension -> RelayServer -> Mock STT Server -> Text Signal Emit
    """
    import websockets

    received_texts = []

    bridge = CaptionSignalBridge()
    bridge.text_received.connect(received_texts.append)

    mock_port = get_free_port()
    relay_port = get_free_port()

    # Start Mock STT Server on dynamic port
    mock_stt = await run_mock_stt_server(host="127.0.0.1", port=mock_port)

    # Start RelayServer on dynamic port connecting to mock STT server
    relay = RelayServer(
        host="127.0.0.1",
        port=relay_port,
        remote_url=f"ws://127.0.0.1:{mock_port}/transcribe",
        signal_bridge=bridge
    )
    await relay.start_server()

    try:
        # Simulate Chrome extension connecting to Relay Server
        async with websockets.connect(f"ws://127.0.0.1:{relay_port}") as ext_ws:
            # Send initial config message
            config = json.dumps({"type": "config", "language": "es"})
            await ext_ws.send(config)

            # Send dummy binary PCM chunk
            dummy_pcm = b"\x00\x00" * 8000
            await ext_ws.send(dummy_pcm)

            # Wait briefly for mock server to process and relay signal
            await asyncio.sleep(0.7)

            assert len(received_texts) > 0
            assert any("demostración" in t or "Transcripción" in t or "bienvenidos" in t for t in received_texts)

    finally:
        mock_stt.close()
        await mock_stt.wait_closed()
        await relay.stop()


def test_overlay_plain_text_format(qapp):
    """Verify QLabel uses plain text format to avoid parsing HTML tags in captions (DEF-010)."""
    overlay = TransparentOverlayWindow(initial_text="Normal Text")
    assert overlay.label.textFormat() == Qt.TextFormat.PlainText

    html_text = '<h1 style="color:red">HACKED</h1><script>alert(1)</script>'
    overlay.set_caption_text(html_text)
    assert overlay.label.text() == html_text
    assert overlay.label.textFormat() == Qt.TextFormat.PlainText


def test_overlay_dynamic_height_for_long_text(qapp):
    """Verify overlay window dynamically resizes for long transcriptions to prevent clipping (DEF-011)."""
    overlay = TransparentOverlayWindow(initial_text="Short caption")
    initial_height = overlay.height()
    assert initial_height >= 140

    long_text = "This is a very long transcription string. " * 20
    overlay.set_caption_text(long_text)
    long_height = overlay.height()

    assert long_height > initial_height, f"Expected height {long_height} to be greater than initial height {initial_height}"

    # Verify height corresponds to heightForWidth of label
    margins = overlay.layout().contentsMargins()
    label_w = overlay.width() - margins.left() - margins.right()
    expected_lbl_h = overlay.label.heightForWidth(label_w)
    expected_window_h = max(140, expected_lbl_h + margins.top() + margins.bottom())
    assert long_height == expected_window_h


def test_overlay_clear_caption_hides_label(qapp):
    """Verify clearing caption hides label to prevent displaying an empty dark box during silence (DEF-012)."""
    overlay = TransparentOverlayWindow(initial_text="Active caption")
    overlay.show()
    assert overlay.label.isVisible() is True

    overlay._clear_caption()
    assert overlay.label.text() == ""
    assert overlay.label.isVisible() is False

    overlay.set_caption_text("New active caption")
    assert overlay.label.text() == "New active caption"
    assert overlay.label.isVisible() is True


@pytest.mark.asyncio
async def test_relay_server_single_session_lock():
    """Verify RelayServer enforces single-session lock and rejects secondary connections (DEF-008)."""
    import websockets

    mock_port = get_free_port()
    relay_port = get_free_port()

    mock_stt = await run_mock_stt_server(host="127.0.0.1", port=mock_port)
    bridge = CaptionSignalBridge()
    statuses = []
    bridge.status_changed.connect(statuses.append)

    relay = RelayServer(
        host="127.0.0.1",
        port=relay_port,
        remote_url=f"ws://127.0.0.1:{mock_port}/transcribe",
        signal_bridge=bridge
    )
    await relay.start_server()

    try:
        async with websockets.connect(f"ws://127.0.0.1:{relay_port}") as client1:
            await client1.send(json.dumps({"type": "config", "language": "es"}))
            await asyncio.sleep(0.1)

            # Secondary client connection attempt
            with pytest.raises(websockets.exceptions.ConnectionClosed):
                async with websockets.connect(f"ws://127.0.0.1:{relay_port}") as client2:
                    await client2.send(json.dumps({"type": "config", "language": "es"}))
                    await client2.recv()

            # Status should not indicate disconnect while Client 1 is still active
            assert "Disconnected from extension." not in statuses[-1] if statuses else True
    finally:
        mock_stt.close()
        await mock_stt.wait_closed()
        await relay.stop()


@pytest.mark.asyncio
async def test_relay_server_remote_stt_disconnect_status():
    """Verify RelayServer reports remote STT disconnect status when remote STT drops (DEF-009)."""
    import websockets

    mock_port = get_free_port()
    relay_port = get_free_port()

    server_ws_ref = []

    async def mock_handler(websocket):
        server_ws_ref.append(websocket)
        async for msg in websocket:
            pass

    mock_stt = await websockets.serve(mock_handler, "127.0.0.1", mock_port)
    bridge = CaptionSignalBridge()
    statuses = []
    bridge.status_changed.connect(statuses.append)

    relay = RelayServer(
        host="127.0.0.1",
        port=relay_port,
        remote_url=f"ws://127.0.0.1:{mock_port}/transcribe",
        signal_bridge=bridge
    )
    await relay.start_server()

    try:
        async with websockets.connect(f"ws://127.0.0.1:{relay_port}") as client:
            await client.send(json.dumps({"type": "config", "language": "es"}))
            await asyncio.sleep(0.1)

            # Simulate remote STT server dropping connection
            if server_ws_ref:
                await server_ws_ref[0].close(1001, "Server shutting down")

            await asyncio.sleep(0.2)

            assert any("Remote STT server disconnected." in s for s in statuses)
    finally:
        mock_stt.close()
        await mock_stt.wait_closed()
        await relay.stop()


