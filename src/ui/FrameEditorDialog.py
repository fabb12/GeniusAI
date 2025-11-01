from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSlider, QSizePolicy)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QRect, QSize
from .ResizableRubberBand import ResizableRubberBand
from screeninfo import get_monitors

class FrameEditorDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Frame")
        self.setModal(True)

        self.original_pixmap = pixmap
        self.scale_factor = 1.0

        monitor = get_monitors()[0]
        dialog_width = monitor.width // 2
        dialog_height = monitor.height // 2
        self.resize(dialog_width, dialog_height)

        self.base_display_pixmap = self.original_pixmap.scaled(
            dialog_width, dialog_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rubber_band = ResizableRubberBand(self.image_label)

        main_layout.addWidget(self.image_label)

        size_control_layout = QHBoxLayout()
        size_control_layout.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(20, 300)
        self.size_slider.setValue(100)
        self.size_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        size_control_layout.addWidget(self.size_slider)
        main_layout.addLayout(size_control_layout)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset")
        self.apply_button = QPushButton("Apply")
        self.cancel_button = QPushButton("Cancel")

        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.reset_button.clicked.connect(self.reset_changes)
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.size_slider.valueChanged.connect(self.update_display_size)

        self.update_display_size(100)

    def update_display_size(self, value):
        percentage = value / 100.0

        new_width = int(self.base_display_pixmap.width() * percentage)
        new_height = int(self.base_display_pixmap.height() * percentage)

        self.display_pixmap = self.base_display_pixmap.scaled(
            new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.setFixedSize(self.display_pixmap.size())

        if self.display_pixmap.width() > 0:
            self.scale_factor = self.original_pixmap.width() / self.display_pixmap.width()
        else:
            self.scale_factor = 1.0

        if hasattr(self, 'rubber_band'):
            self.rubber_band.setGeometry(self.image_label.rect())

    def reset_changes(self):
        self.rubber_band.setGeometry(QRect(0, 0, self.image_label.width(), self.image_label.height()))
        self.size_slider.setValue(100)

    def get_crop_rect(self):
        geom = self.rubber_band.band_geometry()
        return QRect(
            int(geom.x() * self.scale_factor),
            int(geom.y() * self.scale_factor),
            int(geom.width() * self.scale_factor),
            int(geom.height() * self.scale_factor)
        )

    def get_size_percentage(self):
        return self.size_slider.value()

    def showEvent(self, event):
        super().showEvent(event)
        self.rubber_band.show()
