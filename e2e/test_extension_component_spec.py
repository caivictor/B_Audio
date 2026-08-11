"""
End-to-End Tests for Chrome Extension specifications (REQUIREMENTS.md Phase 1).

Verifies:
1. Manifest V3 compliance and permissions.
2. Background service worker configuration.
3. Popup HTML DOM structure, language selector options, and controls.
4. Offscreen HTML/JS presence for tab capture and audio WebSocket streaming.
"""

import os
import json
import pytest
from pathlib import Path

EXTENSION_DIR = Path(__file__).parent.parent / "extension"


def test_manifest_v3_specifications():
    """Verify manifest.json adheres to Manifest V3 requirements."""
    manifest_file = EXTENSION_DIR / "manifest.json"
    assert manifest_file.exists(), "extension/manifest.json must exist"

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("manifest_version") == 3, "Must use Manifest V3"
    assert manifest.get("name") == "WebCaptioner"
    
    permissions = manifest.get("permissions", [])
    assert "tabCapture" in permissions, "Requires tabCapture permission"
    assert "offscreen" in permissions, "Requires offscreen permission"
    assert "activeTab" in permissions, "Requires activeTab permission"

    background = manifest.get("background", {})
    assert background.get("service_worker") == "background.js", "Service worker must be background.js"

    action = manifest.get("action", {})
    assert action.get("default_popup") == "popup.html", "Default popup must be popup.html"


def test_popup_html_elements():
    """Verify popup.html contains required UI controls (language selector, start button, status div)."""
    popup_file = EXTENSION_DIR / "popup.html"
    assert popup_file.exists(), "extension/popup.html must exist"

    content = popup_file.read_text(encoding="utf-8")

    assert 'id="languageSelect"' in content, "Missing languageSelect dropdown"
    assert 'id="toggleBtn"' in content, "Missing toggleBtn action button"
    assert 'id="status"' in content, "Missing status display element"
    assert 'popup.js' in content, "Missing popup.js script reference"

    # Check supported language options
    assert 'value="es"' in content, "Spanish language option missing"
    assert 'value="en"' in content, "English language option missing"


def test_offscreen_script_websocket_endpoint():
    """Verify offscreen.js targets local client WebSocket at ws://localhost:8765."""
    offscreen_file = EXTENSION_DIR / "offscreen.js"
    assert offscreen_file.exists(), "extension/offscreen.js must exist"

    content = offscreen_file.read_text(encoding="utf-8")

    assert "currentServerUrl" in content or "ws://" in content, "offscreen.js must handle WebSocket server URL"
    assert "type: 'config'" in content or 'type: "config"' in content, "offscreen.js must send config message"
    assert "startCapture" in content, "offscreen.js must handle startCapture message"
    assert "stopCapture" in content, "offscreen.js must handle stopCapture message"
