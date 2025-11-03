from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QSizePolicy, QLabel, QDialogButtonBox
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QRect

from .ResizableRubberBand import ResizableRubberBand

class ImageCropDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ritaglia Immagine")
        self.setMinimumSize(400, 300)

        self.pixmap = pixmap
        self.crop_rect = QRect()

        layout = QVBoxLayout(self)
        self.image_label = QLabel()
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.image_label)

        self.rubber_band = ResizableRubberBand(self.image_label)
        self.rubber_band.setGeometry(QRect(10, 10, 100, 100))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_crop_rect(self):
        return self.rubber_band.geometry()

    def accept(self):
        self.crop_rect = self.rubber_band.geometry()
        super().accept()
