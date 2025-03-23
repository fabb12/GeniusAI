from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush

class VideoFrameLabel(QLabel):
    selectionCompleted = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)

        # Per la selezione
        self.selecting = False
        self.start_point = None
        self.current_point = None
        self.selection_rect = QRect()

        # Per il disegno
        self.setMouseTracking(True)

    def paintEvent(self, event):
        super().paintEvent(event)

        # Disegna sopra il video solo se c'è qualcosa da mostrare
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Disegna il rettangolo durante la selezione
        if self.selecting and self.start_point and self.current_point:
            rect = QRect(self.start_point, self.current_point).normalized()
            self._drawSelection(painter, rect)
        # Disegna il rettangolo di selezione salvato
        elif not self.selection_rect.isEmpty():
            self._drawSelection(painter, self.selection_rect)

    def _drawSelection(self, painter, rect):
        # Disegna un rettangolo con linea tratteggiata rossa
        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 0, 0, 30)))  # Rosso semi-trasparente
        painter.drawRect(rect)

        # Disegna maniglie agli angoli come punti rossi
        handle_size = 8
        painter.setBrush(QBrush(QColor(255, 0, 0)))  # Punti rossi
        painter.setPen(QPen(Qt.PenStyle.NoPen))

        corners = [
            (rect.left(), rect.top()),
            (rect.right(), rect.top()),
            (rect.left(), rect.bottom()),
            (rect.right(), rect.bottom())
        ]

        for x, y in corners:
            painter.drawEllipse(x - handle_size // 2, y - handle_size // 2, handle_size, handle_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Tasto destro inizia una nuova selezione
            self.selecting = True
            self.start_point = event.position().toPoint()
            self.current_point = self.start_point
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton:
            # Tasto sinistro resetta la selezione corrente
            self.clearSelection()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.current_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self.selecting:
            self.selecting = False
            self.current_point = event.position().toPoint()
            self.selection_rect = QRect(self.start_point, self.current_point).normalized()
            self.selectionCompleted.emit(self.selection_rect)
            self.update()

    def clearSelection(self):
        # Reset completo di tutti i parametri della selezione
        self.selection_rect = QRect()
        self.selecting = False
        self.start_point = None
        self.current_point = None
        self.update()

    def getSelectionRect(self):
        return self.selection_rect