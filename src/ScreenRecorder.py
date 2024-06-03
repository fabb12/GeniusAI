import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
import pyaudio
import wave
import time
from mss import mss
from moviepy.config import change_settings
import os
import ctypes.wintypes

# Imposta il percorso di ffmpeg relativamente al percorso di esecuzione dello script
ffmpeg_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
change_settings({"FFMPEG_BINARY": ffmpeg_executable_path})

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()
    audio_ready_signal = pyqtSignal(bool)  # Segnale per indicare se l'audio è pronto

    def __init__(self, video_writer, audio_path=None, region=None, audio_input=None, audio_channels=2):
        super().__init__()
        self.video_writer = video_writer
        self.audio_path = audio_path
        self.region = region
        self.audio_input = audio_input
        self.audio_channels = audio_channels
        self.is_running = True
        self.frame_rate = 30  # Frames per second
        self.audio_rate = 44100  # Audio sample rate
        self.p = pyaudio.PyAudio() if audio_input is not None else None
        self.frame_period = 1.0 / self.frame_rate

    def run(self):
        self.recording_started_signal.emit()
        audio_buffer = []
        start_time = time.time()

        if self.audio_input is not None:
            try:
                stream = self.p.open(format=pyaudio.paInt16,
                                     channels=self.audio_channels,
                                     rate=self.audio_rate,
                                     input=True,
                                     input_device_index=self.audio_input,
                                     frames_per_buffer=1024)
                self.audio_ready_signal.emit(True)  # Audio pronto
            except Exception as e:
                self.audio_ready_signal.emit(False)  # Audio non pronto
                self.error_signal.emit(f"Audio input error: {str(e)}")
                return
            stream.start_stream()
        else:
            stream = None
            self.audio_ready_signal.emit(False)

        with mss() as sct:
            next_frame_time = start_time + self.frame_period
            try:
                while self.is_running:
                    current_time = time.time()
                    if current_time >= next_frame_time:
                        if self.region:
                            img = sct.grab(self.region)
                        else:
                            img = sct.grab(sct.monitors[0])
                        frame = np.array(img)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                        # Aggiungi cerchio rosso attorno al puntatore del mouse
                        mouse_x, mouse_y = self.get_mouse_position()
                        cv2.circle(frame, (mouse_x, mouse_y), 10, (0, 0, 255), -1)  # Cerchio rosso con raggio 10

                        self.video_writer.write(frame)
                        next_frame_time += self.frame_period

                    if stream is not None:
                        audio_data = stream.read(1024, exception_on_overflow=False)
                        audio_buffer.append(audio_data)

                    # Sincronizzazione precisa
                    sleep_time = next_frame_time - time.time()
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            except Exception as e:
                self.error_signal.emit(f"Recording error: {str(e)}")
            finally:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
                    self.save_audio(audio_buffer)
                self.recording_stopped_signal.emit()
                if self.p is not None:
                    self.p.terminate()

    def get_mouse_position(self):
        # Ottieni la posizione del puntatore del mouse
        mouse_x, mouse_y = 0, 0
        try:
            import ctypes
            cursor_info = ctypes.windll.user32.GetCursorPos
            cursor_info.restype = ctypes.wintypes.BOOL
            cursor_info.argtypes = [ctypes.POINTER(ctypes.wintypes.POINT)]
            pt = ctypes.wintypes.POINT()
            if cursor_info(ctypes.byref(pt)):
                mouse_x, mouse_y = pt.x, pt.y
        except Exception as e:
            self.error_signal.emit(f"Failed to get mouse position: {str(e)}")
        return mouse_x, mouse_y

    def save_audio(self, audio_buffer):
        if self.audio_path is None:
            return  # Non salvare l'audio se l'opzione "Salva solo il video" è selezionata

        try:
            with wave.open(self.audio_path, 'wb') as wf:
                wf.setnchannels(self.audio_channels)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.audio_rate)
                # Scrivi un file audio completo
                audio_data_full = b''.join(audio_buffer)
                wf.writeframes(audio_data_full)
        except Exception as e:
            self.error_signal.emit(f"Failed to save audio: {str(e)}")

    def stop(self):
        self.is_running = False
        self.wait()
