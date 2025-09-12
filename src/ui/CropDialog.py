from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from .ResizableRubberBand import ResizableRubberBand

class CropDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Video")
        self.setModal(True)

        self.pixmap = pixmap

        main_layout = QVBoxLayout(self)

        self.image_label = QLabel()
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setMinimumSize(self.pixmap.size())

        self.rubber_band = ResizableRubberBand(self.image_label)

        # Center the rubber band initially
        rb_width = self.pixmap.width() // 2
        rb_height = self.pixmap.height() // 2
        rb_x = (self.pixmap.width() - rb_width) // 2
        rb_y = (self.pixmap.height() - rb_height) // 2
        self.rubber_band.setGeometry(rb_x, rb_y, rb_width, rb_height)

        main_layout.addWidget(self.image_label)

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Applica")
        self.cancel_button = QPushButton("Annulla")

        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)

        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_crop_rect(self):
        return self.rubber_band.geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self.rubber_band.show()
