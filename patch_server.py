import re

with open("server/stt.py", "r") as f:
    content = f.read()

# Add condition_on_previous_text=False to speed up inference
transcribe_old = """            segments_iter, _ = self.model.transcribe(audio_data, beam_size=1, **kwargs)"""
transcribe_new = """            segments_iter, _ = self.model.transcribe(audio_data, beam_size=1, condition_on_previous_text=False, **kwargs)"""
content = content.replace(transcribe_old, transcribe_new)

transcribe_old2 = """            segments_iter, _ = self.model.transcribe(audio_data, beam_size=1)"""
transcribe_new2 = """            segments_iter, _ = self.model.transcribe(audio_data, beam_size=1, condition_on_previous_text=False)"""
content = content.replace(transcribe_old2, transcribe_new2)

with open("server/stt.py", "w") as f:
    f.write(content)

with open("server/config.py", "r") as f:
    config_content = f.read()

# Reduce max buffer from 30 to 10 seconds to drastically cut O(N^2) CPU transcription latency
config_content = config_content.replace('os.getenv("MAX_BUFFER_SECONDS", "30")', 'os.getenv("MAX_BUFFER_SECONDS", "10")')

with open("server/config.py", "w") as f:
    f.write(config_content)
