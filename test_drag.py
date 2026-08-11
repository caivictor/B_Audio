import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent

class DragWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Try to drag me!")
        self.label.setStyleSheet("background-color: rgba(0,0,0,150); color: white; padding: 20px;")
        
        # Test fix
        # self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.layout.addWidget(self.label)
        self._drag_position = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_position is not None:
            self.move(event.globalPosition().toPoint() - self._drag_position)

app = QApplication(sys.argv)
win = DragWindow()
win.show()
# app.exec()
