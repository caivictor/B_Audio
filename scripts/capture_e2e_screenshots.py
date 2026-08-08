import os
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.main import TransparentOverlayWindow

def main():
    os.makedirs("screenshots", exist_ok=True)
    app = QApplication(sys.argv)

    # Screenshot 1: Phase 1 Native Spanish Caption Overlay
    overlay_es = TransparentOverlayWindow(
        initial_text="Hola, bienvenidos a la demostración de WebCaptioner."
    )
    overlay_es.show()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.05)
    overlay_es.grab().save("screenshots/phase1_spanish_caption_overlay.png")
    overlay_es.close()

    # Screenshot 2: Phase 1 English Caption Overlay
    overlay_en = TransparentOverlayWindow(
        initial_text="Hello, welcome to the real-time WebCaptioner demonstration."
    )
    overlay_en.show()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.05)
    overlay_en.grab().save("screenshots/phase1_english_caption_overlay.png")
    overlay_en.close()

    # Screenshot 3: Standby / Ready Overlay
    overlay_ready = TransparentOverlayWindow(initial_text="WebCaptioner Ready")
    overlay_ready.show()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.05)
    overlay_ready.grab().save("screenshots/phase1_overlay_ready.png")
    overlay_ready.close()

    print("Successfully captured screenshots under screenshots/")

if __name__ == "__main__":
    main()
