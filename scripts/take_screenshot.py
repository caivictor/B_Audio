"""
Script to launch WebCaptioner overlay UI, simulate receiving a caption,
and capture screenshots for verification.
"""

import os
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QGuiApplication

# Ensure client module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.main import TransparentOverlayWindow


def main():
    os.makedirs("screenshots", exist_ok=True)

    app = QApplication(sys.argv)

    overlay = TransparentOverlayWindow(
        initial_text="Hola, bienvenidos a la demostración de WebCaptioner."
    )
    overlay.show()

    # Process events to render window
    for _ in range(10):
        app.processEvents()
        time.sleep(0.05)

    # Grab widget screenshot
    widget_pixmap = overlay.grab()
    widget_path = "screenshots/overlay_widget.png"
    widget_pixmap.save(widget_path)
    print(f"Saved widget screenshot to {widget_path}")

    # Grab full screen screenshot
    primary_screen = QGuiApplication.primaryScreen()
    if primary_screen:
        screen_pixmap = primary_screen.grabWindow(0)
        screen_path = "screenshots/overlay_desktop.png"
        screen_pixmap.save(screen_path)
        print(f"Saved desktop screenshot to {screen_path}")

    app.quit()


if __name__ == "__main__":
    main()
