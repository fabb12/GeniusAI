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

    def setGeometry(self, rect):
        """ Override setGeometry to update handles whenever it's called. """
        super().setGeometry(rect)
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
            # Use global position for stable reference, map to parent
            self.drag_start_position = self.mapToParent(event.pos())
            self.drag_start_geometry = self.geometry()
            self.is_resizing = False
            self.is_dragging = False # Reset dragging state

            # Check if a handle is clicked
            for i, handle in enumerate(self.handles):
                if handle.contains(event.pos()):
                    self.is_resizing = True
                    self.is_dragging = True
                    self.resize_handle = i
                    return # Stop processing

            # If not resizing, check if the main body is clicked for dragging
            if self.rect().contains(event.pos()):
                self.is_dragging = True

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            # Map current mouse position to parent's coordinate system
            current_pos = self.mapToParent(event.pos())
            delta = current_pos - self.drag_start_position

            if self.is_resizing:
                 # For resizing, we need the delta relative to the widget's corner
                local_delta = event.pos() - self.mapFromParent(self.drag_start_position)
                self.resize_geometry(local_delta)
            else:  # Moving
                new_top_left = self.drag_start_geometry.topLeft() + delta
                parent_rect = self.parent().rect()

                # Clamp movement within the parent
                new_top_left.setX(max(0, min(new_top_left.x(), parent_rect.right() - self.width())))
                new_top_left.setY(max(0, min(new_top_left.y(), parent_rect.bottom() - self.height())))

                self.move(new_top_left)

        self.update_cursor(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.resize_handle = None
            self.update_handles() # Final update
        self.update_cursor(event.pos()) # Update cursor on release

    def resize_geometry(self, delta):
        rect = QRect(self.drag_start_geometry)
        parent_rect = self.parent().rect()

        # Adjust geometry based on the handle being dragged
        if self.resize_handle == 0:  # Top-left
            rect.setTopLeft(rect.topLeft() + delta)
        elif self.resize_handle == 1:  # Top-right
            rect.setTopRight(rect.topRight() + delta)
        elif self.resize_handle == 2:  # Bottom-left
            rect.setBottomLeft(rect.bottomLeft() + delta)
        elif self.resize_handle == 3:  # Bottom-right
            rect.setBottomRight(rect.bottomRight() + delta)
        elif self.resize_handle == 4:  # Top
            rect.setTop(rect.top() + delta.y())
        elif self.resize_handle == 5:  # Bottom
            rect.setBottom(rect.bottom() + delta.y())
        elif self.resize_handle == 6:  # Left
            rect.setLeft(rect.left() + delta.x())
        elif self.resize_handle == 7:  # Right
            rect.setRight(rect.right() + delta.x())

        # --- Validation and Correction ---

        # 1. Enforce minimum size (prevent inversion)
        if rect.width() < self.min_size:
            if self.resize_handle in [0, 2, 6]: # Dragging left edge
                rect.setLeft(rect.right() - self.min_size)
            else: # Dragging right edge
                rect.setRight(rect.left() + self.min_size)

        if rect.height() < self.min_size:
            if self.resize_handle in [0, 1, 4]: # Dragging top edge
                rect.setTop(rect.bottom() - self.min_size)
            else: # Dragging bottom edge
                rect.setBottom(rect.top() + self.min_size)

        # 2. Constrain to parent boundaries
        final_rect = rect.intersected(parent_rect)

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