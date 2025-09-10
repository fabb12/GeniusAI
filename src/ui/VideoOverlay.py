from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap
import os

class VideoOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Assicurati di ricevere gli eventi del mouse
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.rect_start = None
        self.rect_end = None
        self.crop_rect = QRect()
        self.watermark_enabled = False
        self.watermark_path = None
        self.watermark_size = 0
        self.watermark_pixmap = None
        self.watermark_position = "Bottom Right"

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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.rect_start = event.pos()
            self.rect_end = self.rect_start
            self.crop_rect = QRect()  # Reset
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.RightButton:
            if self.rect_start:
                self.rect_end = event.pos()
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self.rect_start:
            self.rect_end = event.pos()
            self.crop_rect = QRect(self.rect_start, self.rect_end).normalized()
            self.rect_start = None
            self.rect_end = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw cropping rectangle
        if self.rect_start and self.rect_end:
            rect = QRect(self.rect_start, self.rect_end).normalized()
            # Use a thicker pen and a semi-transparent brush for visibility
            pen = QPen(QColor(255, 0, 0), 4, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0, 50))
            painter.drawRect(rect)
        elif not self.crop_rect.isNull():
            # Draw the final rectangle after selection is done
            pen = QPen(QColor(255, 0, 0), 4, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
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
