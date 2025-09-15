import subprocess
import re
from screeninfo import get_monitors
from PyQt6.QtCore import QThread, pyqtSignal
import os
from src.config import WATERMARK_IMAGE
from src.config import DEFAULT_AUDIO_CHANNELS, DEFAULT_FRAME_RATE


class ScreenRecorder(QThread):
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
            # Usa WASAPI per catturare l'audio di sistema (quello che esce dalle cuffie)
            ffmpeg_command.extend([
                '-f', 'dshow',
                '-i', 'audio=virtual-audio-capturer'  # Nome del dispositivo virtuale
            ])
            audio_input_count += 1
            system_audio_index = audio_input_count + (2 if self.use_watermark else 1)

            # Alternativa: prova con il dispositivo di loopback predefinito
            # Se virtual-audio-capturer non funziona, prova con:
            # '-i', 'audio=Stereo Mix (Realtek High Definition Audio)'
            # o con WASAPI direttamente:
            # ffmpeg_command.extend([
            #     '-f', 'dshow',
            #     '-audio_buffer_size', '50',
            #     '-i', 'audio=@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\wave_{GUID_DEL_DISPOSITIVO}'
            # ])

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

            if audio_input_count == 1:
                # Single audio source
                audio_index = audio_input_start_index if not self.use_watermark else audio_input_start_index
                audio_input_stream = f"[{audio_index}:a]"

                if apply_volume_filter:
                    volume_filter = f"{audio_input_stream}volume={self.audio_volume}[a_out]"
                    filter_complex_parts.append(volume_filter)
                    map_args.extend(['-map', '[a_out]'])
                else:
                    map_args.extend(['-map', f'{audio_index}:a'])

            else:
                # Multiple audio sources - mix them together
                audio_inputs_to_mix = []
                current_index = audio_input_start_index

                # Aggiungi tutti gli input audio
                for i in range(audio_input_count):
                    audio_inputs_to_mix.append(f"[{current_index}:a]")
                    current_index += 1

                # Crea il filtro amix per mixare tutti gli audio
                audio_merge = "".join(audio_inputs_to_mix)

                if self.bluetooth_mode:
                    # Per Bluetooth usa amix invece di amerge per migliore compatibilità
                    mix_filter = f"{audio_merge}amix=inputs={audio_input_count}:duration=longest:dropout_transition=2"
                else:
                    mix_filter = f"{audio_merge}amerge=inputs={audio_input_count}"

                if apply_volume_filter:
                    mix_filter += f"[a_mixed];[a_mixed]volume={self.audio_volume}[a_out]"
                else:
                    mix_filter += "[a_out]"

                filter_complex_parts.append(mix_filter)
                map_args.extend(['-map', '[a_out]'])

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