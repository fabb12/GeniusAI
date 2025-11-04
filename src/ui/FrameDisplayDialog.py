from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QSlider, QDialogButtonBox
from PyQt6.QtCore import Qt

class FrameDisplayDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Regola dimensione e inserisci frame")
        self.setModal(True)
        self.pixmap = pixmap

        layout = QVBoxLayout(self)
        self.image_label = QLabel()
        self.image_label.setPixmap(self.pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.image_label)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(10, 200)
        self.size_slider.setValue(100)
        self.size_slider.valueChanged.connect(self.update_image_size)
        layout.addWidget(self.size_slider)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_image_size(self, value):
        new_width = int(self.pixmap.width() * (value / 100))
        self.image_label.setPixmap(self.pixmap.scaledToWidth(new_width, Qt.TransformationMode.SmoothTransformation))

    def get_display_size(self):
        return self.image_label.pixmap().size()