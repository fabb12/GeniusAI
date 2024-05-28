from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.config import change_settings
import os

class VideoCuttingThread(QThread):
    progress = pyqtSignal(int)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, media_path, start_time, end_time, output_path):
        super().__init__()
        self.media_path = media_path
        self.start_time = start_time
        self.end_time = end_time
        self.output_path = output_path

        # Imposta il percorso di ffmpeg relativamente al percorso di esecuzione dello script
        ffmpeg_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
        change_settings({"FFMPEG_BINARY": ffmpeg_executable_path})

    def run(self):
        try:
            # Determina se il file è video o audio in base all'estensione
            if self.media_path.lower().endswith(('.mp4', '.mov', '.avi')):
                media = VideoFileClip(self.media_path)
                is_video = True
            elif self.media_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac')):
                media = AudioFileClip(self.media_path)
                is_video = False
            else:
                raise ValueError("Formato file non supportato")

            # Taglia il media tra start_time e end_time
            clip = media.subclip(self.start_time, self.end_time)

            if is_video:
                # Salva il file video tagliato
                clip.write_videofile(self.output_path, codec="libx264", audio_codec="aac")
            else:
                # Salva il file audio tagliato
                clip.write_audiofile(self.output_path)

            self.progress.emit(100)  # Completa il progresso al 100%
            self.completed.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
