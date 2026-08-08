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
    Manages loading and running inference with faster-whisper models.
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

        try:
            segments, _ = self.model.transcribe(audio_data, beam_size=1, **kwargs)
            text_segments = [s.text.strip() for s in segments if s.text and s.text.strip()]
            return " ".join(text_segments)
        except ValueError as val_err:
            logger.warning(
                f"Whisper transcription ValueError with kwargs {kwargs}: {val_err}. Retrying with default settings."
            )
            try:
                segments, _ = self.model.transcribe(audio_data, beam_size=1)
                text_segments = [s.text.strip() for s in segments if s.text and s.text.strip()]
                return " ".join(text_segments)
            except Exception as retry_err:
                logger.error(f"Error during fallback transcription inference: {retry_err}")
                return ""
        except Exception as e:
            logger.error(f"Error during transcription inference: {e}")
            return ""


# Global service instance
stt_service = STTService()
