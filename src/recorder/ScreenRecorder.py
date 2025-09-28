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
                 record_webcam=False, webcam_device_name=None, webcam_resolution="640x480",
                 webcam_position="Bottom Right", webcam_size=25):
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

        self.record_webcam = record_webcam and self.record_video
        self.webcam_device_name = webcam_device_name
        self.webcam_resolution = webcam_resolution
        self.webcam_position = webcam_position
        self.webcam_size = webcam_size

        self.use_watermark = use_watermark and self.record_video
        raw_path = watermark_path if watermark_path else WATERMARK_IMAGE
        self.watermark_image = raw_path.replace('\\', '/')
        self.watermark_size = watermark_size
        self.watermark_position = watermark_position
        self.ffmpeg_process = None

        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

        if self.use_watermark and not os.path.isfile(raw_path):
            self.error_signal.emit(f"Watermark image not found at {raw_path}")
            self.use_watermark = False

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

        ffmpeg_command = [self.ffmpeg_path, '-hwaccel', 'auto']

        input_count = 0
        video_input_index = -1
        webcam_input_index = -1
        watermark_input_index = -1
        audio_input_start_index = -1

        offset_x, offset_y, screen_width, screen_height = self.get_monitor_offset()
        if self.record_video:
            ffmpeg_command.extend([
                '-f', 'gdigrab',
                '-framerate', str(self.frame_rate),
                '-offset_x', str(offset_x),
                '-offset_y', str(offset_y),
                '-video_size', f'{screen_width}x{screen_height}',
                '-i', 'desktop',
            ])
            video_input_index = input_count
            input_count += 1

            if self.record_webcam and self.webcam_device_name:
                ffmpeg_command.extend([
                    '-f', 'dshow',
                    '-s', self.webcam_resolution,
                    '-i', f'video={self.webcam_device_name}'
                ])
                webcam_input_index = input_count
                input_count += 1

            if self.use_watermark:
                ffmpeg_command.extend(['-i', self.watermark_image])
                watermark_input_index = input_count
                input_count += 1

        if self.record_audio:
            audio_input_start_index = input_count
            for audio_device in self.audio_inputs:
                ffmpeg_command.extend(['-f', 'dshow'])
                if self.bluetooth_mode:
                    ffmpeg_command.extend(['-audio_buffer_size', '100'])
                ffmpeg_command.extend(['-i', f'audio={audio_device}'])
                input_count += 1

        filter_complex_parts = []
        map_args = []
        audio_codec_args = []

        video_chain = f"[{video_input_index}:v]" if self.record_video else ""

        if self.record_webcam and webcam_input_index != -1:
            webcam_stream = f"[{webcam_input_index}:v]"

            webcam_scale_filter = f"{webcam_stream}scale=-1:{screen_height}*({self.webcam_size}/100)[scaled_wc]"
            filter_complex_parts.append(webcam_scale_filter)

            if self.webcam_position == "Top Left":
                overlay_pos = "10:10"
            elif self.webcam_position == "Top Right":
                overlay_pos = "W-w-10:10"
            elif self.webcam_position == "Bottom Left":
                overlay_pos = "10:H-h-10"
            else:
                overlay_pos = "W-w-10:H-h-10"

            webcam_overlay_filter = f"{video_chain}[scaled_wc]overlay={overlay_pos}[v_with_wc]"
            filter_complex_parts.append(webcam_overlay_filter)
            video_chain = "[v_with_wc]"

        if self.use_watermark and watermark_input_index != -1:
            watermark_stream = f"[{watermark_input_index}:v]"
            scale_filter = f"{watermark_stream}scale=-1:ih*{self.watermark_size/100}[scaled_wm]"
            filter_complex_parts.append(scale_filter)

            if self.watermark_position == "Top Left":
                overlay_pos = "10:10"
            elif self.watermark_position == "Top Right":
                overlay_pos = "W-w-10:10"
            elif self.watermark_position == "Bottom Left":
                overlay_pos = "10:H-h-10"
            else:
                overlay_pos = "W-w-10:H-h-10"

            overlay_filter = f"{video_chain}[scaled_wm]overlay={overlay_pos}[v_out]"
            filter_complex_parts.append(overlay_filter)
            video_chain = "[v_out]"

        if self.record_video:
            map_args.extend(['-map', video_chain])

        if self.record_audio:
            num_audio_inputs = len(self.audio_inputs)
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

        creationflags = subprocess.CREATE_NO_WINDOW
        self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, creationflags=creationflags)

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
                print(line_str)

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