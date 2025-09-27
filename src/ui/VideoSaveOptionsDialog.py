from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QRadioButton,
                             QGroupBox, QSlider, QDialogButtonBox, QHBoxLayout, QCheckBox)
from PyQt6.QtCore import Qt, QSettings
import os


class VideoSaveOptionsDialog(QDialog):
    def __init__(self, source_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opzioni Salvataggio Video")
        self.setModal(True)
        self.source_path = source_path
        self.settings = QSettings("Genius", "GeniusAI")

        layout = QVBoxLayout(self)

        # Instructions
        label = QLabel("Seleziona il formato di salvataggio del video:")
        layout.addWidget(label)

        # Radio buttons for options
        self.originalRadio = QRadioButton("Formato originale (qualità massima)")
        self.originalRadio.setChecked(True)
        layout.addWidget(self.originalRadio)

        self.compressedRadio = QRadioButton("Formato compresso (per email)")
        layout.addWidget(self.compressedRadio)

        # Playback speed option
        self.saveWithPlaybackSpeedCheck = QCheckBox("Salva con velocità di riproduzione")
        self.saveWithPlaybackSpeedCheck.setChecked(False)
        layout.addWidget(self.saveWithPlaybackSpeedCheck)

        # Compression options group
        self.compressionGroup = QGroupBox("Opzioni di compressione")
        compressLayout = QVBoxLayout()

        # Quality slider
        qualityLayout = QHBoxLayout()
        qualityLayout.addWidget(QLabel("Bassa"))

        self.qualitySlider = QSlider(Qt.Orientation.Horizontal)
        self.qualitySlider.setMinimum(1)
        self.qualitySlider.setMaximum(10)
        self.qualitySlider.setValue(5)
        self.qualitySlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.qualitySlider.setTickInterval(1)
        qualityLayout.addWidget(self.qualitySlider)

        qualityLayout.addWidget(QLabel("Alta"))
        compressLayout.addLayout(qualityLayout)

        self.qualityLabel = QLabel("Qualità: 5")
        self.qualitySlider.valueChanged.connect(
            lambda value: self.qualityLabel.setText(f"Qualità: {value}")
        )
        compressLayout.addWidget(self.qualityLabel)

        # Target file size estimation
        self.fileSizeLabel = QLabel(self.get_file_size_info())
        self.qualitySlider.valueChanged.connect(
            lambda _: self.update_file_size_estimation()
        )
        compressLayout.addWidget(self.fileSizeLabel)

        self.compressionGroup.setLayout(compressLayout)
        layout.addWidget(self.compressionGroup)

        # Enable/disable options based on selection
        self.originalRadio.toggled.connect(self.update_options_state)
        self.compressedRadio.toggled.connect(self.update_options_state)

        # Set initial state
        self.update_options_state()

        # Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def update_options_state(self):
        is_compressed = self.compressedRadio.isChecked()
        self.compressionGroup.setEnabled(is_compressed)

    def getOptions(self):
        return {
            'use_compression': self.compressedRadio.isChecked(),
            'compression_quality': self.qualitySlider.value(),
            'save_with_speed': self.saveWithPlaybackSpeedCheck.isChecked()
        }

    def get_file_size_info(self):
        try:
            # Get original file size in MB
            original_size = os.path.getsize(self.source_path) / (1024 * 1024)
            return f"Dimensione originale: {original_size:.1f} MB\nDimensione stimata: {self.estimate_compressed_size()}"
        except Exception:
            return "Dimensione file: N/A"

    def estimate_compressed_size(self):
        try:
            # Get original file size in MB
            original_size = os.path.getsize(self.source_path) / (1024 * 1024)

            # Map quality 1-10 to compression ratio
            # Quality 1: ~20% of original, Quality 10: ~80% of original
            quality = self.qualitySlider.value()
            ratio = 0.2 + (quality - 1) * 0.06

            estimated_size = original_size * ratio
            return f"~{estimated_size:.1f} MB"
        except Exception:
            return "N/A"

    def update_file_size_estimation(self):
        self.fileSizeLabel.setText(self.get_file_size_info())