import os
from PyQt6.QtCore import QThread, pyqtSignal
from scipy.io.wavfile import write, read
import time
import pycountry
import uuid
import speech_recognition as sr
from pydub import AudioSegment
import io
from moviepy.config import change_settings

# Imposta il percorso di ffmpeg relativamente al percorso di esecuzione dello script
ffmpeg_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
change_settings({"FFMPEG_BINARY": ffmpeg_executable_path})


class TranscriptionThread(QThread):
    update_progress = pyqtSignal(int, str)  # Signal for updating progress with an index and message
    transcription_complete = pyqtSignal(str, list)  # Signal when transcription is complete, including temporary files to clean
    error_occurred = pyqtSignal(str)  # Signal for reporting errors

    def __init__(self, media_path, parent=None):
        super().__init__(parent)
        self.media_path = media_path



    def run(self):
        try:
            if os.path.splitext(self.media_path)[1].lower() in ['.wav', '.mp3', '.flac', '.aac']:
                audio_file = self.media_path
            else:
                audio_buffer = self.convertVideoToAudio(self.media_path)
                if audio_buffer is None or audio_buffer.getbuffer().nbytes == 0:
                    raise Exception("La conversione del video in audio è fallita.")
                fps, audio_array = read(audio_buffer)
                audio_file = {'fps': fps, 'array': audio_array}
                audio_buffer.close()

            chunks = self.splitAudio(audio_file)
            transcription = ""
            last_timestamp = None

            for index, (chunk, start_time) in enumerate(chunks):
                text, start_time, _ = self.transcribeAudioChunk(chunk, start_time)
                start_mins, start_secs = divmod(start_time // 1000, 60)
                current_time_in_seconds = (start_mins * 60) + start_secs

                if last_timestamp is None or (current_time_in_seconds - last_timestamp >= 30):
                    transcription += f"[{start_mins:02d}:{start_secs:02d}] {text}\n\n"
                    last_timestamp = current_time_in_seconds
                else:
                    transcription += f"{text}\n\n"

                self.update_progress.emit(index + 1, f"Trascrizione {index + 1}/{len(chunks)}")

            self.transcription_complete.emit(transcription, [])  # Emit completion with no temp files to clean
        except Exception as e:
            self.error_occurred.emit(str(e))



    def convertVideoToAudio(self, video_file, audio_format='wav'):
        """Estrae la traccia audio dal video e la converte in formato WAV mantenendo tutto in memoria."""
        # Carica il clip video usando Pydub (potrebbe richiedere ffmpeg installato)
        video = AudioSegment.from_file(video_file)

        # Converti l'audio in formato WAV e salvalo in un buffer di memoria
        buffer = io.BytesIO()
        video.export(buffer, format=audio_format)
        buffer.seek(0)  # Riporta il cursore all'inizio del buffer

        return buffer

    def splitAudio(self, audio_input, length=60000):
        if isinstance(audio_input, dict):
            audio_array = audio_input['array']
            fps = audio_input['fps']
            audio = AudioSegment(data=audio_array.tobytes(), sample_width=audio_array.dtype.itemsize,
                                 frame_rate=fps, channels=len(audio_array.shape))
        else:
            audio = AudioSegment.from_file(audio_input)
        chunks = [(audio[i:i + length], i) for i in range(0, len(audio), length)]
        return chunks


    def get_locale_from_language(self, language_code):
        """Converte un codice di lingua ISO 639-1 in un locale più specifico."""
        try:
            language = pycountry.languages.get(alpha_2=language_code)
            return {
                'en': 'en-US',
                'es': 'es-ES',
                'fr': 'fr-FR',
                'it': 'it-IT',
                'de': 'de-DE'
            }.get(language.alpha_2, f"{language.alpha_2}-{language.alpha_2.upper()}")
        except Exception:
            return language_code  # Ritorna il codice originale se la mappatura fallisce

    def transcribeAudioChunk(self, audio_chunk, start_time):

        def try_remove_chunk_file(chunk_file):
            """Rimuove il file audio temporaneo con tentativi multipli."""
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    os.remove(chunk_file)
                    break
                except PermissionError:
                    if attempt < max_attempts - 1:
                        time.sleep(0.5)  # Aspetta un po' prima di riprovare

        recognizer = sr.Recognizer()
        unique_id = uuid.uuid4()
        chunk_file = f"temp_chunk_{unique_id}.wav"
        audio_chunk.export(chunk_file, format="wav")

        try:
            with sr.AudioFile(chunk_file) as source:
                audio_data = recognizer.record(source)
                language_video = self.parent().languageComboBox.currentData()  # Ottiene il codice lingua dalla comboBox
                locale = self.get_locale_from_language(language_video)
                text = recognizer.recognize_google(audio_data, language=locale)
            return text, start_time, language_video
        except sr.UnknownValueError:
            return "[Incomprensibile]", start_time, language_video
        except sr.RequestError as e:
            return f"[Errore: {e}]", start_time, language_video
        finally:
            try_remove_chunk_file(chunk_file)
