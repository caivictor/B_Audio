"""
Test client script to verify Remote STT Server WebSocket endpoint.
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import numpy as np
import pytest
import websockets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SERVER_URL = os.getenv("STT_SERVER_URL", "ws://127.0.0.1:8000/transcribe")


def generate_test_speech_pcm() -> bytes:
    """
    Generates synthetic speech audio using espeak-ng & ffmpeg if available,
    otherwise returns 3 seconds of synthesized audio.
    """
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_pcm = tempfile.NamedTemporaryFile(suffix=".pcm", delete=False)
    tmp_wav.close()
    tmp_pcm.close()

    try:
        # Try generating speech using espeak-ng
        subprocess.run(
            ["espeak-ng", "-w", tmp_wav.name, "Hello world, this is a test of real time speech transcription."],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_wav.name, "-ar", "16000", "-ac", "1", "-f", "s16le", tmp_pcm.name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        with open(tmp_pcm.name, "rb") as f:
            pcm_bytes = f.read()
        return pcm_bytes
    except Exception:
        # Fallback: create 3 seconds of 440Hz sine wave int16 PCM at 16kHz
        sr = 16000
        t = np.linspace(0, 3, sr * 3, endpoint=False)
        audio = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        return audio.tobytes()
    finally:
        if os.path.exists(tmp_wav.name):
            os.remove(tmp_wav.name)
        if os.path.exists(tmp_pcm.name):
            os.remove(tmp_pcm.name)


@pytest.mark.asyncio
async def test_stt_websocket():
    """
    Connects to server WebSocket, sends config, streams PCM audio, prints response.
    If target server is offline, starts an in-process mock STT server instance.
    """
    print(f"Connecting to {SERVER_URL}...")
    pcm_data = generate_test_speech_pcm()
    print(f"Prepared test audio buffer: {len(pcm_data)} bytes ({len(pcm_data)/32000:.2f} seconds)")

    server_task = None

    try:
        ws_test = await websockets.connect(SERVER_URL)
        await ws_test.close()
    except (OSError, ConnectionRefusedError):
        import uvicorn
        from server.main import app

        parsed = urllib.parse.urlparse(SERVER_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8000

        config = uvicorn.Config(app, host=host, port=port, log_level="error")
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())
        
        # Wait until server is listening
        for _ in range(30):
            try:
                ws = await websockets.connect(SERVER_URL)
                await ws.close()
                break
            except (OSError, ConnectionRefusedError):
                await asyncio.sleep(0.2)

    try:
        async with websockets.connect(SERVER_URL) as ws:
            # 1. Send JSON config message
            config_msg = {"type": "config", "language": "en"}
            await ws.send(json.dumps(config_msg))
            print(f"Sent config: {config_msg}")

            # 2. Stream audio in ~1 second chunks (32000 bytes)
            chunk_size = 32000
            responses = []

            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i + chunk_size]
                await ws.send(chunk)
                print(f"Sent binary audio chunk {i // chunk_size + 1} ({len(chunk)} bytes)")

                response_raw = await ws.recv()
                if isinstance(response_raw, str):
                    resp = json.loads(response_raw)
                else:
                    resp = json.loads(response_raw.decode("utf-8"))

                print(f"Received response: {resp}")
                assert "text" in resp, "Response missing 'text' field!"
                text = resp["text"]
                if text:
                    assert "[Speaker" in text, f"Expected speaker tag in transcription, got '{text}'"
                responses.append(text)

            print("\nTest finished successfully!")
            print(f"Final transcription text: '{responses[-1] if responses else ''}'")
    finally:
        if server_task:
            server.should_exit = True
            await server_task


if __name__ == "__main__":
    asyncio.run(test_stt_websocket())
