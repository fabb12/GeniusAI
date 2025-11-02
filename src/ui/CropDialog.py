import cv2
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap, QImage, QResizeEvent
from PyQt6.QtCore import Qt, QRect, QSize, QRectF
from .ResizableRubberBand import ResizableRubberBand
from screeninfo import get_monitors

class CropDialog(QDialog):
    def __init__(self, video_path, current_time=0, start_time=None, end_time=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Video")
        self.setModal(True)

        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.start_frame = int(start_time * self.fps) if start_time else 0
        self.end_frame = int(end_time * self.fps) if end_time else self.total_frames - 1

        self.current_frame_pos = int(current_time / 1000 * self.fps)
        if not (self.start_frame <= self.current_frame_pos <= self.end_frame):
             self.current_frame_pos = self.start_frame

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)

        self.original_pixmap = self._get_current_frame_as_pixmap()
        self.aspect_ratio = self.original_pixmap.width() / self.original_pixmap.height() if self.original_pixmap.height() > 0 else 1.0

        monitor = get_monitors()[0]
        dialog_width = monitor.width // 2
        dialog_height = monitor.height // 2
        self.resize(dialog_width, dialog_height)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.image_label)

        self.rubber_band = ResizableRubberBand(self.image_label)

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

        self.update_pixmap_display()
        self._center_rubber_band()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.update_pixmap_display()

    def update_pixmap_display(self):
        container_size = self.image_label.size()
        w, h = container_size.width(), container_size.height()

        if self.aspect_ratio > w / h:
            new_width = w
            new_height = int(w / self.aspect_ratio)
        else:
            new_height = h
            new_width = int(h * self.aspect_ratio)

        self.display_pixmap = self.original_pixmap.scaled(
            new_width, new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(self.display_pixmap)

        # Aggiorna la geometria del rubber band in modo proporzionale
        if hasattr(self, 'rubber_band_ratio'):
            rb_w = int(new_width * self.rubber_band_ratio.width())
            rb_h = int(new_height * self.rubber_band_ratio.height())
            rb_x = int(new_width * self.rubber_band_ratio.x())
            rb_y = int(new_height * self.rubber_band_ratio.y())
            self.rubber_band.setGeometry(QRect(rb_x, rb_y, rb_w, rb_h))

    def _get_current_frame_as_pixmap(self):
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qt_image)
        return QPixmap()

    def _center_rubber_band(self):
        w = self.display_pixmap.width()
        h = self.display_pixmap.height()
        rb_w = w // 2
        rb_h = h // 2
        rb_x = (w - rb_w) // 2
        rb_y = (h - rb_h) // 2
        self.rubber_band.setGeometry(QRect(rb_x, rb_y, rb_w, rb_h))
        self.rubber_band_ratio = QRectF(rb_x/w, rb_y/h, rb_w/w, rb_h/h)

    def update_frame(self, new_frame_pos):
        if self.start_frame <= new_frame_pos <= self.end_frame:
            self.current_frame_pos = new_frame_pos
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)
            self.original_pixmap = self._get_current_frame_as_pixmap()
            self.update_pixmap_display()

    def next_frame(self):
        self.update_frame(self.current_frame_pos + 1)

    def prev_frame(self):
        self.update_frame(self.current_frame_pos - 1)

    def get_crop_rect(self):
        scale_factor_w = self.original_pixmap.width() / self.display_pixmap.width() if self.display_pixmap.width() > 0 else 1
        scale_factor_h = self.original_pixmap.height() / self.display_pixmap.height() if self.display_pixmap.height() > 0 else 1

        geom = self.rubber_band.geometry()
        return QRect(
            int(geom.x() * scale_factor_w),
            int(geom.y() * scale_factor_h),
            int(geom.width() * scale_factor_w),
            int(geom.height() * scale_factor_h)
        )

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

    def accept(self):
        # Salva le proporzioni del rubber band prima di chiudere
        w = self.display_pixmap.width()
        h = self.display_pixmap.height()
        geom = self.rubber_band.geometry()
        self.rubber_band_ratio = QRectF(geom.x()/w, geom.y()/h, geom.width()/w, geom.height()/h)
        super().accept()
