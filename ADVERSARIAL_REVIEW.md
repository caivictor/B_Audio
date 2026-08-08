## ADV-001: Unsupported language or task string in JSON config crashes remote STT WebSocket session

- Session: phase-1 gate
- Suggested severity: HIGH

What I did: Connected a WebSocket client to ws://127.0.0.1:8000/transcribe, sent JSON config message {"type": "config", "language": "english"} or {"type": "config", "language": "invalid_lang"} (instead of 2-letter ISO code like en), and sent an audio chunk.
Expected: Server validates language string, falls back gracefully or ignores invalid language code, and continues servicing the WebSocket connection.
Actual: faster_whisper raises unhandled ValueError: 'invalid_lang' is not a valid language code. The exception escapes the transcription loop in server/main.py and crashes the entire WebSocket session immediately.

Disposition: ACCEPTED -> DEF-003

## ADV-002: Odd-length binary audio message permanently corrupts 16-bit PCM sample alignment

- Session: phase-1 gate
- Suggested severity: HIGH

What I did: Connected a WebSocket client to ws://127.0.0.1:8000/transcribe and sent an odd-length audio chunk (e.g. 1 byte or 1001 bytes). Then sent standard 16-bit PCM audio chunks.
Expected: Server trims or discards leftover odd bytes when processing chunks so that future chunks maintain proper 2-byte 16-bit PCM sample alignment.
Actual: server/main.py computes valid_len = len(audio_buffer) - (len(audio_buffer) % 2) and converts audio_buffer[:valid_len] to np.int16, but leaves the remaining 1 byte at index 0 of audio_buffer. Every subsequent 2-byte sample added to audio_buffer becomes byte-swapped (high and low bytes inverted), permanently corrupting all transcriptions for the rest of the session with static noise.

Disposition: ACCEPTED -> DEF-004

## ADV-003: Extension UI gets permanently stuck in "Captioning" state on WebSocket drop or server offline

- Session: phase-1 gate
- Suggested severity: HIGH

What I did: Clicked "Start Captioning" in Chrome extension when local relay server was offline, or killed local relay server while captioning.
Expected: Offscreen script catches connection error/close, notifies background worker and popup, stops audio capture, and resets extension popup UI to "Start Captioning" with an error status.
Actual: offscreen.js ws.onerror and ws.onclose only log to console and do not notify background.js or popup.js. Offscreen document continues capturing tab audio endlessly, background.js retains isCapturing = true, and popup UI remains permanently stuck in "Status: Captioning..." and "Stop Captioning" state.

Disposition: ACCEPTED -> DEF-005

## ADV-004: Extension offscreen capture initialization uses race-prone hardcoded 200ms delay

- Session: phase-1 gate
- Suggested severity: MEDIUM

What I did: Inspected background.js lines 32-39 during audio capture initialization.
Expected: Service worker waits for offscreen document to confirm ready state via message/event before dispatching startCapture.
Actual: background.js uses setTimeout(() => { chrome.runtime.sendMessage({ action: 'startCapture', ... }) }, 200). If document creation takes longer than 200ms due to system load, startCapture message is lost before listener registers. Extension state becomes isCapturing = true but audio capture never starts.

Disposition: ACCEPTED -> DEF-006

## ADV-005: Extension audio WebSocket opened before media stream acquisition leads to hung sessions

- Session: phase-1 gate
- Suggested severity: MEDIUM

What I did: Inspected offscreen.js startCapture function. Simulated navigator.mediaDevices.getUserMedia failure (e.g. user denied tab capture permission or tab closed).
Expected: If tab capture fails, open WebSocket should be closed and error reported to service worker.
Actual: ws = new WebSocket('ws://localhost:8765') is created before getUserMedia() is called. When getUserMedia() throws an error, catch block logs error but leaves ws open in background. Extension remains stuck in isCapturing = true with a silent hung WebSocket connection.

Disposition: ACCEPTED -> DEF-007

## ADV-006: Multiple concurrent client connections on Local Relay Server corrupt UI overlay and misreport status

- Session: phase-1 gate
- Suggested severity: MEDIUM

What I did: Connected two extension clients/tabs simultaneously to local relay server (ws://localhost:8765), streamed audio from both, then disconnected Client 1 while Client 2 was still active.
Expected: Relay server handles connections cleanly or enforces single-session lock without mixing transcriptions or setting incorrect global status.
Actual: Transcriptions from both clients are emitted to the same PyQt overlay window, interleaving and overwriting captions. When Client 1 disconnects, finally block emits status "Disconnected from extension", setting UI status to disconnected even though Client 2 is still actively streaming.

Disposition: ACCEPTED -> DEF-008

## ADV-007: RelayServer logs misleading status "Disconnected from extension" when remote STT server drops connection

- Session: phase-1 gate
- Suggested severity: LOW

What I did: Connected extension through local relay server to remote STT server, then terminated remote STT server process mid-stream.
Expected: Relay server UI signal and logs indicate remote STT connection dropped (e.g., "Remote STT server disconnected").
Actual: RelayServer.handle_client in client/main.py catches remote disconnect in finally and emits self.signal_bridge.status_changed.emit("Disconnected from extension."), giving misleading diagnostic feedback.

Disposition: ACCEPTED -> DEF-009

## ADV-008: Transparent Overlay UI renders unescaped HTML tags in transcriptions

- Session: phase-1 gate
- Suggested severity: LOW

What I did: Sent transcription text containing HTML tags (e.g. <h1 style="color:red">HACKED</h1> or <speaker 1>) to overlay window.
Expected: Text rendered as plain escaped text on overlay label.
Actual: QLabel in Qt interprets text containing HTML tags as rich text formatting, modifying font sizes, colors, or structure on the overlay window.
Screenshot: screenshots/adv-008.png

Disposition: ACCEPTED -> DEF-010

## ADV-009: Long transcriptions vertically overflow fixed 140px overlay window

- Session: phase-1 gate
- Suggested severity: LOW

What I did: Sent multi-line or long (500+ char) caption text to overlay window.
Expected: Overlay window resizes or wraps text cleanly without clipping bottom lines.
Actual: client/main.py hardcodes window height to height = 140. When multi-line captions exceed 140px in total height, the bottom lines of text are clipped off the bottom edge of the overlay window.
Screenshot: screenshots/adv-009.png

Disposition: ACCEPTED -> DEF-011

## ADV-010: Overlay window displays empty dark background box during silence after clearing text

- Session: phase-1 gate
- Suggested severity: LOW

What I did: Triggered caption clear via 10-second silence timer _clear_caption().
Expected: Overlay window becomes completely transparent or hidden during silence.
Actual: _clear_caption() sets label.setText(""), but QLabel stylesheet padding and background (rgba(18, 18, 24, 0.82)) remain visible as a dark empty box floating on screen.
Screenshot: screenshots/adv-010.png
