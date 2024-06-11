from PyQt6.QtGui import QPainter, QPen, QColor, QWheelEvent
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout
import sys
import os
import logging
# Configura il logging
logging.basicConfig(filename='transcription_log.txt', level=logging.DEBUG, format='[%(asctime)s - %(levelname)s] - %(message)s')
# Reindirizza stdout e stderr a os.devnull per ignorare l'output
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')


class CropVideoWidget(QVideoWidget):
    cropRectChanged = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.isSelecting = False
        self.isPanning = False
        self.origin = QPoint()
        self.end = QPoint()
        self.cropRect = QRect()
        self.scale_factor = 1.0
        self.translation = QPoint(0, 0)
        self.last_mouse_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.origin = event.position().toPoint()
            self.end = self.origin
            self.isSelecting = True
            self.isPanning = False
            self.update()
        elif event.button() == Qt.MouseButton.LeftButton and not self.isSelecting:
            self.last_mouse_pos = event.position().toPoint()
            self.isPanning = True

    def mouseMoveEvent(self, event):
        if self.isSelecting:
            self.end = event.position().toPoint()
            self.update()
        elif self.isPanning:
            delta = event.position().toPoint() - self.last_mouse_pos
            self.translation += delta
            self.last_mouse_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.isSelecting and event.button() == Qt.MouseButton.RightButton:
            self.isSelecting = False
            self.end = event.position().toPoint()
            self.cropRect = QRect(self.origin, self.end).normalized()
            self.cropRectChanged.emit(self.cropRect)
            self.update()
        logging.debug(self.cropRect)
        self.isPanning = False

    def wheelEvent(self, event):
        angle_delta = event.angleDelta().y() / 8
        steps = angle_delta / 15
        self.scale_factor += steps * 0.1
        self.scale_factor = max(0.1, min(self.scale_factor, 10.0))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.scale(self.scale_factor, self.scale_factor)
        painter.translate(self.translation / self.scale_factor)

        if self.isSelecting or not self.cropRect.isNull():
            pen = QPen(QColor(255, 0, 0), 4, Qt.PenStyle.SolidLine)  # Rettangolo rosso spesso
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0, 50))  # Colore rosso semi-trasparente
            painter.drawRect(QRect(self.origin, self.end).normalized())

    def getCropRect(self):
        return self.cropRect.normalized()


def main():
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    video_widget = CropVideoWidget()
    layout.addWidget(video_widget)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
