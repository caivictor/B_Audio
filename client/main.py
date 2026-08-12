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
import re
import html
from typing import Optional

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, QStyleOption, QStyle
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QMouseEvent, QTextDocument, QTextOption

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
    font_size_changed = pyqtSignal(int)


SPEAKER_COLORS = {
    "Speaker 1": "#ff9999",
    "Speaker A": "#ff9999",
    "Speaker 2": "#99ccff",
    "Speaker B": "#99ccff",
    "Speaker 3": "#99ff99",
    "Speaker C": "#99ff99",
    "Speaker 4": "#ffcc99",
    "Speaker D": "#ffcc99",
    "Speaker 5": "#cc99ff",
    "Speaker E": "#cc99ff",
    "Speaker 6": "#ffff99",
    "Speaker F": "#ffff99",
    "Speaker 7": "#ff99ff",
    "Speaker G": "#ff99ff",
    "Speaker 8": "#99ffff",
    "Speaker H": "#99ffff",
    "Speaker 9": "#ffb3e6",
    "Speaker I": "#ffb3e6",
    "Speaker 10": "#c2f0c2",
    "Speaker J": "#c2f0c2",
}

DEFAULT_PALETTE = [
    "#ff9999",
    "#99ccff",
    "#99ff99",
    "#ffcc99",
    "#cc99ff",
    "#ffff99",
    "#ff99ff",
    "#99ffff",
    "#ffb3e6",
    "#c2f0c2",
]


def get_speaker_color(speaker_id: str) -> str:
    """Return hex color code associated with a speaker label."""
    clean_id = speaker_id.strip()
    if clean_id in SPEAKER_COLORS:
        return SPEAKER_COLORS[clean_id]
    for k, v in SPEAKER_COLORS.items():
        if k.lower() == clean_id.lower():
            return v
    idx = sum(ord(c) for c in clean_id) % len(DEFAULT_PALETTE)
    return DEFAULT_PALETTE[idx]


def parse_speaker_tags(text: str) -> str:
    """
    Parse speaker tags (e.g., [Speaker 1]: or [Speaker A]:) in transcription text
    and format them into HTML spans with assigned speaker colors.
    If speaker tags are present, HTML characters in raw text segments are safely escaped.
    If no speaker tags are present, returns original text unchanged.
    """
    if not text:
        return ""

    pattern = r"\[(Speaker\s*[^\]]+)\]:?"
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    if not matches:
        return text

    escaped_text = html.escape(text).replace('\n', '<br>')
    escaped_matches = list(re.finditer(pattern, escaped_text, re.IGNORECASE))

    result = []
    last_idx = 0
    for i, match in enumerate(escaped_matches):
        prefix = escaped_text[last_idx:match.start()]
        
        # Insert line break if a new speaker tag appears and there isn't already one
        if i > 0:
            if prefix and not prefix.rstrip().endswith('<br>'):
                prefix += '<br>'
            elif not prefix:
                result.append('<br>')
                
        if prefix:
            result.append(prefix)

        speaker_label = match.group(1).strip()
        color = get_speaker_color(speaker_label)
        next_start = escaped_matches[i + 1].start() if i + 1 < len(escaped_matches) else len(escaped_text)
        segment_text = escaped_text[match.end():next_start]

        formatted_segment = f'<span style="color: {color};"><b>[{match.group(1)}]:</b>{segment_text}</span>'
        result.append(formatted_segment)
        last_idx = next_start

    return "".join(result)


class StrokedLabel(QLabel):
    """
    QLabel subclass that renders text with a dark outline (stroke)
    around text to ensure readability on bright/light backgrounds.
    Supports RichText/HTML formatting for color-coded speaker tags.
    """
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._stroke_color = QColor(0, 0, 0, 255)
        self._stroke_width = 2
        self._text_color = QColor(255, 255, 255, 255)

    def set_stroke_width(self, width: int):
        self._stroke_width = width
        self.update()

    def set_stroke_color(self, color: QColor):
        self._stroke_color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

        text = self.text()
        if not text:
            return

        rect = self.contentsRect()
        alignment = self.alignment()
        painter.setFont(self.font())

        fmt = self.textFormat()
        if fmt == Qt.TextFormat.RichText:
            is_rich = True
        elif fmt == Qt.TextFormat.PlainText:
            is_rich = False
        else:
            is_rich = Qt.mightBeRichText(text)

        w = self._stroke_width

        if is_rich:
            rich_text = text.replace('\n', '<br>')

            doc = QTextDocument()
            doc.setDefaultFont(self.font())
            doc.setDefaultStyleSheet("body { color: #ffffff; }")
            doc.setTextWidth(rect.width())
            doc.setHtml(f'<div align="center">{rich_text}</div>')

            doc_height = doc.size().height()
            y_offset = rect.y() + max(0, (rect.height() - doc_height) / 2)

            if w > 0:
                stroke_color_hex = self._stroke_color.name()
                stroke_html = re.sub(r'color:\s*[^;"]+;?', f'color: {stroke_color_hex};', rich_text)
                stroke_doc = QTextDocument()
                stroke_doc.setDefaultFont(self.font())
                stroke_doc.setDefaultStyleSheet(f"* {{ color: {stroke_color_hex} !important; }}")
                stroke_doc.setTextWidth(rect.width())
                stroke_doc.setHtml(f'<div align="center">{stroke_html}</div>')

                for dx in range(-w, w + 1):
                    for dy in range(-w, w + 1):
                        if dx == 0 and dy == 0:
                            continue
                        if dx * dx + dy * dy <= (w + 0.5) ** 2:
                            painter.save()
                            painter.translate(rect.x() + dx, y_offset + dy)
                            stroke_doc.drawContents(painter)
                            painter.restore()

            painter.save()
            painter.translate(rect.x(), y_offset)
            doc.drawContents(painter)
            painter.restore()
        else:
            if w > 0:
                painter.setPen(self._stroke_color)
                for dx in range(-w, w + 1):
                    for dy in range(-w, w + 1):
                        if dx == 0 and dy == 0:
                            continue
                        if dx * dx + dy * dy <= (w + 0.5) ** 2:
                            painter.drawText(
                                rect.translated(dx, dy),
                                alignment | Qt.TextFlag.TextWordWrap,
                                text
                            )

            painter.setPen(self._text_color)
            painter.drawText(
                rect,
                alignment | Qt.TextFlag.TextWordWrap,
                text
            )


class TransparentOverlayWindow(QWidget):
    """
    Frameless, transparent, always-on-top overlay window
    for rendering real-time speech captions on screen.
    Draggable using mouse press and move events.
    """

    def __init__(self, initial_text: Optional[str] = None, font_size: int = 24):
        super().__init__()

        # Draggable state tracking
        self._drag_position = None
        self._user_dragged = False
        self.font_size = font_size

        # Enable translucent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Set window flags: Frameless, Always-On-Top, Tool window (Removed WindowTransparentForInput to allow dragging)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self._init_ui(initial_text)
        self._position_window()

        # Timer to clear captions after prolonged silence
        self.clear_timer = QTimer(self)
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self._clear_caption)

    def _init_ui(self, initial_text: Optional[str]):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add a close button layout at the top right
        from PyQt6.QtWidgets import QHBoxLayout, QPushButton
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(5, 5, 5, 0)
        top_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #a6adc8; border: none; font-weight: bold; }"
            "QPushButton:hover { color: #f38ba8; }"
        )
        self.close_btn.clicked.connect(self.close)
        # Initially hide the close button, show it on mouse enter
        self.close_btn.setVisible(False)
        top_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(top_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 5, 20, 20)
        main_layout.addLayout(layout)

        text_to_display = initial_text if initial_text is not None else "WebCaptioner Ready"
        parsed_text = parse_speaker_tags(text_to_display)
        self.label = StrokedLabel(parsed_text)
        if parsed_text != text_to_display:
            self.label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)

        if not text_to_display:
            self.label.setVisible(False)

        # Style sheet for high contrast subtitle look
        self._apply_label_style(self.font_size)

        # Add drop shadow for high contrast on light backgrounds
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.label.setGraphicsEffect(shadow)

        layout.addWidget(self.label)
        self.setLayout(layout)

    def _apply_label_style(self, size: int):
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(18, 18, 24, 0.82);
                color: #FFFFFF;
                border-radius: 12px;
                padding: 16px 24px;
                font-family: 'Segoe UI', 'Ubuntu', 'Helvetica Neue', sans-serif;
                font-size: {size}px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }}
        """)
        font = self.label.font()
        font.setPointSize(size)
        self.label.setFont(font)

    def set_font_size(self, size: int):
        """Dynamically update font size of overlay text."""
        try:
            size = int(size)
            if size < 12 or size > 72:
                return
        except (ValueError, TypeError):
            return
        self.font_size = size
        self._apply_label_style(size)
        self._update_geometry()


    def closeEvent(self, event):
        """Ensure the entire application exits when the overlay is closed."""
        super().closeEvent(event)
        import os
        os._exit(0)  # Force kill to prevent any lingering asyncio/websocket threads


    def closeEvent(self, event):
        """Ensure the entire application exits when the overlay is closed."""
        super().closeEvent(event)
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        import os
        os._exit(0) # Force kill to prevent any lingering asyncio/websocket threads


    def closeEvent(self, event):
        """Ensure the entire application exits when the overlay is closed."""
        super().closeEvent(event)
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        import os
        os._exit(0) # Force kill to prevent any lingering asyncio/websocket threads

    def keyPressEvent(self, event):
        """Close on Escape key"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def enterEvent(self, event):
        """Show close button on hover"""
        if hasattr(self, 'close_btn'):
            self.close_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide close button when mouse leaves"""
        if hasattr(self, 'close_btn'):
            self.close_btn.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Capture drag start position when left mouse button is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._user_dragged = True
            if self.windowHandle() and hasattr(self.windowHandle(), "startSystemMove"):
                if self.windowHandle().startSystemMove():
                    event.accept()
                    return
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Move window position when left mouse button is dragged."""
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_position is not None:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            self._user_dragged = True
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Release drag state on mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            event.accept()

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
            default_width = int(screen_geom.width() * 0.75)
            default_x = screen_geom.x() + (screen_geom.width() - default_width) // 2
            screen_bottom = screen_geom.y() + screen_geom.height()
        else:
            default_width = 1000
            default_x = 100
            screen_bottom = 800

        width = self.width() if self._user_dragged else default_width
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
        if not self._user_dragged:
            y = screen_bottom - req_height - 60
            self.setGeometry(QRect(default_x, y, default_width, req_height))

    def set_caption_text(self, text: str):
        """Update caption label and restart clear timer."""
        if not text:
            self._clear_caption()
            return
        parsed_text = parse_speaker_tags(text)
        if parsed_text != text:
            self.label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setText(parsed_text)
        self.label.setVisible(True)
        self._update_geometry()
        # Reset clear timer for 10 seconds of silence
        self.clear_timer.start(10000)

    def set_status_text(self, status: str):
        """Display status or connection message."""
        logger.info("Status update: %s", status)
        if any(keyword in status.lower() for keyword in ["error", "disconnected", "reconnecting", "unavailable", "failed"]):
            self.label.setText(f"[{status}]")
            self.label.setVisible(True)
            self._update_geometry()

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

            try:
                config_data = json.loads(config_msg)
                if isinstance(config_data, dict) and "fontSize" in config_data:
                    font_size = int(config_data["fontSize"])
                    if self.signal_bridge:
                        self.signal_bridge.font_size_changed.emit(font_size)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            # 2. Connect to Remote STT server (with auto-retry resilience)
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    remote_ws = await websockets.connect(self.remote_url)
                    logger.info("Connected to remote STT server at %s", self.remote_url)
                    if self.signal_bridge:
                        self.signal_bridge.status_changed.emit("Connected to STT server. Audio streaming active.")
                    break
                except Exception as exc:
                    logger.warning("Attempt %d/%d to connect to STT server at %s failed: %s", attempt, max_retries, self.remote_url, exc)
                    if attempt < max_retries:
                        if self.signal_bridge:
                            self.signal_bridge.status_changed.emit(f"STT Server offline. Retrying... ({attempt}/{max_retries})")
                        await asyncio.sleep(1.0)
                    else:
                        logger.error("Failed to connect to remote STT server at %s after %d attempts: %s", self.remote_url, max_retries, exc)
                        disconnect_reason = f"Error connecting to STT server: {exc}"
                        if self.signal_bridge:
                            self.signal_bridge.status_changed.emit(disconnect_reason)
                        await websocket.close()
                        return

            # 3. Forward config message to Remote STT server
            await remote_ws.send(config_msg)

            # 4. Bidirectional relay loops with immediate disconnect detection
            async def forward_audio_to_remote():
                nonlocal disconnect_reason
                try:
                    async for message in websocket:
                        if isinstance(message, str):
                            try:
                                data = json.loads(message)
                                if isinstance(data, dict) and "fontSize" in data:
                                    font_size = int(data["fontSize"])
                                    if self.signal_bridge:
                                        self.signal_bridge.font_size_changed.emit(font_size)
                            except (json.JSONDecodeError, TypeError, ValueError):
                                pass
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
            "es": [
                "[Speaker 1]: Hola, bienvenidos a la demostración.",
                "[Speaker 2]: Transcripción en tiempo real funcionando.",
                "[Speaker 1]: ¿Cómo estás? [Speaker 2]: Muy bien, gracias."
            ],
            "en": [
                "[Speaker 1]: Hello, welcome to the demonstration.",
                "[Speaker 2]: Real-time transcription working correctly.",
                "[Speaker 1]: How are you? [Speaker 2]: I am doing great, thank you."
            ],
        }
        lang = "es"
        task = "transcribe"
        texts = sample_texts["es"]
        idx = 0

        try:
            async for message in websocket:
                if isinstance(message, (str, bytes)):
                    try:
                        data = json.loads(message)
                        if isinstance(data, dict):
                            if "language" in data or "task" in data or data.get("type") == "config":
                                lang = data.get("language", lang)
                                task = data.get("task", task)
                                if task == "translate":
                                    texts = sample_texts["en"]
                                else:
                                    texts = sample_texts.get(lang, sample_texts["es"])
                                idx = 0
                                logger.info("Mock STT updated config: language=%s, task=%s", lang, task)
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
    bridge.font_size_changed.connect(overlay.set_font_size)
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
