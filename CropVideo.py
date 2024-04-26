from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtWidgets import QWidget
class SelectionOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.isSelecting = False
        self.origin = QPoint()
        self.end = QPoint()
        self.cropRect = QRect()

    def mousePressEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.origin = event.position().toPoint()
            self.end = self.origin
            self.isSelecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.isSelecting:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.isSelecting:
            self.isSelecting = False
            self.end = event.position().toPoint()
            self.cropRect = QRect(self.origin, self.end).normalized()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.cropRect.isNull():
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.drawRect(self.cropRect)

class CropVideoWidget(QVideoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.origin = QPoint()
        self.end = QPoint()
        self.isSelecting = False
        self.cropRect = QRect()

    def mousePressEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.origin = event.position().toPoint()
            self.end = self.origin
            self.isSelecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.isSelecting:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.isSelecting:
            self.end = event.position().toPoint()
            self.isSelecting = False
            self.cropRect = QRect(self.origin, self.end).normalized()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)  # Renderizza prima il video
        if not self.cropRect.isNull():
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.drawRect(self.cropRect)  # Disegna il rettangolo
    def getCropRect(self):
        return self.cropRect.normalized()