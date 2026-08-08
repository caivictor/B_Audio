# WebCaptioner / Personal Space

Real-time browser audio transcription & translation application.

## Components

- `client/`: Local Client & UI (PyQt6 transparent overlay)
- `extension/`: Chrome Extension for tab audio capture (Manifest V3)
- `server/`: Remote STT Server (FastAPI + `faster-whisper` + WebSockets)

---

## 1. Quick Start — Local Client UI (`client/`)

### Setup & Prerequisites (Linux / Ubuntu 24.04)

1. Ensure Python 3.12+ and system Qt dependencies are installed:
   ```bash
   sudo apt update
   sudo apt install -y python3.12 python3.12-venv libxcb-cursor0
   ```

2. Create virtual environment and install dependencies:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install pyqt6 websockets pytest pytest-qt pytest-asyncio
   ```

### Running the Local Client UI

Launch the PyQt6 transparent subtitle overlay:
```bash
# Standard mode (connects to local relay at ws://localhost:8765 and remote STT at ws://127.0.0.1:8000/transcribe)
python3 client/main.py

# Standalone testing mode with built-in mock STT server (no GPU server required)
python3 client/main.py --mock-server
```

### Running Client Unit Tests

```bash
PYTHONPATH=. pytest tests/
```

---

## 2. Quick Start — Chrome Extension (`extension/`)

### Installation (Google Chrome / Chromium)

1. Open Google Chrome and navigate to `chrome://extensions`.
2. Enable **Developer mode** using the toggle switch in the top right corner.
3. Click **Load unpacked**.
4. Select the `extension/` folder from this repository.

### Usage

1. Open a Chrome tab playing media (e.g., YouTube or live stream).
2. Click the **WebCaptioner** extension icon in the toolbar.
3. Select the source language (e.g. `Spanish (es)`).
4. Click **Start Captioning**.
5. The local client overlay will receive audio chunks and display real-time captions on screen.
6. Click **Stop Captioning** when finished.

---

## 3. Quick Start — Remote STT Server (`server/`)

1. Set up virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r server/requirements.txt
   ```

2. Start the Remote STT Server:
   ```bash
   uvicorn server.main:app --host 0.0.0.0 --port 8000
   ```

3. Run server unit tests and verification script:
   ```bash
   pytest server/tests/
   python server/test_client.py
   ```

See [`server/README.md`](server/README.md) for full server details and configuration options.
