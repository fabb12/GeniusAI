import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit,
    QSpinBox, QPushButton, QDialogButtonBox, QColorDialog, QFontDialog,
    QHBoxLayout, QLabel, QFileDialog, QComboBox, QDoubleSpinBox
)

class AddMediaDialog(QDialog):
    # Signal to be emitted when the dialog is accepted
    # It will carry a dictionary with the media information
    media_added = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Media/Text")
        self.setMinimumWidth(450)

        # Main layout
        self.layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        self.tab_text = QWidget()
        self.tab_image = QWidget()
        self.tab_gif = QWidget()

        self.tabs.addTab(self.tab_text, "Text")
        self.tabs.addTab(self.tab_image, "Image")
        self.tabs.addTab(self.tab_gif, "GIF")

        self.layout.addWidget(self.tabs)

        # Create the UI for each tab
        self._create_text_tab()
        self._create_image_tab()
        self._create_gif_tab()

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _create_text_tab(self):
        layout = QFormLayout(self.tab_text)

        # Text Input
        self.text_input = QLineEdit()
        layout.addRow("Text:", self.text_input)

        # Font
        font_layout = QHBoxLayout()
        self.font_label = QLabel("Arial, 12")
        self.font_button = QPushButton("Choose Font...")
        self.font_button.clicked.connect(self._choose_font)
        font_layout.addWidget(self.font_label)
        font_layout.addWidget(self.font_button)
        layout.addRow("Font:", font_layout)
        self.current_font = QFont("Arial", 12)

        # Color
        color_layout = QHBoxLayout()
        self.color_label = QLabel()
        self.color_button = QPushButton("Choose Color...")
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_label)
        color_layout.addWidget(self.color_button)
        layout.addRow("Color:", color_layout)
        self.current_color = QColor("white")
        self._update_color_label()

        # Position
        pos_layout = QHBoxLayout()
        self.pos_x_spinbox = QSpinBox()
        self.pos_x_spinbox.setRange(0, 9999)
        self.pos_y_spinbox = QSpinBox()
        self.pos_y_spinbox.setRange(0, 9999)
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.pos_x_spinbox)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.pos_y_spinbox)
        layout.addRow("Position (px):", pos_layout)

        # Duration
        self.duration_spinbox_text = QDoubleSpinBox()
        self.duration_spinbox_text.setRange(0.1, 600.0)
        self.duration_spinbox_text.setValue(5.0)
        self.duration_spinbox_text.setSuffix(" s")
        layout.addRow("Duration:", self.duration_spinbox_text)

    def _create_image_tab(self):
        layout = QFormLayout(self.tab_image)

        # File Path
        file_layout = QHBoxLayout()
        self.image_path_label = QLineEdit()
        self.image_path_label.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(lambda: self._browse_file(self.image_path_label, "Images (*.png *.jpg *.jpeg)"))
        file_layout.addWidget(self.image_path_label)
        file_layout.addWidget(browse_button)
        layout.addRow("Image File:", file_layout)

        # Position
        pos_layout = QHBoxLayout()
        self.image_pos_x_spinbox = QSpinBox()
        self.image_pos_x_spinbox.setRange(0, 9999)
        self.image_pos_y_spinbox = QSpinBox()
        self.image_pos_y_spinbox.setRange(0, 9999)
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.image_pos_x_spinbox)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.image_pos_y_spinbox)
        layout.addRow("Position (px):", pos_layout)

        # Size
        size_layout = QHBoxLayout()
        self.image_width_spinbox = QSpinBox()
        self.image_width_spinbox.setRange(1, 9999)
        self.image_width_spinbox.setValue(100)
        self.image_height_spinbox = QSpinBox()
        self.image_height_spinbox.setRange(1, 9999)
        self.image_height_spinbox.setValue(100)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.image_width_spinbox)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.image_height_spinbox)
        layout.addRow("Size (px):", size_layout)

        # Duration
        self.duration_spinbox_image = QDoubleSpinBox()
        self.duration_spinbox_image.setRange(0.1, 600.0)
        self.duration_spinbox_image.setValue(5.0)
        self.duration_spinbox_image.setSuffix(" s")
        layout.addRow("Duration:", self.duration_spinbox_image)

    def _create_gif_tab(self):
        layout = QFormLayout(self.tab_gif)

        # File Path
        file_layout = QHBoxLayout()
        self.gif_path_label = QLineEdit()
        self.gif_path_label.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(lambda: self._browse_file(self.gif_path_label, "GIFs (*.gif)"))
        file_layout.addWidget(self.gif_path_label)
        file_layout.addWidget(browse_button)
        layout.addRow("GIF File:", file_layout)

        # Position
        pos_layout = QHBoxLayout()
        self.gif_pos_x_spinbox = QSpinBox()
        self.gif_pos_x_spinbox.setRange(0, 9999)
        self.gif_pos_y_spinbox = QSpinBox()
        self.gif_pos_y_spinbox.setRange(0, 9999)
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.gif_pos_x_spinbox)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.gif_pos_y_spinbox)
        layout.addRow("Position (px):", pos_layout)

        # Size
        size_layout = QHBoxLayout()
        self.gif_width_spinbox = QSpinBox()
        self.gif_width_spinbox.setRange(1, 9999)
        self.gif_width_spinbox.setValue(100)
        self.gif_height_spinbox = QSpinBox()
        self.gif_height_spinbox.setRange(1, 9999)
        self.gif_height_spinbox.setValue(100)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.gif_width_spinbox)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.gif_height_spinbox)
        layout.addRow("Size (px):", size_layout)

        # Duration
        self.duration_spinbox_gif = QDoubleSpinBox()
        self.duration_spinbox_gif.setRange(0.1, 600.0)
        self.duration_spinbox_gif.setValue(5.0)
        self.duration_spinbox_gif.setSuffix(" s")
        layout.addRow("Duration:", self.duration_spinbox_gif)

    def _choose_font(self):
        font, ok = QFontDialog.getFont(self.current_font, self)
        if ok:
            self.current_font = font
            self.font_label.setText(f"{font.family()}, {font.pointSize()}")

    def _choose_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self._update_color_label()

    def _update_color_label(self):
        self.color_label.setText(self.current_color.name())
        self.color_label.setStyleSheet(f"background-color: {self.current_color.name()}; color: {'black' if self.current_color.lightness() > 127 else 'white'}; padding: 2px;")

    def _browse_file(self, label_widget, file_filter):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_name:
            label_widget.setText(file_name)

    def get_media_data(self):
        current_tab_index = self.tabs.currentIndex()
        data = {}

        if current_tab_index == 0: # Text
            data = {
                "type": "text",
                "text": self.text_input.text(),
                "font": self.current_font.family(),
                "fontsize": self.current_font.pointSize(),
                "color": self.current_color.name(),
                "position": (self.pos_x_spinbox.value(), self.pos_y_spinbox.value()),
                "duration": self.duration_spinbox_text.value(),
            }
        elif current_tab_index == 1: # Image
            data = {
                "type": "image",
                "path": self.image_path_label.text(),
                "position": (self.image_pos_x_spinbox.value(), self.image_pos_y_spinbox.value()),
                "size": (self.image_width_spinbox.value(), self.image_height_spinbox.value()),
                "duration": self.duration_spinbox_image.value(),
            }
        elif current_tab_index == 2: # GIF
            data = {
                "type": "gif",
                "path": self.gif_path_label.text(),
                "position": (self.gif_pos_x_spinbox.value(), self.gif_pos_y_spinbox.value()),
                "size": (self.gif_width_spinbox.value(), self.gif_height_spinbox.value()),
                "duration": self.duration_spinbox_gif.value(),
            }
        return data

    def accept(self):
        data = self.get_media_data()
        # Basic validation
        if data['type'] in ['image', 'gif'] and not data.get('path'):
            return # Don't accept if path is missing
        if data['type'] == 'text' and not data.get('text'):
            return # Don't accept if text is missing

        self.media_added.emit(data)
        super().accept()