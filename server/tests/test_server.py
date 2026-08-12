"""
Unit tests for Remote STT Server API endpoints and transcription service.
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app
from server.stt import STTService, stt_service

client = TestClient(app)


def test_health_endpoint():
    """
    Test GET /health returns OK status and model info.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data
    assert "device" in data


def test_stt_service_transcribe():
    """
    Test STTService directly with numpy array input.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    audio = np.zeros(1600, dtype=np.float32)
    res = stt.transcribe(audio, language="en")
    assert isinstance(res, dict)
    assert "text" in res
    assert "start" in res
    assert "end" in res
    assert isinstance(res["text"], str)
    assert isinstance(res["start"], (int, float))
    assert isinstance(res["end"], (int, float))


def test_websocket_transcribe_flow():
    """
    Test WebSocket /transcribe flow with config message and binary PCM chunk.
    """
    with client.websocket_connect("/transcribe") as websocket:
        # Send initial config message
        websocket.send_json({"type": "config", "language": "en"})

        # Send 0.1 second of PCM bytes
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)

        # Receive JSON response
        response = websocket.receive_json()
        assert "text" in response
        assert "start" in response
        assert "end" in response
        assert isinstance(response["text"], str)
        assert isinstance(response["start"], (int, float))
        assert isinstance(response["end"], (int, float))


def test_websocket_invalid_json():
    """
    Test WebSocket resilience when receiving invalid JSON config text.
    """
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_text("invalid json")

        # Send audio bytes after invalid json
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)

        response = websocket.receive_json()
        assert "text" in response
        assert "start" in response
        assert "end" in response
        assert isinstance(response["text"], str)


def test_websocket_config_update():
    """
    Test updating config mid-session.
    """
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_json({"type": "config", "language": "es"})
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)
        res1 = websocket.receive_json()
        assert "text" in res1
        assert "start" in res1
        assert "end" in res1

        websocket.send_json({"type": "config", "language": "en", "task": "translate"})
        websocket.send_bytes(pcm_bytes)
        res2 = websocket.receive_json()
        assert "text" in res2
        assert "start" in res2
        assert "end" in res2


def test_websocket_invalid_language_and_task():
    """
    Test WebSocket session stability when receiving invalid/unsupported language or task config (DEF-003).
    """
    audio = np.zeros(1600, dtype=np.float32)

    # Direct STTService test with invalid language & task
    res1 = stt_service.transcribe(audio, language="invalid_lang", task="invalid_task")
    assert isinstance(res1, dict)
    assert isinstance(res1["text"], str)

    res2 = stt_service.transcribe(audio, language="english", task="unknown")
    assert isinstance(res2, dict)
    assert isinstance(res2["text"], str)

    # WebSocket integration test
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_json({"type": "config", "language": "invalid_lang", "task": "invalid_task"})
        pcm_bytes = bytes(3200)
        websocket.send_bytes(pcm_bytes)
        res1 = websocket.receive_json()
        assert "text" in res1
        assert "start" in res1
        assert "end" in res1


def test_websocket_odd_length_audio_chunks():
    """
    Test WebSocket handling of odd-length binary audio messages without corrupting alignment (DEF-004).
    """
    with client.websocket_connect("/transcribe") as websocket:
        # Send 1 byte odd message (ignored/trimmed, no response generated since buffer is empty)
        websocket.send_bytes(b"\x01")

        # Send 1001 bytes odd message (trimmed to 1000 bytes)
        websocket.send_bytes(bytes(1001))
        res1 = websocket.receive_json()
        assert "text" in res1

        # Send standard 3200 byte chunk (100ms)
        websocket.send_bytes(bytes(3200))
        res2 = websocket.receive_json()
        assert "text" in res2


def test_websocket_ping_pong_keepalive():
    """
    Test ping/pong keepalive messages during WebSocket session.
    """
    with client.websocket_connect("/transcribe") as websocket:
        # Send ping
        websocket.send_json({"type": "ping"})
        res = websocket.receive_json()
        assert res == {"type": "pong"}

        # Send pong back to server (ignored gracefully)
        websocket.send_json({"type": "pong"})

        # Follow up with audio stream
        websocket.send_bytes(bytes(3200))
        res2 = websocket.receive_json()
        assert "text" in res2


def test_websocket_abrupt_disconnect_mid_stream():
    """
    Test server resilience and clean resource shutdown on abrupt WebSocket disconnect mid-stream.
    """
    ws = client.websocket_connect("/transcribe")
    websocket = ws.__enter__()
    websocket.send_json({"type": "config", "language": "en"})
    websocket.send_bytes(bytes(3200))
    # Close connection abruptly mid-stream without explicit disconnect handshake
    ws.__exit__(None, None, None)


def test_websocket_idle_timeout_keepalive(monkeypatch):
    """
    Test server sending periodic ping frame when client is idle.
    """
    monkeypatch.setattr("server.main.KEEPALIVE_TIMEOUT_SECONDS", 0.1)
    with client.websocket_connect("/transcribe") as websocket:
        # Client stays idle; server should send keepalive ping after timeout
        msg = websocket.receive_json()
        assert msg == {"type": "ping"}


def test_stt_service_translate_task_parameter():
    """
    Test that STTService correctly passes task='translate' to faster-whisper model.transcribe.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    audio = np.zeros(1600, dtype=np.float32)

    with patch.object(stt.model, "transcribe", return_value=([], None)) as mock_transcribe:
        # Test default task 'transcribe'
        stt.transcribe(audio, language="es")
        mock_transcribe.assert_called_once()
        _, kwargs1 = mock_transcribe.call_args
        assert kwargs1.get("task") == "transcribe"

        mock_transcribe.reset_mock()

        # Test explicit 'translate' task
        stt.transcribe(audio, language="es", task="translate")
        mock_transcribe.assert_called_once()
        _, kwargs2 = mock_transcribe.call_args
        assert kwargs2.get("task") == "translate"
        assert kwargs2.get("language") == "es"


def test_websocket_translate_task_parameter():
    """
    Test that WebSocket endpoint correctly parses 'task': 'translate' from config message
    and passes task='translate' to STTService.
    """
    mock_res = {"text": "[Speaker 1]: hello world", "start": 0.0, "end": 1.0}
    with patch.object(stt_service, "transcribe", return_value=mock_res) as mock_transcribe:
        with client.websocket_connect("/transcribe") as websocket:
            # Send translation config
            websocket.send_json({"type": "config", "language": "es", "task": "translate"})
            # Send audio bytes
            websocket.send_bytes(bytes(3200))

            res = websocket.receive_json()
            assert res == mock_res
            assert mock_transcribe.called
            _, kwargs = mock_transcribe.call_args
            assert kwargs.get("task") == "translate"
            assert kwargs.get("language") == "es"


class MockSegment:
    def __init__(self, text: str, start: float = 0.0, end: float = 1.0):
        self.text = text
        self.start = start
        self.end = end


def test_stt_service_speaker_diarization_tagging():
    """
    Test STTService prefixes transcribed text with [Speaker 1]: tag.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    stt.reset_speaker()
    audio = np.ones(16000, dtype=np.float32) * 0.1
    segments = [MockSegment("Hello world", start=0.0, end=1.0)]

    with patch.object(stt.model, "transcribe", return_value=(segments, None)):
        res = stt.transcribe(audio, language="en")
        assert res["text"] == "[Speaker 1]: Hello world"
        assert res["start"] == 0.0
        assert res["end"] == 1.0


def test_stt_service_pause_speaker_alternation():
    """
    Test STTService alternates speaker tags ([Speaker 1]: -> [Speaker 2]:) when pause >= 0.4s occurs.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    stt.reset_speaker()
    audio = np.ones(16000, dtype=np.float32) * 0.1

    segments = [
        MockSegment("Hello there", start=0.0, end=1.0),
        MockSegment("General Kenobi", start=1.8, end=2.8)
    ]

    with patch.object(stt.model, "transcribe", return_value=(segments, None)):
        res = stt.transcribe(audio, language="en")
        assert res["text"] == "[Speaker 1]: Hello there [Speaker 2]: General Kenobi"
        assert res["start"] == 0.0
        assert res["end"] == 2.8


def test_stt_service_turn_taking_across_silent_chunks():
    """
    Test speaker turn taking across audio chunks separated by silence.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    stt.reset_speaker()

    speech_audio = np.ones(16000, dtype=np.float32) * 0.1
    silent_audio = np.zeros(16000, dtype=np.float32)

    # Chunk 1: Speaker 1 (1.0s audio)
    seg1 = [MockSegment("First speaker here", start=0.0, end=1.0)]
    with patch.object(stt.model, "transcribe", return_value=(seg1, None)):
        res1 = stt.transcribe(speech_audio)
        assert res1["text"] == "[Speaker 1]: First speaker here"
        assert res1["start"] == 0.0
        assert res1["end"] == 1.0

    # Chunk 2: Silence (1.0s audio)
    with patch.object(stt.model, "transcribe", return_value=([], None)):
        res2 = stt.transcribe(silent_audio)
        assert res2["text"] == ""
        assert res2["start"] == 1.0
        assert res2["end"] == 2.0

    # Chunk 3: Speaker 2 (Speech resumes after silence, 1.0s audio)
    seg2 = [MockSegment("Second speaker replying", start=0.0, end=1.0)]
    with patch.object(stt.model, "transcribe", return_value=(seg2, None)):
        res3 = stt.transcribe(speech_audio)
        assert res3["text"] == "[Speaker 2]: Second speaker replying"
        assert res3["start"] == 2.0
        assert res3["end"] == 3.0


def test_websocket_speaker_diarization_response():
    """
    Test WebSocket /transcribe endpoint returns JSON {"text": "[Speaker 1]: ...", "start": ..., "end": ...} response with speaker tags.
    """
    mock_segments = [MockSegment("Hello from WebSocket", start=0.0, end=1.0)]
    with patch.object(stt_service.model, "transcribe", return_value=(mock_segments, None)):
        with client.websocket_connect("/transcribe") as websocket:
            websocket.send_json({"type": "config", "language": "en"})
            pcm_bytes = (np.ones(16000, dtype=np.int16) * 3000).tobytes()
            websocket.send_bytes(pcm_bytes)

            response = websocket.receive_json()
            assert "text" in response
            assert response["text"] == "[Speaker 1]: Hello from WebSocket"
            assert response["start"] == 0.0
            assert response["end"] == 1.0


def test_stt_service_timestamps_accumulate_across_chunks():
    """
    Test that STTService correctly accumulates audio duration across multiple chunks to generate absolute timestamps.
    """
    stt = STTService(model_size="tiny", device="cpu", compute_type="int8")
    stt.load_model()
    stt.reset_speaker()

    # Chunk 1: 2 seconds of audio (32000 samples)
    audio1 = np.ones(32000, dtype=np.float32) * 0.1
    seg1 = [MockSegment("First chunk", start=0.5, end=1.8)]
    with patch.object(stt.model, "transcribe", return_value=(seg1, None)):
        res1 = stt.transcribe(audio1)
        assert res1["text"] == "[Speaker 1]: First chunk"
        assert res1["start"] == 0.5
        assert res1["end"] == 1.8

    # Chunk 2: 3 seconds of audio (48000 samples). Total prior audio = 2.0s.
    audio2 = np.ones(48000, dtype=np.float32) * 0.1
    seg2 = [MockSegment("Second chunk", start=0.2, end=2.5)]
    with patch.object(stt.model, "transcribe", return_value=(seg2, None)):
        res2 = stt.transcribe(audio2)
        assert res2["text"] == "[Speaker 1]: Second chunk"
        assert res2["start"] == 2.2  # 2.0 + 0.2
        assert res2["end"] == 4.5    # 2.0 + 2.5


def test_vram_check_low_memory_fallback():
    """
    Test that STTService falls back to device="cpu" and compute_type="int8"
    when pynvml detects less than 2GB free VRAM (< 2 * 1024**3 bytes).
    """
    stt = STTService(model_size="tiny")
    stt.model = None

    class MockMemoryInfo:
        free = 1 * 1024 * 1024 * 1024  # 1 GB free VRAM (< 2GB)

    with patch("pynvml.nvmlInit"), \
         patch("pynvml.nvmlDeviceGetHandleByIndex"), \
         patch("pynvml.nvmlDeviceGetMemoryInfo", return_value=MockMemoryInfo()), \
         patch("pynvml.nvmlShutdown"), \
         patch("server.stt.WhisperModel") as mock_whisper:

        stt.load_model()

        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        mock_whisper.assert_called_once_with("tiny", device="cpu", compute_type="int8")


def test_vram_check_sufficient_memory_cuda():
    """
    Test that STTService selects device="cuda" and compute_type="float16"
    when pynvml detects at least 2GB free VRAM (>= 2 * 1024**3 bytes).
    """
    stt = STTService(model_size="tiny")
    stt.model = None

    class MockMemoryInfo:
        free = 4 * 1024 * 1024 * 1024  # 4 GB free VRAM (>= 2GB)

    with patch("pynvml.nvmlInit"), \
         patch("pynvml.nvmlDeviceGetHandleByIndex"), \
         patch("pynvml.nvmlDeviceGetMemoryInfo", return_value=MockMemoryInfo()), \
         patch("pynvml.nvmlShutdown"), \
         patch("server.stt.WhisperModel") as mock_whisper:

        stt.load_model()

        assert stt.device == "cuda"
        assert stt.compute_type == "float16"
        mock_whisper.assert_called_once_with("tiny", device="cuda", compute_type="float16")


def test_dynamic_vram_reload_recovery_to_gpu():
    """
    Test dynamic reloading: when model is on CPU and VRAM becomes >= 2GB,
    check_vram_and_reload() unloads the model and reloads it on GPU.
    """
    stt = STTService(model_size="tiny")
    stt.model = MagicMock()
    stt.device = "cpu"
    stt.compute_type = "int8"

    class MockMemoryInfo:
        free = 3 * 1024 * 1024 * 1024  # 3 GB free VRAM

    with patch("pynvml.nvmlInit"), \
         patch("pynvml.nvmlDeviceGetHandleByIndex"), \
         patch("pynvml.nvmlDeviceGetMemoryInfo", return_value=MockMemoryInfo()), \
         patch("pynvml.nvmlShutdown"), \
         patch("server.stt.WhisperModel") as mock_whisper:

        reloaded = stt.check_vram_and_reload()

        assert reloaded is True
        assert stt.device == "cuda"
        assert stt.compute_type == "float16"
        mock_whisper.assert_called_once_with("tiny", device="cuda", compute_type="float16")


def test_vram_check_pynvml_exception_fallback():
    """
    Test that STTService defaults gracefully to CPU if pynvml raises an Exception.
    """
    stt = STTService(model_size="tiny")
    stt.model = None

    with patch("pynvml.nvmlInit", side_effect=Exception("NVML driver error")), \
         patch("server.stt.WhisperModel") as mock_whisper:

        stt.load_model()

        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        mock_whisper.assert_called_once_with("tiny", device="cpu", compute_type="int8")


def test_cuda_load_failure_fallback_to_cpu():
    """
    Test that if CUDA initialization raises an Exception despite >= 2GB VRAM,
    load_model() catches it and falls back to CPU int8.
    """
    stt = STTService(model_size="tiny")
    stt.model = None

    class MockMemoryInfo:
        free = 4 * 1024 * 1024 * 1024  # 4 GB free VRAM

    def mock_whisper_side_effect(model_size, device, compute_type):
        if device == "cuda":
            raise RuntimeError("CUDA device out of memory")
        return MagicMock()

    with patch("pynvml.nvmlInit"), \
         patch("pynvml.nvmlDeviceGetHandleByIndex"), \
         patch("pynvml.nvmlDeviceGetMemoryInfo", return_value=MockMemoryInfo()), \
         patch("pynvml.nvmlShutdown"), \
         patch("server.stt.WhisperModel", side_effect=mock_whisper_side_effect) as mock_whisper:

        stt.load_model()

        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        assert mock_whisper.call_count == 2


def test_websocket_ui_config_preserves_speaker_and_buffer():
    """
    Test DEF-035 & DEF-042: UI config updates (e.g. fontSize) or identical language/task
    do NOT clear audio buffer or reset speaker state, whereas changing language/task DOES reset state.
    """
    recorded_speaker_states = []

    def mock_transcribe(audio, language=None, task="transcribe", speaker_state=None):
        if speaker_state:
            recorded_speaker_states.append({
                "audio_processed": speaker_state.total_audio_processed,
                "current_speaker": speaker_state.current_speaker
            })
            # Simulate total_audio_processed accumulation
            speaker_state.total_audio_processed += len(audio) / 16000.0
        return {"text": "hello", "start": 0.0, "end": 1.0}

    with patch.object(stt_service, "transcribe", side_effect=mock_transcribe):
        with client.websocket_connect("/transcribe") as websocket:
            # 1. Initial config
            websocket.send_json({"type": "config", "language": "en", "task": "transcribe"})
            websocket.send_bytes(bytes(3200))  # 0.2s
            websocket.receive_json()

            # 2. UI config update only (fontSize: 18) - should NOT reset
            websocket.send_json({"type": "config", "fontSize": 18})
            websocket.send_bytes(bytes(3200))  # 0.2s
            websocket.receive_json()

            # 3. Same language config update - should NOT reset
            websocket.send_json({"type": "config", "language": "en"})
            websocket.send_bytes(bytes(3200))  # 0.2s
            websocket.receive_json()

            # 4. Actual language change (en -> es) - SHOULD reset speaker state
            websocket.send_json({"type": "config", "language": "es"})
            websocket.send_bytes(bytes(3200))  # 0.2s
            websocket.receive_json()

    assert len(recorded_speaker_states) == 4
    # Call 1: initial (audio_processed = 0.0)
    assert recorded_speaker_states[0]["audio_processed"] == 0.0
    # Call 2: after 1st 0.1s chunk, audio_processed should be 0.1s (NOT reset by fontSize config)
    assert pytest.approx(recorded_speaker_states[1]["audio_processed"], 0.01) == 0.1
    # Call 3: after 2nd 0.1s chunk, audio_processed should be 0.2s (NOT reset by same language config)
    assert pytest.approx(recorded_speaker_states[2]["audio_processed"], 0.01) == 0.2
    # Call 4: after language change to 'es', speaker state was reset, so audio_processed reset back to 0.0
    assert recorded_speaker_states[3]["audio_processed"] == 0.0


@pytest.mark.asyncio
async def test_websocket_drain_loop_disconnect_graceful():
    """
    Test DEF-039: Receiving websocket.disconnect during the receive drain loop
    breaks out cleanly without raising Starlette RuntimeError.
    """
    import asyncio
    from server.main import transcribe_websocket

    mock_ws = MagicMock()

    # Async mock for accept
    async def mock_accept():
        pass

    mock_ws.accept = mock_accept

    # Mock receive calls:
    # 1. Binary chunk message (outer loop receive)
    # 2. Disconnect message (drain loop receive)
    # 3. Second disconnect message (if called again, raises RuntimeError like Starlette)
    call_count = 0

    async def mock_receive():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"type": "websocket.bytes", "bytes": bytes(3200)}
        elif call_count == 2:
            return {"type": "websocket.disconnect", "code": 1000}
        else:
            raise RuntimeError('Cannot call "receive" once a disconnect message has been received.')

    mock_ws.receive = mock_receive

    with patch("server.main.stt_service") as mock_stt:
        mock_stt.transcribe.return_value = {"text": "test", "start": 0.0, "end": 0.2}
        # Should complete cleanly without raising RuntimeError
        await transcribe_websocket(mock_ws)

    assert call_count == 2



