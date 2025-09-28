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
                 record_video=True, use_watermark=True, watermark_path=None, watermark_size=10,
                 watermark_position="Bottom Right", bluetooth_mode=False, audio_volume=1.0,
                 record_webcam=False, webcam_device=None):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_inputs = audio_inputs if audio_inputs is not None else []
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.record_video = record_video
        self.bluetooth_mode = bluetooth_mode
        self.audio_volume = audio_volume
        self.record_audio = record_audio and bool(self.audio_inputs)
        self.is_running = True
        self.use_watermark = use_watermark and self.record_video
        raw_path = watermark_path if watermark_path else WATERMARK_IMAGE
        self.watermark_image = raw_path.replace('\\', '/')
        self.watermark_size = watermark_size
        self.watermark_position = watermark_position
        self.ffmpeg_process = None
        self.webcam_process = None

        self.record_webcam = record_webcam and self.record_video
        self.webcam_device = webcam_device
        self.webcam_output_path = None

        if self.record_webcam:
            if not self.webcam_device:
                self.error_signal.emit("Nessun dispositivo webcam specificato.")
                self.is_running = False
            else:
                base, ext = os.path.splitext(self.output_path)
                self.webcam_output_path = f"{base}_webcam.mp4"

        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

        if self.use_watermark and not os.path.isfile(raw_path):
            self.error_signal.emit(f"Watermark image not found at {raw_path}")
            self.use_watermark = False

    def get_webcam_output_path(self):
        return self.webcam_output_path

    @staticmethod
    def get_video_devices(ffmpeg_path):
        if not os.path.isfile(ffmpeg_path):
            return []

        command = [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
        try:
            # CREATE_NO_WINDOW flag to hide the console window
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=creationflags)
            output = result.stderr

            devices = []
            video_device_section = False
            for line in output.splitlines():
                if "DirectShow video devices" in line:
                    video_device_section = True
                elif "DirectShow audio devices" in line:
                    break

                if video_device_section:
                    match = re.search(r'\]\s+"([^"]+)"\s+\(video\)', line)
                    if match:
                        devices.append(match.group(1))
            return list(dict.fromkeys(devices))
        except Exception as e:
            print(f"Error getting video devices: {e}")
            return []

    def get_monitor_offset(self):
        monitors = get_monitors()
        if self.monitor_index < len(monitors):
            monitor = monitors[self.monitor_index]
            return monitor.x, monitor.y, monitor.width, monitor.height
        return 0, 0, 1920, 1080  # Default fallback

    def run(self):
        if not self.is_running:
            self.recording_stopped_signal.emit()
            return

        self.recording_started_signal.emit()

        ffmpeg_command = [self.ffmpeg_path]

        if self.record_video:
            offset_x, offset_y, screen_width, screen_height = self.get_monitor_offset()
            ffmpeg_command.extend([
                '-f', 'gdigrab',
                '-framerate', str(self.frame_rate),
                '-offset_x', str(offset_x),
                '-offset_y', str(offset_y),
                '-video_size', f'{screen_width}x{screen_height}',
                '-i', 'desktop',
            ])
            if self.use_watermark:
                ffmpeg_command.extend(['-i', self.watermark_image])

        # Add audio inputs if any
        if self.record_audio:
            for audio_device in self.audio_inputs:
                ffmpeg_command.extend(['-f', 'dshow'])
                # For Bluetooth, set device options for compatibility
                if self.bluetooth_mode:
                    ffmpeg_command.extend(['-audio_buffer_size', '100'])

                # Let ffmpeg use the default sample rate and channels from the device
                # ffmpeg_command.extend(['-sample_rate', '44100'])
                # ffmpeg_command.extend(['-channels', '2'])
                ffmpeg_command.extend(['-i', f'audio={audio_device}'])

        # --- Build the filter_complex string and map arguments ---
        filter_complex_parts = []
        map_args = []
        audio_codec_args = []
        num_audio_inputs = len(self.audio_inputs)
        audio_input_start_index = 0

        if self.record_video:
            if self.use_watermark:
                # Watermark is input 1, so video is [0:v] and watermark is [1:v]
                scale_filter = f"[1:v]scale=-1:ih*{self.watermark_size/100}[scaled_wm]"
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
                audio_input_start_index = 2  # Audio inputs start after video and watermark
            else:
                # No watermark, just map the video directly
                map_args.extend(['-map', '0:v'])
                audio_input_start_index = 1  # Audio inputs start after video
        else:
            audio_input_start_index = 0

        if self.record_audio:
            apply_volume_filter = self.audio_volume and self.audio_volume != 1.0
            audio_codec = 'libmp3lame' if not self.record_video else 'aac'

            if num_audio_inputs == 1:
                audio_input_stream = f"[{audio_input_start_index}:a]"
                if apply_volume_filter:
                    volume_filter = f"{audio_input_stream}volume={self.audio_volume}[a_out]"
                    filter_complex_parts.append(volume_filter)
                    map_args.extend(['-map', '[a_out]'])
                else:
                    map_args.extend(['-map', audio_input_stream])
                audio_codec_args = ['-c:a', audio_codec, '-b:a', '192k']

            elif num_audio_inputs > 1:
                audio_merge_inputs = "".join([f"[{i + audio_input_start_index}:a]" for i in range(num_audio_inputs)])
                if apply_volume_filter:
                    audio_filter = f"{audio_merge_inputs}amerge=inputs={num_audio_inputs}[a_merged];[a_merged]volume={self.audio_volume}[a_out]"
                else:
                    audio_filter = f"{audio_merge_inputs}amerge=inputs={num_audio_inputs}[a_out]"
                filter_complex_parts.append(audio_filter)
                map_args.extend(['-map', '[a_out]'])
                audio_codec_args = ['-c:a', audio_codec, '-b:a', '192k', '-ac', '2']

        if filter_complex_parts:
            combined_filter = ";".join(filter_complex_parts)
            ffmpeg_command.extend(['-filter_complex', combined_filter])

        ffmpeg_command.extend(map_args)

        if self.record_video:
            ffmpeg_command.extend([
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
            ])

        if self.record_audio:
            ffmpeg_command.extend(audio_codec_args)

        ffmpeg_command.extend(['-y', self.output_path])

        # Use CREATE_NO_WINDOW to hide the console window
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        # Start the ffmpeg process for screen recording
        self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, creationflags=creationflags)

        # Start the ffmpeg process for webcam recording if enabled
        if self.record_webcam and self.is_running:
            webcam_command = [
                self.ffmpeg_path,
                '-f', 'dshow',
                '-r', '25',
                '-i', f'video="{self.webcam_device}"',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p',
                '-y', self.webcam_output_path
            ]
            self.webcam_process = subprocess.Popen(webcam_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, creationflags=creationflags)

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
                print(line_str) # for debugging

        # Ensure recording is stopped cleanly
        if self.ffmpeg_process.poll() is None:
            self.stop_recording()

    def stop_recording(self):
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                # Write binary 'q' to stdin
                self.ffmpeg_process.stdin.write(b'q')
                self.ffmpeg_process.stdin.flush()
                self.ffmpeg_process.wait(timeout=5)
            except (OSError, ValueError, BrokenPipeError, subprocess.TimeoutExpired) as e:
                self.error_signal.emit(f"ffmpeg did not terminate gracefully, killing process. Error: {str(e)}")
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()

        if self.webcam_process and self.webcam_process.poll() is None:
            try:
                self.webcam_process.stdin.write(b'q')
                self.webcam_process.stdin.flush()
                self.webcam_process.wait(timeout=5)
            except (OSError, ValueError, BrokenPipeError, subprocess.TimeoutExpired) as e:
                self.error_signal.emit(f"ffmpeg (webcam) did not terminate gracefully, killing process. Error: {str(e)}")
                self.webcam_process.kill()
                self.webcam_process.wait()

        self.is_running = False
        self.recording_stopped_signal.emit()

    def stop(self):
        self.is_running = False
        if (self.ffmpeg_process and self.ffmpeg_process.poll() is None) or \
           (self.webcam_process and self.webcam_process.poll() is None):
            self.stop_recording()
        else:
            self.recording_stopped_signal.emit()
