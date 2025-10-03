import os
import tempfile
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QWidget, QDialogButtonBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class PreviewDialog(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anteprima Presentazione")
        self.setMinimumSize(800, 600)

        self.image_paths = image_paths

        main_layout = QVBoxLayout(self)

        # Area di scorrimento per le anteprime
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_content = QWidget()
        self.preview_layout = QVBoxLayout(scroll_content)

        for i, path in enumerate(self.image_paths):
            if os.path.exists(path):
                slide_label = QLabel(f"Slide {i + 1}")
                pixmap = QPixmap(path)
                # Scala l'immagine per l'anteprima
                scaled_pixmap = pixmap.scaled(720, 540, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label = QLabel()
                image_label.setPixmap(scaled_pixmap)
                self.preview_layout.addWidget(slide_label)
                self.preview_layout.addWidget(image_label)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Pulsanti
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept) # Chiude semplicemente la dialog

        main_layout.addWidget(self.button_box)

    def cleanup(self):
        """Rimuove i file di immagine temporanei."""
        for path in self.image_paths:
            if os.path.exists(path):
                os.remove(path)

        # Rimuove la cartella temporanea se è vuota
        temp_dir = os.path.dirname(self.image_paths[0])
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
