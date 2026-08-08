# Phase 2 Plan

## Goal
Make the application usable and visually pleasing, with improved resilience.

## Task Spec: frontend-dev
- **Scope:** Local Client UI (`client/main.py`) & Extension (`extension/`).
- **UI Controls (Draggable):** Update the PyQt6 overlay window to be click-and-draggable (since it is frameless). Ensure `mousePressEvent` and `mouseMoveEvent` correctly update the window position.
- **Visuals (Stroke/Styling):** Update the PyQt6 label rendering to include a text outline (stroke) so white text is visible on light backgrounds. (Hint: Use `QGraphicsDropShadowEffect` or custom `paintEvent` for text outline).
- **Visuals (Font Size):** Add a font size control (e.g., in the extension popup or via hotkeys in the client). If in the extension popup, send a config message like `{"type": "config", "fontSize": 24}` to the client.
- **Resilience:** Ensure the client and extension both handle network drops gracefully (reconnecting or showing an error UI).
- **Verification:** Run unit tests, take screenshots of the stroked text, and verify the window is draggable.

## Task Spec: backend-dev
- **Scope:** Remote STT Server (`server/main.py`).
- **Resilience:** Ensure the server gracefully handles sudden WebSocket disconnects without leaking memory or crashing (if not fully covered in Phase 1 fixes). Add ping/pong keepalives if appropriate.
- **Verification:** Run tests simulating network drops mid-stream.
