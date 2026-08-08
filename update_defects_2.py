import re

def update_defect(content, def_id, new_status, reason, history_line):
    # Find the block for the defect
    pattern = rf"(## {def_id}:.*?)- Status: OPEN(.*?)History:(.*?)(?=## DEF-|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"Could not find {def_id}")
        return content
    
    header = match.group(1)
    middle = match.group(2)
    history = match.group(3).rstrip()
    
    # Replace the block
    new_block = f"{header}- Status: {new_status}{middle}History:{history}\n- orchestrator: {history_line}\n\n"
    
    content = content[:match.start()] + new_block + content[match.end():]
    return content

with open("DEFECTS.md", "r") as f:
    content = f.read()

updates = {
    "DEF-003": "FIX READY — Validated language and task codes against faster-whisper supported sets with fallback to auto-detection/transcribe and exception handling in `server/stt.py` and `server/main.py`.",
    "DEF-004": "FIX READY — Trimmed trailing odd bytes on incoming binary audio chunks and copied byte buffers in `server/main.py` so future 16-bit PCM chunks remain 2-byte aligned without buffer export lock errors.",
    "DEF-005": "FIX READY — Added WebSocket close/error handling in `extension/offscreen.js` to trigger `stopCapture()` and dispatch `captureStopped` messages to `background.js` and `popup.js`, resetting state and returning popup UI to \"Start Captioning\".",
    "DEF-006": "FIX READY — Replaced race-prone `setTimeout(200)` delay in `extension/background.js` with event-driven synchronization using an `offscreenReady` initialization message sent from `extension/offscreen.js`.",
    "DEF-007": "FIX READY — Updated `extension/offscreen.js` `startCapture()` to acquire the tab `MediaStream` prior to instantiating the WebSocket connection, catching stream errors and stopping capture cleanly.",
    "DEF-008": "FIX READY — Added single-session lock (`self.active_client`) in `RelayServer` (`client/main.py`) to reject concurrent client connections with close code 1008 and preserve active stream integrity and UI status.",
    "DEF-009": "FIX READY — Updated `RelayServer` (`client/main.py`) to track disconnect sources and emit `\"Remote STT server disconnected.\"` when remote STT connections drop.",
    "DEF-010": "FIX READY — Set `self.label.setTextFormat(Qt.TextFormat.PlainText)` on `TransparentOverlayWindow` in `client/main.py` to render raw HTML tags in transcriptions as literal plain text.",
    "DEF-011": "FIX READY — Added `_update_geometry()` to `TransparentOverlayWindow` (`client/main.py`) to dynamically adjust window height based on text content hint to accommodate multi-line captions without clipping.",
    "DEF-012": "FIX READY — Modified `_clear_caption()` and `set_caption_text()` in `client/main.py` to toggle `self.label.setVisible(False)` when text is empty, hiding stylesheet background and border boxes during silence."
}

for def_id, reason in updates.items():
    content = update_defect(content, def_id, "FIX-READY", reason, f"marked FIX-READY on behalf of developer: {reason}")

with open("DEFECTS.md", "w") as f:
    f.write(content)
