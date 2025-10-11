from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QRect, QSize
from .ResizableRubberBand import ResizableRubberBand
from screeninfo import get_monitors

class CropDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Video")
        self.setModal(True)

        self.original_pixmap = pixmap
        self.parent_window = parent
        self.scale_factor = 1.0

        # Set the dialog size to half of the screen
        monitor = get_monitors()[0]
        dialog_width = monitor.width // 2
        dialog_height = monitor.height // 2

        # We set the size of the dialog directly.
        self.resize(dialog_width, dialog_height)

        # Scale the pixmap to fit within the dialog, preserving aspect ratio
        self.display_pixmap = self.original_pixmap.scaled(
            dialog_width,
            dialog_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Recalculate scale factor based on the actual scaling
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

        # Center the rubber band initially (now smaller)
        rb_width = self.display_pixmap.width() // 4
        rb_height = self.display_pixmap.height() // 4
        rb_x = (self.display_pixmap.width() - rb_width) // 2
        rb_y = (self.display_pixmap.height() - rb_height) // 2
        self.initial_rb_geometry = QRect(rb_x, rb_y, rb_width, rb_height)
        self.rubber_band.setGeometry(self.initial_rb_geometry)

        main_layout.addWidget(self.image_label)

        # Layout for frame navigation
        frame_nav_layout = QHBoxLayout()
        self.prev_frame_button = QPushButton("<")
        self.next_frame_button = QPushButton(">")
        frame_nav_layout.addStretch()
        frame_nav_layout.addWidget(self.prev_frame_button)
        frame_nav_layout.addWidget(self.next_frame_button)
        frame_nav_layout.addStretch()
        main_layout.addLayout(frame_nav_layout)

        # Layout for main buttons
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

    def reset_rubber_band(self):
        self.rubber_band.setGeometry(self.initial_rb_geometry)

    def get_crop_rect(self):
        # Return the crop rectangle relative to the original pixmap size
        geom = self.rubber_band.geometry()
        return QRect(
            int(geom.x() * self.scale_factor),
            int(geom.y() * self.scale_factor),
            int(geom.width() * self.scale_factor),
            int(geom.height() * self.scale_factor)
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.rubber_band.show()

    def update_pixmap(self, pixmap):
        if pixmap:
            self.original_pixmap = pixmap

            # Get the dialog's current size to fit the new pixmap
            dialog_size = self.size()

            self.display_pixmap = self.original_pixmap.scaled(
                dialog_size.width(),
                dialog_size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            if self.display_pixmap.width() > 0:
                 self.scale_factor = self.original_pixmap.width() / self.display_pixmap.width()
            else:
                 self.scale_factor = 1.0

            self.image_label.setPixmap(self.display_pixmap)
            self.image_label.setFixedSize(self.display_pixmap.size())

            # Reset rubber band on new frame
            rb_width = self.display_pixmap.width() // 4
            rb_height = self.display_pixmap.height() // 4
            rb_x = (self.display_pixmap.width() - rb_width) // 2
            rb_y = (self.display_pixmap.height() - rb_height) // 2
            self.initial_rb_geometry = QRect(rb_x, rb_y, rb_width, rb_height)
            self.rubber_band.setGeometry(self.initial_rb_geometry)

    def next_frame(self):
        if self.parent_window:
            new_pixmap = self.parent_window.get_next_frame()
            self.update_pixmap(new_pixmap)

    def previous_frame(self):
        if self.parent_window:
            new_pixmap = self.parent_window.get_previous_frame()
            self.update_pixmap(new_pixmap)

    def keyPressEvent(self, event):
        """Accept the dialog when Enter or Return is pressed."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)