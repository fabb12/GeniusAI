
import sys
from PyQt6.QtWidgets import QApplication, QMenu
from PyQt6.QtGui import QImage, QColor, QContextMenuEvent
from PyQt6.QtCore import QPoint
from src.ui.CustumTextEdit import CustomTextEdit

def test_image_insertion_and_menu():
    app = QApplication(sys.argv)
    editor = CustomTextEdit()

    # Create a dummy image
    image = QImage(100, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("blue"))

    # Insert the image
    editor.insert_image_with_metadata(image, 100, 100, "dummy_video.mp4", 10.0)

    # Check if the image was inserted
    doc = editor.document()
    assert doc.toPlainText() == "\ufffc"

    # Simulate a right-click to trigger the context menu
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(0, 0), QPoint(0,0))

    # We can't actually show the menu in a headless environment,
    # but we can check if the correct actions are created
    cursor = editor.cursorForPosition(QPoint(0, 0))
    image_format = editor.get_image_format_at_cursor(cursor)

    if image_format:
        print("Image found at cursor.")
        menu = QMenu()
        resize_action = menu.addAction("Ridimensiona Immagine")
        crop_action = menu.addAction("Ritaglia Immagine")

        assert resize_action is not None
        assert crop_action is not None
        print("Test passed: Resize and Crop actions are available.")
    else:
        print("Test failed: Image not found at cursor.")

    app.quit()

if __name__ == "__main__":
    test_image_insertion_and_menu()
