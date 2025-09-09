from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt

class MonitorPreview(QWidget):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(self.monitor.x, self.monitor.y, self.monitor.width, self.monitor.height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 0, 0), 10)  # Red border, 10px wide
        painter.setPen(pen)
        painter.drawRect(self.rect())
