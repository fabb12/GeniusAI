import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QTime, QTimer
import sounddevice as sd
import soundfile as sf
import time
from mss import mss
import ctypes.wintypes
from queue import Queue
from threading import Lock


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
        self.frame_period = 1.0 / self.frame_rate
        self.audio_queue = Queue()
        self.lock = Lock()
        self.sync_event = Lock()

    def run(self):
        self.recording_started_signal.emit()
        start_time = time.time()

        if self.audio_input is not None:
            try:
                self.audio_file = sf.SoundFile(self.audio_path, mode='w', samplerate=self.audio_rate,
                                               channels=self.audio_channels, format='WAV')
                self.stream = sd.InputStream(samplerate=self.audio_rate, channels=self.audio_channels,
                                             device=self.audio_input, callback=self.audio_callback)
                self.stream.start()
                self.audio_ready_signal.emit(True)  # Audio pronto
            except Exception as e:
                self.audio_ready_signal.emit(False)  # Audio non pronto
                self.error_signal.emit(f"Audio input error: {str(e)}")
                return
        else:
            self.stream = None
            self.audio_ready_signal.emit(False)

        self.sync_event.acquire()  # Wait for audio to be ready

        with mss() as sct:
            next_frame_time = start_time + self.frame_period
            try:
                while self.is_running:
                    current_time = time.time()
                    if current_time >= next_frame_time:
                        try:
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
                        except Exception as e:
                            self.error_signal.emit(f"Screen capture error: {str(e)}")
                            self.stop()
                            break

                    # Sincronizzazione precisa
                    sleep_time = next_frame_time - time.time()
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            except Exception as e:
                self.error_signal.emit(f"Recording error: {str(e)}")
            finally:
                if self.stream is not None:
                    self.stream.stop()
                    self.stream.close()
                    self.audio_file.close()
                self.recording_stopped_signal.emit()

    def audio_callback(self, indata, frames, time, status):
        if status:
            self.error_signal.emit(f"Audio stream status: {status}")

        # Normalizza il volume
        amplified_audio = self.normalize_audio(indata)

        self.audio_file.write(amplified_audio)
        self.audio_queue.put(amplified_audio)
        if not self.sync_event.locked():
            self.sync_event.release()  # Release sync event when the first audio data is received

    def normalize_audio(self, indata, factor=2.0):
        """
        Normalizza il volume del segnale audio.
        :param indata: Input audio data
        :param factor: Amplification factor
        :return: Amplified audio data
        """
        return indata * factor

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

    def stop(self):
        self.is_running = False
        self.wait()
