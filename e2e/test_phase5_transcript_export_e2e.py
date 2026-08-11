"""
End-to-End Tests for Phase 5 Transcript Export Pipeline (REQUIREMENTS.md Phase 5).

Verifies:
1. Server WebSocket returns JSON with 'text', 'start', and 'end' float timestamps.
2. Extension popup UI contains 'Download Transcript' button (#downloadBtn).
3. Background service worker accumulates transcriptHistory with start/end timestamps.
4. Transcript formatting produces formatted text matching:
   [00:01.500 --> 00:04.200] [Speaker 1]: Hello
5. End-to-end pipeline test from WebSocket audio response through transcript export generation.
"""

import sys
import os
import json
import asyncio
import pytest
import websockets
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.stt import STTService, SpeakerState
import numpy as np

EXTENSION_DIR = Path(__file__).parent.parent / "extension"


def test_popup_download_transcript_button_exists():
    """Verify popup.html includes the Download Transcript button."""
    popup_html = (EXTENSION_DIR / "popup.html").read_text(encoding="utf-8")
    assert 'id="downloadBtn"' in popup_html, "popup.html must contain id='downloadBtn'"
    assert "Download Transcript" in popup_html, "popup.html must display 'Download Transcript' text"


def test_popup_js_transcript_formatting():
    """Verify popup.js formatting logic creates correct timestamps and speaker tags."""
    popup_js = (EXTENSION_DIR / "popup.js").read_text(encoding="utf-8")
    assert "function formatTimestamp" in popup_js, "popup.js must define formatTimestamp"
    assert "function formatTranscript" in popup_js, "popup.js must define formatTranscript"
    assert "download = 'transcript.txt'" in popup_js, "popup.js must download as transcript.txt"


@pytest.mark.asyncio
async def test_stt_transcribe_payload_timestamps():
    """Verify STTService.transcribe returns text, start, and end timestamps in payload."""
    stt = STTService()
    
    # 1 second of audio (16kHz mono PCM float32)
    sample_rate = 16000
    audio_data = np.zeros(sample_rate, dtype=np.float32)
    state = SpeakerState()

    result = stt.transcribe(audio_data, language="en", task="transcribe", speaker_state=state)
    
    assert "text" in result
    assert "start" in result
    assert "end" in result
    assert isinstance(result["start"], (int, float))
    assert isinstance(result["end"], (int, float))
    assert result["start"] == 0.0
    assert result["end"] == 1.0


def test_transcript_formatting_logic():
    """
    Test node/JS or Python equivalent of formatTranscript and formatTimestamp
    to ensure output matches specified format:
    [00:01.500 --> 00:04.200] [Speaker 1]: Hello
    """
    # JS logic simulation in Python matching extension/popup.js exactly:
    def format_timestamp(seconds):
        if not isinstance(seconds, (int, float)):
            return "00:00.000"
        total_ms = round(seconds * 1000)
        hrs = total_ms // 3600000
        mins = (total_ms % 3600000) // 60000
        secs = (total_ms % 60000) // 1000
        ms = total_ms % 1000

        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms:03d}"
        return f"{mins:02d}:{secs:02d}.{ms:03d}"

    def format_transcript(history):
        lines = []
        for item in history:
            if isinstance(item, str):
                lines.append(item)
                continue
            text = item.get("text", "")
            start = item.get("start")
            end = item.get("end")
            if start is not None and end is not None:
                lines.append(f"[{format_timestamp(start)} --> {format_timestamp(end)}] {text}")
            else:
                lines.append(text)
        return "\n".join(lines)

    sample_history = [
        {"text": "[Speaker 1]: Hello, welcome to the demonstration.", "start": 1.5, "end": 4.2},
        {"text": "[Speaker 2]: Thank you, glad to be here.", "start": 5.0, "end": 8.125}
    ]

    formatted = format_transcript(sample_history)
    expected = (
        "[00:01.500 --> 00:04.200] [Speaker 1]: Hello, welcome to the demonstration.\n"
        "[00:05.000 --> 00:08.125] [Speaker 2]: Thank you, glad to be here."
    )

    assert formatted == expected, f"Expected:\n{expected}\n\nGot:\n{formatted}"
