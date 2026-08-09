"""
Speech-to-Text service wrapper around faster-whisper.
"""
import logging
import numpy as np
from faster_whisper import WhisperModel
try:
    from faster_whisper.tokenizer import _LANGUAGE_CODES
    SUPPORTED_LANGUAGES = set(_LANGUAGE_CODES)
except Exception:
    SUPPORTED_LANGUAGES = None

from server.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

logger = logging.getLogger("stt_server")

SUPPORTED_TASKS = {"transcribe", "translate"}


class SpeakerState:
    """
    Encapsulates speaker diarization tracking state for an individual session.
    """
    def __init__(self):
        self.current_speaker: int = 1
        self.last_audio_had_speech: bool = False
        self.time_since_last_speech_end: float = 0.0
        self.last_segment_end_time: float = 0.0

    def reset(self) -> None:
        self.current_speaker = 1
        self.last_audio_had_speech = False
        self.time_since_last_speech_end = 0.0
        self.last_segment_end_time = 0.0

    def toggle_speaker(self) -> None:
        self.current_speaker = 2 if self.current_speaker == 1 else 1


class STTService:
    """
    Manages loading and running inference with faster-whisper models and speaker diarization.
    """
    _shared_model = None
    _shared_device = None
    _shared_compute_type = None

    def __init__(
        self,
        model_size: str = WHISPER_MODEL,
        device: str = WHISPER_DEVICE,
        compute_type: str = WHISPER_COMPUTE_TYPE
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

        # Speaker diarization state
        self.speaker_state = SpeakerState()
        self.pause_threshold_sec = 0.4
        self.silence_energy_threshold = 0.005
        self.pyannote_pipeline = None
        self._init_diarization()

    @property
    def model(self):
        if self._model is not None:
            return self._model
        return STTService._shared_model

    @model.setter
    def model(self, value):
        self._model = value
        STTService._shared_model = value

    @property
    def current_speaker(self) -> int:
        return self.speaker_state.current_speaker

    @current_speaker.setter
    def current_speaker(self, val: int) -> None:
        self.speaker_state.current_speaker = val

    @property
    def last_audio_had_speech(self) -> bool:
        return self.speaker_state.last_audio_had_speech

    @last_audio_had_speech.setter
    def last_audio_had_speech(self, val: bool) -> None:
        self.speaker_state.last_audio_had_speech = val

    @property
    def time_since_last_speech_end(self) -> float:
        return self.speaker_state.time_since_last_speech_end

    @time_since_last_speech_end.setter
    def time_since_last_speech_end(self, val: float) -> None:
        self.speaker_state.time_since_last_speech_end = val

    @property
    def last_segment_end_time(self) -> float:
        return self.speaker_state.last_segment_end_time

    @last_segment_end_time.setter
    def last_segment_end_time(self, val: float) -> None:
        self.speaker_state.last_segment_end_time = val

    def _init_diarization(self) -> None:
        """
        Attempts to load pyannote.audio diarization pipeline if available and authorized.
        Falls back gracefully to pause/silence speaker simulation.
        """
        try:
            from pyannote.audio import Pipeline
            self.pyannote_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=True
            )
            logger.info("pyannote.audio diarization pipeline initialized.")
        except Exception:
            self.pyannote_pipeline = None
            logger.info("pyannote.audio not available or not configured; using pause/silence speaker simulation.")

    def reset_speaker(self) -> None:
        """
        Resets speaker diarization tracking state.
        """
        self.speaker_state.reset()

    def toggle_speaker(self) -> None:
        """
        Alternates current speaker between 1 and 2.
        """
        self.speaker_state.toggle_speaker()

    def format_speaker_tag(self, text: str, speaker_num: int) -> str:
        """
        Formats text with [Speaker N]: tag prefix if not already present.
        """
        cleaned = text.strip()
        if not cleaned:
            return ""
        if cleaned.startswith("[Speaker") or cleaned.startswith("[speaker"):
            return cleaned
        return f"[Speaker {speaker_num}]: {cleaned}"

    def load_model(self) -> None:
        """
        Loads the faster-whisper model. Falls back to CPU if CUDA initialization fails.
        """
        if self.model is not None:
            return

        logger.info(
            f"Loading Whisper model '{self.model_size}' "
            f"(device={self.device}, compute_type={self.compute_type})..."
        )
        try:
            loaded_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Failed to load Whisper model on device '{self.device}': {e}. "
                f"Falling back to CPU int8."
            )
            loaded_model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            self.device = "cpu"
            self.compute_type = "int8"
            logger.info("Fallback CPU Whisper model loaded successfully.")

        STTService._shared_model = loaded_model
        STTService._shared_device = self.device
        STTService._shared_compute_type = self.compute_type
        self._model = loaded_model

    def transcribe(
        self,
        audio_data: np.ndarray,
        language: str | None = None,
        task: str = "transcribe",
        speaker_state: SpeakerState | None = None
    ) -> str:
        """
        Transcribes numpy float32 audio array (16kHz mono).
        """
        state = speaker_state if speaker_state is not None else self.speaker_state

        if self.model is None:
            self.load_model()

        kwargs = {}
        if language and isinstance(language, str):
            lang_clean = language.strip().lower()
            if lang_clean not in ("auto", ""):
                if SUPPORTED_LANGUAGES is None or lang_clean in SUPPORTED_LANGUAGES:
                    kwargs["language"] = lang_clean
                else:
                    logger.warning(
                        f"Unsupported language code '{language}', falling back to auto-detection."
                    )

        if task and isinstance(task, str):
            task_clean = task.strip().lower()
            if task_clean in SUPPORTED_TASKS:
                kwargs["task"] = task_clean
            else:
                logger.warning(
                    f"Unsupported task '{task}', defaulting to 'transcribe'."
                )
                kwargs["task"] = "transcribe"

        audio_rms = np.sqrt(np.mean(audio_data**2)) if len(audio_data) > 0 else 0.0
        is_silent = audio_rms < self.silence_energy_threshold
        sample_rate = 16000
        chunk_duration = len(audio_data) / sample_rate if len(audio_data) > 0 else 0.0

        try:
            segments_iter, _ = self.model.transcribe(audio_data, beam_size=1, **kwargs)
            segments = list(segments_iter)
        except ValueError as val_err:
            logger.warning(
                f"Whisper transcription ValueError with kwargs {kwargs}: {val_err}. Retrying with default settings."
            )
            try:
                segments_iter, _ = self.model.transcribe(audio_data, beam_size=1)
                segments = list(segments_iter)
            except Exception as retry_err:
                logger.error(f"Error during fallback transcription inference: {retry_err}")
                return ""
        except Exception as e:
            logger.error(f"Error during transcription inference: {e}")
            return ""

        valid_segments = [s for s in segments if s.text and s.text.strip()]
        if not valid_segments:
            if is_silent or state.last_audio_had_speech:
                state.last_audio_had_speech = False
            if state.last_segment_end_time > 0.0 or state.time_since_last_speech_end > 0.0:
                state.time_since_last_speech_end += chunk_duration
            return ""

        tagged_segments = []
        prev_seg_end = None

        for i, s in enumerate(valid_segments):
            seg_text = s.text.strip()
            if i == 0:
                if state.last_audio_had_speech or state.time_since_last_speech_end > 0.0:
                    pause_before_seg = state.time_since_last_speech_end + s.start
                else:
                    pause_before_seg = 0.0
            else:
                pause_before_seg = s.start - prev_seg_end

            if pause_before_seg >= self.pause_threshold_sec:
                state.toggle_speaker()

            tagged_seg = self.format_speaker_tag(seg_text, state.current_speaker)
            tagged_segments.append(tagged_seg)

            prev_seg_end = s.end

        last_seg = valid_segments[-1]
        state.last_audio_had_speech = True
        state.time_since_last_speech_end = max(0.0, chunk_duration - last_seg.end)
        state.last_segment_end_time = last_seg.end

        return " ".join(tagged_segments)


# Global service instance
stt_service = STTService()
