from PyQt6.QtGui import QPainter, QPen, QColor, QWheelEvent, QKeyEvent
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout
import sys
import os
import logging

class CropVideoWidget(QVideoWidget):
    """A simple video widget that serves as a display surface for video content."""
    spacePressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F:
            if self.isFullScreen():
                self.setFullScreen(False)
            else:
                self.setFullScreen(True)
        elif event.key() == Qt.Key.Key_Space:
            self.spacePressed.emit()
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    video_widget = CropVideoWidget()
    layout.addWidget(video_widget)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
