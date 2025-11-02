from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.dragging = False
        self.resizing = False
        self.drag_start_position = QPoint()
        self.resize_handle = None
        self.handles = {}
        self.handle_size = 10
        self.updateHandles()
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Disegna il bordo giallo solido
        pen = QPen(QColor("yellow"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        # Disegna il riempimento giallo semi-trasparente
        fill_color = QColor(255, 255, 0, 80)  # Giallo con 80/255 di opacità
        painter.setBrush(fill_color)

        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # Disegna le maniglie di ridimensionamento
        painter.setBrush(QColor("yellow"))
        for handle, rect in self.handles.items():
            painter.drawRect(rect)

    def updateHandles(self):
        s = self.handle_size
        self.handles = {
            "top-left": QRect(0, 0, s, s),
            "top-right": QRect(self.width() - s, 0, s, s),
            "bottom-left": QRect(0, self.height() - s, s, s),
            "bottom-right": QRect(self.width() - s, self.height() - s, s, s),
        }

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.updateHandles()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.globalPosition().toPoint()
            for handle, rect in self.handles.items():
                if rect.contains(event.pos()):
                    self.resizing = True
                    self.resize_handle = handle
                    self.original_geometry = self.geometry()
                    self.update()
                    return

            self.dragging = True

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.resizing:
            self.resizeWidget(event.globalPosition().toPoint())
        elif self.dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            new_pos = self.mapToParent(self.pos() + delta)
            # Limita il movimento all'interno del genitore
            parent_rect = self.parentWidget().rect()
            new_rect = self.geometry().translated(delta)

            if new_rect.left() < parent_rect.left():
                new_rect.moveLeft(parent_rect.left())
            if new_rect.top() < parent_rect.top():
                new_rect.moveTop(parent_rect.top())
            if new_rect.right() > parent_rect.right():
                new_rect.moveRight(parent_rect.right())
            if new_rect.bottom() > parent_rect.bottom():
                new_rect.moveBottom(parent_rect.bottom())

            self.move(new_rect.topLeft())
            self.drag_start_position = event.globalPosition().toPoint()

        else:
            # Aggiorna il cursore del mouse in base alla posizione
            self.updateCursorShape(event.pos())

    def updateCursorShape(self, pos):
        cursor = Qt.CursorShape.ArrowCursor
        for handle, rect in self.handles.items():
            if rect.contains(pos):
                if handle in ["top-left", "bottom-right"]:
                    cursor = Qt.CursorShape.SizeFDiagCursor
                elif handle in ["top-right", "bottom-left"]:
                    cursor = Qt.CursorShape.SizeBDiagCursor
                break
        self.setCursor(cursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_handle = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def resizeWidget(self, new_pos):
        delta = new_pos - self.drag_start_position
        new_rect = QRect(self.original_geometry)

        if self.resize_handle == "top-left":
            new_rect.setTopLeft(new_rect.topLeft() + delta)
        elif self.resize_handle == "top-right":
            new_rect.setTopRight(new_rect.topRight() + delta)
        elif self.resize_handle == "bottom-left":
            new_rect.setBottomLeft(new_rect.bottomLeft() + delta)
        elif self.resize_handle == "bottom-right":
            new_rect.setBottomRight(new_rect.bottomRight() + delta)

        # Limita il ridimensionamento all'interno del genitore
        parent_rect = self.parentWidget().rect()
        new_rect = new_rect.intersected(parent_rect)

        # Assicura una dimensione minima per evitare che il widget si "inverta"
        if new_rect.width() < self.handle_size:
            if self.resize_handle in ["top-left", "bottom-left"]:
                 new_rect.setLeft(new_rect.right() - self.handle_size)
            else:
                 new_rect.setWidth(self.handle_size)

        if new_rect.height() < self.handle_size:
            if self.resize_handle in ["top-left", "top-right"]:
                new_rect.setTop(new_rect.bottom() - self.handle_size)
            else:
                new_rect.setHeight(self.handle_size)

        self.setGeometry(new_rect)
        self.update()
        self.updateHandles()
