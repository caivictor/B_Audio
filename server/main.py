"""
FastAPI application for Remote Speech-To-Text processing via WebSockets.
"""
import asyncio
import json
import logging
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from server.config import KEEPALIVE_TIMEOUT_SECONDS, MAX_BUFFER_SECONDS, SAMPLE_RATE
from server.stt import stt_service, SpeakerState

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
    2. Heartbeat / ping: {"type": "ping"} -> server responds {"type": "pong"}
    3. Subsequent messages are binary blobs containing 16kHz mono PCM chunks.
    4. Server responds to each audio chunk with JSON: {"text": "..."}
    """
    await websocket.accept()
    logger.info("Client connected to /transcribe endpoint.")

    # Dynamic VRAM check & recovery on new connection
    stt_service.check_vram_and_reload()

    # Isolated speaker diarization state per connection (DEF-018)
    session_speaker_state = SpeakerState()

    language: str | None = None
    task: str = "transcribe"
    audio_buffer = bytearray()
    max_bytes = MAX_BUFFER_SECONDS * SAMPLE_RATE * 2  # 16-bit PCM = 2 bytes per sample

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=KEEPALIVE_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                logger.info("WebSocket idle timeout reached, sending keepalive ping.")
                try:
                    await websocket.send_json({"type": "ping"})
                    continue
                except Exception as ping_err:
                    logger.info(f"Client disconnected during keepalive ping: {ping_err}")
                    break

            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                logger.info("Client disconnected.")
                break

            # Handle text messages (JSON configuration or heartbeat ping/pong)
            if "text" in message and message["text"]:
                try:
                    config = json.loads(message["text"])
                    if isinstance(config, dict):
                        msg_cmd = config.get("type")
                        if msg_cmd == "ping":
                            await websocket.send_json({"type": "pong"})
                            continue
                        elif msg_cmd == "pong":
                            continue

                        if "language" in config:
                            language = config["language"]
                        if "task" in config:
                            task = config["task"]
                        # Clear buffer on new configuration
                        audio_buffer.clear()
                        session_speaker_state.reset()
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

                # Drain pending binary chunks to catch up if CPU transcription is lagging
                while True:
                    try:
                        next_msg = await asyncio.wait_for(websocket.receive(), timeout=0.001)
                        if "bytes" in next_msg and next_msg["bytes"]:
                            nxt_chunk = next_msg["bytes"]
                            if len(nxt_chunk) % 2 != 0:
                                nxt_chunk = nxt_chunk[:-1]
                            audio_buffer.extend(nxt_chunk)
                        elif "text" in next_msg:
                            # If we hit a text/config message, put it back or ignore? 
                            # Since we can't un-receive, we just skip it if it's a ping, or process it if config.
                            try:
                                config = __import__("json").loads(next_msg["text"])
                                if config.get("type") == "ping":
                                    await websocket.send_json({"type": "pong"})
                            except:
                                pass
                            break
                    except __import__("asyncio").TimeoutError:
                        break

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
                    result = await asyncio.to_thread(
                        stt_service.transcribe,
                        audio_np,
                        language=language,
                        task=task,
                        speaker_state=session_speaker_state
                    )
                except Exception as transcribe_err:
                    logger.error(f"Error during transcription task: {transcribe_err}")
                    result = {
                        "text": "",
                        "start": round(session_speaker_state.total_audio_processed, 3),
                        "end": round(session_speaker_state.total_audio_processed, 3)
                    }

                audio_buffer.clear()

                try:
                    await websocket.send_json(result)
                except (WebSocketDisconnect, RuntimeError, ConnectionResetError) as send_err:
                    logger.info(f"Client disconnected while sending transcription: {send_err}")
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected gracefully.")
    except (RuntimeError, ConnectionResetError) as conn_err:
        logger.info(f"WebSocket connection reset or closed abruptly: {conn_err}")
    except asyncio.CancelledError:
        logger.info("WebSocket session cancelled.")
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
    finally:
        audio_buffer.clear()
        logger.info("Cleaned up WebSocket session resources.")
