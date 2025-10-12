import unittest
import os
import sys
import numpy as np
from moviepy.audio.AudioClip import AudioClip
from moviepy.video.VideoClip import VideoClip
from PyQt6.QtCore import QCoreApplication

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.SilenceRemover import SilenceRemoverThread

class TestSilenceRemover(unittest.TestCase):

    def setUp(self):
        """Set up a test video file with silent and non-silent parts."""
        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication(sys.argv)

        self.test_video_path = "test_video.mp4"
        self.output_video_path = "test_output.mp4"

        duration = 10  # seconds
        fps = 24
        samplerate = 44100

        def make_frame(t):
            # Ensure t is an array
            if not isinstance(t, np.ndarray):
                t = np.array([t])

            # Create boolean masks for the time intervals
            mask1 = (2 <= t) & (t < 5)
            mask2 = (7 <= t) & (t < 10)
            combined_mask = mask1 | mask2

            # Generate sine wave for all t
            wave = np.sin(440 * 2 * np.pi * t) * 0.5

            # Create a silent stereo array
            stereo_wave = np.zeros((len(t), 2))

            # Apply the wave to both channels where the mask is True
            stereo_wave[combined_mask, 0] = wave[combined_mask]
            stereo_wave[combined_mask, 1] = wave[combined_mask]

            # If the input was a single value, return a single frame
            if len(t) == 1:
                return stereo_wave[0]

            return stereo_wave

        audio = AudioClip(make_frame, duration=duration, fps=samplerate)

        # Create a simple video clip (black screen)
        width, height = 640, 480
        video = VideoClip(lambda t: np.zeros((height, width, 3), dtype=np.uint8), duration=duration).set_fps(fps)
        video = video.set_audio(audio)

        video.write_videofile(self.test_video_path, codec="libx264", audio_codec="aac", logger=None)
        video.close()
        audio.close()


    def tearDown(self):
        """Clean up the created files."""
        if os.path.exists(self.test_video_path):
            os.remove(self.test_video_path)
        if os.path.exists(self.output_video_path):
            os.remove(self.output_video_path)
        if os.path.exists("temp_audio_for_silence_detection.wav"):
            os.remove("temp_audio_for_silence_detection.wav")

    def test_silence_removal(self):
        """Test that the SilenceRemoverThread correctly removes silent parts."""

        thread = SilenceRemoverThread(
            video_path=self.test_video_path,
            silence_threshold_db=-30,  # A reasonable threshold for the test audio
            min_silence_len_ms=500,
            output_path=self.output_video_path
        )

        # Run the thread synchronously for the test
        thread.run()

        # Check if the output file was created
        self.assertTrue(os.path.exists(self.output_video_path))

        # Check that the output video is shorter than the original
        from moviepy.editor import VideoFileClip
        original_duration = VideoFileClip(self.test_video_path).duration
        output_duration = VideoFileClip(self.output_video_path).duration

        self.assertLess(output_duration, original_duration)

        # The expected duration is the sum of the two non-silent parts (3s + 3s = 6s)
        # We allow for a small margin of error due to processing.
        self.assertAlmostEqual(output_duration, 6, delta=0.5)

if __name__ == '__main__':
    unittest.main()