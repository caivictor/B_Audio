"""
FastAPI application for Remote Speech-To-Text processing via WebSockets.
"""
import asyncio
import json
import logging
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from server.config import MAX_BUFFER_SECONDS, SAMPLE_RATE
from server.stt import stt_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stt_server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to preload the STT model on startup.
    """
    try:
        stt_service.load_model()
    except Exception as e:
        logger.error(f"Error preloading STT model: {e}")
    yield


app = FastAPI(
    title="Remote STT Server",
    description="Real-time WebSocket audio transcription service",
    lifespan=lifespan
)


@app.get("/health")
def health_check():
    """
    Health check endpoint returning server status and model configuration.
    """
    return {
        "status": "ok",
        "model": stt_service.model_size,
        "device": stt_service.device,
        "compute_type": stt_service.compute_type
    }


@app.websocket("/transcribe")
async def transcribe_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription.
    Protocol:
    1. First message can be JSON config: {"type": "config", "language": "es", "task": "transcribe"}
    2. Subsequent messages are binary blobs containing 16kHz mono PCM chunks.
    3. Server responds to each audio chunk with JSON: {"text": "..."}
    """
    await websocket.accept()
    logger.info("Client connected to /transcribe endpoint.")

    language: str | None = None
    task: str = "transcribe"
    audio_buffer = bytearray()
    max_bytes = MAX_BUFFER_SECONDS * SAMPLE_RATE * 2  # 16-bit PCM = 2 bytes per sample

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                logger.info("Client disconnected.")
                break

            # Handle text messages (JSON configuration)
            if "text" in message and message["text"]:
                try:
                    config = json.loads(message["text"])
                    if isinstance(config, dict):
                        if "language" in config:
                            language = config["language"]
                        if "task" in config:
                            task = config["task"]
                        # Clear buffer on new configuration
                        audio_buffer.clear()
                        logger.info(f"Updated config: language={language}, task={task}")
                except Exception as parse_err:
                    logger.warning(f"Failed to parse JSON config message: {parse_err}")

            # Handle binary messages (16kHz PCM audio chunks)
            elif "bytes" in message and message["bytes"]:
                chunk = message["bytes"]

                # Trim trailing odd byte if chunk length is odd to maintain 2-byte alignment
                if len(chunk) % 2 != 0:
                    chunk = chunk[:len(chunk) - 1]

                if not chunk:
                    continue

                audio_buffer.extend(chunk)

                # Maintain maximum buffer window (even byte aligned)
                if len(audio_buffer) > max_bytes:
                    audio_buffer = audio_buffer[-max_bytes:]
                    if len(audio_buffer) % 2 != 0:
                        audio_buffer = audio_buffer[1:]

                if len(audio_buffer) == 0:
                    continue

                # Convert 16-bit signed integer PCM to float32 normalized [-1.0, 1.0]
                pcm_int16 = np.frombuffer(bytes(audio_buffer), dtype=np.int16)
                audio_np = pcm_int16.astype(np.float32) / 32768.0

                # Run transcription in thread pool to prevent blocking asyncio loop
                try:
                    text = await asyncio.to_thread(
                        stt_service.transcribe,
                        audio_np,
                        language=language,
                        task=task
                    )
                except Exception as transcribe_err:
                    logger.error(f"Error during transcription task: {transcribe_err}")
                    text = ""

                await websocket.send_json({"text": text})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected gracefully.")
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
