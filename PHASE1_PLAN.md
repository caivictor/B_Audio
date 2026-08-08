# Phase 1 Plan

## Goal
Prove the end-to-end pipeline works for a single speaker in their native language.

## API Contract (WebSocket)

### 1. Browser Extension -> Local Client (PyQt6)
- **Endpoint:** `ws://localhost:8765`
- **Initialization:** First message sent upon connection is a JSON config:
  `{"type": "config", "language": "es"}` (language code chosen by user)
- **Audio Stream:** Subsequent messages are binary blobs containing 16kHz mono PCM audio chunks (e.g., ~1 second chunks).

### 2. Local Client -> Remote STT Server (FastAPI)
- **Endpoint:** `ws://127.0.0.1:8000/transcribe` (Local testing address; prod is 192.168.0.30)
- **Initialization:** Forwards the JSON config:
  `{"type": "config", "language": "es"}`
- **Audio Stream:** Forwards the binary 16kHz mono PCM audio chunks.
- **Response (Server -> Client):** JSON messages containing transcription text:
  `{"text": "Hola, ¿cómo estás?"}`

## Task Spec: frontend-dev
- **Scope:** Chrome Extension (`extension/`) + Local Client & UI (`client/`).
- **Extension (Manifest V3):**
  - Popup UI with language selector and "Start Captioning" button.
  - `background.js` or offscreen document to handle `chrome.tabCapture`, process audio via `AudioContext` into 16kHz mono PCM, and stream to `ws://localhost:8765`.
- **Local Client (Python 3.12+, PyQt6, websockets):**
  - Listen on `ws://localhost:8765`.
  - Forward messages to `ws://127.0.0.1:8000/transcribe`.
  - Render a frameless, transparent, "always-on-top", click-through window displaying the text received from the server.
- **Verification:** Run the PyQt6 app (use a mock server if needed), capture screenshots, ensure the overlay is transparent and frameless. Update `README.md` for both components.

## Task Spec: backend-dev
- **Scope:** Remote STT Server (`server/`).
- **Tech:** Python 3.12+, FastAPI, `faster-whisper`, `websockets`.
- **Functionality:** 
  - Expose `ws://127.0.0.1:8000/transcribe`.
  - Parse the initial config JSON, instantiate or configure the `faster-whisper` model.
  - Continuously receive binary PCM chunks, transcribe them, and send back `{"text": "..."}` JSON.
- **Verification:** Use a smaller model (e.g., `tiny` or `base`) to ensure it runs during testing. Write a basic unit test or test script. Update `README.md` with setup instructions.
