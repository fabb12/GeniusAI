from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QPolygon
import os

class VideoOverlay(QWidget):
    panned = pyqtSignal(QPoint)
    zoomed = pyqtSignal(float, QPoint)
    view_reset = pyqtSignal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)  # Enable mouse tracking

        self.crop_points = []
        self.crop_rect = QRect()

        # Watermark attributes
        self.watermark_enabled = False
        self.watermark_path = None
        self.watermark_size = 0
        self.watermark_pixmap = None
        self.watermark_position = "Bottom Right"

        # Cursor highlight attributes
        self.show_red_dot = False
        self.show_yellow_triangle = False
        self.cursor_pos = QPoint()

        self.is_panning = False
        self.last_mouse_position = QPoint()

    def setWatermark(self, enabled, path, size, position):
        self.watermark_enabled = enabled
        self.watermark_path = path
        self.watermark_size = size
        self.watermark_position = position
        if self.watermark_enabled and self.watermark_path and os.path.exists(self.watermark_path):
            self.watermark_pixmap = QPixmap(self.watermark_path)
        else:
            self.watermark_pixmap = None
        self.update()

    def set_show_red_dot(self, show):
        self.show_red_dot = show
        self.update()

    def set_show_yellow_triangle(self, show):
        self.show_yellow_triangle = show
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoomed.emit(delta, event.position().toPoint())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.last_mouse_position = event.position().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            if self.main_window.zoom_level != 1.0:
                self.view_reset.emit()
            else:
                if len(self.crop_points) >= 2:
                    self.crop_points = []
                    self.crop_rect = QRect()
                self.crop_points.append(event.pos())
                if len(self.crop_points) == 2:
                    self.crop_rect = QRect(self.crop_points[0], self.crop_points[1]).normalized()
                self.update()

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.pos()
        if self.is_panning:
            delta = event.position().toPoint() - self.last_mouse_position
            self.panned.emit(delta)
            self.last_mouse_position = event.position().toPoint()
        self.update() # Trigger repaint to show cursor highlights

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.cursor_pos = QPoint(-1, -1) # Hide cursor when it leaves the widget
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw cropping points and rectangle
        pen = QPen(QColor(255, 0, 0), 4, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        for point in self.crop_points:
            painter.drawEllipse(point, 5, 5)

        if len(self.crop_points) == 2 and not self.crop_rect.isNull():
            painter.setBrush(QColor(255, 0, 0, 50))
            painter.drawRect(self.crop_rect)

        # Draw watermark
        if self.watermark_enabled and self.watermark_pixmap:
            parent_width = self.parent().width()
            parent_height = self.parent().height()

            watermark_height = int(parent_height * (self.watermark_size / 100.0))
            scaled_pixmap = self.watermark_pixmap.scaledToHeight(watermark_height, Qt.TransformationMode.SmoothTransformation)

            margin = 10
            if self.watermark_position == "Top Left":
                x = margin
                y = margin
            elif self.watermark_position == "Top Right":
                x = parent_width - scaled_pixmap.width() - margin
                y = margin
            elif self.watermark_position == "Bottom Left":
                x = margin
                y = parent_height - scaled_pixmap.height() - margin
            else:  # Bottom Right
                x = parent_width - scaled_pixmap.width() - margin
                y = parent_height - scaled_pixmap.height() - margin

            painter.drawPixmap(x, y, scaled_pixmap)

        # Draw cursor highlights
        if self.cursor_pos.x() > 0 and self.cursor_pos.y() > 0:
            if self.show_red_dot:
                painter.setBrush(QColor(255, 0, 0, 180))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(self.cursor_pos, 5, 5)

            if self.show_yellow_triangle:
                painter.setBrush(QColor(255, 255, 0, 180))
                painter.setPen(Qt.PenStyle.NoPen)

                triangle = QPolygon([
                    QPoint(self.cursor_pos.x(), self.cursor_pos.y() - 15),
                    QPoint(self.cursor_pos.x() - 10, self.cursor_pos.y() - 5),
                    QPoint(self.cursor_pos.x() + 10, self.cursor_pos.y() - 5)
                ])
                painter.drawPolygon(triangle)
