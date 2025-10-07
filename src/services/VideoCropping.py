import re
import os
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip
from proglog import ProgressBarLogger

class CropLogger(ProgressBarLogger):
    """
    This class parses the ffmpeg output to update a progress bar.
    It subclasses proglog.ProgressBarLogger to be compatible with moviepy.
    """
    def __init__(self, progress_signal):
        super().__init__()
        self.progress_signal = progress_signal
        self.duration = None
        # Regex to find the duration of the video
        self.re_duration = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}")
        # Regex to find the current time of the processing
        self.re_time = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")

    def callback(self, **kwargs):
        """
        This method is called by proglog with each line of ffmpeg's output.
        """
        line = kwargs.get("message", "")
        if "Duration" in line:
            match = self.re_duration.search(line)
            if match:
                h, m, s = map(float, match.groups())
                self.duration = h * 3600 + m * 60 + s

        if self.duration and "time=" in line:
            match = self.re_time.search(line)
            if match:
                h, m, s = map(float, match.groups())
                elapsed = h * 3600 + m * 60 + s
                progress = int((elapsed / self.duration) * 100)
                self.progress_signal.emit(progress)

    # The __call__ and iter_bar methods are provided by the parent class ProgressBarLogger.

class CropThread(QThread):
    """
    A QThread to run the video cropping process in the background.
    """
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, video_path, crop_rect, project_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.crop_rect = crop_rect
        self.project_path = project_path

    def run(self):
        try:
            video = VideoFileClip(self.video_path)
            video_width, video_height = video.size

            # The crop dialog displays the frame at half size, so we must scale the coordinates up by 2
            scale_factor = 2

            x1 = int(self.crop_rect.x() * scale_factor)
            y1 = int(self.crop_rect.y() * scale_factor)
            x2 = int((self.crop_rect.x() + self.crop_rect.width()) * scale_factor)
            y2 = int((self.crop_rect.y() + self.crop_rect.height()) * scale_factor)

            # Ensure coordinates are within video bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(video_width, x2)
            y2 = min(video_height, y2)

            if x1 >= x2 or y1 >= y2:
                self.error.emit("L'area di ritaglio non è valida.")
                return

            cropped_video = video.crop(x1=x1, y1=y1, x2=x2, y2=y2)

            # Define output path based on whether a project is active
            if self.project_path:
                clip_dir = os.path.join(self.project_path, "clips")
                os.makedirs(clip_dir, exist_ok=True)
                original_filename = os.path.basename(self.video_path)
                base, ext = os.path.splitext(original_filename)
                # Ensure the extension is .mp4 for consistency
                if not ext:
                    ext = '.mp4'
                output_filename = f"cropped_{base}{ext}"
                output_path = os.path.join(clip_dir, output_filename)
            else:
                # Fallback to creating a temporary file if no project is open
                fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='cropped_')
                os.close(fd)

            # Use the custom logger to get progress updates
            logger = CropLogger(self.progress)

            cropped_video.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=logger)

            self.completed.emit(output_path)
        except Exception as e:
            self.error.emit(str(e))