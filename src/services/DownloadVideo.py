import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal
import tempfile
import os
import re
import requests
from bs4 import BeautifulSoup
from yt_dlp.postprocessor import FFmpegPostProcessor
from src.config import FFMPEG_PATH


class DownloadThread(QThread):
    completed = pyqtSignal(list)  # Emits [path, title, language, date]
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # Signal for download progress
    stream_url_found = pyqtSignal(str)  # Nuovo segnale per l'URL del flusso trovato

    def __init__(self, url, download_video, ffmpeg_path, parent_window=None):
        super().__init__()
        self.url = url
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        FFmpegPostProcessor._ffmpeg_location.set(FFMPEG_PATH)
        self.download_video = download_video
        if parent_window and hasattr(parent_window, 'get_temp_dir'):
            self.temp_dir = parent_window.get_temp_dir(prefix="downloads_")
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="downloads_", dir=os.getcwd())

    def run(self):
        # Controlla se è un URL di StreamingCommunity
        if self.is_streaming_community_url(self.url):
            # Prima ottieni l'URL del flusso
            stream_url = self.extract_stream_url(self.url)
            if stream_url:
                self.stream_url_found.emit(stream_url)  # Emetti il segnale con l'URL del flusso
                if self.download_video:
                    self.download_from_stream_url(stream_url)
            else:
                self.error.emit("Impossibile estrarre l'URL del flusso da StreamingCommunity.")
        else:
            # Per altri URL, usa il comportamento esistente
            if self.download_video:
                self.download_video_file()
            else:
                self.download_audio_only()

    def is_streaming_community_url(self, url):
        """Verifica se l'URL è di StreamingCommunity"""
        pattern = r"streamingcommunity\.(buzz|hiphop|prof|[a-z]+)/watch/\d+\?e=\d+"
        return bool(re.search(pattern, url))

    def extract_stream_url(self, url):
        """
        Estrae l'URL del flusso m3u8 da un URL di StreamingCommunity
        Restituisce URL come: https://vixcloud.co/playlist/288952?token=aaa61fe48d91286d4a46e948366eec75&expires=1746868873&h=1
        """
        try:
            # Estrai playerid e episode_id dall'URL
            pattern = r"watch/(\d+)\?e=(\d+)"
            match = re.search(pattern, url)
            if not match:
                self.error.emit("URL di StreamingCommunity non valido.")
                return None

            playerid = match.group(1)
            episode_id = match.group(2)

            # Ottieni il dominio base
            base_pattern = r"(https?://[^/]+)"
            base_match = re.search(base_pattern, url)
            base_url = base_match.group(1) if base_match else "https://streamingcommunity.hiphop"

            self.progress.emit(10, "Estrazione URL di streaming...")

            # Costruisci l'URL dell'iframe
            iframe_url = f"{base_url}/iframe/{playerid}"
            params = {'episode_id': episode_id}

            # Headeres per la richiesta dell'iframe
            headers = {
                'Referer': url,
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }

            # Richiedi l'iframe
            response = requests.get(iframe_url, headers=headers, params=params)
            response.raise_for_status()

            # Analizza la risposta per trovare l'iframe
            soup = BeautifulSoup(response.text, 'html.parser')
            iframe_tag = soup.find('iframe', {'ref': 'iframe'})

            if not iframe_tag:
                self.error.emit("Impossibile trovare l'iframe nella pagina.")
                return None

            iframe_src = iframe_tag.get('src')

            self.progress.emit(30, "Estrazione URL di streaming...")

            # Headers per la richiesta del contenuto dell'iframe
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'referer': base_url + '/',
                'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'iframe',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'cross-site',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
            }

            # Richiedi il contenuto dell'iframe
            response = requests.get(iframe_src, headers=headers)
            response.raise_for_status()

            self.progress.emit(50, "Estrazione URL di streaming...")

            # Estrai i parametri necessari dal contenuto JavaScript dell'iframe
            url_pattern = r"url: '([^']+)'"
            token_pattern = r"'token': '([^']+)'"
            expires_pattern = r"'expires': '([^']+)'"

            url_match = re.search(url_pattern, response.text)
            token_match = re.search(token_pattern, response.text)
            expires_match = re.search(expires_pattern, response.text)

            if not (url_match and token_match and expires_match):
                self.error.emit("Impossibile estrarre i parametri necessari dalla pagina.")
                return None

            stream_url = url_match.group(1)
            token = token_match.group(1)
            expires = expires_match.group(1)

            self.progress.emit(70, "Costruzione URL finale...")

            # Costruisci l'URL finale del flusso
            if '?' in stream_url:
                # Se l'URL contiene già un punto interrogativo, usa & per i parametri aggiuntivi
                final_url = f"{stream_url}&token={token}&expires={expires}&h=1"
            else:
                # Altrimenti, inizia i parametri con ?
                final_url = f"{stream_url}?token={token}&expires={expires}&h=1"

            self.progress.emit(90, "URL finale costruito.")

            return final_url

        except requests.RequestException as e:
            self.error.emit(f"Errore di rete durante l'estrazione dell'URL: {str(e)}")
        except Exception as e:
            self.error.emit(f"Errore durante l'estrazione dell'URL del flusso: {str(e)}")

        return None

    def download_from_stream_url(self, stream_url):
        """Scarica un video dall'URL del flusso usando yt-dlp"""
        try:
            # Estrai un nome file di base dall'URL
            base_name = "video"
            match = re.search(r"playlist/(\d+)", stream_url)
            if match:
                base_name = f"video_{match.group(1)}"

            output_path = os.path.join(self.temp_dir, f"{base_name}.mp4")

            # Configura yt-dlp
            ydl_opts = {
                'format': 'best',
                'outtmpl': output_path,
                'quiet': True,
                'ffmpeg_location': self.ffmpeg_path,
                'progress_hooks': [self.yt_progress_hook],
            }

            # Esegui il download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([stream_url])

            # Emetti il segnale di completamento
            self.completed.emit([output_path, base_name, "it", None])  # Lingua predefinita: italiano

        except Exception as e:
            self.error.emit(f"Errore durante il download del video: {str(e)}")

    def download_audio_only(self):
        """Download only the audio from a YouTube video and emit the title."""
        audio_options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',  # Change to mp3 for more universal playback
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'quiet': True,
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [self.yt_progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(audio_options) as ydl:
                info = ydl.extract_info(self.url, download=True)
                if 'id' in info:
                    # Robustly find the output file
                    files_in_temp = os.listdir(self.temp_dir)
                    if not files_in_temp:
                        self.error.emit("No file found in temporary directory after download.")
                        return
                    # Assuming the first file is the correct one, as the directory should be empty before download
                    audio_file_path = os.path.join(self.temp_dir, files_in_temp[0])

                    video_title = info.get('title', 'Unknown Title')
                    video_language = info.get('language', 'Lingua non rilevata')
                    upload_date = info.get('upload_date', None)
                    self.completed.emit([audio_file_path, video_title, video_language, upload_date])
                else:
                    self.error.emit("Video ID not found.")
        except Exception as e:
            self.error.emit(str(e))

    def download_video_file(self):
        """Download both audio and video from a YouTube video and emit the title."""
        video_options = {
            'format': 'bestvideo+bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'quiet': True,
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [self.yt_progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(video_options) as ydl:
                info = ydl.extract_info(self.url, download=True)
                if 'id' in info:
                    # Robustly find the output file
                    files_in_temp = os.listdir(self.temp_dir)
                    if not files_in_temp:
                        self.error.emit("No file found in temporary directory after download.")
                        return
                    # Assuming the first file is the correct one
                    video_file_path = os.path.join(self.temp_dir, files_in_temp[0])

                    video_title = info.get('title', 'Unknown Title')
                    video_language = info.get('language', 'Lingua non rilevata')
                    upload_date = info.get('upload_date', None)
                    self.completed.emit([video_file_path, video_title, video_language, upload_date])
                else:
                    self.error.emit("Video ID not found.")
        except Exception as e:
            self.error.emit(str(e))

    def yt_progress_hook(self, d):
        """Progress hook for yt_dlp download updates."""
        if d['status'] == 'downloading':
            # Calculate progress as a percentage
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                progress = int((d['downloaded_bytes'] / total_bytes) * 100)
                total_mb = total_bytes / (1024 * 1024)
                speed_str = d.get('_speed_str', 'N/A').strip()
                label = f"Download in corso: {progress}% di {total_mb:.2f}MB @ {speed_str}"
                self.progress.emit(progress, label)
        elif d['status'] == 'finished':
            # When finished, set progress to 100%
            self.progress.emit(100, "Download completato. Inizio elaborazione...")