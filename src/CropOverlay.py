from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QSlider, QLabel, QGroupBox, QPushButton, QHBoxLayout, QCheckBox, QComboBox, QFileDialog, QMessageBox, QSizePolicy, QTextEdit
from PyQt6.QtGui import QPainter, QColor, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QPoint, QTimer, QTime, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class QOverlayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 0, 0, 127))  # Rosso semi-trasparente
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect().adjusted(10, 10, -10, -10)  # Rettangolo con margine
        painter.drawRect(rect)