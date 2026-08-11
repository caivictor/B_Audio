from PyQt6.QtWidgets import QApplication, QWidget
import sys

app = QApplication(sys.argv)
win = QWidget()
win.show()
print(hasattr(win.windowHandle(), "startSystemMove"))
