from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QRect
from .ResizableRubberBand import ResizableRubberBand

class CropDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Video")
        self.setModal(True)

        self.pixmap = pixmap
        self.parent_window = parent

        main_layout = QVBoxLayout(self)

        self.image_label = QLabel()
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setMinimumSize(self.pixmap.size())
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rubber_band = ResizableRubberBand(self.image_label)

        # Center the rubber band initially and store the geometry
        rb_width = self.pixmap.width() // 2
        rb_height = self.pixmap.height() // 2
        rb_x = (self.pixmap.width() - rb_width) // 2
        rb_y = (self.pixmap.height() - rb_height) // 2
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
        return self.rubber_band.geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self.rubber_band.show()

    def update_pixmap(self, pixmap):
        if pixmap:
            self.pixmap = pixmap
            self.image_label.setPixmap(self.pixmap)
            self.image_label.setMinimumSize(self.pixmap.size())
            self.rubber_band.setGeometry(self.initial_rb_geometry) # Reset rubber band on new frame

    def next_frame(self):
        if self.parent_window:
            new_pixmap = self.parent_window.get_next_frame()
            self.update_pixmap(new_pixmap)

    def previous_frame(self):
        if self.parent_window:
            new_pixmap = self.parent_window.get_previous_frame()
            self.update_pixmap(new_pixmap)
