import cv2
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QCheckBox, QDialogButtonBox, QSizePolicy)
from PyQt6.QtGui import QPixmap, QIntValidator, QPainter, QColor
from PyQt6.QtCore import Qt, QRect

from src.ui.ResizableRubberBand import ResizableRubberBand

class ImageEditorDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modifica Frame")
        self.original_pixmap = pixmap
        self.current_pixmap = pixmap
        self.crop_rect = None

        self.setMinimumSize(800, 600) # Increased size for better usability

        main_layout = QVBoxLayout(self)

        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.image_label, 1)

        self.rubber_band = None # Will be created when crop mode is enabled

        # Controls layout
        controls_layout = QHBoxLayout()

        # Resizing controls
        size_layout = QHBoxLayout()
        self.width_edit = QLineEdit(str(self.original_pixmap.width()))
        self.width_edit.setValidator(QIntValidator(1, 10000))
        self.height_edit = QLineEdit(str(self.original_pixmap.height()))
        self.height_edit.setValidator(QIntValidator(1, 10000))
        self.aspect_ratio_checkbox = QCheckBox("Mantieni proporzioni")
        self.aspect_ratio_checkbox.setChecked(True)

        size_layout.addWidget(QLabel("W:"))
        size_layout.addWidget(self.width_edit)
        size_layout.addWidget(QLabel("H:"))
        size_layout.addWidget(self.height_edit)
        size_layout.addWidget(self.aspect_ratio_checkbox)
        controls_layout.addLayout(size_layout)

        controls_layout.addStretch()

        # Frame navigation
        self.prev_frame_button = QPushButton("<< Frame Prec.")
        self.next_frame_button = QPushButton("Frame Succ. >>")
        controls_layout.addWidget(self.prev_frame_button)
        controls_layout.addWidget(self.next_frame_button)

        controls_layout.addStretch()

        # Cropping
        self.crop_button = QPushButton("Ritaglia")
        self.crop_button.setCheckable(True)
        self.crop_button.toggled.connect(self.toggle_crop_mode)
        controls_layout.addWidget(self.crop_button)

        main_layout.addLayout(controls_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.width_edit.textChanged.connect(self.on_width_changed)
        self.height_edit.textChanged.connect(self.on_height_changed)

    def on_width_changed(self, text):
        if not text or not self.aspect_ratio_checkbox.isChecked():
            return
        new_width = int(text)
        aspect_ratio = self.original_pixmap.height() / self.original_pixmap.width()
        new_height = int(new_width * aspect_ratio)
        self.height_edit.blockSignals(True)
        self.height_edit.setText(str(new_height))
        self.height_edit.blockSignals(False)
        self.update_image_preview()

    def on_height_changed(self, text):
        if not text or not self.aspect_ratio_checkbox.isChecked():
            return
        new_height = int(text)
        aspect_ratio = self.original_pixmap.width() / self.original_pixmap.height()
        new_width = int(new_height * aspect_ratio)
        self.width_edit.blockSignals(True)
        self.width_edit.setText(str(new_width))
        self.width_edit.blockSignals(False)
        self.update_image_preview()

    def update_image_preview(self):
        if not self.original_pixmap.isNull():
            w = int(self.width_edit.text()) if self.width_edit.text() else 0
            h = int(self.height_edit.text()) if self.height_edit.text() else 0

            scaled_pixmap = self.original_pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.current_pixmap = scaled_pixmap
            self.image_label.setPixmap(self.current_pixmap)

    def toggle_crop_mode(self, checked):
        if checked:
            if not self.rubber_band:
                self.rubber_band = ResizableRubberBand(self.image_label)
                # Apply a stylesheet to make it a red transparent rectangle
                self.rubber_band.setStyleSheet("background-color: rgba(255, 0, 0, 0.5); border: 2px solid red;")

            # Center the rubber band
            label_size = self.image_label.size()
            rb_width, rb_height = 200, 150
            self.rubber_band.setGeometry(
                (label_size.width() - rb_width) // 2,
                (label_size.height() - rb_height) // 2,
                rb_width,
                rb_height
            )
            self.rubber_band.show()
            self.crop_button.setText("Applica Ritaglio")
        else:
            if self.rubber_band:
                self.crop_rect = self.rubber_band.geometry()
                self.rubber_band.hide()
            self.crop_button.setText("Ritaglia")
            self.apply_crop()

    def apply_crop(self):
        if self.crop_rect and self.image_label.pixmap():
            # Scale the rubber band geometry to the original pixmap's coordinates
            label_size = self.image_label.size()
            pixmap_on_label = self.image_label.pixmap()

            # This is the actual size of the pixmap as displayed in the label
            pixmap_size = pixmap_on_label.size()

            if pixmap_size.width() == 0 or pixmap_size.height() == 0:
                return

            x_scale = self.original_pixmap.width() / pixmap_size.width()
            y_scale = self.original_pixmap.height() / pixmap_size.height()

            # Calculate the offset of the pixmap within the label (due to KeepAspectRatio)
            x_offset = (label_size.width() - pixmap_size.width()) / 2
            y_offset = (label_size.height() - pixmap_size.height()) / 2

            # Translate rubber band coordinates to pixmap coordinates
            scaled_rect = QRect(
                int((self.crop_rect.x() - x_offset) * x_scale),
                int((self.crop_rect.y() - y_offset) * y_scale),
                int(self.crop_rect.width() * x_scale),
                int(self.crop_rect.height() * y_scale)
            )

            # Ensure the crop rectangle is within the bounds of the original pixmap
            scaled_rect = scaled_rect.intersected(self.original_pixmap.rect())

            if scaled_rect.isValid():
                cropped = self.original_pixmap.copy(scaled_rect)
                self.original_pixmap = cropped # The new "original" is the cropped version
                self.current_pixmap = cropped

                # Update UI elements
                self.width_edit.setText(str(cropped.width()))
                self.height_edit.setText(str(cropped.height()))
                self.update_image_preview() # This will display the new cropped pixmap

            self.crop_rect = None # Reset crop rect

    def get_edited_data(self):
        return {
            "image": self.current_pixmap.toImage(),
            "width": self.current_pixmap.width(),
            "height": self.current_pixmap.height()
        }

    def set_new_pixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.current_pixmap = pixmap
        self.width_edit.setText(str(pixmap.width()))
        self.height_edit.setText(str(pixmap.height()))
        self.update_image_preview()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image_preview()
