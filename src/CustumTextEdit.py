from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import pyqtSignal
class CustomTextEdit(QTextEdit):
    cursorPositionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.cursorPositionChanged.emit()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.cursorPositionChanged.emit()

    def insertFromMimeData(self, source):
        if source.hasText():
            plain_text = source.text()
            self.insertPlainText(plain_text)
        else:
            super().insertFromMimeData(source)
        self.cursorPositionChanged.emit()
