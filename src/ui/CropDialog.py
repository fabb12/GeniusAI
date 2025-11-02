import cv2
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSlider
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QRect
from .ResizableRubberBand import ResizableRubberBand
from screeninfo import get_monitors

class CropDialog(QDialog):
    def __init__(self, video_path, start_time=None, end_time=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Video")
        self.setModal(True)

        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        # Gestione dei bookmark
        self.start_frame = 0
        if start_time:
            self.start_frame = int(start_time * self.fps)

        self.end_frame = self.total_frames - 1
        if end_time:
            self.end_frame = int(end_time * self.fps)

        self.current_frame_pos = self.start_frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)

        self.original_pixmap = self._get_current_frame_as_pixmap()
        self.scale_factor = 1.0

        monitor = get_monitors()[0]
        dialog_width = monitor.width // 2
        dialog_height = monitor.height // 2
        self.resize(dialog_width, dialog_height)

        self.display_pixmap = self.original_pixmap.scaled(
            dialog_width, dialog_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self._recalculate_scale_factor()

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rubber_band = ResizableRubberBand(self.image_label)
        self._center_rubber_band()

        main_layout.addWidget(self.image_label)

        # Slider per lo zoom
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 200) # dal 50% al 200%
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        zoom_layout.addWidget(self.zoom_slider)
        main_layout.addLayout(zoom_layout)

        frame_nav_layout = QHBoxLayout()
        self.prev_frame_button = QPushButton("<")
        self.next_frame_button = QPushButton(">")
        frame_nav_layout.addStretch()
        frame_nav_layout.addWidget(self.prev_frame_button)
        frame_nav_layout.addWidget(self.next_frame_button)
        frame_nav_layout.addStretch()
        main_layout.addLayout(frame_nav_layout)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset")
        self.apply_button = QPushButton("Applica")
        self.cancel_button = QPushButton("Annulla")
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.reset_button.clicked.connect(self._center_rubber_band)
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.prev_frame_button.clicked.connect(self.prev_frame)
        self.next_frame_button.clicked.connect(self.next_frame)

    def _get_current_frame_as_pixmap(self):
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qt_image)
        return QPixmap()

    def _recalculate_scale_factor(self):
        if self.display_pixmap.width() > 0:
            self.scale_factor = self.original_pixmap.width() / self.display_pixmap.width()
        else:
            self.scale_factor = 1.0

    def _center_rubber_band(self):
        rb_width = self.display_pixmap.width() // 2
        rb_height = self.display_pixmap.height() // 2
        rb_x = (self.display_pixmap.width() - rb_width) // 2
        rb_y = (self.display_pixmap.height() - rb_height) // 2
        self.rubber_band.setGeometry(QRect(rb_x, rb_y, rb_width, rb_height))

    def update_frame(self, new_frame_pos):
        if self.start_frame <= new_frame_pos <= self.end_frame:
            self.current_frame_pos = new_frame_pos
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)
            self.original_pixmap = self._get_current_frame_as_pixmap()
            self.update_zoom(self.zoom_slider.value()) # Ridisegna con lo zoom corrente

    def next_frame(self):
        self.update_frame(self.current_frame_pos + 1)

    def prev_frame(self):
        self.update_frame(self.current_frame_pos - 1)

    def update_zoom(self, value):
        zoom_factor = value / 100.0
        new_width = int(self.original_pixmap.width() * zoom_factor)
        new_height = int(self.original_pixmap.height() * zoom_factor)

        self.display_pixmap = self.original_pixmap.scaled(
            new_width, new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.adjustSize()
        self._recalculate_scale_factor()

    def get_crop_rect(self):
        geom = self.rubber_band.geometry()
        return QRect(
            int(geom.x() * self.scale_factor),
            int(geom.y() * self.scale_factor),
            int(geom.width() * self.scale_factor),
            int(geom.height() * self.scale_factor)
        )

    def get_cropped_pixmap(self):
        """Returns the selected area of the original pixmap as a new pixmap."""
        crop_rect = self.get_crop_rect()
        return self.original_pixmap.copy(crop_rect)

    def showEvent(self, event):
        super().showEvent(event)
        self.rubber_band.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)
