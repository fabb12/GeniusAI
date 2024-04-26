from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip
class VideoCuttingThread(QThread):
    progress = pyqtSignal(int)
    completed = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, media_path, start_time, output_path1, output_path2):
        super().__init__()
        self.media_path = media_path
        self.start_time = start_time
        self.output_path1 = output_path1
        self.output_path2 = output_path2

    def run(self):
        try:
            media = VideoFileClip(self.media_path)
            clip1 = media.subclip(0, self.start_time)
            clip2 = media.subclip(self.start_time, media.duration)

            clip1.write_videofile(self.output_path1, codec="libx264", audio_codec="aac")
            self.progress.emit(50)  # Aggiorna il progresso al 50% dopo il completamento della prima parte

            clip2.write_videofile(self.output_path2, codec="libx264", audio_codec="aac")
            self.progress.emit(100)  # Completa il progresso al 100%
            self.completed.emit(self.output_path1, self.output_path2)
        except Exception as e:
            self.error.emit(str(e))
