from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QRect
from .ResizableRubberBand import ResizableRubberBand
from screeninfo import get_monitors
import cv2

class CropDialog(QDialog):
    def __init__(self, parent, video_path, initial_pixmap, video_duration_ms, start_time_ms, end_time_ms, initial_position_ms):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Video")
        self.setModal(True)

        self.parent_window = parent
        self.video_path = video_path
        self.original_pixmap = initial_pixmap
        self.scale_factor = 1.0

        self.video_duration_ms = video_duration_ms
        self.start_time_ms = start_time_ms
        self.end_time_ms = end_time_ms
        self.current_position_ms = initial_position_ms

        monitor = get_monitors()[0]
        dialog_width = monitor.width // 2
        dialog_height = monitor.height // 2
        self.resize(dialog_width, dialog_height)

        self.display_pixmap = self.original_pixmap.scaled(
            dialog_width, dialog_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        if self.display_pixmap.width() > 0:
            self.scale_factor = self.original_pixmap.width() / self.display_pixmap.width()
        else:
            self.scale_factor = 1.0

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.setFixedSize(self.display_pixmap.size())
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rubber_band = ResizableRubberBand(self.image_label)

        main_layout.addWidget(self.image_label)

        frame_nav_layout = QHBoxLayout()
        self.prev_frame_button = QPushButton("< Prev Frame")
        self.next_frame_button = QPushButton("Next Frame >")
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

        self.reset_button.clicked.connect(self.reset_rubber_band)
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.prev_frame_button.clicked.connect(self.previous_frame)
        self.next_frame_button.clicked.connect(self.next_frame)

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Errore", "Impossibile aprire il file video.")
            self.reject()
            return
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0: self.fps = 25 # Fallback
        self.frame_interval_ms = 1000 / self.fps


    def reset_rubber_band(self):
        self.rubber_band.setGeometry(self.image_label.rect())

    def get_crop_rect(self):
        geom = self.rubber_band.band_geometry()
        return QRect(
            int(geom.x() * self.scale_factor),
            int(geom.y() * self.scale_factor),
            int(geom.width() * self.scale_factor),
            int(geom.height() * self.scale_factor)
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.rubber_band.show()

    def update_frame(self):
        new_pixmap = self.parent_window.get_frame_at(self.current_position_ms)
        if new_pixmap and not new_pixmap.isNull():
            self.original_pixmap = new_pixmap

            # Scale the new pixmap to the existing label size to avoid resizing it
            self.display_pixmap = self.original_pixmap.scaled(
                self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )

            # Recalculate the scale factor based on the new pixmap
            if self.display_pixmap.width() > 0:
                self.scale_factor = self.original_pixmap.width() / self.display_pixmap.width()
            else:
                self.scale_factor = 1.0

            self.image_label.setPixmap(self.display_pixmap)
            # Crucially, do NOT resize the image_label or reset the rubber_band geometry.
            # This preserves the user's crop selection across frames.

    def next_frame(self):
        new_pos = self.current_position_ms + self.frame_interval_ms
        if new_pos <= self.end_time_ms:
            self.current_position_ms = new_pos
            self.update_frame()

    def previous_frame(self):
        new_pos = self.current_position_ms - self.frame_interval_ms
        if new_pos >= self.start_time_ms:
            self.current_position_ms = new_pos
            self.update_frame()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.previous_frame()
        elif key == Qt.Key.Key_Right:
            self.next_frame()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        super().closeEvent(event)