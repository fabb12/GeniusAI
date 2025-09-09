from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class ScreenButton(QWidget):
    clicked = pyqtSignal(int)

    def __init__(self, screen_number, resolution, is_primary, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.screen_number = screen_number
        self.is_selected = False

        self.setFixedSize(150, 100)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        self.number_label = QLabel(f"Schermo {self.screen_number}")
        font = self.number_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.number_label.setFont(font)
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.resolution_label = QLabel(resolution)
        font = self.resolution_label.font()
        font.setPointSize(10)
        self.resolution_label.setFont(font)
        self.resolution_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.primary_label = QLabel("Primario" if is_primary else "")
        font = self.primary_label.font()
        font.setPointSize(9)
        font.setItalic(True)
        self.primary_label.setFont(font)
        self.primary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.number_label)
        self.layout.addWidget(self.resolution_label)
        self.layout.addWidget(self.primary_label)

        self.update_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.screen_number - 1)

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                ScreenButton {
                    background-color: #1a93ec;
                    color: white;
                    border: 2px solid #1a93ec;
                    border-radius: 10px;
                }
                QLabel {
                    color: white;
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                ScreenButton {
                    background-color: gray;
                    color: white;
                    border: 2px solid gray;
                    border-radius: 10px;
                }
                QLabel {
                    color: white;
                    background-color: transparent;
                }
            """)
