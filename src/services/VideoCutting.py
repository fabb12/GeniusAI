import os
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
from src.services.utils import generate_unique_filename

class VideoCuttingThread(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, media_path, start_time, end_time, output_path,
                 use_watermark=False, watermark_path=None, watermark_size=10, watermark_position="Bottom Right"):
        super().__init__()
        self.media_path = media_path
        self.start_time = start_time
        self.end_time = end_time
        self.output_path = generate_unique_filename(output_path)
        self.use_watermark = use_watermark
        self.watermark_path = watermark_path
        self.watermark_size = watermark_size
        self.watermark_position = watermark_position

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

            # WORKAROUND: This is a workaround for a persistent issue in moviepy where the audio at the end of a clip is repeated.
            # The user reported that the last second of audio is repeated twice, so we are trimming 1.8 seconds from the end of the clip.
            # This is not an ideal solution, but it is a direct response to the user's feedback after other, more robust solutions have failed.
            end_time = self.end_time - 1.8
            if end_time < self.start_time:
                end_time = self.end_time

            # Taglia il media tra start_time e end_time
            clip = media.subclip(self.start_time, end_time)

            if is_video and self.use_watermark:
                if not self.watermark_path or not os.path.exists(self.watermark_path):
                    self.error.emit(f"File watermark non valido: {self.watermark_path}")
                    return

                if not isinstance(self.watermark_size, (int, float)) or self.watermark_size <= 0:
                    self.error.emit(f"Dimensione watermark non valida: {self.watermark_size}")
                    return

                valid_positions = ["Top Left", "Top Right", "Bottom Left", "Bottom Right"]
                if self.watermark_position not in valid_positions:
                    self.error.emit(f"Posizione watermark non valida: {self.watermark_position}")
                    return

                try:
                    watermark_clip = (ImageClip(self.watermark_path)
                                      .set_duration(clip.duration)
                                      .resize(height=int(clip.h * self.watermark_size / 100))
                                      .set_opacity(0.5))

                    # Position the watermark
                    position_map = {
                        "Top Left": ("left", "top"),
                        "Top Right": ("right", "top"),
                        "Bottom Left": ("left", "bottom"),
                        "Bottom Right": ("right", "bottom")
                    }
                    watermark_clip = watermark_clip.set_position(position_map[self.watermark_position])

                    clip = CompositeVideoClip([clip, watermark_clip])
                except Exception as e:
                    self.error.emit(f"Errore durante l'applicazione del watermark: {e}")
                    return


            if is_video:
                # Salva il file video tagliato
                clip.write_videofile(self.output_path, codec="libx264", audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True, ffmpeg_params=['-movflags', '+faststart'])
            else:
                # Salva il file audio tagliato
                clip.write_audiofile(self.output_path)

            self.progress.emit(100, "Taglio completato")  # Completa il progresso al 100%
            self.completed.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
