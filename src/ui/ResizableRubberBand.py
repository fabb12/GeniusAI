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
        """ Recalculates handle positions. """
        self.handles = []
        s = self.handle_size
        h_s = s // 2  # half size
        w = self.width()
        h = self.height()

        # Corner handles
        self.handles.append(QRect(0 - h_s, 0 - h_s, s, s))          # Top-left
        self.handles.append(QRect(w - h_s, 0 - h_s, s, s))          # Top-right
        self.handles.append(QRect(0 - h_s, h - h_s, s, s))          # Bottom-left
        self.handles.append(QRect(w - h_s, h - h_s, s, s))          # Bottom-right

        # Side handles
        self.handles.append(QRect(w//2 - h_s, 0 - h_s, s, s))       # Top
        self.handles.append(QRect(w//2 - h_s, h - h_s, s, s))       # Bottom
        self.handles.append(QRect(0 - h_s, h//2 - h_s, s, s))       # Left
        self.handles.append(QRect(w - h_s, h//2 - h_s, s, s))       # Right

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.drag_start_geometry = self.geometry()
            self.is_resizing = False

            # Check if a handle is clicked
            for i, handle in enumerate(self.handles):
                if handle.contains(event.pos()):
                    self.is_resizing = True
                    self.is_dragging = True
                    self.resize_handle = i
                    break

            # If not resizing, check if the main body is clicked for dragging
            if not self.is_resizing and self.rect().contains(event.pos()):
                self.is_dragging = True

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.pos() - self.drag_start_position
            if self.is_resizing:
                self.resize_geometry(delta)
            else:  # Moving
                new_pos = self.drag_start_geometry.topLeft() + delta
                parent_rect = self.parent().rect()

                # Clamp the new position to stay within the parent's boundaries
                new_pos.setX(max(0, min(new_pos.x(), parent_rect.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent_rect.height() - self.height())))

                self.move(new_pos)

        # Update cursor based on position, even if not dragging
        self.update_cursor(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.resize_handle = None
            self.update_handles() # Final update
        self.update_cursor(event.pos()) # Update cursor on release
        super().mouseReleaseEvent(event)

    def resize_geometry(self, delta):
        rect = self.drag_start_geometry
        new_rect = QRect(rect)
        parent_rect = self.parent().rect()

        # Horizontal adjustments
        if self.resize_handle in [0, 2, 6]: # Left handles
            new_rect.setLeft(rect.left() + delta.x())
        elif self.resize_handle in [1, 3, 7]: # Right handles
            new_rect.setRight(rect.right() + delta.x())

        # Vertical adjustments
        if self.resize_handle in [0, 1, 4]: # Top handles
            new_rect.setTop(rect.top() + delta.y())
        elif self.resize_handle in [2, 3, 5]: # Bottom handles
            new_rect.setBottom(rect.bottom() + delta.y())

        # --- Validation and Correction ---

        # 1. Enforce minimum size (prevent inversion)
        if new_rect.width() < self.min_size:
            if self.resize_handle in [0, 2, 6]: # Dragging left edge
                new_rect.setLeft(new_rect.right() - self.min_size)
            else: # Dragging right edge
                new_rect.setRight(new_rect.left() + self.min_size)

        if new_rect.height() < self.min_size:
            if self.resize_handle in [0, 1, 4]: # Dragging top edge
                new_rect.setTop(new_rect.bottom() - self.min_size)
            else: # Dragging bottom edge
                new_rect.setBottom(new_rect.top() + self.min_size)

        # 2. Constrain to parent boundaries
        # Ensure the new rectangle is within the parent's bounds
        final_rect = new_rect.intersected(parent_rect)

        self.setGeometry(final_rect.normalized())
        self.update() # Request a repaint
        self.update_handles()

    def update_cursor(self, pos):
        """ Updates the cursor shape based on its position over handles or the main body. """
        handle_at_pos = -1
        for i, handle in enumerate(self.handles):
            if handle.contains(pos):
                handle_at_pos = i
                break

        cursor = Qt.CursorShape.ArrowCursor
        if self.is_dragging and not self.is_resizing:
            cursor = Qt.CursorShape.SizeAllCursor
        elif handle_at_pos != -1:
            # Diagonal cursors
            if handle_at_pos == 0 or handle_at_pos == 3: # Top-left, Bottom-right
                cursor = Qt.CursorShape.SizeFDiagCursor
            elif handle_at_pos == 1 or handle_at_pos == 2: # Top-right, Bottom-left
                cursor = Qt.CursorShape.SizeBDiagCursor
            # Axial cursors
            elif handle_at_pos == 4 or handle_at_pos == 5: # Top, Bottom
                cursor = Qt.CursorShape.SizeVerCursor
            else: # Left, Right
                cursor = Qt.CursorShape.SizeHorCursor
        elif self.rect().contains(pos):
             cursor = Qt.CursorShape.SizeAllCursor # Indicate the body is draggable

        self.setCursor(cursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the main rectangle (slightly inset)
        rect_pen = QPen(QColor(255, 255, 0, 200), 2, Qt.PenStyle.DashLine)
        painter.setPen(rect_pen)
        painter.setBrush(QColor(255, 255, 0, 20)) # Very light fill
        # Draw rectangle inset to not overlap handles
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # Draw resize handles
        handle_pen = QPen(QColor(0, 0, 0, 180), 1) # Semi-transparent black border
        painter.setPen(handle_pen)
        painter.setBrush(QColor(255, 255, 0, 220)) # Solid yellow fill
        for handle in self.handles:
            painter.drawRect(handle)

    def get_geometry(self):
        return self.geometry()