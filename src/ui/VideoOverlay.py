from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap
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
        self.crop_points = []
        self.crop_rect = QRect()
        self.watermark_enabled = False
        self.watermark_path = None
        self.watermark_size = 0
        self.watermark_pixmap = None
        self.watermark_position = "Bottom Right"
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
        if self.is_panning:
            delta = event.position().toPoint() - self.last_mouse_position
            self.panned.emit(delta)
            self.last_mouse_position = event.position().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False

    def paintEvent(self, event):
        painter = QPainter(self)

        pen = QPen(QColor(255, 0, 0), 4, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        # Draw points
        for point in self.crop_points:
            painter.drawEllipse(point, 5, 5)

        # Draw cropping rectangle if 2 points are selected
        if len(self.crop_points) == 2 and not self.crop_rect.isNull():
            painter.setBrush(QColor(255, 0, 0, 50))
            painter.drawRect(self.crop_rect)

        # Draw watermark
        if self.watermark_enabled and self.watermark_pixmap:
            parent_width = self.parent().width()
            parent_height = self.parent().height()

            # Calculate watermark size based on percentage of parent widget's height
            watermark_height = int(parent_height * (self.watermark_size / 100.0))
            scaled_pixmap = self.watermark_pixmap.scaledToHeight(watermark_height, Qt.TransformationMode.SmoothTransformation)

            # Position at bottom right with a margin
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
