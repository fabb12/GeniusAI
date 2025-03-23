from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip, AudioFileClip

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

            # Verifica se ci sono parametri di ritaglio spaziale
            if hasattr(self, 'crop_rect') and is_video and not self.crop_rect.isEmpty():
                # Ritaglio spaziale (area)
                x1 = max(0, self.crop_rect.x())
                y1 = max(0, self.crop_rect.y())
                x2 = min(media.size[0], x1 + self.crop_rect.width())
                y2 = min(media.size[1], y1 + self.crop_rect.height())

                media = media.crop(x1=x1, y1=y1, x2=x2, y2=y2)

            # Ritaglio temporale (taglia tra start_time e end_time)
            if is_video:
                clip = media.subclip(self.start_time, self.end_time)
                # Salva il file video tagliato
                clip.write_videofile(self.output_path, codec="libx264", audio_codec="aac")
            else:
                # Salva il file audio tagliato
                clip = media.subclip(self.start_time, self.end_time)
                clip.write_audiofile(self.output_path)

            self.progress.emit(100)  # Completa il progresso al 100%
            self.completed.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))