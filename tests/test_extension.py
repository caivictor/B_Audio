"""
Unit tests to validate Chrome Extension files, Manifest V3 compliance, and HTML structure.
"""

import json
from pathlib import Path


def test_manifest_v3_structure():
    """Verify manifest.json contains valid Manifest V3 structure and permissions."""
    manifest_path = Path("extension/manifest.json")
    assert manifest_path.exists(), "extension/manifest.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("manifest_version") == 3, "Manifest version must be 3"
    assert data.get("name") == "WebCaptioner"
    
    permissions = data.get("permissions", [])
    assert "tabCapture" in permissions, "tabCapture permission is required"
    assert "offscreen" in permissions, "offscreen permission is required"

    background = data.get("background", {})
    assert background.get("service_worker") == "background.js", "Background service worker must be background.js"

    action = data.get("action", {})
    assert action.get("default_popup") == "popup.html", "Default popup must be popup.html"


def test_extension_files_exist():
    """Verify all extension required files exist."""
    required_files = [
        "extension/manifest.json",
        "extension/popup.html",
        "extension/popup.js",
        "extension/background.js",
        "extension/offscreen.html",
        "extension/offscreen.js",
    ]
    for rel_path in required_files:
        assert Path(rel_path).exists(), f"File missing: {rel_path}"


def test_extension_offscreen_websocket_and_readiness_logic():
    """Verify offscreen.js acquires mediaStream before WS and signals readiness / error handling (DEF-005, DEF-006, DEF-007)."""
    offscreen_code = Path("extension/offscreen.js").read_text(encoding="utf-8")
    
    # Verify offscreenReady signal
    assert "offscreenReady" in offscreen_code
    
    # Verify getUserMedia appears before WebSocket instantiation in startCapture
    get_user_media_idx = offscreen_code.find("navigator.mediaDevices.getUserMedia")
    ws_init_idx = offscreen_code.find("new WebSocket")
    assert get_user_media_idx != -1 and ws_init_idx != -1
    assert get_user_media_idx < ws_init_idx, "getUserMedia must be called before new WebSocket (DEF-007)"

    # Verify disconnect / error notification
    assert "captureStopped" in offscreen_code
    assert "handleWsDisconnect" in offscreen_code


def test_extension_background_and_popup_event_driven_handling():
    """Verify background.js uses event-driven offscreen readiness and popup.js handles disconnects (DEF-005, DEF-006)."""
    bg_code = Path("extension/background.js").read_text(encoding="utf-8")
    popup_code = Path("extension/popup.js").read_text(encoding="utf-8")

    # Verify background worker does not use race-prone setTimeout delay
    assert "setTimeout" not in bg_code, "background.js must not use hardcoded setTimeout for offscreen init (DEF-006)"
    assert "offscreenReady" in bg_code
    assert "captureStopped" in bg_code

    # Verify popup.js listens for captureStopped
    assert "captureStopped" in popup_code


def test_extension_font_size_controls():
    """Verify extension popup, background, and offscreen JS support dynamic font size control."""
    popup_html = Path("extension/popup.html").read_text(encoding="utf-8")
    popup_js = Path("extension/popup.js").read_text(encoding="utf-8")
    bg_js = Path("extension/background.js").read_text(encoding="utf-8")
    offscreen_js = Path("extension/offscreen.js").read_text(encoding="utf-8")

    assert "fontSizeSelect" in popup_html, "popup.html must contain fontSizeSelect element"
    assert "fontSizeSelect" in popup_js, "popup.js must bind to fontSizeSelect"
    assert "updateConfig" in popup_js, "popup.js must send updateConfig message on font size change"
    assert "currentFontSize" in bg_js, "background.js must maintain currentFontSize"
    assert "updateConfig" in bg_js, "background.js must handle updateConfig message"
    assert "currentFontSize" in offscreen_js, "offscreen.js must handle fontSize config"


def test_extension_translation_toggle():
    """Verify popup HTML, popup JS, background JS, and offscreen JS support Translate to English toggle."""
    popup_html = Path("extension/popup.html").read_text(encoding="utf-8")
    popup_js = Path("extension/popup.js").read_text(encoding="utf-8")
    bg_js = Path("extension/background.js").read_text(encoding="utf-8")
    offscreen_js = Path("extension/offscreen.js").read_text(encoding="utf-8")

    # popup.html UI element check
    assert 'id="translateCheckbox"' in popup_html, "popup.html must contain translateCheckbox element"
    assert "Translate to English" in popup_html, "popup.html must contain Translate to English label"

    # popup.js logic check
    assert "translateCheckbox" in popup_js, "popup.js must reference translateCheckbox"
    assert "'translate'" in popup_js or '"translate"' in popup_js, "popup.js must handle translate task mode"
    assert "'transcribe'" in popup_js or '"transcribe"' in popup_js, "popup.js must handle transcribe task mode"

    # background.js state and messaging check
    assert "currentTask" in bg_js, "background.js must maintain currentTask"

    # offscreen.js WebSocket config message check
    assert "currentTask" in offscreen_js, "offscreen.js must maintain currentTask"
    assert "task:" in offscreen_js or '"task"' in offscreen_js, "offscreen.js must include task in config JSON message"
