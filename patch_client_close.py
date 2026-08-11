with open("client/main.py", "r") as f:
    content = f.read()

close_event_code = """
    def closeEvent(self, event):
        \"\"\"Ensure the entire application exits when the overlay is closed.\"\"\"
        super().closeEvent(event)
        import os
        os._exit(0)  # Force kill to prevent any lingering asyncio/websocket threads

    def keyPressEvent(self, event):
        \"\"\"Close on Escape key\"\"\"
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def enterEvent"""

content = content.replace("    def enterEvent", close_event_code)

with open("client/main.py", "w") as f:
    f.write(content)
print("Done")
