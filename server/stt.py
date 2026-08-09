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


class STTService:
    """
    Manages loading and running inference with faster-whisper models and speaker diarization.
    """
    def __init__(
        self,
        model_size: str = WHISPER_MODEL,
        device: str = WHISPER_DEVICE,
        compute_type: str = WHISPER_COMPUTE_TYPE
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

        # Speaker diarization state
        self.current_speaker = 1
        self.last_audio_had_speech = False
        self.last_segment_end_time = 0.0
        self.pause_threshold_sec = 0.4
        self.silence_energy_threshold = 0.005
        self.pyannote_pipeline = None
        self._init_diarization()

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
        self.current_speaker = 1
        self.last_audio_had_speech = False
        self.last_segment_end_time = 0.0

    def toggle_speaker(self) -> None:
        """
        Alternates current speaker between 1 and 2.
        """
        self.current_speaker = 2 if self.current_speaker == 1 else 1

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
            self.model = WhisperModel(
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
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            self.device = "cpu"
            self.compute_type = "int8"
            logger.info("Fallback CPU Whisper model loaded successfully.")

    def transcribe(
        self,
        audio_data: np.ndarray,
        language: str | None = None,
        task: str = "transcribe"
    ) -> str:
        """
        Transcribes numpy float32 audio array (16kHz mono).
        """
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
            if is_silent:
                self.last_audio_had_speech = False
            return ""

        # Switch speaker if silence occurred prior to this speech chunk
        if not self.last_audio_had_speech and self.last_segment_end_time > 0.0:
            self.toggle_speaker()

        tagged_segments = []
        for s in valid_segments:
            seg_text = s.text.strip()
            # Switch speaker if there was a pause >= threshold before this segment
            if self.last_audio_had_speech and (s.start - self.last_segment_end_time >= self.pause_threshold_sec):
                self.toggle_speaker()

            tagged_seg = self.format_speaker_tag(seg_text, self.current_speaker)
            tagged_segments.append(tagged_seg)

            self.last_segment_end_time = s.end
            self.last_audio_had_speech = True

        return " ".join(tagged_segments)


# Global service instance
stt_service = STTService()
