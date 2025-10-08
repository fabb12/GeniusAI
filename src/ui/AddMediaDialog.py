import os
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QFontInfo
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit,
    QSpinBox, QPushButton, QDialogButtonBox, QColorDialog, QFontDialog,
    QHBoxLayout, QLabel, QFileDialog, QComboBox, QDoubleSpinBox, QGroupBox
)

class AddMediaDialog(QDialog):
    media_added = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Add Media/Text with Preview")
        self.setMinimumSize(900, 600)

        # Main horizontal layout
        self.main_layout = QHBoxLayout(self)

        # Left side for settings
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.main_layout.addWidget(self.settings_widget, 1) # Add with stretch factor

        # Tab widget for different media types
        self.tabs = QTabWidget()
        self.tab_text = QWidget()
        self.tab_image = QWidget()
        self.tab_gif = QWidget()

        self.tabs.addTab(self.tab_text, "Text")
        self.tabs.addTab(self.tab_image, "Image")
        self.tabs.addTab(self.tab_gif, "GIF")
        self.settings_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.update_preview)

        self._create_text_tab()
        self._create_image_tab()
        self._create_gif_tab()

        # Dialog buttons (OK, Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.settings_layout.addWidget(self.button_box)

        # Right side for preview
        self.preview_group = QGroupBox("Preview")
        self.preview_layout = QVBoxLayout(self.preview_group)
        self.main_layout.addWidget(self.preview_group, 2) # Add with stretch factor

        self.preview_label = QLabel("Preview will be shown here.")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(480, 270)
        self.preview_label.setStyleSheet("border: 1px solid #ccc;")
        self.preview_label.mousePressEvent = self.preview_clicked
        self.preview_layout.addWidget(self.preview_label)

        self.refresh_preview_button = QPushButton("Refresh Preview")
        self.refresh_preview_button.clicked.connect(self.update_preview)
        self.preview_layout.addWidget(self.refresh_preview_button)

        self.update_preview() # Initial preview

    def preview_clicked(self, event):
        if not self.preview_label.pixmap() or self.preview_label.pixmap().isNull():
            return

        # Get the original video frame size
        original_pixmap = self.main_window.get_frame_at(self.main_window.player.position())
        if not original_pixmap:
            return
        original_width = original_pixmap.width()
        original_height = original_pixmap.height()

        # Get the size of the label and the displayed pixmap
        label_size = self.preview_label.size()
        pixmap_size = self.preview_label.pixmap().size()

        # Calculate the position of the click relative to the pixmap within the label
        click_pos = event.pos()
        x_offset = (label_size.width() - pixmap_size.width()) / 2
        y_offset = (label_size.height() - pixmap_size.height()) / 2

        # Check if the click is outside the pixmap area
        if not (x_offset <= click_pos.x() < x_offset + pixmap_size.width() and
                y_offset <= click_pos.y() < y_offset + pixmap_size.height()):
            return

        pixmap_x = click_pos.x() - x_offset
        pixmap_y = click_pos.y() - y_offset

        # Calculate the scaling factor
        scale_w = pixmap_size.width() / original_width
        scale_h = pixmap_size.height() / original_height
        # Since we use KeepAspectRatio, scale_w and scale_h should be the same
        scale = min(scale_w, scale_h) if scale_w > 0 and scale_h > 0 else 1.0

        # Convert the click coordinates to the original video frame's coordinates
        original_x = int(pixmap_x / scale)
        original_y = int(pixmap_y / scale)

        # Update the corresponding spinboxes based on the current tab
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index == 0: # Text
            self.pos_x_spinbox.setValue(original_x)
            self.pos_y_spinbox.setValue(original_y)
        elif current_tab_index == 1: # Image
            self.image_pos_x_spinbox.setValue(original_x)
            self.image_pos_y_spinbox.setValue(original_y)
        elif current_tab_index == 2: # GIF
            self.gif_pos_x_spinbox.setValue(original_x)
            self.gif_pos_y_spinbox.setValue(original_y)

        # The spinbox valueChanged signal will automatically call update_preview

    def update_preview(self):
        if not self.main_window:
            return

        # 1. Get the current frame from the main window
        base_pixmap = self.main_window.get_frame_at(self.main_window.player.position())
        if not base_pixmap:
            self.preview_label.setText("Could not get video frame.")
            return

        # Create a mutable pixmap to draw on
        preview_pixmap = base_pixmap.copy()

        # 2. Get current media settings
        media_data = self.get_media_data()

        # 3. Draw the overlay
        painter = QPainter(preview_pixmap)
        media_type = media_data.get('type')

        if media_type == 'text' and media_data.get('text'):
            font = self.current_font
            color = self.current_color
            position = media_data['position']
            text = media_data['text']

            painter.setFont(font)
            painter.setPen(color)
            painter.drawText(position[0], position[1], text)

        elif media_type == 'image' and media_data.get('path'):
            image_path = media_data['path']
            if os.path.exists(image_path):
                overlay_pixmap = QPixmap(image_path)
                if not overlay_pixmap.isNull():
                    position = media_data['position']
                    size = media_data['size']
                    painter.drawPixmap(position[0], position[1], size[0], size[1], overlay_pixmap)

        elif media_type == 'gif' and media_data.get('path'):
            # For GIF, we just show the first frame as a static image in the preview
            gif_path = media_data['path']
            if os.path.exists(gif_path):
                overlay_pixmap = QPixmap(gif_path) # QPixmap loads the first frame of a GIF
                if not overlay_pixmap.isNull():
                    position = media_data['position']
                    size = media_data['size']
                    painter.drawPixmap(position[0], position[1], size[0], size[1], overlay_pixmap)

        painter.end()

        # 4. Display the result, scaled to fit the label
        self.preview_label.setPixmap(preview_pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))


    def _create_text_tab(self):
        layout = QFormLayout(self.tab_text)

        # Text Input
        self.text_input = QLineEdit()
        self.text_input.textChanged.connect(self.update_preview)
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
        self.pos_x_spinbox.valueChanged.connect(self.update_preview)
        self.pos_y_spinbox = QSpinBox()
        self.pos_y_spinbox.setRange(0, 9999)
        self.pos_y_spinbox.valueChanged.connect(self.update_preview)
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
        self.image_pos_x_spinbox.valueChanged.connect(self.update_preview)
        self.image_pos_y_spinbox = QSpinBox()
        self.image_pos_y_spinbox.setRange(0, 9999)
        self.image_pos_y_spinbox.valueChanged.connect(self.update_preview)
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
        self.image_width_spinbox.valueChanged.connect(self.update_preview)
        self.image_height_spinbox = QSpinBox()
        self.image_height_spinbox.setRange(1, 9999)
        self.image_height_spinbox.setValue(100)
        self.image_height_spinbox.valueChanged.connect(self.update_preview)
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
        self.gif_pos_x_spinbox.valueChanged.connect(self.update_preview)
        self.gif_pos_y_spinbox = QSpinBox()
        self.gif_pos_y_spinbox.setRange(0, 9999)
        self.gif_pos_y_spinbox.valueChanged.connect(self.update_preview)
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
        self.gif_width_spinbox.valueChanged.connect(self.update_preview)
        self.gif_height_spinbox = QSpinBox()
        self.gif_height_spinbox.setRange(1, 9999)
        self.gif_height_spinbox.setValue(100)
        self.gif_height_spinbox.valueChanged.connect(self.update_preview)
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
            self.update_preview()

    def _choose_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self._update_color_label()
            self.update_preview()

    def _update_color_label(self):
        self.color_label.setText(self.current_color.name())
        self.color_label.setStyleSheet(f"background-color: {self.current_color.name()}; color: {'black' if self.current_color.lightness() > 127 else 'white'}; padding: 2px;")

    def _browse_file(self, label_widget, file_filter):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_name:
            label_widget.setText(file_name)
            self.update_preview()

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