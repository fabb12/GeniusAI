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
import subprocess
from screeninfo import get_monitors

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()
    audio_ready_signal = pyqtSignal(bool)  # Segnale per indicare se l'audio è pronto

    def __init__(self, video_writer, audio_path=None, monitor_index=0, audio_input=None, audio_channels=2):
        super().__init__()
        self.video_writer = video_writer
        self.audio_path = audio_path
        self.monitor_index = monitor_index
        self.audio_input = audio_input
        self.audio_channels = audio_channels
        self.is_running = True
        self.frame_rate = 25  # Frames per second
        self.audio_rate = 44100  # Audio sample rate
        self.frame_period = 1.0 / self.frame_rate
        self.audio_queue = Queue()
        self.lock = Lock()
        self.sync_event = Lock()
        self.drawing = False  # True quando il mouse è premuto
        self.start_point = (0, 0)
        self.end_point = (0, 0)
        self.enlarge_circle = False
        self.enlarge_timestamp = 0

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
                            img = sct.grab(sct.monitors[self.monitor_index + 1 ])
                            frame = np.array(img)
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                            # Aggiungi cerchio rosso attorno al puntatore del mouse
                            mouse_x, mouse_y = self.get_mouse_position()
                            if self.enlarge_circle and current_time - self.enlarge_timestamp < 0.5:
                                radius = 14
                            else:
                                radius = 8
                                self.enlarge_circle = False
                            cv2.circle(frame, (mouse_x, mouse_y), radius, (0, 0, 255), -1)  # Cerchio rosso

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

    def unisciVideoAAudio(self, video_path, new_audio_path, output_path):
        try:
            # Usa ffmpeg per unire il video e l'audio
            command = [
                'ffmpeg', '-y', '-i', video_path, '-i', new_audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', output_path
            ]
            subprocess.run(command, check=True)
            print(f"Unione di {video_path} e {new_audio_path} completata con successo.")
        except subprocess.CalledProcessError as e:
            print(f"Errore durante l'unione di audio e video: {e}")

    def handle_mouse_events(self):
        cv2.namedWindow('Screen Capture')
        cv2.setMouseCallback('Screen Capture', self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.enlarge_circle = True
            self.enlarge_timestamp = time.time()
