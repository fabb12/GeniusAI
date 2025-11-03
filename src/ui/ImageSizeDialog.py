# File: src/ui/ImageSizeDialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel, QSpinBox
)
from PyQt6.QtCore import Qt

class ImageSizeDialog(QDialog):
    """
    A simple dialog to select the size of an image to be inserted.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scegli Dimensione Immagine")
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["Micro (10%)", "Molto Piccola (15%)", "Piccola (25%)", "Media (50%)", "Grande (75%)", "Originale (100%)"])
        self.size_combo.setCurrentIndex(3) # Default to Medium

        layout.addWidget(self.size_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def get_selected_size_percentage(self):
        """
        Returns the selected size as an integer percentage.
        """
        text = self.size_combo.currentText()
        if "10" in text:
            return 10
        if "15" in text:
            return 15
        if "25" in text:
            return 25
        if "50" in text:
            return 50
        if "75" in text:
            return 75
        return 100

class ResizedImageDialog(QDialog):
    def __init__(self, current_width, current_height, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ridimensiona Immagine")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Nuova Larghezza:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 2000)
        self.width_spin.setValue(current_width)
        layout.addWidget(self.width_spin)

        layout.addWidget(QLabel("Nuova Altezza:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 2000)
        self.height_spin.setValue(current_height)
        layout.addWidget(self.height_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_new_size(self):
        return self.width_spin.value(), self.height_spin.value()
