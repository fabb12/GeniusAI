# File: src/ui/ExportDialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QDialogButtonBox, QFileDialog, QWidget
)
import os

class ExportDialog(QDialog):
    """
    A dialog for configuring DOCX export options, including file path
    and whether to remove timestamps.
    """
    def __init__(self, default_filename="summary.docx", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Esporta in DOCX")
        self.setMinimumWidth(400)

        # Main layout
        layout = QVBoxLayout(self)

        # File path layout
        file_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(default_filename)
        self.browse_button = QPushButton("Sfoglia...")
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.path_edit)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)

        # Options
        self.remove_timestamps_checkbox = QCheckBox("Rimuovi i timecode dal documento")
        self.remove_timestamps_checkbox.setChecked(True)
        layout.addWidget(self.remove_timestamps_checkbox)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def browse_file(self):
        """
        Opens a file dialog to select the save location for the DOCX file.
        """
        current_path = self.path_edit.text()
        directory = os.path.dirname(current_path) if os.path.dirname(current_path) else "."

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Documento Word",
            directory,
            "Word Document (*.docx)"
        )

        if path:
            if not path.lower().endswith('.docx'):
                path += '.docx'
            self.path_edit.setText(path)

    def get_options(self):
        """
        Returns the selected export options.
        """
        return {
            "filepath": self.path_edit.text(),
            "remove_timestamps": self.remove_timestamps_checkbox.isChecked()
        }