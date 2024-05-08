import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal
import tempfile
import os
from moviepy.config import change_settings
class DownloadThread(QThread):
    finishedAudio = pyqtSignal(str, str, str)  # Emits path of audio and video title
    error = pyqtSignal(str)
    progress = pyqtSignal(int)            # Signal for download progress

    def __init__(self, url):
        super().__init__()
        self.url = url
        # Crea una directory temporanea nella cartella principale
        self.temp_dir = tempfile.mkdtemp(prefix="audio_downloads_", dir=os.getcwd())
        # Imposta il percorso di ffmpeg relativamente al percorso di esecuzione dello script
        ffmpeg_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
        change_settings({"FFMPEG_BINARY": ffmpeg_executable_path})
        print(ffmpeg_executable_path)

    def run(self):
        self.download_audio_only()

    def download_audio_only(self):
        """Download only the audio from a YouTube video and emit the title."""
        audio_options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',  # Change to mp3 for more universal playback
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),  # Salva i file nella directory temporanea
            'quiet': True,
            'ffmpeg_location': r'C:\ffmpeg\bin',
            'progress_hooks': [self.yt_progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(audio_options) as ydl:
                info = ydl.extract_info(self.url, download=True)
                if 'id' in info:
                    audio_file_path = os.path.join(self.temp_dir, f"{info['id']}.mp3")
                    video_title = info.get('title', 'Unknown Title')
                    # Cerca di ottenere la lingua dai metadati del video, se presente
                    video_language = info.get('language', 'Lingua non rilevata')
                    self.finishedAudio.emit(audio_file_path, video_title, video_language)
                else:
                    self.error.emit("Video ID not found.")
        except Exception as e:
            self.error.emit(str(e))

    def yt_progress_hook(self, d):
        """Progress hook for yt_dlp download updates."""
        if d['status'] == 'downloading':
            # Calculate progress as a percentage
            if d['total_bytes'] or d['total_bytes_estimate']:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                progress = int((d['downloaded_bytes'] / total_bytes) * 100)
                self.progress.emit(progress)
        elif d['status'] == 'finished':
            # When finished, set progress to 100%
            self.progress.emit(100)
