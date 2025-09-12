from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap
import os

class VideoOverlay(QWidget):
    crop_finalized = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # Initially transparent
        self.setMouseTracking(True)

        self.is_cropping = False
        self.crop_size = 200
        self.mouse_pos = QPoint()

        self.watermark_enabled = False
        self.watermark_path = None
        self.watermark_size = 0
        self.watermark_pixmap = None
        self.watermark_position = "Bottom Right"

    def start_cropping(self):
        self.is_cropping = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.update()

    def stop_cropping(self):
        self.is_cropping = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.update()

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

    def mouseMoveEvent(self, event):
        if self.is_cropping:
            self.mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        if self.is_cropping:
            delta = event.angleDelta().y()
            if delta > 0:
                self.crop_size += 10
            else:
                self.crop_size = max(20, self.crop_size - 10)  # Minimum size of 20
            self.update()
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.is_cropping:
            if event.button() == Qt.MouseButton.RightButton:
                half_size = self.crop_size // 2
                top_left = self.mouse_pos - QPoint(half_size, half_size)
                crop_rect = QRect(top_left, QPoint(top_left.x() + self.crop_size, top_left.y() + self.crop_size))
                self.crop_finalized.emit(crop_rect)
                self.stop_cropping()
            elif event.button() == Qt.MouseButton.LeftButton:
                self.stop_cropping()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)

        if self.is_cropping:
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0, 50))

            half_size = self.crop_size // 2
            top_left = self.mouse_pos - QPoint(half_size, half_size)
            crop_rect = QRect(top_left, QPoint(top_left.x() + self.crop_size, top_left.y() + self.crop_size))
            painter.drawRect(crop_rect)

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
