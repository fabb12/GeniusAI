import re
import os
import tempfile
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip
from proglog import ProgressBarLogger

class CropLogger(ProgressBarLogger):
    def __init__(self, progress_signal, thread):
        super().__init__()
        self.progress_signal = progress_signal
        self.thread = thread
        self.duration = None
        self.re_duration = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}")
        self.re_time = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")

    def callback(self, **kwargs):
        if not self.thread.running:
            # Moviepy non ha un modo pulito per interrompere, quindi solleviamo un'eccezione
            # per fermare il processo di scrittura del file.
            raise InterruptedError("Cropping cancelled by user.")

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
                if self.thread.running:
                    self.progress_signal.emit(progress)


class CropThread(QThread):
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, video_path, crop_rect, project_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.crop_rect = crop_rect
        self.project_path = project_path
        self.process = None
        self.running = True
        self.original_popen = None

    def stop(self):
        self.running = False
        if self.process:
            try:
                self.process.kill()
                self.process = None
                self.error.emit("Ritaglio video annullato.")
            except Exception as e:
                self.error.emit(f"Errore durante l'annullamento: {e}")

    def _monkey_patch_subprocess(self):
        """Sostituisce temporaneamente subprocess.Popen per catturare il processo ffmpeg."""
        self.original_popen = subprocess.Popen
        def custom_popen(*args, **kwargs):
            # Assicurati che CREATE_NO_WINDOW sia usato se su Windows
            if os.name == 'nt':
                kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
            self.process = self.original_popen(*args, **kwargs)
            return self.process
        subprocess.Popen = custom_popen

    def _unpatch_subprocess(self):
        """Ripristina l'originale subprocess.Popen."""
        if self.original_popen:
            subprocess.Popen = self.original_popen
            self.original_popen = None


    def run(self):
        if not self.running:
            return

        self._monkey_patch_subprocess()
        try:
            video = VideoFileClip(self.video_path)
            video_width, video_height = video.size

            x1 = self.crop_rect.x()
            y1 = self.crop_rect.y()
            x2 = self.crop_rect.x() + self.crop_rect.width()
            y2 = self.crop_rect.y() + self.crop_rect.height()

            # Ensure coordinates are within the video dimensions
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(video_width, x2), min(video_height, y2)

            if x1 >= x2 or y1 >= y2:
                self.error.emit("L'area di ritaglio non è valida.")
                return

            cropped_video = video.crop(x1=x1, y1=y1, x2=x2, y2=y2)

            # Ensure the duration of the cropped video is the same as the original
            cropped_video = cropped_video.set_duration(video.duration)

            if self.project_path:
                clip_dir = os.path.join(self.project_path, "clips")
                os.makedirs(clip_dir, exist_ok=True)
                original_filename = os.path.basename(self.video_path)
                base, ext = os.path.splitext(original_filename)
                ext = ext if ext else '.mp4'
                output_filename = f"cropped_{base}{ext}"
                output_path = os.path.join(clip_dir, output_filename)
            else:
                fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='cropped_')
                os.close(fd)

            logger = CropLogger(self.progress, self)

            cropped_video.write_videofile(
                output_path,
                fps=video.fps,
                codec='libx264',
                audio_codec='aac',
                logger=logger
            )

            if self.running:
                self.completed.emit(output_path)
        except InterruptedError:
            # This exception is raised by our custom logger when cancelled
            if not self.running:
                # Se l'interruzione è dovuta a una cancellazione, non segnalare un errore.
                pass # L'errore è già stato emesso dal metodo stop()
        except Exception as e:
            if self.running:
                self.error.emit(str(e))
        finally:
            # Ripristina sempre la funzione originale
            self._unpatch_subprocess()
            self.process = None