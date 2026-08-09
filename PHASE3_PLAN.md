# Phase 3 Plan

## Goal
Support real-time translation to English.

## Task Spec: frontend-dev
- **Scope:** Extension (`extension/`).
- **Implementation:** 
  - Add a "Translate to English" toggle checkbox in `extension/popup.html`.
  - Update `extension/popup.js`, `extension/background.js`, and `extension/offscreen.js` to read this checkbox state.
  - When the toggle is active, include `"task": "translate"` in the JSON config message sent over WebSocket (`{"type": "config", "language": "es", "task": "translate"}`). When inactive, send `"task": "transcribe"`.
- **Verification:** Write or update frontend tests. Ensure the UI looks clean and functions correctly.

## Task Spec: backend-dev
- **Scope:** Remote STT Server (`server/`).
- **Implementation:** 
  - The backend already parses `"task"` in the config message (from Phase 1 fixes), but ensure that if `"task": "translate"` is received, it correctly passes `task="translate"` to the `faster-whisper` transcribe call. 
  - Verify that `faster-whisper` natively handles translation to English when `task="translate"` is provided.
- **Verification:** Run tests and add a specific test for the translate task config.

## Git Workflow
- Frontend: Create branch `feature/phase3-frontend`, implement, commit, push, create PR.
- Backend: Create branch `feature/phase3-backend`, implement, commit, push, create PR.