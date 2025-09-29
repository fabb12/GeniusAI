from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import os
import time
import proglog

class CompositingProgressLogger(proglog.ProgressBarLogger):
    def __init__(self, progress_signal_emitter):
        super().__init__()
        self.progress_signal_emitter = progress_signal_emitter
        self.duration = 0

    def bars_callback(self, bar, attr, value, old_value=None):
        super().bars_callback(bar, attr, value, old_value)
        if attr == 'duration':
            self.duration = value
        elif attr == 't' and self.duration > 0:
            percent = int((value / self.duration) * 100)
            # Map rendering progress to a reasonable range
            progress_value = 10 + int(percent * 0.85)
            self.progress_signal_emitter.emit(progress_value, f"Rendering: {percent}%")

class VideoCompositingThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, base_video_path, overlay_path, overlay_type, position, size, start_time, parent=None):
        super().__init__(parent)
        self.base_video_path = base_video_path
        self.overlay_path = overlay_path
        self.overlay_type = overlay_type
        self.position = position
        self.size_percent = size
        self.start_time = start_time
        self.running = True

    def run(self):
        base_clip = None
        overlay_clip = None
        try:
            self.progress.emit(5, "Caricamento clip...")
            base_clip = VideoFileClip(self.base_video_path)

            if self.overlay_type == 'video':
                overlay_clip = VideoFileClip(self.overlay_path).set_start(self.start_time)
            elif self.overlay_type == 'image':
                duration = base_clip.duration - self.start_time
                if duration < 0:
                    duration = 0
                overlay_clip = ImageClip(self.overlay_path).set_duration(duration).set_start(self.start_time)
            else:
                raise ValueError("Tipo di overlay non supportato.")

            if not self.running: return

            # Calculate size
            self.progress.emit(15, "Calcolo dimensione e posizione...")
            overlay_width = int(base_clip.w * (self.size_percent / 100))
            overlay_clip = overlay_clip.resize(width=overlay_width)

            # Calculate position
            margin = int(base_clip.w * 0.02) # 2% margin
            if self.position == "Top Right":
                pos = (base_clip.w - overlay_clip.w - margin, margin)
            elif self.position == "Top Left":
                pos = (margin, margin)
            elif self.position == "Bottom Right":
                pos = (base_clip.w - overlay_clip.w - margin, base_clip.h - overlay_clip.h - margin)
            elif self.position == "Bottom Left":
                pos = (margin, base_clip.h - overlay_clip.h - margin)
            elif self.position == "Center":
                pos = ('center', 'center')
            else: # Default to top right
                pos = (base_clip.w - overlay_clip.w - margin, margin)

            overlay_clip = overlay_clip.set_position(pos)

            if not self.running: return

            self.progress.emit(25, "Composizione video...")
            final_clip = CompositeVideoClip([base_clip, overlay_clip])

            base_dir = os.path.dirname(self.base_video_path)
            base_name = os.path.splitext(os.path.basename(self.base_video_path))[0]
            output_path = os.path.join(base_dir, f"{base_name}_overlay_{int(time.time())}.mp4")

            if not self.running: return

            logger = CompositingProgressLogger(self.progress)
            final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=logger)

            if self.running:
                self.progress.emit(100, "Completato")
                self.completed.emit(output_path)

        except Exception as e:
            if self.running:
                self.error.emit(str(e))
        finally:
            if base_clip:
                base_clip.close()
            if overlay_clip:
                overlay_clip.close()

    def stop(self):
        self.running = False
        self.progress.emit(0, "Annullamento in corso...")