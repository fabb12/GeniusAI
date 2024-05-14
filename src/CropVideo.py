from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtWidgets import QWidget

class CropVideoWidget(QVideoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)  # Permette il tracking del mouse sul widget
        self.isSelecting = False  # Flag per controllare se la selezione è attiva
        self.origin = QPoint()  # Punto di origine del rettangolo di selezione
        self.end = QPoint()  # Punto finale del rettangolo di selezione
        self.cropRect = QRect()  # QRect che mantiene le coordinate del rettangolo di selezione

    def mousePressEvent(self, event):
        # Attiva la selezione solo con il tasto sinistro del mouse e il tasto Control premuto
        if event.buttons() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.origin = event.position().toPoint()
            self.end = self.origin
            self.isSelecting = True
            self.update()

    def mouseMoveEvent(self, event):
        # Aggiorna il punto finale durante il movimento del mouse se la selezione è attiva
        if self.isSelecting:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        # Completa la selezione quando il tasto del mouse viene rilasciato
        if self.isSelecting:
            self.isSelecting = False
            self.end = event.position().toPoint()
            self.cropRect = QRect(self.origin, self.end).normalized()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)  # Renderizza il video prima di sovrapporre il rettangolo
        if not self.cropRect.isNull():
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine))  # Imposta il colore e lo stile della penna
            painter.setBrush(QColor(0, 0, 0, 0))  # Nessun colore di riempimento
            painter.drawRect(self.cropRect)  # Disegna il rettangolo di selezione

    def getCropRect(self):
        return self.cropRect.normalized()  # Restituisce il rettangolo di selezione normalizzato
