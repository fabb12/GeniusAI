from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super(ResizableRubberBand, self).__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.drag_start_position = QPoint()
        self.is_dragging = False
        self.is_resizing = False
        self.resize_handle = None
        self.handles = []
        self.handle_size = 8

        self.setGeometry(QRect(100, 100, 200, 150))
        self.update_handles()

    def update_handles(self):
        self.handles = []
        s = self.handle_size
        w = self.width()
        h = self.height()
        # Top-left, top-right, bottom-left, bottom-right
        self.handles.append(QRect(0, 0, s, s))
        self.handles.append(QRect(w - s, 0, s, s))
        self.handles.append(QRect(0, h - s, s, s))
        self.handles.append(QRect(w - s, h - s, s, s))
        # Top, bottom, left, right
        self.handles.append(QRect(s, 0, w - 2 * s, s))
        self.handles.append(QRect(s, h - s, w - 2 * s, s))
        self.handles.append(QRect(0, s, s, h - 2 * s))
        self.handles.append(QRect(w - s, s, s, h - 2 * s))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.is_dragging = True

            for i, handle in enumerate(self.handles):
                if handle.contains(event.pos()):
                    self.is_resizing = True
                    self.resize_handle = i
                    break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.pos() - self.drag_start_position
            if self.is_resizing:
                self.resize_geometry(delta)
            else: # Moving
                self.move(self.pos() + delta)
        self.update_cursor(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.resize_handle = None
        super().mouseReleaseEvent(event)

    def resize_geometry(self, delta):
        rect = self.geometry()
        if self.resize_handle == 0: # Top-left
            rect.setTopLeft(rect.topLeft() + delta)
        elif self.resize_handle == 1: # Top-right
            rect.setTopRight(rect.topRight() + delta)
        elif self.resize_handle == 2: # Bottom-left
            rect.setBottomLeft(rect.bottomLeft() + delta)
        elif self.resize_handle == 3: # Bottom-right
            rect.setBottomRight(rect.bottomRight() + delta)
        elif self.resize_handle == 4: # Top
            rect.setTop(rect.top() + delta.y())
        elif self.resize_handle == 5: # Bottom
            rect.setBottom(rect.bottom() + delta.y())
        elif self.resize_handle == 6: # Left
            rect.setLeft(rect.left() + delta.x())
        elif self.resize_handle == 7: # Right
            rect.setRight(rect.right() + delta.x())

        self.setGeometry(rect)
        self.update_handles()

    def update_cursor(self, pos):
        cursor = Qt.CursorShape.ArrowCursor
        for i, handle in enumerate(self.handles):
            if handle.contains(pos):
                if i in [0, 3]: cursor = Qt.CursorShape.SizeFDiagCursor
                elif i in [1, 2]: cursor = Qt.CursorShape.SizeBDiagCursor
                elif i in [4, 5]: cursor = Qt.CursorShape.SizeVerCursor
                elif i in [6, 7]: cursor = Qt.CursorShape.SizeHorCursor
                break
        self.setCursor(cursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the main rectangle
        rect_pen = QPen(QColor(255, 0, 0, 200), 2, Qt.PenStyle.SolidLine)
        painter.setPen(rect_pen)
        painter.setBrush(QColor(255, 0, 0, 50))
        painter.drawRect(self.rect().adjusted(self.handle_size // 2, self.handle_size // 2, -self.handle_size // 2, -self.handle_size // 2))

        # Draw resize handles
        handle_pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(handle_pen)
        painter.setBrush(QColor(255, 255, 255))
        for handle in self.handles[:4]: # only corner handles
             painter.drawRect(handle)

    def get_geometry(self):
        return self.geometry()
