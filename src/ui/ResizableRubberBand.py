from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super(ResizableRubberBand, self).__init__(parent)
        self.setMouseTracking(True)

        self.drag_start_position = QPoint()
        self.drag_start_geometry = QRect()  # Store geometry at start of drag
        self.is_dragging = False
        self.is_resizing = False
        self.resize_handle = None
        self.handles = []
        self.handle_size = 10
        self.min_size = 20  # Minimum crop size

        self.setGeometry(QRect(100, 100, 200, 150))
        self.update_handles()

    def update_handles(self):
        self.handles = []
        s = self.handle_size
        half_s = s // 2
        w = self.width()
        h = self.height()

        # Corner handles (0-3)
        self.handles.append(QRect(0, 0, s, s))  # Top-left
        self.handles.append(QRect(w - s, 0, s, s))  # Top-right
        self.handles.append(QRect(0, h - s, s, s))  # Bottom-left
        self.handles.append(QRect(w - s, h - s, s, s))  # Bottom-right

        # Side handles (4-7)
        self.handles.append(QRect(w // 2 - half_s, 0, s, s))  # Top
        self.handles.append(QRect(w // 2 - half_s, h - s, s, s))  # Bottom
        self.handles.append(QRect(0, h // 2 - half_s, s, s))  # Left
        self.handles.append(QRect(w - s, h // 2 - half_s, s, s))  # Right

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.drag_start_geometry = self.geometry()
            self.is_dragging = True
            self.is_resizing = False  # Reset resizing state

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
            else:  # Moving
                new_geo = self.drag_start_geometry.translated(delta)

                # Constrain movement to parent boundaries
                parent_rect = self.parent().rect()
                new_geo.moveLeft(max(0, min(new_geo.left(), parent_rect.width() - new_geo.width())))
                new_geo.moveTop(max(0, min(new_geo.top(), parent_rect.height() - new_geo.height())))

                self.setGeometry(new_geo)

        self.update_cursor(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.resize_handle = None
        super().mouseReleaseEvent(event)

    def resize_geometry(self, delta):
        rect = QRect(self.drag_start_geometry)
        parent_rect = self.parent().rect()

        # Adjust geometry based on the handle being dragged
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

        # Enforce minimum size, preventing inversion
        if rect.width() < self.min_size:
            if self.resize_handle in [0, 2, 6]: # Left handles
                rect.setLeft(rect.right() - self.min_size)
            else: # Right handles
                rect.setRight(rect.left() + self.min_size)

        if rect.height() < self.min_size:
            if self.resize_handle in [0, 1, 4]: # Top handles
                rect.setTop(rect.bottom() - self.min_size)
            else: # Bottom handles
                rect.setBottom(rect.top() + self.min_size)

        # Constrain to parent boundaries
        rect.setLeft(max(parent_rect.left(), rect.left()))
        rect.setTop(max(parent_rect.top(), rect.top()))
        rect.setRight(min(parent_rect.right(), rect.right()))
        rect.setBottom(min(parent_rect.bottom(), rect.bottom()))

        self.setGeometry(rect.normalized())
        self.update_handles()

    def update_cursor(self, pos):
        cursor = Qt.CursorShape.ArrowCursor
        # Only change cursor if not dragging the whole box
        if not (self.is_dragging and not self.is_resizing):
            for i, handle in enumerate(self.handles):
                if handle.contains(pos):
                    if i in [0, 3]: cursor = Qt.CursorShape.SizeFDiagCursor
                    elif i in [1, 2]: cursor = Qt.CursorShape.SizeBDiagCursor
                    elif i in [4, 5]: cursor = Qt.CursorShape.SizeVerCursor
                    elif i in [6, 7]: cursor = Qt.CursorShape.SizeHorCursor
                    break
        else:
            cursor = Qt.CursorShape.SizeAllCursor
        self.setCursor(cursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the main rectangle
        rect_pen = QPen(QColor(255, 255, 0, 200), 2, Qt.PenStyle.DashLine) # Yellow dashed line
        painter.setPen(rect_pen)
        painter.setBrush(QColor(255, 255, 0, 25)) # Lighter fill

        painter.drawRect(self.rect())

        # Draw resize handles
        handle_pen = QPen(QColor(0, 0, 0), 1)
        painter.setPen(handle_pen)
        painter.setBrush(QColor(255, 255, 0)) # Yellow handles for visibility
        for handle in self.handles:
             painter.drawRect(handle)

    def get_geometry(self):
        return self.geometry()