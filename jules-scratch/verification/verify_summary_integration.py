import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QCoreApplication
from PyQt6.QtGui import QImage, QPixmap
import time
import mss
import mss.tools
from PIL import Image

# Add the src directory to the python path
sys.path.append(os.path.abspath('.'))

from src.TGeniusAI import VideoAudioManager

def find_widget(widget, object_name):
    """Recursively find a widget by its object name."""
    if widget.objectName() == object_name:
        return widget
    for child in widget.findChildren(QWidget):
        if child.objectName() == object_name:
            return child
    return None

def main():
    app = QApplication(sys.argv)

    # Heuristic to find the main window
    main_window = None
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, VideoAudioManager):
            main_window = widget
            break

    if not main_window:
        print("Main window not found.")
        sys.exit(1)

    def run_test():
        # 1. Load a video
        video_path = os.path.abspath("test/test_video.mp4")
        if not os.path.exists(video_path):
            print(f"Test video not found at {video_path}")
            # Create a dummy video file for testing
            os.makedirs("test", exist_ok=True)
            from moviepy.editor import ColorClip
            clip = ColorClip(size=(640, 480), color=(0,0,0), duration=10)
            clip.write_videofile(video_path, fps=24)

        main_window.loadVideo(video_path)

        # 2. Add dummy transcription text
        main_window.singleTranscriptionTextArea.setPlainText("This is a test transcription. It has several sentences. This is the second sentence. This is the third sentence.")

        # 3. Click the "Genera Riassunto Integrato" button
        button = main_window.integrateSummaryWithFramesButton
        button.click()

        # 4. Wait for completion
        def check_completion():
            if not main_window.current_thread or not main_window.current_thread.isRunning():
                QTimer.singleShot(1000, take_screenshot) # Wait a bit for UI to update
            else:
                QTimer.singleShot(1000, check_completion)

        QTimer.singleShot(1000, check_completion)

    def take_screenshot():
        with mss.mss() as sct:
            # Get a screenshot of the 1st monitor
            sct_img = sct.grab(sct.monitors[1])

            # Create an Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Crop the image to the application window
            x, y, w, h = main_window.geometry().getRect()
            img = img.crop((x, y, x + w, y + h))

            # Save the screenshot
            mss.tools.to_png(img.tobytes(), img.size, "jules-scratch/verification/verification.png")

        print("Screenshot saved to jules-scratch/verification/verification.png")
        QCoreApplication.quit()

    QTimer.singleShot(1000, run_test)
    app.exec()

if __name__ == "__main__":
    main()
