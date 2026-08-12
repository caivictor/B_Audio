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

Disposition: PENDING

## ADV-011: Disconnect during WebSocket receive drain loop in server/main.py triggers unhandled Starlette RuntimeError

- Session: final
- Suggested severity: HIGH

What I did: Connected a WebSocket client to ws://127.0.0.1:8000/transcribe, sent a binary PCM audio chunk, and immediately closed the client connection while the server was draining incoming messages in server/main.py.
Expected: The receive loop detects websocket.disconnect, exits the receive drain loop cleanly, and closes the session without errors.
Actual: The while True drain loop in server/main.py receives {"type": "websocket.disconnect"}. Because the disconnect message lacks both "bytes" and "text" keys, the loop fails to break and calls websocket.receive() again. Starlette raises RuntimeError: Cannot call "receive" once a disconnect message has been received, dumping an unhandled exception in server logs.

Disposition: ACCEPTED -> DEF-039

## ADV-012: Speaker tags without trailing colons fail regex matching in Chrome extension content script

- Session: final
- Suggested severity: MEDIUM

What I did: Streamed transcription text containing speaker tags without trailing colons (e.g. [Speaker 1] Hello world or [Speaker A] Good morning) to the Chrome extension content script content.js.
Expected: Extension overlay matches speaker tags regardless of trailing colon presence (matching client/main.py behavior) and formats them with speaker color highlighting, bold styling, and line breaks.
Actual: content.js uses regex = /\[(Speaker\s*[^\]]+)\]:/gi with a mandatory trailing colon. Speaker tags lacking a colon fail to match, causing [Speaker 1] Hello world to render as plain white unformatted text without speaker color highlights or line breaks.

Disposition: ACCEPTED -> DEF-040

## ADV-013: Uncleared reconnect timer in offscreen.js spawns duplicate leaking WebSockets on rapid capture start/stop toggling

- Session: final
- Suggested severity: HIGH

What I did: Simulated a WebSocket connection drop in offscreen.js, then rapidly clicked "Stop Captioning" and "Start Captioning" in the extension popup within 1 second while the reconnect timer was pending.
Expected: Calling stopCapture() clears any pending reconnect setTimeout so that starting a new capture session creates exactly one active WebSocket connection.
Actual: ws.onclose schedules setTimeout for reconnection without saving the timer ID. stopCapture() does not clear the timer. When the 1-second timer fires, if (mediaStream) evaluates to true because the new session re-initialized mediaStream, opening a duplicate second WebSocket connection (ws = new WebSocket(...)) in parallel. Both WebSockets stream audio chunks simultaneously, corrupting server session state and triggering session lock rejection.

Disposition: ACCEPTED -> DEF-041

## ADV-014: Rapidly toggling settings or translation mid-stream dumps audio buffer and resets speaker diarization state

- Session: final
- Suggested severity: MEDIUM

What I did: Rapidly toggled the "Translate to English" checkbox or changed settings in the extension popup while streaming active audio.
Expected: Configuration updates change inference parameters for subsequent audio frames without discarding already-buffered PCM audio or resetting active speaker history.
Actual: When server/main.py receives a JSON type: "config" message mid-stream, it executes audio_buffer.clear() and session_speaker_state.reset(). Part-second PCM audio chunks currently in the buffer are immediately deleted (causing audio dropouts and missing words in transcripts), and speaker diarization state resets back to Speaker 1.

Disposition: ACCEPTED -> DEF-042

## ADV-015: Unbounded transcriptHistory array in background service worker causes memory growth and popup IPC latency

- Session: final
- Suggested severity: MEDIUM

What I did: Ran an extended audio captioning session producing thousands of transcript chunks, then clicked the extension icon to open the popup UI.
Expected: background.js maintains a capped sliding window for transcript history or pages response data to keep popup loading instantaneous.
Actual: background.js appends every captionText entry to transcriptHistory without size limits. When the popup opens and sends { action: 'getStatus' }, background.js serializes and transmits the entire unbounded history array across Chrome IPC, causing high background worker memory consumption and noticeable delay when opening the popup UI.

Disposition: ACCEPTED -> DEF-043

## ADV-016: Offscreen document ignores server keepalive ping messages and fails to respond with pong

- Session: final
- Suggested severity: LOW

What I did: Left the audio stream idle for longer than KEEPALIVE_TIMEOUT_SECONDS (60s) so server/main.py issued a {"type": "ping"} JSON message over the WebSocket connection.
Expected: offscreen.js receives the ping frame and responds with {"type": "pong"} to confirm bidirectional connection liveness.
Actual: ws.onmessage in offscreen.js parses message JSON but does not check for data.type === "ping". It ignores the message and sends no pong response, preventing proper keepalive heartbeat acknowledgment during extended quiet periods.

Disposition: ACCEPTED -> DEF-044

## ADV-017: Unbounded font size parameters in extension config cause overlay caption distortion

- Session: final
- Suggested severity: LOW

What I did: Dispatched a config update with an extreme font size value (e.g., fontSize: 200) via updateConfig message to extension/content.js.
Expected: content.js validates and clamps fontSize within readable subtitle bounds (e.g., 12px - 72px, matching PyQt client validation).
Actual: content.js applies textBg.style.fontSize = `${msg.fontSize}px` directly without bounds checking. Large font values cause the overlay box to swell beyond the viewport bounds, while small values make captions illegible.
Screenshot: screenshots/adv-017.png

Disposition: ACCEPTED -> DEF-045

## ADV-018: RelayServer handle_client leaves client WebSocket open after remote STT connection failure

- Session: final
- Suggested severity: LOW

What I did: Connected the Chrome extension to local RelayServer (ws://localhost:8765) while the remote STT server was offline or set to an invalid host (ws://invalid-host:9999).
Expected: After max connection retries fail, RelayServer sends a close frame to the extension WebSocket to inform it of the failure.
Actual: RelayServer.handle_client updates the UI status signal to Error connecting to STT server and returns from the function without explicitly calling await websocket.close(). The extension WebSocket is left in an unclosed state until function cleanup implicitly tears down the connection.

Disposition: ACCEPTED -> DEF-046
