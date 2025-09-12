from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QTimer

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

        # Imposta un timer per chiudere la finestra dopo 5 secondi
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(5000)  # 5000 millisecondi = 5 secondi

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 0, 0), 10)  # Red border, 10px wide
        painter.setPen(pen)
        painter.drawRect(self.rect())
