from PyQt6.QtWidgets import QWidget, QRubberBand
from PyQt6.QtCore import QRect, QPoint, Qt, QSize
from PyQt6.QtGui import QPainter, QColor

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

        self.setGeometry(parent.rect())

        # Initialize an internal geometry for the rubber band
        initial_width = self.width() / 2
        initial_height = self.height() / 2
        initial_x = (self.width() - initial_width) / 2
        initial_y = (self.height() - initial_height) / 2
        self._band_geometry = QRect(int(initial_x), int(initial_y), int(initial_width), int(initial_height))
        self.rubber_band.setGeometry(self._band_geometry)

        self.drag_position = None
        self.resize_handle = None
        self.handle_size = 10
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def band_geometry(self):
        return self._band_geometry

    def set_band_geometry(self, rect):
        self._band_geometry = rect.normalized()
        self.rubber_band.setGeometry(self._band_geometry)
        self.update()

    def get_handles(self):
        rect = self._band_geometry
        handles = {
            "top-left": QRect(rect.topLeft() - QPoint(self.handle_size//2, self.handle_size//2), QSize(self.handle_size, self.handle_size)),
            "top-right": QRect(rect.topRight() - QPoint(-self.handle_size//2, self.handle_size//2), QSize(self.handle_size, self.handle_size)),
            "bottom-left": QRect(rect.bottomLeft() - QPoint(self.handle_size//2, -self.handle_size//2), QSize(self.handle_size, self.handle_size)),
            "bottom-right": QRect(rect.bottomRight() + QPoint(-self.handle_size//2, -self.handle_size//2), QSize(self.handle_size, self.handle_size)),
            "top": QRect(rect.left() + rect.width()//2 - self.handle_size//2, rect.top() - self.handle_size//2, self.handle_size, self.handle_size),
            "bottom": QRect(rect.left() + rect.width()//2 - self.handle_size//2, rect.bottom() - self.handle_size//2, self.handle_size, self.handle_size),
            "left": QRect(rect.left() - self.handle_size//2, rect.top() + rect.height()//2 - self.handle_size//2, self.handle_size, self.handle_size),
            "right": QRect(rect.right() - self.handle_size//2, rect.top() + rect.height()//2 - self.handle_size//2, self.handle_size, self.handle_size),
        }
        return handles

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.pos()
            for handle, rect in self.get_handles().items():
                if rect.contains(event.pos()):
                    self.resize_handle = handle
                    return

            if self._band_geometry.contains(event.pos()):
                self.resize_handle = "move"
            else:
                self.resize_handle = None

    def mouseMoveEvent(self, event):
        if self.drag_position is not None:
            delta = event.pos() - self.drag_position
            new_rect = QRect(self._band_geometry)

            if self.resize_handle == "move":
                new_rect.translate(delta)
            elif self.resize_handle:
                if "top" in self.resize_handle:
                    new_rect.setTop(new_rect.top() + delta.y())
                if "bottom" in self.resize_handle:
                    new_rect.setBottom(new_rect.bottom() + delta.y())
                if "left" in self.resize_handle:
                    new_rect.setLeft(new_rect.left() + delta.x())
                if "right" in self.resize_handle:
                    new_rect.setRight(new_rect.right() + delta.x())

            # Boundary checks
            parent_rect = self.parentWidget().rect()
            if new_rect.left() < parent_rect.left(): new_rect.setLeft(parent_rect.left())
            if new_rect.right() > parent_rect.right(): new_rect.setRight(parent_rect.right())
            if new_rect.top() < parent_rect.top(): new_rect.setTop(parent_rect.top())
            if new_rect.bottom() > parent_rect.bottom(): new_rect.setBottom(parent_rect.bottom())

            self.set_band_geometry(new_rect)
            self.drag_position = event.pos()
        else:
            cursor = Qt.CursorShape.ArrowCursor
            for handle, rect in self.get_handles().items():
                if rect.contains(event.pos()):
                    if "top-left" in handle or "bottom-right" in handle:
                        cursor = Qt.CursorShape.SizeFDiagCursor
                    elif "top-right" in handle or "bottom-left" in handle:
                        cursor = Qt.CursorShape.SizeBDiagCursor
                    elif "top" in handle or "bottom" in handle:
                        cursor = Qt.CursorShape.SizeVerCursor
                    else:
                        cursor = Qt.CursorShape.SizeHorCursor
                    break
            self.setCursor(cursor)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.resize_handle = None

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw transparent yellow rectangle
        painter.fillRect(self._band_geometry, QColor(255, 255, 0, 100))

        # Draw handles
        painter.setBrush(QColor("black"))
        for rect in self.get_handles().values():
            painter.drawRect(rect)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        # When the main widget is resized, we must ensure the band geometry is also updated.
        # Here we can choose to reset or scale it. For simplicity, let's reset to the center.
        initial_width = rect.width() / 2
        initial_height = rect.height() / 2
        initial_x = (rect.width() - initial_width) / 2
        initial_y = (rect.height() - initial_height) / 2
        self._band_geometry = QRect(int(initial_x), int(initial_y), int(initial_width), int(initial_height))
        self.update()
