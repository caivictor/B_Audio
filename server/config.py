"""
Configuration settings for the Remote STT Server.
Environment variables can override default settings.
"""
import os

# Whisper model configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "default")

# Server host & port settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Audio processing settings
SAMPLE_RATE = 16000
MAX_BUFFER_SECONDS = int(os.getenv("MAX_BUFFER_SECONDS", "30"))
