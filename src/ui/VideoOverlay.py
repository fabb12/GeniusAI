from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QColor

class VideoOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Assicurati di ricevere gli eventi del mouse
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.rect_start = None
        self.rect_end = None
        self.crop_rect = QRect()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.rect_start = event.pos()
            self.rect_end = self.rect_start
            self.crop_rect = QRect()  # Reset
            self.update()

    def mouseMoveEvent(self, event):
        if self.rect_start:
            self.rect_end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect_start:
            self.rect_end = event.pos()
            self.crop_rect = QRect(self.rect_start, self.rect_end).normalized()
            self.rect_start = None
            self.rect_end = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Per debug: disegna un riempimento semi-trasparente per verificare che l'overlay sia visibile
        painter.fillRect(self.rect(), QColor(255, 0, 0, 50))
        # Imposta una penna rossa tratteggiata
        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        # Se stai disegnando il rettangolo attivo
        if self.rect_start and self.rect_end:
            rect = QRect(self.rect_start, self.rect_end).normalized()
            painter.drawRect(rect)
        elif not self.crop_rect.isNull():
            painter.drawRect(self.crop_rect)
