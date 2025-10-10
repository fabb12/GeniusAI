# File: src/ui/ExportDialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QDialogButtonBox, QFileDialog, QWidget, QComboBox, QLabel
)
import os

class ExportDialog(QDialog):
    """
    A dialog for configuring file export options, including file path,
    format (Word or PDF), and whether to remove timestamps.
    """
    def __init__(self, default_filename="summary", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Esporta Riepilogo")
        self.setMinimumWidth(450)

        self.default_basename = default_filename

        # Main layout
        layout = QVBoxLayout(self)

        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Word Document (*.docx)", "PDF Document (*.pdf)"])
        self.format_combo.currentIndexChanged.connect(self.update_filepath_extension)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # File path layout
        file_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.browse_button = QPushButton("Sfoglia...")
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.path_edit)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)

        # Initialize with the correct extension
        self.update_filepath_extension()

        # Options
        self.remove_timestamps_checkbox = QCheckBox("Rimuovi i timecode dal documento")
        self.remove_timestamps_checkbox.setChecked(True)
        layout.addWidget(self.remove_timestamps_checkbox)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def update_filepath_extension(self):
        """Updates the file path extension based on the selected format."""
        current_format = self.format_combo.currentText()

        current_path = self.path_edit.text()
        base, _ = os.path.splitext(current_path)

        if not base: # If the line edit is empty, use the default
            base = self.default_basename

        if "(*.docx)" in current_format:
            self.path_edit.setText(f"{base}.docx")
        elif "(*.pdf)" in current_format:
            self.path_edit.setText(f"{base}.pdf")

    def browse_file(self):
        """
        Opens a file dialog to select the save location for the exported file.
        """
        current_path = self.path_edit.text()
        directory = os.path.dirname(current_path) if os.path.dirname(current_path) else "."

        selected_format = self.format_combo.currentText()

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Documento",
            current_path,
            f"{selected_format};;All Files (*)"
        )

        if path:
            # Ensure the correct extension is appended if the user doesn't add it
            if "(*.docx)" in selected_format and not path.lower().endswith('.docx'):
                path += '.docx'
            elif "(*.pdf)" in selected_format and not path.lower().endswith('.pdf'):
                path += '.pdf'
            self.path_edit.setText(path)

    def get_options(self):
        """
        Returns the selected export options.
        """
        selected_format = self.format_combo.currentText()
        file_format = 'docx'
        if '(*.pdf)' in selected_format:
            file_format = 'pdf'

        return {
            "filepath": self.path_edit.text(),
            "format": file_format,
            "remove_timestamps": self.remove_timestamps_checkbox.isChecked()
        }