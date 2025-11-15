import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import shutil
import tempfile

# Add src to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.DownloadDialog import DownloadDialog
from PyQt6.QtWidgets import QWidget

class TestDownloadFlow(unittest.TestCase):

    def setUp(self):
        # Create a mock 'self' object for the DownloadDialog instance.
        # This avoids calling the QDialog constructor entirely.
        self.mock_dialog_instance = MagicMock()

        # Define the spec for the parent window to include all methods that will be called
        parent_spec = [
            'show_status_message',
            'start_task',
            'onTranscriptionComplete',
            'onTranscriptionError',
            'update_status_progress',
            'loadVideo',
            'load_project',
            '_update_json_file',
            'projectDock'
        ]
        # Create the mock parent window and attach it to our mock dialog instance
        self.mock_parent_window = MagicMock(spec=parent_spec)
        self.mock_parent_window.current_project_path = tempfile.mkdtemp()
        self.mock_parent_window.project_manager = MagicMock()
        self.mock_parent_window.projectDock = MagicMock()
        self.mock_dialog_instance.parent_window = self.mock_parent_window

        # Attach other necessary attributes to the mock dialog instance
        self.mock_dialog_instance.transcribe_checkbox = Mock()

    def tearDown(self):
        shutil.rmtree(self.mock_parent_window.current_project_path)

    @patch('src.ui.DownloadDialog.shutil.move')
    @patch('src.ui.DownloadDialog.utils.generate_unique_filename')
    @patch('src.ui.DownloadDialog.WhisperTranscriptionThread')
    @patch('src.ui.DownloadDialog.QSettings') # Mock QSettings
    def test_onDownloadFinished_with_transcription(self, mock_qsettings, mock_whisper_thread, mock_generate_unique_filename, mock_shutil_move):
        # Arrange
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.close()

        video_title = "test_video"
        permanent_path = os.path.join(self.mock_parent_window.current_project_path, 'clips', f'{video_title}.mp4')
        mock_generate_unique_filename.return_value = permanent_path

        self.mock_dialog_instance.transcribe_checkbox.isChecked.return_value = True

        result = (temp_file.name, video_title, "en", "20230101")

        # Act
        # Call the method directly on the class, passing our mock instance as 'self'
        DownloadDialog.onDownloadFinished(self.mock_dialog_instance, result)

        # Assert
        # 1. shutil.move was called correctly
        mock_shutil_move.assert_called_once_with(temp_file.name, permanent_path)

        # 2. Project manager was called to add the clip
        self.mock_parent_window.project_manager.add_clip_to_project_from_path.assert_called_once()

        # 3. loadVideo was called with the permanent path
        self.mock_parent_window.loadVideo.assert_called_once_with(permanent_path, video_title)

        # 4. Transcription thread was started
        mock_whisper_thread.assert_called_once()
        self.mock_parent_window.start_task.assert_called_with(
            mock_whisper_thread.return_value,
            self.mock_parent_window.onTranscriptionComplete,
            self.mock_parent_window.onTranscriptionError,
            self.mock_parent_window.update_status_progress
        )

        # Cleanup
        os.remove(temp_file.name)

    @patch('src.ui.DownloadDialog.shutil.move')
    @patch('src.ui.DownloadDialog.utils.generate_unique_filename')
    @patch('src.ui.DownloadDialog.WhisperTranscriptionThread')
    @patch('src.ui.DownloadDialog.QSettings') # Mock QSettings
    def test_onDownloadFinished_without_transcription(self, mock_qsettings, mock_whisper_thread, mock_generate_unique_filename, mock_shutil_move):
        # Arrange
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.close()

        video_title = "test_video_no_transcription"
        permanent_path = os.path.join(self.mock_parent_window.current_project_path, 'clips', f'{video_title}.mp4')
        mock_generate_unique_filename.return_value = permanent_path

        self.mock_dialog_instance.transcribe_checkbox.isChecked.return_value = False

        result = (temp_file.name, video_title, "en", "20230101")

        # Act
        DownloadDialog.onDownloadFinished(self.mock_dialog_instance, result)

        # Assert
        # 1. Verify file was moved and added to project
        mock_shutil_move.assert_called_once_with(temp_file.name, permanent_path)
        self.mock_parent_window.project_manager.add_clip_to_project_from_path.assert_called_once()
        self.mock_parent_window.loadVideo.assert_called_once_with(permanent_path, video_title)

        # 2. Verify transcription thread was NOT started
        mock_whisper_thread.assert_not_called()

        # Cleanup
        os.remove(temp_file.name)


if __name__ == '__main__':
    unittest.main()
