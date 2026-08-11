import re

with open("client/main.py", "r") as f:
    content = f.read()

close_event_code = """
    def closeEvent(self, event):
        \"\"\"Ensure the entire application exits when the overlay is closed.\"\"\"
        super().closeEvent(event)
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        import os
        os._exit(0) # Force kill to prevent any lingering asyncio/websocket threads
"""

# Insert before the last method in TransparentOverlayWindow
if "    def keyPressEvent" in content:
    content = content.replace("    def keyPressEvent", close_event_code + "\n    def keyPressEvent")
    with open("client/main.py", "w") as f:
        f.write(content)
        print("Patched client/main.py")
