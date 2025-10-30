# File: src/ui/ImageSizeDialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QDialogButtonBox
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
        self.size_combo.addItems(["Piccola (25%)", "Media (50%)", "Grande (75%)", "Originale (100%)"])
        self.size_combo.setCurrentIndex(1) # Default to Medium

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
        if "25" in text:
            return 25
        if "50" in text:
            return 50
        if "75" in text:
            return 75
        return 100
