from PyQt6.QtCore import QThread, pyqtSignal
import tempfile
import time
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs, Voice, VoiceSettings

load_dotenv()

anthropic_key = os.getenv("ANTHROPIC_API_KEY")
model_3_5_sonnet = os.getenv("MODEL_3_5_SONNET")
model_3_haiku = os.getenv("MODEL_3_HAIKU")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

class AudioGenerationThread(QThread):
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, text, voice_settings, parent=None):
        super().__init__(parent)
        self.text = text
        self.voice_settings = voice_settings
        self.client = ElevenLabs(api_key=elevenlabs_api_key)

    def run(self):
        try:
            # Configurazione della voce
            voice_config = VoiceSettings(
                stability=self.voice_settings['stability'],
                similarity_boost=self.voice_settings['similarity_boost'],
                style=self.voice_settings['style'],
                use_speaker_boost=self.voice_settings['use_speaker_boost'],
                model="eleven_multilingual_v1"
            )

            voice = Voice(
                voice_id=self.voice_settings['voice_id'],
                settings=voice_config
            )

            # Simulazione del progresso di elaborazione
            for percent_complete in range(0, 101, 10):
                time.sleep(1)
                self.progress.emit(percent_complete)

            # Generazione dell'audio tramite il client
            audio_generated = self.client.generate(text=self.text, voice=voice)

            # Controlla se l'output di `generate` è già un oggetto bytes
            if isinstance(audio_generated, bytes):
                audio_data = audio_generated
            else:
                # Se `generate` restituisce un generatore, leggi i dati a blocchi
                audio_data = b''.join(chunk for chunk in audio_generated)

            # Scrittura dell'audio in un file temporaneo
            temp_audio_path = tempfile.mktemp(suffix='.mp3')
            with open(temp_audio_path, 'wb') as file:
                file.write(audio_data)

            self.completed.emit(temp_audio_path)
            self.progress.emit(100)
        except Exception as e:
            self.error.emit(str(e))

