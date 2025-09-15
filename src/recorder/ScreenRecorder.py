import subprocess
import re
from screeninfo import get_monitors
from PyQt6.QtCore import QThread, pyqtSignal
import os
try:
    import pyaudiowpatch as pyaudio
except ImportError:
    print("PyAudioWPatch not found, falling back to standard PyAudio. Loopback recording might not work.")
    import pyaudio

from src.config import WATERMARK_IMAGE
from src.config import DEFAULT_AUDIO_CHANNELS, DEFAULT_FRAME_RATE


class ScreenRecorder(QThread):
    def _get_loopback_device_name(self):
        """
        Usa PyAudioWPatch per trovare il dispositivo di loopback WASAPI predefinito.
        Questo cattura l'audio che viene riprodotto sul dispositivo di output predefinito (es. cuffie).
        """
        # Prima di tutto, controlla se stiamo usando la versione patchata di PyAudio.
        # La versione standard non ha questo attributo.
        if not hasattr(pyaudio, 'get_loopback_device_info_generator'):
            self.error_signal.emit("Libreria audio richiesta non trovata. Eseguire 'pip install PyAudioWPatch' e riprovare.")
            return None

        try:
            p = pyaudio.PyAudio()
            # Trova l'API host WASAPI
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            if not wasapi_info:
                self.error_signal.emit("WASAPI host API not found.")
                return None

            # Trova il dispositivo di loopback predefinito per WASAPI
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    # Cerca un dispositivo di loopback che corrisponda al nome del dispositivo di output
                    # o che abbia un nome simile, escludendo la parte "(loopback)"
                    if default_speakers["name"] in loopback["name"]:
                        device_name = loopback["name"]
                        print(f"Found loopback device: {device_name}")
                        # Sanitize the name for ffmpeg by removing the problematic suffix
                        if "[Loopback]" in device_name:
                            device_name = device_name.replace("[Loopback]", "").strip()
                            print(f"Using sanitized loopback device name: {device_name}")
                        return device_name

            device_name = default_speakers["name"]
            print(f"Using default loopback device: {device_name}")
            # Sanitize the name for ffmpeg
            if "[Loopback]" in device_name:
                device_name = device_name.replace("[Loopback]", "").strip()
                print(f"Using sanitized default loopback device name: {device_name}")
            return device_name

        except Exception as e:
            self.error_signal.emit(f"Error getting loopback device: {e}")
            return None
        finally:
            if 'p' in locals() and p:
                p.terminate()

    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()
    stats_updated = pyqtSignal(dict)

    def __init__(self, output_path, ffmpeg_path='ffmpeg.exe', monitor_index=0, audio_inputs=None,
                 audio_channels=DEFAULT_AUDIO_CHANNELS, frames=DEFAULT_FRAME_RATE, record_audio=True,
                 use_watermark=True, watermark_path=None, watermark_size=10, watermark_position="Bottom Right",
                 bluetooth_mode=False, audio_volume=1.0, use_system_audio=False):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_inputs = audio_inputs if audio_inputs is not None else []
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.bluetooth_mode = bluetooth_mode
        self.audio_volume = audio_volume
        self.use_system_audio = use_system_audio  # Nuovo parametro per audio di sistema
        # Correctly determine if audio should be recorded
        self.record_audio = record_audio and (bool(self.audio_inputs) or use_system_audio)
        self.is_running = True
        self.use_watermark = use_watermark
        self.watermark_image = watermark_path if watermark_path else WATERMARK_IMAGE
        self.watermark_size = watermark_size
        self.watermark_position = watermark_position
        self.ffmpeg_process = None

        # Check if ffmpeg.exe exists
        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

        # Check if watermark image exists
        if self.use_watermark and not os.path.isfile(self.watermark_image):
            self.error_signal.emit(f"Watermark image not found at {self.watermark_image}")
            self.use_watermark = False

    def get_monitor_offset(self):
        monitor = get_monitors()[self.monitor_index]
        return monitor.x, monitor.y, monitor.width, monitor.height

    def run(self):
        if not self.is_running:
            self.recording_stopped_signal.emit()
            return

        self.recording_started_signal.emit()

        offset_x, offset_y, screen_width, screen_height = self.get_monitor_offset()

        # Base command for video input
        ffmpeg_command = [
            self.ffmpeg_path,
            '-f', 'gdigrab',
            '-framerate', str(self.frame_rate),
            '-offset_x', str(offset_x),
            '-offset_y', str(offset_y),
            '-video_size', f'{screen_width}x{screen_height}',
            '-i', 'desktop',
        ]

        if self.use_watermark:
            ffmpeg_command.extend(['-i', self.watermark_image])

        # Aggiungi audio di sistema se richiesto (WASAPI loopback per Windows)
        audio_input_count = 0
        system_audio_index = None

        if self.use_system_audio:
            loopback_device_name = self._get_loopback_device_name()
            if loopback_device_name:
                print(f"Using system audio loopback device: {loopback_device_name}")
                ffmpeg_command.extend([
                    '-f', 'dshow',
                    '-i', f'audio={loopback_device_name}'
                ])
                audio_input_count += 1
                # L'indice dell'input audio di sistema sarà sempre il primo dopo il video (e watermark se presente)
                system_audio_index = 1 if not self.use_watermark else 2
            else:
                self.error_signal.emit("System audio recording requested, but no loopback device found.")
                # Disabilita la registrazione dell'audio di sistema se non si trova il dispositivo
                self.use_system_audio = False

        # Add microphone/other audio inputs
        if self.record_audio and self.audio_inputs:
            for audio_device in self.audio_inputs:
                ffmpeg_command.extend(['-f', 'dshow'])

                # Configurazione specifica per Bluetooth
                if self.bluetooth_mode or 'bluetooth' in audio_device.lower():
                    ffmpeg_command.extend([
                        '-audio_buffer_size', '200',  # Buffer più grande per Bluetooth
                        '-thread_queue_size', '1024'  # Coda thread più grande
                    ])
                else:
                    ffmpeg_command.extend([
                        '-sample_rate', '44100',
                        '-channels', '2',
                        '-audio_buffer_size', '50'
                    ])

                ffmpeg_command.extend(['-i', f'audio={audio_device}'])
                audio_input_count += 1

        # --- Build the filter_complex string and map arguments ---
        filter_complex_parts = []
        map_args = []
        audio_codec_args = []

        if self.use_watermark:
            # Watermark processing
            scale_filter = f"[1:v]scale=-1:ih*{self.watermark_size / 100}[scaled_wm]"
            filter_complex_parts.append(scale_filter)

            # Position the watermark
            if self.watermark_position == "Top Left":
                overlay_filter = "[0:v][scaled_wm]overlay=10:10[v_out]"
            elif self.watermark_position == "Top Right":
                overlay_filter = "[0:v][scaled_wm]overlay=W-w-10:10[v_out]"
            elif self.watermark_position == "Bottom Left":
                overlay_filter = "[0:v][scaled_wm]overlay=10:H-h-10[v_out]"
            else:  # Bottom Right
                overlay_filter = "[0:v][scaled_wm]overlay=W-w-10:H-h-10[v_out]"

            filter_complex_parts.append(overlay_filter)
            map_args.extend(['-map', '[v_out]'])
            audio_input_start_index = 2
        else:
            map_args.extend(['-map', '0:v'])
            audio_input_start_index = 1

        # Gestione audio migliorata
        if audio_input_count > 0:
            apply_volume_filter = self.audio_volume and self.audio_volume != 1.0

            # Elenco degli stream audio di input (es. ['[2:a]', '[3:a]'])
            input_streams = [f"[{audio_input_start_index + i}:a]" for i in range(audio_input_count)]

            last_processed_stream = ""

            if audio_input_count == 1:
                # Se c'è una sola fonte audio, questa è il nostro stream di partenza
                last_processed_stream = input_streams[0]
            else:
                # Se ci sono più fonti, le mixiamo
                merged_inputs = "".join(input_streams)
                # L'output del mixaggio diventa il nostro nuovo stream
                last_processed_stream = "[a_mixed]"

                if self.bluetooth_mode:
                    mix_filter = f"{merged_inputs}amix=inputs={audio_input_count}:duration=longest:dropout_transition=2{last_processed_stream}"
                else:
                    mix_filter = f"{merged_inputs}amerge=inputs={audio_input_count}{last_processed_stream}"

                filter_complex_parts.append(mix_filter)

            # Applica il filtro del volume all'ultimo stream processato (singolo o mixato)
            if apply_volume_filter:
                final_audio_stream = "[a_out]"
                volume_filter = f"{last_processed_stream}volume={self.audio_volume}{final_audio_stream}"
                filter_complex_parts.append(volume_filter)
            else:
                # Se non c'è filtro volume, lo stream finale è l'ultimo processato
                final_audio_stream = last_processed_stream

            # Mappa lo stream audio finale
            map_args.extend(['-map', final_audio_stream])

            # Configurazione codec audio
            if self.bluetooth_mode:
                # Configurazione ottimizzata per Bluetooth
                audio_codec_args = [
                    '-c:a', 'aac',
                    '-b:a', '128k',  # Bitrate ridotto per Bluetooth
                    '-ac', '2',  # Stereo
                    '-ar', '44100'  # Sample rate standard
                ]
            else:
                audio_codec_args = [
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ac', '2'
                ]

        if filter_complex_parts:
            combined_filter = ";".join(filter_complex_parts)
            ffmpeg_command.extend(['-filter_complex', combined_filter])

        ffmpeg_command.extend(map_args)

        # Video encoding options
        ffmpeg_command.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
        ])

        # Add audio codec options if audio is recorded
        if audio_input_count > 0:
            ffmpeg_command.extend(audio_codec_args)
            # Aggiungi sincronizzazione audio migliorata
            ffmpeg_command.extend([
                '-async', '1',  # Sincronizzazione audio
                '-vsync', 'cfr'  # Frame rate costante
            ])

        ffmpeg_command.extend(['-y', self.output_path])

        # Debug: stampa il comando completo
        print("FFmpeg command:", " ".join(ffmpeg_command))

        # Use CREATE_NO_WINDOW to hide the console window
        creationflags = subprocess.CREATE_NO_WINDOW

        # Start the ffmpeg process
        self.ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            creationflags=creationflags
        )

        # Regex to parse ffmpeg's progress output
        stats_regex = re.compile(
            r"frame=\s*(?P<frame>\d+)\s+"
            r"fps=\s*(?P<fps>[\d.]+)\s+"
            r"q=(?P<q>[\d.-]+)\s+"
            r"size=\s*(?P<size>\d+)kB\s+"
            r"time=(?P<time>[\d:.]+)\s+"
            r"bitrate=\s*(?P<bitrate>[\d.]+)kbits/s"
        )

        while self.is_running:
            if self.ffmpeg_process.poll() is not None:
                break

            line = self.ffmpeg_process.stderr.readline()
            if line:
                line_str = line.decode('utf-8', errors='ignore').strip()
                match = stats_regex.search(line_str)
                if match:
                    stats = match.groupdict()
                    self.stats_updated.emit(stats)
                # Debug output
                if "error" in line_str.lower() or "warning" in line_str.lower():
                    print(f"FFmpeg: {line_str}")

        # Ensure recording is stopped cleanly
        if self.ffmpeg_process.poll() is None:
            self.stop_recording()

    def stop_recording(self):
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                self.ffmpeg_process.stdin.write(b'q')
                self.ffmpeg_process.stdin.flush()
                self.ffmpeg_process.wait(timeout=5)
            except (OSError, ValueError, BrokenPipeError, subprocess.TimeoutExpired) as e:
                self.error_signal.emit(f"ffmpeg did not terminate gracefully, killing process. Error: {str(e)}")
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()

        self.is_running = False
        self.recording_stopped_signal.emit()

    def stop(self):
        self.is_running = False
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self.stop_recording()
        else:
            self.recording_stopped_signal.emit()