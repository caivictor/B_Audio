# Phase 6 Plan

## Goal
Give users more control over how the subtitles look without hardcoding CSS.

## Task Spec: frontend-dev
- **Scope:** Extension (`extension/`).
- **Implementation:** 
  - Create an Options Page (`options.html` and `options.js`) where users can configure:
    - Font Family (e.g., Arial, sans-serif, monospace)
    - Subtitle Text Color (Hex color picker, default `#ffffff`)
    - Stroke Thickness (e.g., slider from 0px to 6px, default 2px)
  - Ensure the Options Page is registered in `manifest.json` (`"options_ui": {"page": "options.html", "open_in_tab": true}`).
  - Save these settings in `chrome.storage.local`.
  - Update `content.js` to read these settings on initialization or via message, and apply them dynamically to the `#webcaptioner-text-bg` styles (e.g., `textShadow` generation based on stroke thickness, `color`, `fontFamily`).
- **Verification:** Unit tests or visual confirmation that the options page loads and settings are applied.
- **Git:** Branch `feature/phase6-frontend`, push, create PR.
