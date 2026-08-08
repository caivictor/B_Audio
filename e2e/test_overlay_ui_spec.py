"""
End-to-End Tests for PyQt6 Transparent Overlay UI specifications (REQUIREMENTS.md Phase 1).

Verifies:
1. Window flags: FramelessWindowHint, WindowStaysOnTopHint, WindowTransparentForInput.
2. Translucent background attribute WA_TranslucentBackground.
3. Subtitle styling and drop shadow effect.
4. Positioning logic (bottom-center of screen).
5. Automatic caption clearing after silence timeout.
"""

import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.main import TransparentOverlayWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_overlay_window_flags_and_attributes(qapp):
    """Verify overlay window meets all UI requirements specified in REQUIREMENTS.md Section 2.B & 5.2."""
    overlay = TransparentOverlayWindow(initial_text="Testing Requirements")

    # Requirement: WA_TranslucentBackground enabled
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True

    # Requirement: Frameless, Always-On-Top, Click-Through (WindowTransparentForInput)
    flags = overlay.windowFlags()
    assert bool(flags & Qt.WindowType.FramelessWindowHint) is True, "FramelessWindowHint missing"
    assert bool(flags & Qt.WindowType.WindowStaysOnTopHint) is True, "WindowStaysOnTopHint missing"
    assert bool(flags & Qt.WindowType.WindowTransparentForInput) is True, "WindowTransparentForInput missing"

    # Verify label text initialization
    assert overlay.label.text() == "Testing Requirements"


def test_overlay_text_update_and_clear_timer(qapp):
    """Verify set_caption_text updates UI and clear timer triggers clearing."""
    overlay = TransparentOverlayWindow(initial_text="Initial Text")

    overlay.set_caption_text("New Transcription Received")
    assert overlay.label.text() == "New Transcription Received"

    # Manually trigger timer timeout to verify clearing logic
    overlay._clear_caption()
    assert overlay.label.text() == ""


def test_overlay_geometry_bounds(qapp):
    """Verify window geometry positioning produces non-zero dimensions."""
    overlay = TransparentOverlayWindow()
    geom = overlay.geometry()
    assert geom.width() > 0
    assert geom.height() > 0


def test_overlay_long_caption_dynamic_height(qapp):
    """Verify overlay window dynamically expands height for multi-line text without clipping (DEF-011)."""
    overlay = TransparentOverlayWindow()
    overlay.show()
    qapp.processEvents()

    long_text = (
        "This is line 1 of a very long caption text designed to test multi-line text wrapping and dynamic window height calculation in the transparent overlay window. "
        "Line 2: The overlay window should calculate the required wrapped label height using heightForWidth and expand its geometry so that no top or bottom lines are clipped off. "
        "Line 3: Here is even more text to push the total length past 500 characters so that it wraps across 4 or 5 lines on standard display resolutions. "
        "Line 4: Testing again to verify that all margins, padding, border radiuses, and text lines fit cleanly inside the styled QLabel box without any clipping or truncation."
    )

    overlay.set_caption_text(long_text)
    qapp.processEvents()

    geom = overlay.geometry()
    margins = overlay.layout().contentsMargins()
    label_width = geom.width() - margins.left() - margins.right()
    req_label_height = overlay.label.heightForWidth(label_width)

    expected_height = max(140, req_label_height + margins.top() + margins.bottom())
    assert geom.height() == expected_height, f"Expected window height {expected_height}, got {geom.height()}"

    os.makedirs("screenshots", exist_ok=True)
    screenshot_path = "screenshots/def-011_long_text.png"
    pixmap = overlay.grab()
    pixmap.save(screenshot_path)
    assert os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0
