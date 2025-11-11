import requests
from PyQt6.QtCore import QThread, pyqtSignal

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

class FetchVoicesThread(QThread):
    completed = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api_key, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                voices_data = response.json().get('voices', [])
                # Semplifichiamo i dati, passando solo nome e ID
                voices_list = [{'name': voice['name'], 'voice_id': voice['voice_id']} for voice in voices_data]
                self.completed.emit(voices_list)
            else:
                raise Exception(f"Failed to fetch voices: {response.status_code} - {response.text}")
        except Exception as e:
            self.error.emit(f"Errore di rete o API: {e}")
