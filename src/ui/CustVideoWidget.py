from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
import sys

class CropVideoWidget(QVideoWidget):
    """
    A simple video widget that serves as a display surface for video content.
    All custom drawing and event handling has been moved to the VideoOverlay class.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)


def main():
    """A simple main function to test the widget."""
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    video_widget = CropVideoWidget()
    layout.addWidget(video_widget)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
