# Remote Speech-to-Text (STT) Server

FastAPI WebSocket service powered by `faster-whisper` for low-latency real-time audio transcription.

## Features

- **WebSocket Endpoint (`/transcribe`)**: Accepts JSON configuration messages and streams 16kHz mono PCM binary audio chunks.
- **`faster-whisper` Integration**: Fast Whisper inference supporting configurable model sizes (`tiny`, `base`, `large-v3`, etc.) and compute backends (`cuda`, `cpu`).
- **Real-Time Streaming**: Returns JSON `{"text": "..."}` responses containing transcribed text as audio is processed.
- **Health Check Endpoint (`/health`)**: Reports server status and current model configuration.

## Requirements

- Python 3.12+
- PyTorch / CUDA (for GPU acceleration on RTX 4080 / NVIDIA GPUs) or CPU

## Installation

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r server/requirements.txt
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `tiny` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `WHISPER_DEVICE` | `auto` | Execution device (`auto`, `cuda`, `cpu`) |
| `WHISPER_COMPUTE_TYPE` | `default` | Precision (`default`, `float16`, `int8`, `float32`) |
| `HOST` | `0.0.0.0` | Host interface to bind to |
| `PORT` | `8000` | Port number to bind to |
| `MAX_BUFFER_SECONDS` | `30` | Sliding window audio buffer history limit in seconds |

For production on GPU (e.g., RTX 4080 at 192.168.0.30):

```bash
export WHISPER_MODEL=large-v3
export WHISPER_DEVICE=cuda
export WHISPER_COMPUTE_TYPE=float16
```

## Running the Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Or using python module:

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

## Running Unit Tests

To run the backend unit tests:

```bash
pytest server/tests/
```

## Verification / Test Client

To test the WebSocket connection and transcription stream with a test script:

```bash
python server/test_client.py
```

## API Contract (WebSocket)

- **Endpoint**: `ws://<host>:<port>/transcribe`
- **Initial Configuration (Text Message)**:
  ```json
  {"type": "config", "language": "es", "task": "transcribe"}
  ```
- **Audio Stream (Binary Messages)**:
  Raw 16kHz mono 16-bit PCM binary chunks.
- **Response (Server -> Client)**:
  ```json
  {"text": "Hola, ¿cómo estás?"}
  ```
