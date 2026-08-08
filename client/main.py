"""
WebCaptioner - Local Client & Transparent UI Overlay

This module runs a local WebSocket server to receive PCM audio streams from the
Chrome Extension, relays them to the remote Speech-To-Text (STT) server, and renders
transcription responses in a transparent, frameless, always-on-top desktop overlay.
"""

import sys
import json
import logging
import asyncio
import threading
import argparse
from typing import Optional

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QColor, QFont, QGuiApplication

import websockets

# Configure logging without emojis
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WebCaptionerClient")


class CaptionSignalBridge(QObject):
    """Signal bridge to pass messages safely from asyncio background thread to PyQt UI main thread."""
    text_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)


class TransparentOverlayWindow(QWidget):
    """
    Frameless, transparent, always-on-top, click-through overlay window
    for rendering real-time speech captions on screen.
    """

    def __init__(self, initial_text: Optional[str] = None):
        super().__init__()

        # Enable translucent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Set window flags: Frameless, Always-On-Top, Click-Through, Tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )

        self._init_ui(initial_text)
        self._position_window()

        # Timer to clear captions after prolonged silence
        self.clear_timer = QTimer(self)
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self._clear_caption)

    def _init_ui(self, initial_text: Optional[str]):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        text_to_display = initial_text if initial_text is not None else "WebCaptioner Ready"
        self.label = QLabel(text_to_display)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)

        if not text_to_display:
            self.label.setVisible(False)

        # Style sheet for high contrast subtitle look
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(18, 18, 24, 0.82);
                color: #FFFFFF;
                border-radius: 12px;
                padding: 16px 24px;
                font-family: 'Segoe UI', 'Ubuntu', 'Helvetica Neue', sans-serif;
                font-size: 24px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
        """)

        # Add drop shadow for high contrast on light backgrounds
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.label.setGraphicsEffect(shadow)

        layout.addWidget(self.label)
        self.setLayout(layout)

    def _position_window(self):
        """Position window at bottom center of the primary screen with dynamic height support."""
        self._update_geometry()

    def _update_geometry(self):
        """Dynamically adjust window height based on caption content to prevent clipping."""
        self.ensurePolished()
        self.label.ensurePolished()

        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            width = int(screen_geom.width() * 0.75)
            x = screen_geom.x() + (screen_geom.width() - width) // 2
            screen_bottom = screen_geom.y() + screen_geom.height()
        else:
            width = 1000
            x = 100
            screen_bottom = 800

        self.setFixedWidth(width)

        if not self.label.isHidden() and self.label.text():
            margins = self.layout().contentsMargins()
            label_width = width - margins.left() - margins.right()
            lbl_height = self.label.heightForWidth(label_width)
            if lbl_height > 0:
                req_height = max(140, lbl_height + margins.top() + margins.bottom())
            else:
                req_height = max(140, self.sizeHint().height())
        else:
            req_height = max(140, self.sizeHint().height())

        self.setFixedHeight(req_height)
        y = screen_bottom - req_height - 60
        self.setGeometry(QRect(x, y, width, req_height))

    def set_caption_text(self, text: str):
        """Update caption label and restart clear timer."""
        if not text:
            self._clear_caption()
            return
        self.label.setText(text)
        self.label.setVisible(True)
        self._update_geometry()
        # Reset clear timer for 10 seconds of silence
        self.clear_timer.start(10000)

    def set_status_text(self, status: str):
        """Display status or connection message."""
        logger.info("Status update: %s", status)

    def _clear_caption(self):
        """Clear overlay caption when silent and hide label background box."""
        self.label.setText("")
        self.label.setVisible(False)


class RelayServer:
    """
    WebSocket Relay Server listening on local port (e.g., ws://localhost:8765)
    and forwarding audio streams to the remote STT server (ws://127.0.0.1:8000/transcribe).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        remote_url: str = "ws://127.0.0.1:8000/transcribe",
        signal_bridge: Optional[CaptionSignalBridge] = None
    ):
        self.host = host
        self.port = port
        self.remote_url = remote_url
        self.signal_bridge = signal_bridge
        self.server = None
        self.loop = None
        self.active_client = None

    async def handle_client(self, websocket):
        if self.active_client is not None:
            logger.warning("Rejecting concurrent client connection attempt.")
            await websocket.close(1008, "Another client is already connected")
            return

        self.active_client = websocket
        logger.info("Chrome Extension connected to local relay server.")
        if self.signal_bridge:
            self.signal_bridge.status_changed.emit("Extension connected. Connecting to STT server...")

        remote_ws = None
        disconnect_reason = "Disconnected from extension."

        try:
            # 1. First message from extension is JSON config: {"type": "config", "language": "es"}
            config_msg = await websocket.recv()
            logger.info("Received config message: %s", config_msg)

            # 2. Connect to Remote STT server
            try:
                remote_ws = await websockets.connect(self.remote_url)
                logger.info("Connected to remote STT server at %s", self.remote_url)
                if self.signal_bridge:
                    self.signal_bridge.status_changed.emit("Connected to STT server. Audio streaming active.")
            except Exception as exc:
                logger.error("Failed to connect to remote STT server at %s: %s", self.remote_url, exc)
                disconnect_reason = f"Error connecting to STT server: {exc}"
                if self.signal_bridge:
                    self.signal_bridge.status_changed.emit(disconnect_reason)
                return

            # 3. Forward config message to Remote STT server
            await remote_ws.send(config_msg)

            # 4. Bidirectional relay loops with immediate disconnect detection
            async def forward_audio_to_remote():
                nonlocal disconnect_reason
                try:
                    async for message in websocket:
                        await remote_ws.send(message)
                    disconnect_reason = "Disconnected from extension."
                except websockets.exceptions.ConnectionClosed:
                    if remote_ws.closed:
                        disconnect_reason = "Remote STT server disconnected."
                    else:
                        disconnect_reason = "Disconnected from extension."
                except Exception as exc:
                    logger.error("Error forwarding audio to remote STT: %s", exc)

            async def receive_transcripts_from_remote():
                nonlocal disconnect_reason
                try:
                    async for message in remote_ws:
                        try:
                            data = json.loads(message)
                            text = data.get("text", "")
                            if text:
                                logger.info("Transcription received: %s", text)
                                if self.signal_bridge:
                                    self.signal_bridge.text_received.emit(text)
                        except json.JSONDecodeError:
                            logger.warning("Received invalid JSON from remote STT server: %s", message)
                    logger.info("Remote STT server disconnected.")
                    disconnect_reason = "Remote STT server disconnected."
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Remote STT server disconnected.")
                    disconnect_reason = "Remote STT server disconnected."
                except Exception as exc:
                    logger.error("Error receiving from remote STT: %s", exc)
                    disconnect_reason = f"Remote STT server error: {exc}"

            forward_task = asyncio.create_task(forward_audio_to_remote())
            receive_task = asyncio.create_task(receive_transcripts_from_remote())

            done, pending = await asyncio.wait(
                [forward_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by client or server.")
        except Exception as exc:
            logger.error("Error in relay loop: %s", exc)
        finally:
            if remote_ws:
                await remote_ws.close()
            if self.active_client == websocket:
                self.active_client = None
                if self.signal_bridge:
                    self.signal_bridge.status_changed.emit(disconnect_reason)

    async def start_server(self):
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        logger.info("Local relay server listening on ws://%s:%d", self.host, self.port)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    def run_in_thread(self):
        """Run asyncio loop inside a background daemon thread."""
        def _thread_target():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start_server())
            self.loop.run_forever()

        thread = threading.Thread(target=_thread_target, daemon=True)
        thread.start()
        return thread


async def run_mock_stt_server(host="127.0.0.1", port=8000):
    """
    A mock STT server for local testing when the remote GPU server is offline.
    Responds to audio chunks with mock transcription text.
    Supports mid-session JSON configuration updates (e.g. language selection).
    """
    async def handler(websocket):
        logger.info("Mock STT server client connected.")
        sample_texts = {
            "es": ["Hola, bienvenidos a la demostración.", "Transcripción en tiempo real funcionando."],
            "en": ["Hello, welcome to the demonstration.", "Real-time transcription working correctly."],
        }
        lang = "es"
        texts = sample_texts["es"]
        idx = 0

        try:
            async for message in websocket:
                if isinstance(message, (str, bytes)):
                    try:
                        data = json.loads(message)
                        if isinstance(data, dict):
                            if "language" in data or data.get("type") == "config":
                                lang = data.get("language", lang)
                                texts = sample_texts.get(lang, sample_texts["es"])
                                idx = 0
                                logger.info("Mock STT updated config: language=%s", lang)
                                continue
                    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                        pass

                # Simulate STT processing delay
                await asyncio.sleep(0.5)
                reply = json.dumps({"text": texts[idx % len(texts)]})
                idx += 1
                await websocket.send(reply)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Mock STT client disconnected.")

    server = await websockets.serve(handler, host, port)
    logger.info("Mock STT server running on ws://%s:%d/transcribe", host, port)
    return server


def main():
    parser = argparse.ArgumentParser(description="WebCaptioner Local Client UI")
    parser.add_argument("--host", default="localhost", help="Local relay host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Local relay port (default: 8765)")
    parser.add_argument("--remote-url", default="ws://127.0.0.1:8000/transcribe", help="Remote STT WebSocket URL")
    parser.add_argument("--text", default=None, help="Initial text to display on overlay")
    parser.add_argument("--mock-server", action="store_true", help="Start mock STT server locally on port 8000")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    # Signal bridge for thread safety
    bridge = CaptionSignalBridge()

    # Overlay window
    overlay = TransparentOverlayWindow(initial_text=args.text)
    bridge.text_received.connect(overlay.set_caption_text)
    bridge.status_changed.connect(overlay.set_status_text)
    overlay.show()

    # Optionally start local mock STT server for testing
    if args.mock_server:
        def start_mock():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_mock_stt_server())
            loop.run_forever()
        t = threading.Thread(target=start_mock, daemon=True)
        t.start()

    # Start local relay server in background thread
    relay = RelayServer(
        host=args.host,
        port=args.port,
        remote_url=args.remote_url,
        signal_bridge=bridge
    )
    relay.run_in_thread()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
