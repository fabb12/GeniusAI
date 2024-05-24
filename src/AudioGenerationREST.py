import requests
from PyQt6.QtCore import QThread, pyqtSignal
import tempfile
from moviepy.config import change_settings
import os

# Imposta il percorso di ffmpeg relativamente al percorso di esecuzione dello script
ffmpeg_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
change_settings({"FFMPEG_BINARY": ffmpeg_executable_path})
print(ffmpeg_executable_path)

class AudioGenerationThread(QThread):
    completed = pyqtSignal(str)  # Signal to notify the path of the completed file
    error = pyqtSignal(str)      # Signal to notify errors
    progress = pyqtSignal(int)   # Signal to update progress, if necessary

    def __init__(self, text, voice_id, model_id, voice_settings, api_key, output_path, parent=None):
        super().__init__(parent)
        self.text = text
        self.voice_id = voice_id
        self.model_id = model_id
        self.voice_settings = voice_settings
        self.api_key = api_key
        self.output_path = output_path

    def run(self):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        data = {
            "text": self.text,
            "model_id": self.model_id,
            "voice_settings": self.voice_settings
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                with open(self.output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            self.progress.emit(100)  # You may want to refine progress updates for large files
                self.completed.emit(self.output_path)
            else:
                raise Exception(f"Failed to generate audio: {response.status_code} - {response.text}")
        except Exception as e:
            self.error.emit(str(e))
