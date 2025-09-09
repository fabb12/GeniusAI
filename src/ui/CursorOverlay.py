from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon, QBrush
from PyQt6.QtCore import Qt, QPoint, QTimer

class CursorOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.show_red_dot = True
        self.show_yellow_triangle = True

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(10)  # Update every 10ms

    def update_position(self):
        pos = self.cursor().pos()
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPoint(self.width() // 2, self.height() // 2)

        if self.show_red_dot:
            painter.setBrush(QColor(255, 0, 0, 180))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, 5, 5)

        if self.show_yellow_triangle:
            painter.setBrush(QColor(255, 255, 0, 180))
            painter.setPen(Qt.PenStyle.NoPen)

            triangle = QPolygon([
                QPoint(center.x(), center.y() - 15),
                QPoint(center.x() - 10, center.y() - 5),
                QPoint(center.x() + 10, center.y() - 5)
            ])
            painter.drawPolygon(triangle)

    def set_show_red_dot(self, show):
        self.show_red_dot = show
        self.update()

    def set_show_yellow_triangle(self, show):
        self.show_yellow_triangle = show
        self.update()
