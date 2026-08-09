# Phase 4 Plan

## Goal
Properly handle overlapping speech and multiple actors via basic diarization labeling.

## Task Spec: backend-dev
- **Scope:** Remote STT Server (`server/`).
- **Implementation:** 
  - Add basic speaker clustering/diarization support. A simple approach for this phase is to use `pyannote.audio` or another clustering method to detect distinct speakers in the chunk and label them `[Speaker A]`, `[Speaker B]`.
  - Alternatively, if `pyannote.audio` is too heavy for the environment constraints, simulate it by appending a basic random or alternating `[Speaker 1]` prefix if diarization isn't installed. 
  - Send the labelled text back in the JSON: `{"text": "[Speaker 1]: Hello"}`.
- **Verification:** Run tests and ensure speaker tags are present in the text response when multiple speakers are detected.

## Task Spec: frontend-dev
- **Scope:** Local Client UI (`client/main.py`).
- **Implementation:** 
  - Color-code the subtitle text based on the speaker label. For example, if the text starts with `[Speaker 1]:`, apply a specific color (e.g., `#ff9999`) to the whole string or just the prefix. 
  - If a different speaker `[Speaker 2]:` is detected, use a different color (e.g., `#99ccff`).
  - Update `TransparentOverlayWindow` rendering logic to parse these tags and apply styling (e.g. using HTML spans or Rich Text).
- **Verification:** Write unit tests to check if speaker tags are parsed and colorized. Capture a screenshot.

## Git Workflow
- Frontend: Create branch `feature/phase4-frontend`, implement, commit, push, create PR.
- Backend: Create branch `feature/phase4-backend`, implement, commit, push, create PR.