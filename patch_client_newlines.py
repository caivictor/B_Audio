import re

with open("client/main.py", "r") as f:
    content = f.read()

# Fix 1: Draggable window. Use windowHandle().startSystemMove() if available, and set _user_dragged.
mouse_press_old = """    def mousePressEvent(self, event: QMouseEvent):
        \"\"\"Capture drag start position when left mouse button is pressed.\"\"\"
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()"""

mouse_press_new = """    def mousePressEvent(self, event: QMouseEvent):
        \"\"\"Capture drag start position when left mouse button is pressed.\"\"\"
        if event.button() == Qt.MouseButton.LeftButton:
            self._user_dragged = True
            if self.windowHandle() and hasattr(self.windowHandle(), "startSystemMove"):
                if self.windowHandle().startSystemMove():
                    event.accept()
                    return
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()"""

content = content.replace(mouse_press_old, mouse_press_new)

# Fix 2: Add newlines before speaker tags
parse_tags_old = """    for i, match in enumerate(escaped_matches):
        prefix = escaped_text[last_idx:match.start()]
        if prefix:
            result.append(prefix)"""

parse_tags_new = """    for i, match in enumerate(escaped_matches):
        prefix = escaped_text[last_idx:match.start()]
        
        # Insert line break if a new speaker tag appears and there isn't already one
        if i > 0:
            if prefix and not prefix.rstrip().endswith('<br>'):
                prefix += '<br>'
            elif not prefix:
                result.append('<br>')
                
        if prefix:
            result.append(prefix)"""

content = content.replace(parse_tags_old, parse_tags_new)

with open("client/main.py", "w") as f:
    f.write(content)

