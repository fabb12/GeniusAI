from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QRect
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

        # The ResizableRubberBand is a widget that will be an overlay on the image_label
        self.rubber_band = ResizableRubberBand(self.image_label)

        main_layout.addWidget(self.image_label)

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

        self.reset_button.clicked.connect(self.reset_rubber_band)
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.prev_frame_button.clicked.connect(self.previous_frame)
        self.next_frame_button.clicked.connect(self.next_frame)

    def reset_rubber_band(self):
        # Reset by re-setting the geometry of the widget, which will trigger the internal reset.
        self.rubber_band.setGeometry(self.image_label.rect())

    def get_crop_rect(self):
        # Get geometry from our custom rubber band widget
        geom = self.rubber_band.band_geometry()
        return QRect(
            int(geom.x() * self.scale_factor),
            int(geom.y() * self.scale_factor),
            int(geom.width() * self.scale_factor),
            int(geom.height() * self.scale_factor)
        )

    def showEvent(self, event):
        super().showEvent(event)
        # The rubber band is a child widget, so it will be shown automatically
        self.rubber_band.show()

    def update_pixmap(self, new_pixmap):
        if new_pixmap and not new_pixmap.isNull():
            self.original_pixmap = new_pixmap
            dialog_size = self.size()

            self.display_pixmap = self.original_pixmap.scaled(
                dialog_size.width(), dialog_size.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )

            if self.display_pixmap.width() > 0:
                self.scale_factor = self.original_pixmap.width() / self.display_pixmap.width()
            else:
                self.scale_factor = 1.0

            self.image_label.setPixmap(self.display_pixmap)
            self.image_label.setFixedSize(self.display_pixmap.size())

            # The rubber band should resize with the image label
            self.rubber_band.setGeometry(self.image_label.rect())

    def next_frame(self):
        if self.parent_window:
            self.parent_window.get_next_frame()
            new_pixmap = self.get_current_frame_from_parent()
            if new_pixmap:
                self.update_pixmap(new_pixmap)

    def previous_frame(self):
        if self.parent_window:
            self.parent_window.get_previous_frame()
            new_pixmap = self.get_current_frame_from_parent()
            if new_pixmap:
                self.update_pixmap(new_pixmap)

    def get_current_frame_from_parent(self):
        if self.parent_window and hasattr(self.parent_window, 'player'):
            position_ms = self.parent_window.player.position()
            return self.parent_window.get_frame_at(position_ms)
        return None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)