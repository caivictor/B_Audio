---
title: Browser Audio Transcription PRD
status: Ready for Implementation
tags:
  - prd
  - ai-build
  - stt
  - whisper
  - browser-extension
---

# Product Requirements Document (PRD): Real-Time Browser Audio Transcription & Translation Overlay

## 1. Overview
**Name:** WebCaptioner (Working Title)
**Objective:** An application that captures media audio from Google Chrome, processes it through a remote GPU-accelerated speech-to-text (STT) server, and displays the native transcription in a transparent, always-on-top floating window on a Linux laptop (Ubuntu 24.04). Phase 1 focuses on native language transcription. Phase 2 will introduce English translation.

## 2. Architecture & Components
To meet the constraints (Browser-only capture, Remote GPU processing, Transparent desktop overlay), the system is divided into three components:

### A. Google Chrome Extension (Audio Capture)
*   **Tech Stack:** Manifest V3 Browser Extension (JavaScript).
*   **Functionality:** 
    *   Uses `chrome.tabCapture` or `MediaStream` API to capture audio from the active tab.
    *   Provides a simple popup UI to **manually select the source language**.
    *   Streams audio chunks (e.g., 1-second intervals, downsampled to 16kHz mono WAV/PCM) via WebSockets to the Local Client.

### B. Local Client & UI (Linux Laptop / Ubuntu 24.04)
*   **Tech Stack:** Python 3.12+, PyQt6 (for UI), `websockets`.
*   **Functionality:**
    *   Runs a local WebSocket server (e.g., `ws://localhost:8765`) to receive audio chunks and language metadata from the browser extension.
    *   Buffers and forwards audio chunks over HTTP/REST or WebSockets to the Remote STT Server.
    *   **UI Window:** Renders a frameless, transparent, "always-on-top" (`Qt.WindowType.WindowStaysOnTopHint`), and click-through (`Qt.WindowTransparentForInput`) overlay.
    *   Updates the overlay text in real-time as transcripts return from the remote server.

### C. Remote STT Server (RTX 4080 at 192.168.0.30)
*   **Tech Stack:** Python, FastAPI, `faster-whisper` (for low-latency Whisper inference).
*   **Functionality:**
    *   Exposes an endpoint (e.g., `/transcribe`) that accepts audio chunks and a `language` parameter.
    *   Runs the audio through the local Whisper model on the RTX 4080.
    *   Returns the transcribed text string.

## 3. User Experience (UX) Flow
1. User opens a Google Chrome tab with a video (e.g., YouTube).
2. User clicks the extension icon, selects the spoken language (e.g., "Spanish"), and clicks "Start Captioning".
3. The transparent PyQt6 overlay appears on the screen.
4. As the video plays, transcribed text appears in the overlay with < 2 seconds latency.
5. User can drag the overlay to reposition it over the video.

## 4. Phased Execution Roadmap
To ensure a stable build and avoid over-engineering early on, the AI coding agent MUST execute this project in the following strict phases. Do not proceed to the next phase until the current one is tested and functional.

### Step 1: Proof of Concept (PoC) - The "Happy Path"
*   **Goal:** Prove the end-to-end pipeline works for a single speaker in their native language.
*   **Extension:** Basic manual language selector. Captures tab audio and sends it via WebSocket.
*   **Backend:** RTX 4080 runs `faster-whisper` (large-v3) receiving chunks and returning native text.
*   **UI:** A raw PyQt6 transparent window that just prints the text stream. No dragging, no styling polish.
*   **Multiple Speakers:** Rely purely on Whisper large-v3's innate ability to pick the loudest speaker during overlapping speech.

### Step 2: UX & UI Polish
*   **Goal:** Make the application usable and visually pleasing.
*   **UI Controls:** Add the ability to click-and-drag the overlay.
*   **Visuals:** Add font size controls, text outlines (stroke) so white text is visible on light backgrounds, and auto-clearing of stale text after a few seconds of silence.
*   **Resilience:** Add graceful error handling if the network drops between the ThinkPad and the 192.168.0.30 server.

### Step 3: English Translation Integration
*   **Goal:** Support translation to English.
*   **Extension:** Add a "Translate to English" toggle checkbox in the popup.
*   **Backend:** When the toggle is active, switch the Whisper inference parameter to `task="translate"`. (Whisper handles this natively without a secondary model).

### Step 4: Advanced Multi-Speaker Handling (Cross-talk)
*   **Goal:** Properly handle overlapping speech and multiple actors.
*   **Backend:** Introduce streaming speaker diarization (e.g., `pyannote.audio`) to label text chunks with `[Speaker A]`, `[Speaker B]`.
*   **UI:** Color-code the subtitle text based on the speaker label to visually separate overlapping conversations.
*   *(Optional Future Upgrade):* If diarization isn't enough, implement real-time vocal source separation (e.g., Demucs) to split audio tracks before feeding them to Whisper.

## 5. Technical Instructions for AI Coding Agent
When building Step 1 (PoC), follow these technical directions:
1.  **Remote Backend:** Set up a FastAPI server using `faster-whisper`. Create a WebSocket endpoint optimized for streaming STT.
2.  **Local Python Client:** Create a PyQt6 application. Ensure the main window uses `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)` and `setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)`.
3.  **Extension:** Write a basic `manifest.json`, a background service worker to handle the `tabCapture` stream, and an `AudioContext` processor to convert the stream to PCM data before sending it over the WebSocket.

## 6. Documentation & Handover Requirements
For every step in the Phased Execution Roadmap, the AI coding agent MUST generate and update comprehensive documentation to ensure maintainability:
*   **Inline Code Documentation:** All Python and JavaScript code must include clear docstrings and inline comments explaining the logic, especially for WebSocket streaming, audio buffer management, and concurrency.
*   **Installation & Setup Instructions:** A `README.md` must be created and maintained with step-by-step instructions for:
    *   Setting up the remote FastAPI/Whisper backend on the RTX 4080 (including Python virtual environment and CUDA dependencies).
    *   Installing the local PyQt6 client on Ubuntu 24.04 (including dependency lists).
    *   Loading the unpacked Browser Extension into Google Chrome via Developer Mode (chrome://extensions).
*   **Usage Guide (Per Step):** As each Phase/Step is completed, the README must be updated with exact instructions on how to start the backend server, launch the local UI, and use the newly added features.
