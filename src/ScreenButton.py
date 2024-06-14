from PyQt6.QtGui import QPainter, QPen, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QSize

class ToggleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setMinimumSize(QSize(80, 40))
        self.setStyleSheet(self.get_style())
        self.clicked.connect(self.update_button_style)

    def update_button_style(self):
        self.setStyleSheet(self.get_style())

    def get_style(self):
        if self.isChecked():
            return """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 20px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
            }
            """
        else:
            return """
            QPushButton {
                background-color: #CCC;
                color: black;
                border-radius: 20px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
            }
            """

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
