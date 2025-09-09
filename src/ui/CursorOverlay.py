from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPolygon, QCursor

class CursorOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFixedSize(30, 30)  # A small, fixed-size window

        self.cursor_style = 'red_dot'  # Default style
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)  # Update position roughly 60 times per second

    def setCursorStyle(self, style):
        """
        Sets the style of the cursor.
        :param style: 'red_dot' or 'yellow_triangle'
        """
        if style in ['red_dot', 'yellow_triangle']:
            self.cursor_style = style
            self.update()  # Trigger a repaint

    def update_position(self):
        """
        Updates the position of the overlay to match the mouse cursor.
        """
        pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)

    def paintEvent(self, event):
        """
        Draws the custom cursor.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.cursor_style == 'red_dot':
            painter.setBrush(QColor(255, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(5, 5, 20, 20)  # Centered red dot
        elif self.cursor_style == 'yellow_triangle':
            painter.setBrush(QColor(255, 255, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            points = [
                QPoint(15, 5),
                QPoint(5, 25),
                QPoint(25, 25)
            ]
            painter.drawPolygon(QPolygon(points))
