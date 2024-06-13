from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPainter, QPen, QFont
from PyQt6.QtCore import Qt


class ScreenButton(QPushButton):
    def __init__(self, text, screen_number, parent=None):
        super().__init__(text, parent)
        self.screen_number = screen_number
        self.setFixedSize(100, 100)
        self.setStyleSheet("QPushButton { background-color: gray; color: white; }")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen()
        pen.setColor(Qt.GlobalColor.white)
        painter.setPen(pen)

        # Imposta un font più grande
        font = QFont()
        font.setPointSize(20)  # Dimensione del font aumentata
        painter.setFont(font)

        # Disegna il testo al centro del pulsante
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.screen_number))
