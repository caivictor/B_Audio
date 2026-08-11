# Future Enhancements & Robustness Improvements

Based on UAT feedback, adversarial reviews, and architectural changes, the following features and improvements have been identified to further elevate the user experience and system robustness for WebCaptioner:

## 1. Local STT Processing (WebGPU / WebAssembly)
- **Concept:** Eliminate the need for the remote `192.168.0.30` STT server entirely for users with capable local hardware. 
- **Implementation:** Integrate `whisper.wasm` (WebAssembly) or WebGPU-accelerated models (like Transformers.js) directly into the Chrome Extension's background worker or offscreen document.
- **Benefit:** True zero-latency offline captioning, absolute privacy (no audio leaves the laptop), and removal of network configuration friction.

## 2. Advanced Multi-Speaker Audio Separation
- **Concept:** Improve speaker diarization in overlapping conversation scenarios (cross-talk).
- **Implementation:** Instead of relying purely on pause-thresholds or Whisper's built-in diarization, integrate a real-time vocal source separation model (e.g., Demucs or WebRTC noise suppression profiles) in the `AudioContext` before sending the audio to the STT server.
- **Benefit:** Highly accurate transcription even when multiple people are talking over each other or when there is heavy background music/noise.

## 3. UI Customization Settings Panel
- **Concept:** Give users more control over how the subtitles look without hardcoding CSS.
- **Implementation:** Create an Options Page (`options.html`) in the extension where users can configure:
  - Font Family (e.g., Arial, Comic Sans, Dyslexic fonts)
  - Subtitle Box Position (Top, Bottom, Left, Right)
  - Color Palette configuration for Speaker Tags
  - Text stroke outline thickness
- **Benefit:** Accessibility and personalized UX.

## 4. Subtitle Export & Transcript History
- **Concept:** Allow users to save their captioned sessions.
- **Implementation:** Add a "Download Transcript" button to the extension popup. The background worker stores the session's JSON responses in `chrome.storage.session` and allows exporting them as a `.txt` or `.srt` (SubRip Subtitle) file with timestamps.
- **Benefit:** Extremely useful for meetings, lectures, or language learning.

## 5. Automatic Target Language Translation
- **Concept:** Expand beyond just translating *to* English.
- **Implementation:** Update the STT server to utilize an LLM (like Llama 3) or a dedicated translation model (like SeamlessM4T) chained *after* the Whisper transcription. Allow the user to select the Output Language in the extension popup (e.g., Source: Japanese -> Target: Spanish).
- **Benefit:** Universal real-time translation for any video on the web.

## 6. Dynamic VRAM Management (Backend)
- **Concept:** Prevent the server from crashing or falling back to CPU when other GPU processes (like `llama-server`) are running.
- **Implementation:** Implement dynamic memory allocation checking in `server/stt.py` using `pynvml`. If the GPU has less than 2GB free, automatically route the task to a quantized int8 CPU model. If the GPU frees up later in the session, dynamically hand the context back to the CUDA model.
- **Benefit:** Seamless, crash-free host machine multi-tasking.
