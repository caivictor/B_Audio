with open("REQUIREMENTS.md", "r") as f:
    content = f.read()

new_phases = """
### Step 5: Subtitle Export & Transcript History
*   **Goal:** Allow users to save their captioned sessions.
*   **Extension:** Add a "Download Transcript" button to the extension popup. Accumulate the transcription history during the session and export it as a timestamped `.txt` or `.srt` file when clicked.
*   **Backend:** Ensure the STT server includes relative `start` and `end` timestamps in the WebSocket JSON responses for each chunk.

### Step 6: UI Customization Settings Panel
*   **Goal:** Give users more control over how the subtitles look without hardcoding CSS.
*   **Extension:** Create an Options Page (`options.html`) where users can configure Font Family, Text Color, and Stroke Thickness. Pass these settings to `content.js` to dynamically update the subtitle overlay styling.

### Step 7: Dynamic VRAM Management (Backend)
*   **Goal:** Prevent the remote STT server from crashing when other GPU processes run.
*   **Backend:** Implement a VRAM check before transcription. If GPU memory is exhausted, seamlessly fall back to CPU inference, and attempt to recover GPU usage if memory frees up later.

### Step 8 & 9: Advanced Architectural Shifts
*   **Goal:** Explore WebGPU local browser inference and advanced audio source separation (Demucs) as future experimental branches, replacing the need for the remote server and pause-based diarization.
"""

content = content.replace("## 6. Documentation & Handover Requirements", new_phases + "\n## 6. Documentation & Handover Requirements")

with open("REQUIREMENTS.md", "w") as f:
    f.write(content)
