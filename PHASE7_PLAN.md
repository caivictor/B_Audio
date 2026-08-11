# Phase 7 Plan

## Goal
Prevent the remote STT server from crashing when other GPU processes run by dynamically managing VRAM allocation.

## Task Spec: backend-dev
- **Scope:** Remote STT Server (`server/`).
- **Implementation:** 
  - Add `pynvml` to `requirements.txt`.
  - Update `STTService` in `server/stt.py` to check available VRAM before loading the model. If `pynvml` detects less than ~2GB of free VRAM, default `device="cpu"` and `compute_type="int8"`. Otherwise, use `device="cuda"` and `compute_type="float16"`.
  - Check VRAM periodically (or at the start of a new connection) to see if we can safely reload the model back to `"cuda"` if it was previously on `"cpu"`. To do this, if `self.device == "cpu"` and VRAM becomes available, set `self.model = None` and call `load_model()` to instantiate it back on the GPU.
- **Verification:** Mock `pynvml` in unit tests to test the fallback and recovery logic.
- **Git:** Branch `feature/phase7-backend`, push, create PR.