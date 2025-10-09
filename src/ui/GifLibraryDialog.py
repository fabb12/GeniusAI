import os
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QDialogButtonBox,
    QListWidgetItem
)
from PyQt6.QtGui import QMovie

class GifLibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GIF Library")
        self.setMinimumSize(600, 400)

        # Main layout
        self.main_layout = QHBoxLayout()

        # Left side: GIF list
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_gif_selected)
        self.main_layout.addWidget(self.list_widget, 1)

        # Right side: Preview
        self.preview_label = QLabel("Select a GIF to preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet("border: 1px solid #ccc;")
        self.main_layout.addWidget(self.preview_label, 2)
        self.movie = None

        # Dialog buttons (OK, Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Overall layout
        self.v_layout = QVBoxLayout()
        self.v_layout.addLayout(self.main_layout)
        self.v_layout.addWidget(self.button_box)
        self.setLayout(self.v_layout)

        self.populate_gif_list()
        self.selected_gif_path = None

    def populate_gif_list(self):
        gif_folder = "gifs"
        if not os.path.exists(gif_folder):
            return

        for file_name in os.listdir(gif_folder):
            if file_name.lower().endswith(".gif"):
                item = QListWidgetItem(file_name)
                item.setData(Qt.ItemDataRole.UserRole, os.path.join(gif_folder, file_name))
                self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def on_gif_selected(self, current, previous):
        if current is None:
            if self.movie:
                self.movie.stop()
            self.preview_label.setText("No GIF Selected")
            self.selected_gif_path = None
            return

        gif_path = current.data(Qt.ItemDataRole.UserRole)
        self.selected_gif_path = gif_path

        if self.movie:
            self.movie.stop()

        self.movie = QMovie(gif_path)
        if not self.movie.isValid():
            self.preview_label.setText("Could not load GIF.")
            return

        self.preview_label.setMovie(self.movie)
        self.movie.start()

    def get_selected_gif_path(self):
        if self.result() == QDialog.DialogCode.Accepted and self.selected_gif_path:
            return self.selected_gif_path
        return None