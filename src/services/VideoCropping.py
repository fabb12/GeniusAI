import re
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip

class CropLogger:
    """
    This class parses the ffmpeg output to update a progress bar.
    """
    def __init__(self, progress_signal):
        self.progress_signal = progress_signal
        self.duration = None
        # Regex to find the duration of the video
        self.re_duration = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}")
        # Regex to find the current time of the processing
        self.re_time = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")

    def __call__(self, **kwargs):
        """
        This method is called by moviepy with each line of ffmpeg's output.
        """
        line = kwargs.get("message", "") # It seems moviepy now uses a 'message' keyword argument
        if not line:
            line = kwargs.get("line", "") # Fallback for older versions

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

    def iter_bar(self, **kwargs):
        """
        A dummy iter_bar method to comply with the proglog interface.
        Moviepy expects the logger to have this method.
        """
        iterable = kwargs.get("iterable", kwargs.get("iteration", []))
        return iter(iterable)

class CropThread(QThread):
    """
    A QThread to run the video cropping process in the background.
    """
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, video_path, crop_rect, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.crop_rect = crop_rect

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

            # FIX: Riduci leggermente la durata per evitare l'eco audio alla fine
            if cropped_video.duration and cropped_video.duration > 0.15:
                cropped_video = cropped_video.subclip(0, cropped_video.duration - 0.15)

            output_path = tempfile.mktemp(suffix='.mp4')

            # Use the custom logger to get progress updates
            logger = CropLogger(self.progress)

            cropped_video.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=logger)

            self.completed.emit(output_path)
        except Exception as e:
            self.error.emit(str(e))
