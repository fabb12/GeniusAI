from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSlider
from PyQt6.QtGui import QPixmap, QImage, QPainter
from PyQt6.QtCore import Qt, QRect, QSize
from .ResizableRubberBand import ResizableRubberBand
from screeninfo import get_monitors

class FrameEditorDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modifica Frame")
        self.setModal(True)

        self.original_pixmap = pixmap
        self.display_pixmap = QPixmap(self.original_pixmap)

        monitor = get_monitors()[0]
        dialog_width = monitor.width // 2
        dialog_height = monitor.height // 2
        self.resize(dialog_width, dialog_height)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setPixmap(self.display_pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rubber_band = ResizableRubberBand(self.image_label)

        main_layout.addWidget(self.image_label)

        # Slider per lo zoom
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 200) # dal 50% al 200%
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        zoom_layout.addWidget(self.zoom_slider)
        main_layout.addLayout(zoom_layout)

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Applica")
        self.cancel_button = QPushButton("Annulla")
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.update_image_display()

    def update_zoom(self, value):
        self.update_image_display()

    def update_image_display(self):
        zoom_factor = self.zoom_slider.value() / 100.0
        new_size = self.original_pixmap.size() * zoom_factor
        self.display_pixmap = self.original_pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.adjustSize()
        self.rubber_band.setGeometry(self.image_label.rect())
        self.rubber_band.show()


    def get_edited_pixmap(self):
        pixmap = self.image_label.pixmap()
        if not pixmap or pixmap.isNull():
            return QPixmap()

        label_size = self.image_label.size()
        pixmap_size = pixmap.size()

        offset_x = (label_size.width() - pixmap_size.width()) / 2
        offset_y = (label_size.height() - pixmap_size.height()) / 2

        rubber_band_geometry = self.rubber_band.geometry()

        crop_x = rubber_band_geometry.x() - offset_x
        crop_y = rubber_band_geometry.y() - offset_y

        scale_x = self.original_pixmap.width() / pixmap_size.width()
        scale_y = self.original_pixmap.height() / pixmap_size.height()

        original_crop_x = int(crop_x * scale_x)
        original_crop_y = int(crop_y * scale_y)
        original_crop_width = int(rubber_band_geometry.width() * scale_x)
        original_crop_height = int(rubber_band_geometry.height() * scale_y)

        crop_rect_on_original = QRect(
            original_crop_x,
            original_crop_y,
            original_crop_width,
            original_crop_height
        )
        return self.original_pixmap.copy(crop_rect_on_original)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_image_display()
        self._center_rubber_band()

    def _center_rubber_band(self):
        rb_width = self.image_label.width() // 2
        rb_height = self.image_label.height() // 2
        rb_x = (self.image_label.width() - rb_width) // 2
        rb_y = (self.image_label.height() - rb_height) // 2
        self.rubber_band.setGeometry(QRect(rb_x, rb_y, rb_width, rb_height))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)
