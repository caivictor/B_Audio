
## DEF-023: Unclear UI error when starting capture on restricted tabs
- Status: CLOSED
- Severity: LOW
- Found by: User UAT
- Phase: 1

Steps to reproduce:
1. Open a restricted page (e.g., chrome://extensions, a blank New Tab, or Chrome Settings).
2. Click the extension popup and hit "Start Captioning".

Expected: The UI explains that this tab cannot be captured.
Actual: The UI confusingly displays "Status: Failed to start" with no context, leading users to believe the STT session crashed.

History:
- qa: opened
- frontend-dev: FIX READY - Updated `extension/popup.js` to append `response.error` from Chrome's `runtime.lastError` to the UI label.
- qa: CLOSED - Verified restricted tabs now display descriptive messages like "Failed to start (Cannot capture a chrome:// URL)".

## DEF-020: Overlay box is not draggable on Wayland
- Status: CLOSED
- Severity: MEDIUM
- Found by: User UAT
- Phase: 2

Steps to reproduce:
1. Run local client on Ubuntu 24.04 (Wayland).
2. Attempt to click and drag the overlay window.

Expected: Overlay moves with the mouse.
Actual: Window ignores move events because absolute positioning is blocked by Wayland compositor.

History:
- qa: opened
- frontend-dev: FIX READY - Switched to windowHandle().startSystemMove() for native OS window dragging.
- qa: CLOSED - Verified draggable across X11 and Wayland.

## DEF-021: Speaker tags do not start on new lines
- Status: CLOSED
- Severity: LOW
- Found by: User UAT
- Phase: 4

Steps to reproduce:
1. Stream audio with two speakers.
2. Observe overlay UI formatting.

Expected: Each speaker starts on a new line for readability.
Actual: Transcriptions append as a single continuous string (e.g. `[Speaker 1] xxx. [Speaker 2] yyy.`)

History:
- qa: opened
- frontend-dev: FIX READY - Updated `parse_speaker_tags` in `client/main.py` to prefix new speaker tags with `<br>`.
- qa: CLOSED - Verified multi-speaker captions stack vertically.

## DEF-022: Excessive translation latency and audio desync on CPU
- Status: CLOSED
- Severity: HIGH
- Found by: User UAT
- Phase: 3

Steps to reproduce:
1. Start GPU-less or VRAM-starved remote server (falls back to CPU).
2. Start Japanese to English translation streaming.
3. Observe subtitle sync.

Expected: Latency < 2-3 seconds.
Actual: The text log lags many seconds behind the video and progressively gets worse over time.

History:
- qa: opened
- backend-dev: FIX READY - Reduced MAX_BUFFER_SECONDS from 30 to 10. Added `condition_on_previous_text=False` to speed up Whisper CPU inference. Implemented aggressive WebSocket receive queue draining in `server/main.py` to catch up when CPU thread lags behind the chunk rate.
- qa: CLOSED - Verified translation sync recovers and stays near real-time on CPU.
## DEF-019: Modulo index fallback assigns identical highlight colors to different speakers

- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-016)
- Phase: 3

Steps to reproduce:
1. Launch `client/main.py` overlay window.
2. Send transcription text containing speaker tags for Speakers 3 and 5 (`[Speaker 3]: ... [Speaker 5]: ...`) or Speakers 4 and 6 to the overlay window.
3. Observe assigned text highlight colors for each speaker.

Expected: Each speaker receives a visually distinct color code from the palette.
Actual: `get_speaker_color` in `client/main.py` computes fallback color index using `sum(ord(c) for c in clean_id) % len(DEFAULT_PALETTE)`. For Speaker 5, the ASCII sum 796 modulo 6 yields index 2 (`#99ff99`), which is identical to Speaker 3 (`#99ff99`). Similarly, Speaker 6 evaluates to index 3 (`#ffcc99`), identical to Speaker 4. Speakers 3 and 5 (and Speakers 4 and 6) render in identical colors, making them indistinguishable.
Screenshot: screenshots/adv-014.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Expanded SPEAKER_COLORS palette for up to 10 unique speakers without collisions.
- qa: retested get_speaker_color for Speakers 1 through 10, verified unique hex colors across all 10 speakers (Speaker 3=#99ff99, Speaker 5=#cc99ff, Speaker 4=#ffcc99, Speaker 6=#ffff99), captured and inspected screenshots/def-019_speaker_colors.png, regression tested overlay speaker tag parsing, closed

## DEF-018: Global STTService instance contaminates speaker diarization state across concurrent client sessions

- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-015)
- Phase: 3

Steps to reproduce:
1. Start `server/main.py` STT server on port 8000.
2. Connect two WebSocket clients simultaneously to `/transcribe` endpoint and stream audio from both clients.
3. Observe speaker diarization state across both sessions.

Expected: Each client WebSocket session maintains its own isolated speaker diarization state.
Actual: `stt_service` in `server/stt.py` is instantiated as a global singleton. Calling `reset_speaker()` or `transcribe()` on new connection or incoming audio mutates global attributes (`current_speaker`, `last_audio_had_speech`, `last_segment_end_time`). Concurrent client streams continuously overwrite each other's speaker history, corrupting speaker tracking across sessions.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Manage per-connection SpeakerState instances for concurrent session speaker isolation.
- qa: retested concurrent client SpeakerState instances, verified session 1 state changes do not affect session 2, regression tested WebSocket /transcribe session lifecycle and reset_speaker logic, closed

## DEF-017: Streaming Speaker Diarization pause-threshold calculation compares incompatible timebases across audio chunks

- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-014)
- Phase: 3

Steps to reproduce:
1. Start `server/main.py` STT server on port 8000.
2. Stream two consecutive audio chunks separated by a pause over WebSocket to `/transcribe`.
3. Observe speaker diarization labels in transcription output.

Expected: When a pause exceeding `pause_threshold_sec` (0.4s) occurs between audio chunks, speaker diarization toggles the active speaker label (e.g., from Speaker 1 to Speaker 2).
Actual: `STTService.transcribe` in `server/stt.py` calculates pause duration as `s.start - self.last_segment_end_time`, where `s.start` is the offset in the current chunk buffer (e.g. 0.2s) and `last_segment_end_time` is the offset in the previous chunk buffer (e.g. 2.5s). Subtracting a previous chunk offset from a current chunk offset results in a negative value (e.g. -2.3s), which fails the `>= 0.4` check. Pause detection across streaming chunks never fires, leaving speaker diarization permanently stuck on a single speaker.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Updated server/stt.py to track trailing chunk durations for accurate pause threshold calculation.
- qa: retested pause duration tracking across consecutive streaming audio chunks with trailing silence, verified pause >= 0.4s toggles active speaker label to Speaker 2, regression tested single-chunk and multi-chunk transcriptions, closed

## DEF-016: Multi-line speaker transcriptions separated by newlines lose line breaks when rendered in StrokedLabel

- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-013)
- Phase: 3

Steps to reproduce:
1. Launch `client/main.py` overlay window.
2. Send multi-speaker transcription text containing explicit newlines (e.g. `[Speaker 1]: First line of speech / [Speaker 2]: Second line of speech`) to the overlay window.
3. Observe line rendering on the overlay window.

Expected: Each speaker's dialogue renders on its own separate line in the overlay window.
Actual: `parse_speaker_tags` wraps each speaker segment in HTML `<span>` tags preserving the newline character. However, when `QTextDocument.setHtml` parses the HTML string in `StrokedLabel.paintEvent`, HTML whitespace collapsing rules convert newlines to a single space. The newlines are lost, and all speaker lines are merged onto a single horizontal line.
Screenshot: screenshots/adv-013.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Converts newlines to <br> for multi-line rich text rendering.
- qa: retested multi-speaker transcriptions separated by newlines, verified parse_speaker_tags converts \n to <br> and renders dialogue on separate lines, captured and inspected screenshots/def-016_multiline.png, regression tested single-line speaker tags, closed

## DEF-015: Transcriptions without speaker tags containing angle brackets (<...>) have contents inside brackets erased by RichText parsing in StrokedLabel

- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-012)
- Phase: 3

Steps to reproduce:
1. Launch `client/main.py` overlay window.
2. Send transcription text without speaker tags containing angle brackets (e.g. `Comparing values: 5 < 10 and 20 > 15 in transcription text.` or Whisper non-speech markers like `<music>` or `<applause>`) to the overlay window.
3. Observe the displayed text on the overlay window.

Expected: The text is safely escaped or rendered verbatim, preserving all characters including `<` and `>`.
Actual: `parse_speaker_tags` returns raw text when no speaker tags match. In `StrokedLabel.paintEvent`, line 140 checks `is_rich = self.textFormat() == Qt.TextFormat.RichText or ("<" in text and ">" in text)`, setting `is_rich` to True. `re.sub(r'<[^>]*>', '', text)` strips the contents inside `<...>`, and `QTextDocument.setHtml` ignores the unknown HTML tag, causing text between `<` and `>` (e.g. `10 and 20`) to be completely deleted from the overlay display.
Screenshot: screenshots/adv-012.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Removed forced rich text detection so PlainText format preserves angle brackets.
- qa: retested transcriptions without speaker tags containing angle brackets (<...> and <music>), verified PlainText format preserves angle brackets and text inside brackets verbatim, captured and inspected screenshots/def-015_angle_brackets.png, regression tested rich text speaker tags, closed

## DEF-014: Bold speaker tag formatting causes stroke outline text to wrap at different word boundaries than foreground rich text in StrokedLabel

- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-011)
- Phase: 3

Steps to reproduce:
1. Launch `client/main.py` overlay window with constrained width (e.g. 260px).
2. Send transcription text containing speaker tags (e.g. `[Speaker 1]: Hello everyone welcome to our demonstration today of real time captioning.`) to the overlay window.
3. Observe text wrapping and alignment of stroke outline versus foreground text.

Expected: The black stroke outline text and the colored foreground text wrap at the exact same word boundaries, maintaining a tight, readable outline around all words.
Actual: `StrokedLabel.paintEvent` computes stroke text layout using unstyled plain text (`painter.drawText`) while computing foreground text layout using HTML rich text (`QTextDocument`) containing bold speaker tags (`<b>[Speaker 1]:</b>`). Because bold font metrics make `[Speaker 1]:` wider in rich text, `QTextDocument` wraps words to line 2 earlier than `painter.drawText`. The black stroke outline text and foreground colored text wrap on different words, causing the black stroke outline to detach and misalign from the foreground text on screen.
Screenshot: screenshots/adv-011.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Updated StrokedLabel to use a matching QTextDocument layout for rich text stroke outlines, aligning word wraps.
- qa: retested StrokedLabel rich text rendering with bold speaker tags on constrained width (260px), verified stroke outline QTextDocument layout matches foreground rich text layout and word wrap boundaries, captured and inspected screenshots/def-014_bold_stroke.png, regression tested plain text stroke outline rendering, closed

## DEF-013: Local Client mock STT server ignores task parameter in config JSON and returns untranslated source text

- Status: CLOSED
- Severity: LOW
- Found by: qa
- Phase: 3

Steps to reproduce:
1. Launch `run_mock_stt_server` on port 8000 (or via client `main.py --mock-server`).
2. Connect a WebSocket client to `ws://127.0.0.1:8000/transcribe`.
3. Send JSON config `{"type": "config", "language": "es", "task": "translate"}`.
4. Send binary PCM audio chunk over WebSocket connection.
5. Observe response text returned by mock STT server.

Expected: `run_mock_stt_server` parses `task: "translate"` and returns English translation sample text ("Hello, welcome to the demonstration.").
Actual: `run_mock_stt_server` in `client/main.py` only inspects `language` in config data and ignores `task`. When `language: "es"` and `task: "translate"` are set, it returns untranslated Spanish text ("Hola, bienvenidos a la demostración.").

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of frontend-dev: FIX READY — Updated `run_mock_stt_server` in `client/main.py` to parse the `task` parameter in JSON config messages and return English translation text when `task == "translate"`.
- qa: retested run_mock_stt_server with task="translate" and language="es", verified English translation sample text returned, regression tested dynamic mid-session task switching between "translate" and "transcribe", closed

## DEF-012: Overlay window displays empty dark background box during silence after clearing text

- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-010)
- Phase: 1

Steps to reproduce:
1. Launch `client/main.py` transparent overlay window with active caption displayed.
2. Wait for 10-second silence timer `_clear_caption()` to trigger.
3. Observe overlay window appearance on screen.

Expected: Overlay window becomes completely transparent or hidden during silence.
Actual: `_clear_caption()` sets `label.setText("")`, but `QLabel` stylesheet padding and background (`rgba(18, 18, 24, 0.82)`) remain visible as a dark empty box floating on screen.
Screenshot: screenshots/adv-010.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Modified `_clear_caption()` and `set_caption_text()` in `client/main.py` to toggle `self.label.setVisible(False)` when text is empty, hiding stylesheet background and border boxes during silence.
- qa: retested _clear_caption() and label visibility toggling, inspected screenshots/def-012_cleared_silence.png, closed

## DEF-011: Long transcriptions vertically overflow fixed 140px overlay window

- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-009)
- Phase: 1

Steps to reproduce:
1. Launch `client/main.py` transparent overlay window.
2. Send multi-line or long (500+ char) caption text to the overlay window.
3. Observe text rendering and window dimensions.

Expected: Overlay window resizes or wraps text cleanly without clipping bottom lines.
Actual: `client/main.py` hardcodes window height to `height = 140`. When multi-line captions exceed 140px in total height, the bottom lines of text are clipped off the bottom edge of the overlay window.
Screenshot: screenshots/adv-009.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Added `_update_geometry()` to `TransparentOverlayWindow` (`client/main.py`) to dynamically adjust window height based on text content hint to accommodate multi-line captions without clipping.
- qa: retested long caption rendering with multi-line text; inspected screenshots/def-011_long_text.png and found top and bottom text lines are still clipped because sizeHint().height() doesn't calculate wrapped label height (heightForWidth), reopened
- orchestrator: marked FIX-READY on behalf of frontend-dev: FIX READY — Updated `TransparentOverlayWindow._update_geometry()` in `client/main.py` to calculate the required wrapped label height using `self.label.heightForWidth(label_width)` and enforce it with `self.setFixedHeight(req_height)` using `not self.label.isHidden()` visibility checks.
- qa: retested long caption multi-line wrapping and dynamic window height calculation; verified heightForWidth height expansion and inspected screenshots/def-011_long_text.png, regression tested clear and short text transitions, closed

## DEF-010: Transparent Overlay UI renders unescaped HTML tags in transcriptions

- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-008)
- Phase: 1

Steps to reproduce:
1. Launch `client/main.py` transparent overlay window.
2. Send transcription text containing HTML tags (e.g. `<h1 style="color:red">HACKED</h1>` or `<speaker 1>`) to the overlay window.
3. Observe text rendered on the overlay window.

Expected: Text rendered as plain escaped text on overlay label.
Actual: `QLabel` in Qt interprets text containing HTML tags as rich text formatting, modifying font sizes, colors, or structure on the overlay window.
Screenshot: screenshots/adv-008.png

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Set `self.label.setTextFormat(Qt.TextFormat.PlainText)` on `TransparentOverlayWindow` in `client/main.py` to render raw HTML tags in transcriptions as literal plain text.
- qa: retested QLabel plain text formatting with unescaped HTML tags, inspected screenshots/def-010_plain_text.png, closed

## DEF-009: RelayServer logs misleading status "Disconnected from extension" when remote STT server drops connection

- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-007)
- Phase: 1

Steps to reproduce:
1. Launch `client/main.py` relay server connected to remote STT server.
2. Connect Chrome extension to local relay server and start captioning.
3. Terminate remote STT server process mid-stream.

Expected: Relay server UI signal and logs indicate remote STT connection dropped (e.g., "Remote STT server disconnected").
Actual: `RelayServer.handle_client` in `client/main.py` catches remote disconnect in `finally` and emits `self.signal_bridge.status_changed.emit("Disconnected from extension.")`, giving misleading diagnostic feedback.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Updated `RelayServer` (`client/main.py`) to track disconnect sources and emit `"Remote STT server disconnected."` when remote STT connections drop.
- qa: retested RelayServer disconnect tracking when remote STT closes, verified 'Remote STT server disconnected' status, closed

## DEF-008: Multiple concurrent client connections on Local Relay Server corrupt UI overlay and misreport status

- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-006)
- Phase: 1

Steps to reproduce:
1. Launch `client/main.py` relay server and overlay window.
2. Connect two extension clients/tabs simultaneously to local relay server (`ws://localhost:8765`).
3. Stream audio from both clients, then disconnect Client 1 while Client 2 is still actively streaming.

Expected: Relay server handles connections cleanly or enforces single-session lock without mixing transcriptions or setting incorrect global status.
Actual: Transcriptions from both clients are emitted to the same PyQt overlay window, interleaving and overwriting captions. When Client 1 disconnects, `finally` block emits status "Disconnected from extension", setting UI status to disconnected even though Client 2 is still actively streaming.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Added single-session lock (`self.active_client`) in `RelayServer` (`client/main.py`) to reject concurrent client connections with close code 1008 and preserve active stream integrity and UI status.
- qa: retested RelayServer single-session lock and rejection of concurrent client connections with code 1008, closed

## DEF-007: Extension audio WebSocket opened before media stream acquisition leads to hung sessions

- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-005)
- Phase: 1

Steps to reproduce:
1. Open Chrome with WebCaptioner extension loaded.
2. Click "Start Captioning" in an environment where `navigator.mediaDevices.getUserMedia` fails (e.g., tab capture permission denied or tab closed).
3. Inspect offscreen script background WebSocket connections.

Expected: If tab audio capture fails, open WebSocket should be closed and error reported to service worker.
Actual: `ws = new WebSocket("ws://localhost:8765")` is created before `getUserMedia()` is called in `offscreen.js`. When `getUserMedia()` throws an error, catch block logs error but leaves WebSocket connection open in background, leaving extension stuck in `isCapturing = true` with a silent hung WebSocket connection.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Updated `extension/offscreen.js` `startCapture()` to acquire the tab `MediaStream` prior to instantiating the WebSocket connection, catching stream errors and stopping capture cleanly.
- qa: retested acquiring MediaStream before WebSocket instantiation in offscreen script, verified error catching, closed

## DEF-006: Extension offscreen capture initialization uses race-prone hardcoded 200ms delay

- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-004)
- Phase: 1

Steps to reproduce:
1. Open Chrome with WebCaptioner extension loaded.
2. Click "Start Captioning" under heavy system load or slow offscreen document creation.
3. Inspect `background.js` execution flow during offscreen document setup.

Expected: Service worker waits for offscreen document to confirm ready state via message/event before dispatching `startCapture`.
Actual: `background.js` uses `setTimeout(() => { chrome.runtime.sendMessage({ action: "startCapture", ... }) }, 200)`. If document creation takes longer than 200ms, `startCapture` message is lost before listener registers. Extension state becomes `isCapturing = true` but audio capture never starts.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Replaced race-prone `setTimeout(200)` delay in `extension/background.js` with event-driven synchronization using an `offscreenReady` initialization message sent from `extension/offscreen.js`.
- qa: retested event-driven offscreenReady synchronization between offscreen document and background worker, closed

## DEF-005: Extension UI gets permanently stuck in "Captioning" state on WebSocket drop or server offline

- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-003)
- Phase: 1

Steps to reproduce:
1. Open Chrome with WebCaptioner extension loaded.
2. Ensure local relay server is offline (or kill local relay server process while captioning is active).
3. Click "Start Captioning" in Chrome extension popup.

Expected: Offscreen script catches connection error or close event, notifies background worker and popup, stops audio capture, and resets extension popup UI to "Start Captioning" with an error status.
Actual: `offscreen.js` `ws.onerror` and `ws.onclose` handlers only log to console and do not notify `background.js` or `popup.js`. Offscreen document continues capturing tab audio endlessly, `background.js` retains `isCapturing = true`, and popup UI remains permanently stuck in "Status: Captioning..." and "Stop Captioning" state.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Added WebSocket close/error handling in `extension/offscreen.js` to trigger `stopCapture()` and dispatch `captureStopped` messages to `background.js` and `popup.js`, resetting state and returning popup UI to "Start Captioning".
- qa: retested offscreen WebSocket error and close handlers, verified captureStopped broadcast and popup state reset, closed

## DEF-004: Odd-length binary audio message permanently corrupts 16-bit PCM sample alignment

- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-002)
- Phase: 1

Steps to reproduce:
1. Start `server/main.py` on port 8000.
2. Connect a WebSocket client to `ws://127.0.0.1:8000/transcribe`.
3. Send an odd-length binary audio message (e.g. 1 byte or 1001 bytes).
4. Send subsequent standard 16-bit PCM binary audio chunks.

Expected: Server trims or discards leftover odd bytes when processing chunks so that future chunks maintain proper 2-byte 16-bit PCM sample alignment.
Actual: `server/main.py` computes `valid_len = len(audio_buffer) - (len(audio_buffer) % 2)` and converts `audio_buffer[:valid_len]` to `np.int16`, but leaves remaining 1 byte at index 0 of `audio_buffer`. Every subsequent 2-byte sample added to `audio_buffer` becomes byte-swapped (high and low bytes inverted), permanently corrupting all transcriptions for the rest of the session with static noise.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Trimmed trailing odd bytes on incoming binary audio chunks and copied byte buffers in `server/main.py` so future 16-bit PCM chunks remain 2-byte aligned without buffer export lock errors.
- qa: retested odd-length binary audio chunk alignment trimming and buffer copying, verified PCM byte alignment, closed

## DEF-003: Unsupported language or task string in JSON config crashes remote STT WebSocket session

- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-001)
- Phase: 1

Steps to reproduce:
1. Start `server/main.py` (or mock STT server) on port 8000.
2. Connect a WebSocket client to `ws://127.0.0.1:8000/transcribe`.
3. Send JSON config message `{"type": "config", "language": "english"}` or `{"type": "config", "language": "invalid_lang"}` (instead of 2-letter ISO code like `en`).
4. Send a binary audio chunk over the WebSocket connection.

Expected: Server validates language string, falls back gracefully or ignores invalid language code, and continues servicing the WebSocket connection.
Actual: `faster_whisper` raises unhandled `ValueError: "invalid_lang" is not a valid language code`. The exception escapes the transcription loop in `server/main.py` and crashes the entire WebSocket session immediately.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of developer: FIX READY — Validated language and task codes against faster-whisper supported sets with fallback to auto-detection/transcribe and exception handling in `server/stt.py` and `server/main.py`.
- qa: retested server language/task input validation and fallback handling with invalid language/task config strings, closed

## DEF-002: Local Client mock STT server ignores mid-session JSON config updates

- Status: CLOSED
- Severity: LOW
- Found by: qa
- Phase: 1

Steps to reproduce:
1. Start `run_mock_stt_server` on port 8000.
2. Connect a WebSocket client to `ws://127.0.0.1:8000/transcribe`.
3. Send initial JSON config `{"type": "config", "language": "es"}`.
4. Send an audio chunk and observe response in Spanish.
5. Send an updated JSON config `{"type": "config", "language": "en"}` on the same active connection.
6. Send another audio chunk and observe response.

Expected: The mock STT server updates its active language configuration to English for subsequent responses (matching server/main.py behavior).
Actual: The mock STT server only reads configuration once on connection startup and ignores mid-session JSON config updates, continuing to return Spanish responses.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of frontend-dev: FIX READY — Updated `run_mock_stt_server` in `client/main.py` to parse JSON config messages dynamically inside the websocket message loop and update language configuration mid-session without returning audio response frames for config messages.
- qa: retested run_mock_stt_server mid-session JSON config updates, verified dynamic language switching, closed

## DEF-001: Backend test client server/test_client.py fails under pytest due to missing async decorator

- Status: CLOSED
- Severity: LOW
- Found by: qa
- Phase: 1

Steps to reproduce:
1. Open terminal at project root.
2. Run `.venv/bin/pytest`.
3. Observe test execution output.

Expected: All unit tests collected by pytest execute and pass cleanly.
Actual: `server/test_client.py::test_stt_websocket` fails with error "Failed: async def function... async def functions are not natively supported" because the test function lacks `@pytest.mark.asyncio`.

History:
- qa: opened
- orchestrator: marked FIX-READY on behalf of backend-dev: FIX READY — Added `@pytest.mark.asyncio` decorator to `test_stt_websocket()` in `server/test_client.py` and handled offline STT server connections.
- qa: retested pytest execution of server/test_client.py, passes cleanly with @pytest.mark.asyncio, closed

