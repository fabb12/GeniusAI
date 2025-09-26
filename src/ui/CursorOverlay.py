import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor
from PyQt6.QtCore import Qt, QTimer

class CursorOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(0, 0, 40, 40)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.radius = 15
        self.pen_width = 3

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 0, 0), self.pen_width)
        painter.setPen(pen)
        center = self.rect().center()
        painter.drawEllipse(center, self.radius, self.radius)

    def update_position(self):
        pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)

    def showEvent(self, event):
        self.timer.start(10) # Update position every 10ms
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)