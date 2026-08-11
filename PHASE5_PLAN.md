# Phase 5 Plan

## Goal
Allow users to save their captioned sessions as a downloaded transcript.

## API Contract (WebSocket)
- The backend currently sends: `{"text": "[Speaker 1]: Hello"}`
- **Updated Payload:** The backend will now include the chunk's start and end timestamps (relative to the session start in seconds):
  `{"text": "[Speaker 1]: Hello", "start": 1.5, "end": 4.2}`

## Task Spec: frontend-dev
- **Scope:** Extension (`extension/`).
- **Implementation:** 
  - Update `extension/background.js` to maintain an array of transcript history for the current session (e.g., `let transcriptHistory = []`). Append incoming `captionText` messages (with their timestamps) to this array.
  - Add a "Download Transcript" button to `extension/popup.html`.
  - In `extension/popup.js`, when the button is clicked, fetch the history from `background.js`, format it beautifully as a `.txt` file (e.g., `[00:01.500 --> 00:04.200] [Speaker 1]: Hello`), and trigger a browser download using a Blob and URL.createObjectURL.
- **Verification:** Unit tests for downloading/formatting.
- **Git:** Branch `feature/phase5-frontend`, push, create PR.

## Task Spec: backend-dev
- **Scope:** Remote STT Server (`server/stt.py` and `server/main.py`).
- **Implementation:** 
  - Update `STTService.transcribe` to return a dictionary or tuple containing the text, start time, and end time of the processed chunk. The Whisper segments (`s.start`, `s.end`) hold these times. Add the chunk's base offset to make the timestamps relative to the start of the entire session.
  - Update `server/main.py` to send `{"text": text, "start": abs_start, "end": abs_end}` over the WebSocket.
- **Verification:** Update unit tests to verify the JSON payload contains `start` and `end` floats.
- **Git:** Branch `feature/phase5-backend`, push, create PR.