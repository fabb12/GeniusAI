import os
import re
import subprocess
from screeninfo import get_monitors
from PyQt6.QtCore import QThread, pyqtSignal

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()

    def __init__(self, output_path, ffmpeg_path='ffmpeg.exe', monitor_index=0, audio_input=None, audio_channels=2, frames=25):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_input = audio_input
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.is_running = True

        # Check if ffmpeg.exe exists
        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

    def run(self):
        self.recording_started_signal.emit()

        monitor = get_monitors()[self.monitor_index]
        screen_width = monitor.width
        screen_height = monitor.height

        # Ensure audio input is not None
        audio_input = self.audio_input if self.audio_input else 'none'

        ffmpeg_command = [
            self.ffmpeg_path,  # Use the provided ffmpeg path
            '-f', 'gdigrab',  # For Windows screen capture
            '-framerate', str(self.frame_rate),
            '-offset_x', '0',
            '-offset_y', '0',
            '-video_size', f'{screen_width}x{screen_height}',
            '-i', 'desktop',
            '-f', 'dshow',  # For Windows audio capture
            '-i', f'audio={audio_input}',  # Use the correct audio input
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y', self.output_path,
            '-loglevel', 'verbose',  # Add verbose logging
            '-report'  # Generate detailed report
        ]

        print("Running ffmpeg command:")
        print(" ".join(ffmpeg_command))

        self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        while self.is_running:
            output = self.ffmpeg_process.stderr.readline()
            if output:
                print(output.decode().strip())
            if self.ffmpeg_process.poll() is not None:
                break

        self.stop_recording()

    def stop_recording(self):
        self.is_running = False
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            while True:
                retcode = self.ffmpeg_process.poll()
                if retcode is not None:
                    break
        self.recording_stopped_signal.emit()

    def stop(self):
        self.is_running = False
        self.stop_recording()

def get_audio_devices():
    ffmpeg_command = ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
    process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()

    audio_devices = []
    for line in stderr.decode().split('\n'):
        if 'audio' in line:
            match = re.search(r'\[dshow @ \w+\]  "(.*?)"', line)
            if match:
                audio_devices.append(match.group(1))
    return audio_devices

def main():
    audio_devices = get_audio_devices()
    print("Available audio devices:")
    for i, device in enumerate(audio_devices):
        print(f"{i}: {device}")

    if audio_devices:
        selected_device = audio_devices[0]  # You can change this to select a different device
        print(f"Selected audio device: {selected_device}")

        # Use the selected_device in your ScreenRecorder or ffmpeg command
        output_path = "output.mp4"
        ffmpeg_path = "ffmpeg.exe"  # Assicurati che ffmpeg.exe sia nel percorso specificato o nel PATH del sistema
        monitor_index = 0
        audio_input = selected_device

        recorder = ScreenRecorder(output_path, ffmpeg_path, monitor_index, audio_input)
        recorder.run()
    else:
        print("No audio devices found.")

if __name__ == "__main__":
    main()
