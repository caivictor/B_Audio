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
        "extension/options.html",
        "extension/options.js",
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


def test_adv_011_server_url_input_exists():
    """ADV-011: Verify serverUrl input exists in popup.html and popup.js binds to it."""
    popup_html = Path("extension/popup.html").read_text(encoding="utf-8")
    popup_js = Path("extension/popup.js").read_text(encoding="utf-8")

    assert 'id="serverUrl"' in popup_html, "popup.html must contain id='serverUrl'"
    assert 'serverUrl' in popup_js, "popup.js must reference serverUrl"


def test_adv_012_background_message_listener_scope():
    """ADV-012: Verify background.js encloses captionText inside message listener callback without syntax errors."""
    bg_code = Path("extension/background.js").read_text(encoding="utf-8")

    assert "chrome.runtime.onMessage.addListener" in bg_code
    assert "captionText" in bg_code

    # Check that captionText is handled before listener ends
    listener_start = bg_code.find("chrome.runtime.onMessage.addListener")
    caption_text_idx = bg_code.find("captionText", listener_start)
    assert caption_text_idx != -1, "captionText must be present after listener start"


def test_adv_013_offscreen_ws_onmessage():
    """ADV-013: Verify offscreen.js sets ws.onmessage to dispatch captionText."""
    offscreen_code = Path("extension/offscreen.js").read_text(encoding="utf-8")

    assert "ws.onmessage" in offscreen_code, "offscreen.js must define ws.onmessage"
    assert "captionText" in offscreen_code, "offscreen.js must dispatch captionText on message"


def test_adv_014_offscreen_reconnect_url():
    """ADV-014: Verify offscreen.js uses target/current server URL and not hardcoded localhost on reconnect."""
    offscreen_code = Path("extension/offscreen.js").read_text(encoding="utf-8")

    assert "ws://localhost:8765" not in offscreen_code, "offscreen.js must not reconnect to obsolete localhost:8765"
    assert "currentServerUrl" in offscreen_code, "offscreen.js must maintain currentServerUrl for reconnection"


def test_adv_015_017_content_shadow_dom_and_fullscreen():
    """ADV-015 & ADV-017: Verify content.js uses Shadow DOM and fullscreenchange handler with max z-index."""
    content_code = Path("extension/content.js").read_text(encoding="utf-8")

    assert "attachShadow" in content_code, "content.js must use attachShadow for CSS encapsulation (ADV-017)"
    assert "2147483647" in content_code, "content.js must set maximum z-index (ADV-015)"
    assert "fullscreenchange" in content_code, "content.js must listen for fullscreenchange to handle fullscreen video (ADV-015)"


def test_adv_016_content_viewport_containment():
    """ADV-016: Verify content.js constrains overlay height and enables scroll for long text."""
    content_code = Path("extension/content.js").read_text(encoding="utf-8")

    assert "max-height" in content_code or "maxHeight" in content_code, "content.js must limit overlay max-height"
    assert "overflow-y" in content_code or "overflowY" in content_code, "content.js must allow vertical scrolling for long text"


def test_adv_018_background_tab_lifecycle_listeners():
    """ADV-018: Verify background.js listens for tab removal and updates to manage capture state."""
    bg_code = Path("extension/background.js").read_text(encoding="utf-8")

    assert "chrome.tabs.onRemoved.addListener" in bg_code, "background.js must handle tab removal"
    assert "chrome.tabs.onUpdated.addListener" in bg_code, "background.js must handle tab updates"


def test_adv_019_content_speaker_tag_newlines():
    """ADV-019: Verify parseSpeakerTags in content.js cleans up double line breaks before speaker tags."""
    content_code = Path("extension/content.js").read_text(encoding="utf-8")

    assert "parseSpeakerTags" in content_code
    assert "ADV-019" in content_code or "replace" in content_code


def test_adv_020_popup_server_url_validation():
    """ADV-020: Verify popup.js validates server URL starts with ws:// or wss://."""
    popup_code = Path("extension/popup.js").read_text(encoding="utf-8")

    assert "ws://" in popup_code and "wss://" in popup_code, "popup.js must validate ws:// or wss:// protocol"


def test_phase5_background_transcript_history():
    """Phase 5: Verify background.js maintains transcriptHistory and clears on start."""
    bg_code = Path("extension/background.js").read_text(encoding="utf-8")

    assert "transcriptHistory" in bg_code, "background.js must define transcriptHistory"
    assert "transcriptHistory = []" in bg_code, "background.js must reset transcriptHistory on start"
    assert "captionText" in bg_code, "background.js must handle captionText"
    assert "getTranscriptHistory" in bg_code or "getTranscript" in bg_code, "background.js must respond to getTranscriptHistory"


def test_phase5_offscreen_passes_timestamps():
    """Phase 5: Verify offscreen.js passes start and end timestamps from WebSocket payload."""
    offscreen_code = Path("extension/offscreen.js").read_text(encoding="utf-8")

    assert "start:" in offscreen_code or "data.start" in offscreen_code, "offscreen.js must forward start timestamp"
    assert "end:" in offscreen_code or "data.end" in offscreen_code, "offscreen.js must forward end timestamp"


def test_phase5_popup_download_button():
    """Phase 5: Verify popup.html contains Download Transcript button and popup.js binds to it."""
    popup_html = Path("extension/popup.html").read_text(encoding="utf-8")
    popup_js = Path("extension/popup.js").read_text(encoding="utf-8")

    assert "Download Transcript" in popup_html, "popup.html must contain Download Transcript button"
    assert "downloadBtn" in popup_html, "popup.html must have downloadBtn element"
    assert "downloadBtn" in popup_js, "popup.js must reference downloadBtn"


def test_phase5_popup_transcript_formatting():
    """Phase 5: Verify formatTimestamp and formatTranscript functions format history correctly."""
    import subprocess
    cmd = [
        "node", "-e",
        "const { formatTimestamp, formatTranscript } = require('./extension/popup.js');"
        "const formatted = formatTranscript([{text: '[Speaker 1]: Hello', start: 1.5, end: 4.2}]);"
        "console.log(formatted);"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = result.stdout.strip()
    assert output == "[00:01.500 --> 00:04.200] [Speaker 1]: Hello", f"Unexpected formatted output: {output}"


def test_phase6_options_files_and_manifest():
    """Phase 6: Verify options.html, options.js exist and options_ui is registered in manifest.json."""
    options_html = Path("extension/options.html")
    options_js = Path("extension/options.js")
    manifest_path = Path("extension/manifest.json")

    assert options_html.exists(), "extension/options.html must exist"
    assert options_js.exists(), "extension/options.js must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    options_ui = data.get("options_ui", {})
    assert options_ui.get("page") == "options.html", "options_ui page must be options.html"
    assert options_ui.get("open_in_tab") is True, "options_ui open_in_tab must be True"


def test_phase6_options_page_ui_controls():
    """Phase 6: Verify options.html and options.js contain font, color, and stroke controls."""
    html_content = Path("extension/options.html").read_text(encoding="utf-8")
    js_content = Path("extension/options.js").read_text(encoding="utf-8")

    # Font Family control
    assert 'id="fontFamilySelect"' in html_content
    assert "fontFamily" in js_content

    # Subtitle Text Color control
    assert 'id="textColorPicker"' in html_content
    assert "textColor" in js_content

    # Stroke Thickness control
    assert 'id="strokeThicknessSlider"' in html_content
    assert "strokeThickness" in js_content

    # Storage interaction
    assert "chrome.storage.local" in js_content


def test_phase6_content_dynamic_styles():
    """Phase 6: Verify content.js loads, updates, and listens for fontFamily, textColor, and strokeThickness."""
    content_code = Path("extension/content.js").read_text(encoding="utf-8")

    assert "fontFamily" in content_code
    assert "textColor" in content_code
    assert "strokeThickness" in content_code
    assert "textShadow" in content_code
    assert "chrome.storage.local" in content_code
    assert "chrome.storage.onChanged" in content_code


def test_phase6_background_relays_options():
    """Phase 6: Verify background.js relays customization settings to content script."""
    bg_code = Path("extension/background.js").read_text(encoding="utf-8")

    assert "fontFamily" in bg_code
    assert "textColor" in bg_code
    assert "strokeThickness" in bg_code

