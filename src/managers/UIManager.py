from PyQt6.QtCore import Qt, QSize, QEvent
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QSlider, QToolBar, QStatusBar,
    QTabWidget, QGridLayout, QFrame, QDoubleSpinBox, QListWidget,
    QSizePolicy, QButtonGroup, QRadioButton, QSpinBox
)
from pyqtgraph.dockarea import DockArea

from src.config import get_resource
from src.ui.ChatDock import ChatDock
from src.ui.CustVideoWidget import CropVideoWidget
from src.ui.CustomDock import CustomDock
from src.ui.CustomSlider import CustomSlider
from src.ui.CustomTextEdit import CustomTextEdit
from src.ui.ProjectDock import ProjectDock
from src.ui.ScreenButton import ScreenButton
from src.ui.VideoOverlay import VideoOverlay


class UIManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def initUI(self):
        """
        Initializes the user interface by creating and configuring the dock area,
        setting up the main docks (video input, video output, transcription, AI editing, etc.),
        and defining the transcription section with a QTabWidget and a permanently visible text area.
        """
        # Set the window icon
        self.main_window.setWindowIcon(QIcon(get_resource('eye.png')))

        # Create the dock area
        area = DockArea()
        self.main_window.setCentralWidget(area)
        self.main_window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.setToolTip("Main dock area")

        # ---------------------
        # CREATE MAIN DOCKS
        # ---------------------
        self.main_window.videoPlayerDock = CustomDock("Video Player Input", closable=True)
        self.main_window.videoPlayerDock.setStyleSheet(self.main_window.styleSheet())
        self.main_window.videoPlayerDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.videoPlayerDock.setToolTip("Dock for input video playback")
        area.addDock(self.main_window.videoPlayerDock, 'left')

        self.main_window.videoPlayerOutput = CustomDock("Video Player Output", closable=True)
        self.main_window.videoPlayerOutput.setStyleSheet(self.main_window.styleSheet())
        self.main_window.videoPlayerOutput.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.videoPlayerOutput.setToolTip("Dock for output video playback")
        area.addDock(self.main_window.videoPlayerOutput, 'left')

        self.main_window.transcriptionDock = CustomDock("Audio Transcription and Summary", closable=True)
        self.main_window.transcriptionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.transcriptionDock.setStyleSheet(self.main_window.styleSheet())
        self.main_window.transcriptionDock.setToolTip("Dock for audio transcription and summary")
        area.addDock(self.main_window.transcriptionDock, 'right')

        self.main_window.editingDock = CustomDock("AI Audio Generation", closable=True)
        self.main_window.editingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.editingDock.setStyleSheet(self.main_window.styleSheet())
        self.main_window.editingDock.setToolTip("Dock for AI-assisted audio generation")
        area.addDock(self.main_window.editingDock, 'right')

        self.main_window.recordingDock = self.createRecordingDock()
        self.main_window.recordingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.recordingDock.setStyleSheet(self.main_window.styleSheet())
        self.main_window.recordingDock.setToolTip("Dock for recording")
        area.addDock(self.main_window.recordingDock, 'right')

        self.main_window.audioDock = self.createAudioDock()
        self.main_window.audioDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.audioDock.setStyleSheet(self.main_window.styleSheet())
        self.main_window.audioDock.setToolTip("Dock for Audio/Video management")
        area.addDock(self.main_window.audioDock, 'left')

        self.projectDock = ProjectDock()
        self.projectDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.projectDock.setStyleSheet(self.main_window.styleSheet())
        area.addDock(self.projectDock, 'right', self.main_window.transcriptionDock)

        self.main_window.videoNotesDock = CustomDock("Video Notes", closable=True)
        self.main_window.videoNotesDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.videoNotesDock.setStyleSheet(self.main_window.styleSheet())
        self.main_window.videoNotesDock.setToolTip("Dock for video notes")
        area.addDock(self.main_window.videoNotesDock, 'bottom', self.main_window.transcriptionDock)
        self.createVideoNotesDock()


        self.main_window.infoExtractionDock = CustomDock("Video Info Extraction", closable=True)
        self.main_window.infoExtractionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.infoExtractionDock.setToolTip("Dock for extracting information from videos")
        area.addDock(self.main_window.infoExtractionDock, 'right')
        self.createInfoExtractionDock()

        self.chatDock = ChatDock()
        self.chatDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.addDock(self.chatDock, 'right', self.main_window.transcriptionDock)

        # ---------------------
        # PLAYER INPUT
        # ---------------------
        self.main_window.videoContainer = QWidget()
        self.main_window.videoContainer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.videoContainer.setToolTip("Video container for panning and zooming")

        self.videoCropWidget = CropVideoWidget(parent=self.main_window.videoContainer)
        self.videoCropWidget.setAcceptDrops(True)
        self.videoCropWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoCropWidget.setToolTip("Display and crop area for input video")
        self.main_window.player.setVideoOutput(self.videoCropWidget)

        self.main_window.audioOnlyLabel = QLabel(self.main_window.videoContainer)
        self.main_window.audioOnlyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.audioOnlyLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.audioOnlyLabel.setVisible(False)

        self.videoOverlay = VideoOverlay(self.main_window, parent=self.main_window.videoContainer)
        self.videoOverlay.show()
        self.videoOverlay.raise_()
        self.videoOverlay.installEventFilter(self.main_window)

        self.videoSlider = CustomSlider(Qt.Orientation.Horizontal)
        self.videoSlider.setToolTip("Slider to navigate within the input video")

        self.main_window.fileNameLabel = QLabel("No video loaded")
        self.main_window.fileNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.fileNameLabel.setStyleSheet("QLabel { font-weight: bold; }")
        self.main_window.fileNameLabel.setToolTip("Name of the video file currently loaded in the Input Player")

        self.playButton = QPushButton('')
        self.playButton.setIcon(QIcon(get_resource("play.png")))
        self.playButton.setToolTip("Play/Pause the input video")

        self.stopButton = QPushButton('')
        self.stopButton.setIcon(QIcon(get_resource("stop.png")))
        self.stopButton.setToolTip("Stop playback of the input video")

        self.setStartBookmarkButton = QPushButton('')
        self.setStartBookmarkButton.setIcon(QIcon(get_resource("bookmark_1.png")))
        self.setStartBookmarkButton.setToolTip("Set start bookmark on the input video")

        self.setEndBookmarkButton = QPushButton('')
        self.setEndBookmarkButton.setIcon(QIcon(get_resource("bookmark_2.png")))
        self.setEndBookmarkButton.setToolTip("Set end bookmark on the input video")

        self.clearBookmarksButton = QPushButton('')
        self.clearBookmarksButton.setIcon(QIcon(get_resource("reset.png")))
        self.clearBookmarksButton.setToolTip("Clear all bookmarks")

        self.cutButton = QPushButton('')
        self.cutButton.setIcon(QIcon(get_resource("taglia.png")))
        self.cutButton.setToolTip("Cut the video between the set bookmarks")

        self.cropButton = QPushButton('')
        self.cropButton.setIcon(QIcon(get_resource("crop.png")))
        self.cropButton.setToolTip("Opens the dialog box to crop the video")


        self.rewindButton = QPushButton('<< 5s')
        self.rewindButton.setIcon(QIcon(get_resource("rewind.png")))
        self.rewindButton.setToolTip("Rewind the video by 5 seconds")

        self.frameBackwardButton = QPushButton('|<')
        self.frameBackwardButton.setToolTip("Back one frame")

        self.forwardButton = QPushButton('>> 5s')
        self.forwardButton.setIcon(QIcon(get_resource("forward.png")))
        self.forwardButton.setToolTip("Advance the video by 5 seconds")

        self.frameForwardButton = QPushButton('>|')
        self.frameForwardButton.setToolTip("Forward one frame")

        self.deleteButton = QPushButton('')
        self.deleteButton.setIcon(QIcon(get_resource("trash-bin.png")))
        self.deleteButton.setToolTip("Delete the selected part of the video")

        self.transferToOutputButton = QPushButton('')
        self.transferToOutputButton.setIcon(QIcon(get_resource("change.png")))
        self.transferToOutputButton.setToolTip("Move the video from input to output")

        self.totalTimeLabel = QLabel('/ 00:00:00:000')
        self.totalTimeLabel.setToolTip("Shows the total duration of the input video")

        # ---------------------
        # PLAYER OUTPUT
        # ---------------------
        self.videoOutputWidget = CropVideoWidget()
        self.videoOutputWidget.setAcceptDrops(True)
        self.videoOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoOutputWidget.setToolTip("Display and crop area for output video")

        self.main_window.playerOutput.setAudioOutput(self.main_window.audioOutputOutput)
        self.main_window.playerOutput.setVideoOutput(self.videoOutputWidget)


        self.playButtonOutput = QPushButton('')
        self.playButtonOutput.setIcon(QIcon(get_resource("play.png")))
        self.playButtonOutput.setToolTip("Play/Pause the output video")

        self.stopButtonOutput = QPushButton('')
        self.stopButtonOutput.setIcon(QIcon(get_resource("stop.png")))
        self.stopButtonOutput.setToolTip("Stop playback of the output video")

        self.changeButtonOutput = QPushButton('')
        self.changeButtonOutput.setIcon(QIcon(get_resource("change.png")))
        self.changeButtonOutput.setToolTip("Move the output video to the Input Video Player")

        self.syncPositionButton = QPushButton('Sync Position')
        self.syncPositionButton.setIcon(QIcon(get_resource("sync.png")))
        self.syncPositionButton.setToolTip('Synchronize the position of the output video with that of the source video')

        playbackControlLayoutOutput = QHBoxLayout()
        playbackControlLayoutOutput.addWidget(self.playButtonOutput)
        playbackControlLayoutOutput.addWidget(self.stopButtonOutput)
        playbackControlLayoutOutput.addWidget(self.changeButtonOutput)
        playbackControlLayoutOutput.addWidget(self.syncPositionButton)

        self.videoSliderOutput = CustomSlider(Qt.Orientation.Horizontal)
        self.videoSliderOutput.setRange(0, 1000)
        self.videoSliderOutput.setToolTip("Slider to navigate within the output video")

        self.main_window.currentTimeLabelOutput = QLabel('00:00')
        self.main_window.currentTimeLabelOutput.setToolTip("Shows the current time of the output video")
        self.totalTimeLabelOutput = QLabel('/ 00:00')
        self.totalTimeLabelOutput.setToolTip("Shows the total duration of the output video")
        timecodeLayoutOutput = QHBoxLayout()
        timecodeLayoutOutput.addWidget(self.main_window.currentTimeLabelOutput)
        timecodeLayoutOutput.addWidget(self.totalTimeLabelOutput)

        self.main_window.timecodeEnabled = False

        self.main_window.fileNameLabelOutput = QLabel("No video loaded")
        self.main_window.fileNameLabelOutput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.fileNameLabelOutput.setStyleSheet("QLabel { font-weight: bold; }")
        self.main_window.fileNameLabelOutput.setToolTip("Name of the video file currently loaded in the Output Player")

        videoOutputLayout = QVBoxLayout()
        videoOutputLayout.addWidget(self.main_window.fileNameLabelOutput)
        videoOutputLayout.addWidget(self.videoOutputWidget)
        videoOutputLayout.addLayout(timecodeLayoutOutput)
        videoOutputLayout.addWidget(self.videoSliderOutput)

        speedLayoutOutput = QHBoxLayout()
        speedLayoutOutput.addWidget(QLabel("Speed:"))
        self.speedSpinBoxOutput = QDoubleSpinBox()
        self.speedSpinBoxOutput.setRange(-20.0, 20.0)
        self.speedSpinBoxOutput.setSuffix("x")
        self.speedSpinBoxOutput.setValue(1.0)
        self.speedSpinBoxOutput.setSingleStep(0.1)
        speedLayoutOutput.addWidget(self.speedSpinBoxOutput)
        videoOutputLayout.addLayout(speedLayoutOutput)

        videoOutputLayout.addLayout(playbackControlLayoutOutput)

        videoPlayerOutputWidget = QWidget()
        videoPlayerOutputWidget.setLayout(videoOutputLayout)
        videoPlayerOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_window.videoPlayerOutput.addWidget(videoPlayerOutputWidget)

        self.main_window.playerOutput.durationChanged.connect(lambda duration: self.videoSliderOutput.setRange(0, duration))
        self.main_window.playerOutput.positionChanged.connect(lambda position: self.videoSliderOutput.setValue(position))

        self.transcribeButton = QPushButton('Transcribe Video')
        self.transcribeButton.setToolTip("Start transcription of the currently loaded video")

        playbackControlLayout = QHBoxLayout()
        playbackControlLayout.addWidget(self.rewindButton)
        playbackControlLayout.addWidget(self.frameBackwardButton)
        playbackControlLayout.addWidget(self.playButton)
        playbackControlLayout.addWidget(self.stopButton)
        playbackControlLayout.addWidget(self.forwardButton)
        playbackControlLayout.addWidget(self.frameForwardButton)
        playbackControlLayout.addWidget(self.setStartBookmarkButton)
        playbackControlLayout.addWidget(self.setEndBookmarkButton)
        playbackControlLayout.addWidget(self.cutButton)
        playbackControlLayout.addWidget(self.cropButton)
        playbackControlLayout.addWidget(self.deleteButton)
        playbackControlLayout.addWidget(self.transferToOutputButton)

        videoPlayerLayout = QVBoxLayout()
        videoPlayerLayout.addWidget(self.main_window.fileNameLabel)
        videoPlayerLayout.addWidget(self.main_window.videoContainer)
        timecode_layout = QHBoxLayout()
        self.timecodeInput = QLineEdit()
        self.timecodeInput.setToolTip("Current time / Go to timecode (Press Enter or click Go)")
        timecode_layout.addWidget(self.timecodeInput)
        timecode_layout.addWidget(self.totalTimeLabel)

        self.go_button = QPushButton("Go")
        self.go_button.setToolTip("Go to the specified timecode")
        timecode_layout.addWidget(self.go_button)
        videoPlayerLayout.addLayout(timecode_layout)

        videoPlayerLayout.addWidget(self.videoSlider)

        speedLayout = QHBoxLayout()
        speedLayout.addWidget(QLabel("Speed:"))
        self.speedSpinBox = QDoubleSpinBox()
        self.speedSpinBox.setRange(-20.0, 20.0)
        self.speedSpinBox.setSuffix("x")
        self.speedSpinBox.setValue(1.0)
        self.speedSpinBox.setSingleStep(0.1)
        speedLayout.addWidget(self.speedSpinBox)

        self.reverseButton = QPushButton('')
        self.reverseButton.setIcon(QIcon(get_resource("rewind_play.png")))
        self.reverseButton.setToolTip("Reverse audio/video playback")
        self.reverseButton.setFixedSize(32, 32)
        speedLayout.addWidget(self.reverseButton)

        videoPlayerLayout.addLayout(speedLayout)

        videoPlayerLayout.addLayout(playbackControlLayout)

        self.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(int(self.main_window.audioOutput.volume() * 100))
        self.volumeSlider.setToolTip("Adjust the volume of the input audio")

        self.volumeSliderOutput = QSlider(Qt.Orientation.Horizontal)
        self.volumeSliderOutput.setRange(0, 100)
        self.volumeSliderOutput.setValue(int(self.main_window.audioOutputOutput.volume() * 100))
        self.volumeSliderOutput.setToolTip("Adjust the volume of the output audio")

        videoOutputLayout.addWidget(QLabel("Volume"))
        videoOutputLayout.addWidget(self.volumeSliderOutput)

        videoPlayerWidget = QWidget()
        videoPlayerWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        videoPlayerWidget.setLayout(videoPlayerLayout)
        self.main_window.videoPlayerDock.addWidget(videoPlayerWidget)

        # =================================================================================
        # TRANSCRIPTION AND SUMMARY DOCK (WITH TAB WIDGET)
        # =================================================================================
        self.transcriptionTabWidget = QTabWidget()
        self.transcriptionTabWidget.setToolTip("Manage transcription and generated summaries.")

        # --- Transcription Tab ---
        transcription_tab = QWidget()
        transcription_layout = QVBoxLayout(transcription_tab)

        trans_controls_group = QGroupBox("Transcription Controls")
        main_controls_layout = QVBoxLayout(trans_controls_group)

        # --- Row 1: Language ---
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Select video language:"))
        self.languageComboBox = QComboBox()
        self.languageComboBox.addItems(["Automatic Detection", "Italian", "English", "French", "Spanish", "German"])
        self.languageComboBox.setItemData(0, "auto")
        self.languageComboBox.setItemData(1, "it")
        self.languageComboBox.setItemData(2, "en")
        self.languageComboBox.setItemData(3, "fr")
        self.languageComboBox.setItemData(4, "es")
        self.languageComboBox.setItemData(5, "de")
        language_layout.addWidget(self.languageComboBox)
        language_layout.addStretch()
        self.transcriptionLanguageLabel = QLabel("Detected language: N/A")
        language_layout.addWidget(self.transcriptionLanguageLabel)
        main_controls_layout.addLayout(language_layout)

        # Translation controls
        translation_layout = QHBoxLayout()
        translation_layout.addWidget(QLabel("Translate to:"))
        self.translationComboBox = QComboBox()
        supported_langs = self.main_window.translation_service.get_supported_languages()
        for code, name in supported_langs.items():
            self.translationComboBox.addItem(name.title(), code)
        self.translationComboBox.setCurrentText("English")
        translation_layout.addWidget(self.translationComboBox)
        self.translateTranscriptionButton = QPushButton("Translate Transcription")
        translation_layout.addWidget(self.translateTranscriptionButton)
        main_controls_layout.addLayout(translation_layout)

        # --- Row 2: Transcription Mode (Online/Offline) ---
        mode_layout = QHBoxLayout()
        self.onlineModeCheckbox = QCheckBox("Online (Google)")
        self.offlineModeCheckbox = QCheckBox("Offline (Whisper)")
        self.transcriptionModeGroup = QButtonGroup(self.main_window)
        self.transcriptionModeGroup.addButton(self.onlineModeCheckbox)
        self.transcriptionModeGroup.addButton(self.offlineModeCheckbox)
        self.transcriptionModeGroup.setExclusive(True)
        self.offlineModeCheckbox.setChecked(True) # Default to offline
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.onlineModeCheckbox)
        mode_layout.addWidget(self.offlineModeCheckbox)
        mode_layout.addStretch()
        main_controls_layout.addLayout(mode_layout)

        # --- Row 4: Side-by-Side Control Groups ---
        groups_layout = QHBoxLayout()

        # --- Group 1: File Actions ---
        file_actions_group = QGroupBox("File")
        file_actions_layout = QHBoxLayout(file_actions_group)

        self.transcribeButton = QPushButton('')
        self.transcribeButton.setIcon(QIcon(get_resource("script.png")))
        self.transcribeButton.setFixedSize(32, 32)
        self.transcribeButton.setToolTip("Transcribe Video")
        file_actions_layout.addWidget(self.transcribeButton)

        self.loadButton = QPushButton('')
        self.loadButton.setIcon(QIcon(get_resource("load.png")))
        self.loadButton.setFixedSize(32, 32)
        self.loadButton.setToolTip("Load Text")
        file_actions_layout.addWidget(self.loadButton)

        self.saveTranscriptionButton = QPushButton('')
        self.saveTranscriptionButton.setIcon(QIcon(get_resource("save.png")))
        self.saveTranscriptionButton.setFixedSize(32, 32)
        self.saveTranscriptionButton.setToolTip("Save Transcription to the associated JSON")
        file_actions_layout.addWidget(self.saveTranscriptionButton)

        self.resetButton = QPushButton('')
        self.resetButton.setIcon(QIcon(get_resource("reset.png")))
        self.resetButton.setFixedSize(32, 32)
        self.resetButton.setToolTip("Clear")
        file_actions_layout.addWidget(self.resetButton)

        self.fixTranscriptionButton = QPushButton('')
        self.fixTranscriptionButton.setIcon(QIcon(get_resource("text_fix.png")))
        self.fixTranscriptionButton.setFixedSize(32, 32)
        self.fixTranscriptionButton.setToolTip("Correct Transcription Text")
        file_actions_layout.addWidget(self.fixTranscriptionButton)

        self.pasteToAudioAIButton = QPushButton('')
        self.pasteToAudioAIButton.setIcon(QIcon(get_resource("paste.png")))
        self.pasteToAudioAIButton.setFixedSize(32, 32)
        self.pasteToAudioAIButton.setToolTip("Paste into the Audio AI tab")
        file_actions_layout.addWidget(self.pasteToAudioAIButton)

        self.search_button = QPushButton('')
        self.search_button.setIcon(QIcon(get_resource("find.png")))
        self.search_button.setFixedSize(32, 32)
        self.search_button.setToolTip("Opens the search dialog for the active text (Ctrl+F)")
        file_actions_layout.addWidget(self.search_button)

        groups_layout.addWidget(file_actions_group)

        # --- Group 2: Tools ---
        tools_group = QGroupBox("Tools")
        tools_grid_layout = QGridLayout(tools_group)

        self.timecodeCheckbox = QCheckBox("Insert audio timecode")
        tools_grid_layout.addWidget(self.timecodeCheckbox, 0, 0)

        self.syncButton = QPushButton('')
        self.syncButton.setIcon(QIcon(get_resource("sync.png")))
        self.syncButton.setFixedSize(32, 32)
        self.syncButton.setToolTip("Synchronize Video from Nearby Timecode")
        tools_grid_layout.addWidget(self.syncButton, 0, 1)

        self.pauseTimeEdit = QLineEdit()
        self.pauseTimeEdit.setPlaceholderText("Pause duration (e.g. 1.0s)")
        tools_grid_layout.addWidget(self.pauseTimeEdit, 1, 0)

        self.insertPauseButton = QPushButton("Insert Pause")
        tools_grid_layout.addWidget(self.insertPauseButton, 1, 1)

        self.saveAudioAIButton = QPushButton('')
        self.saveAudioAIButton.setIcon(QIcon(get_resource("save.png")))
        self.saveAudioAIButton.setFixedSize(32, 32)
        self.saveAudioAIButton.setToolTip("Save Audio AI Text to the associated JSON")
        tools_grid_layout.addWidget(self.saveAudioAIButton, 0, 2)

        self.generateGuideButton = QPushButton('')
        self.generateGuideButton.setIcon(QIcon(get_resource("script.png")))
        self.generateGuideButton.setFixedSize(32, 32)
        self.generateGuideButton.setToolTip("Generate Operational Guide from Video")
        tools_grid_layout.addWidget(self.generateGuideButton, 0, 3)

        main_controls_layout.addLayout(groups_layout)

        # --- Row 3: View toggle ---
        view_options_layout = QHBoxLayout()
        self.transcriptionViewToggle = QCheckBox("Show corrected text")
        self.transcriptionViewToggle.setToolTip("Toggle the display of the corrected text.")
        self.transcriptionViewToggle.setEnabled(False) # Disabled by default
        view_options_layout.addWidget(self.transcriptionViewToggle)
        view_options_layout.addStretch()
        main_controls_layout.addLayout(view_options_layout)

        transcription_layout.addWidget(trans_controls_group)
        self.transcriptionTabs = QTabWidget()
        self.transcriptionTabs.setToolTip("View single or multiple transcriptions.")

        self.singleTranscriptionTextArea = CustomTextEdit(self.main_window)
        self.singleTranscriptionTextArea.setPlaceholderText("The transcription of the current video will appear here...")
        self.transcriptionTabs.addTab(self.singleTranscriptionTextArea, "Single Transcription")

        self.batchTranscriptionTextArea = CustomTextEdit(self.main_window)
        self.batchTranscriptionTextArea.setPlaceholderText("The results of the multiple transcription will appear here...")
        self.batchTranscriptionTextArea.setReadOnly(True) # Initially read-only
        self.transcriptionTabs.addTab(self.batchTranscriptionTextArea, "Multiple Transcription")

        transcription_layout.addWidget(self.transcriptionTabs)

        self.transcriptionTabWidget.addTab(transcription_tab, "Transcription")

        # --- Audio AI Tab ---
        self.audio_ai_tab = QWidget()
        audio_ai_layout = QVBoxLayout(self.audio_ai_tab)
        audio_ai_layout.addWidget(tools_group)

        self.audioAiTextArea = CustomTextEdit(self.main_window)
        self.audioAiTextArea.setPlaceholderText("Paste the text to be used for audio generation or other AI functions here...")
        audio_ai_layout.addWidget(self.audioAiTextArea)

        # --- Summary Tab ---
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)

        summary_controls_group = QGroupBox("Summary and AI Controls")
        summary_controls_layout = QVBoxLayout(summary_controls_group)

        top_controls_layout = QHBoxLayout()

        self.summarize_button = QPushButton('')
        self.summarize_button.setIcon(QIcon(get_resource("text_sum.png")))
        self.summarize_button.setFixedSize(32, 32)
        self.summarize_button.setToolTip("Summarize Text")
        top_controls_layout.addWidget(self.summarize_button)

        self.summarize_meeting_button = QPushButton('')
        self.summarize_meeting_button.setIcon(QIcon(get_resource("meet_sum.png")))
        self.summarize_meeting_button.setFixedSize(32, 32)
        self.summarize_meeting_button.setToolTip("Summarize Meeting")
        top_controls_layout.addWidget(self.summarize_meeting_button)

        self.generatePptxActionBtn = QPushButton('')
        self.generatePptxActionBtn.setIcon(QIcon(get_resource("powerpoint.png")))
        self.generatePptxActionBtn.setFixedSize(32, 32)
        self.generatePptxActionBtn.setToolTip("Generate Presentation")
        top_controls_layout.addWidget(self.generatePptxActionBtn)

        self.highlightTextButton = QPushButton('')
        self.highlightTextButton.setIcon(QIcon(get_resource("key.png")))
        self.highlightTextButton.setFixedSize(32, 32)
        self.highlightTextButton.setToolTip("Highlight Selected Text")
        top_controls_layout.addWidget(self.highlightTextButton)

        self.pasteSummaryToAudioAIButton = QPushButton('')
        self.pasteSummaryToAudioAIButton.setIcon(QIcon(get_resource("paste.png")))
        self.pasteSummaryToAudioAIButton.setFixedSize(32, 32)
        self.pasteSummaryToAudioAIButton.setToolTip("Paste summary into the Audio AI tab")
        top_controls_layout.addWidget(self.pasteSummaryToAudioAIButton)

        self.saveSummaryButton = QPushButton('')
        self.saveSummaryButton.setIcon(QIcon(get_resource("save.png")))
        self.saveSummaryButton.setFixedSize(32, 32)
        self.saveSummaryButton.setToolTip("Save Summary to the associated JSON")
        top_controls_layout.addWidget(self.saveSummaryButton)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        top_controls_layout.addWidget(separator)

        self.integraInfoButton = QPushButton("")
        self.integraInfoButton.setIcon(QIcon(get_resource("frame_get.png")))
        self.integraInfoButton.setFixedSize(32, 32)
        self.integraInfoButton.setToolTip("Integrate info from the video into the summary (with smart extraction)")
        top_controls_layout.addWidget(self.integraInfoButton)

        top_controls_layout.addStretch()
        summary_controls_layout.addLayout(top_controls_layout)

        bottom_controls_layout = QHBoxLayout()
        self.showTimecodeSummaryCheckbox = QCheckBox("Show timecode")
        self.showTimecodeSummaryCheckbox.setChecked(True)
        bottom_controls_layout.addWidget(self.showTimecodeSummaryCheckbox)

        bottom_controls_layout.addStretch()
        summary_controls_layout.addLayout(bottom_controls_layout)

        summary_layout.addWidget(summary_controls_group)

        self.summaryTabWidget = QTabWidget()
        self.summaryTabWidget.setToolTip("View the different types of summaries generated.")

        self.summaryDetailedTextArea = CustomTextEdit(self.main_window)
        self.summaryDetailedTextArea.setPlaceholderText("The detailed summary will appear here...")
        self.summaryTabWidget.addTab(self.summaryDetailedTextArea, "Detailed")

        self.summaryMeetingTextArea = CustomTextEdit(self.main_window)
        self.summaryMeetingTextArea.setPlaceholderText("The meeting notes will appear here...")
        self.summaryTabWidget.addTab(self.summaryMeetingTextArea, "Meeting Notes")

        self.summaryDetailedIntegratedTextArea = CustomTextEdit(self.main_window)
        self.summaryDetailedIntegratedTextArea.setPlaceholderText("The detailed summary integrated with video information will appear here...")
        self.summaryTabWidget.addTab(self.summaryDetailedIntegratedTextArea, "Detailed (Integrated)")

        self.summaryMeetingIntegratedTextArea = CustomTextEdit(self.main_window)
        self.summaryMeetingIntegratedTextArea.setPlaceholderText("The meeting notes integrated with video information will appear here...")
        self.summaryTabWidget.addTab(self.summaryMeetingIntegratedTextArea, "Meeting Notes (Integrated)")

        self.summaryCombinedDetailedTextArea = CustomTextEdit(self.main_window)
        self.summaryCombinedDetailedTextArea.setPlaceholderText("The combined detailed summary will appear here...")
        self.summaryTabWidget.addTab(self.summaryCombinedDetailedTextArea, "Combined Detailed")

        self.summaryCombinedMeetingTextArea = CustomTextEdit(self.main_window)
        self.summaryCombinedMeetingTextArea.setPlaceholderText("The combined meeting notes will appear here...")
        self.summaryTabWidget.addTab(self.summaryCombinedMeetingTextArea, "Combined Meeting Notes")

        # Map widgets to their data keys for easier management
        self.summary_widget_map = {
            self.summaryDetailedTextArea: "detailed",
            self.summaryMeetingTextArea: "meeting",
            self.summaryDetailedIntegratedTextArea: "detailed_integrated",
            self.summaryMeetingIntegratedTextArea: "meeting_integrated",
            self.summaryCombinedDetailedTextArea: "detailed_combined",
            self.summaryCombinedMeetingTextArea: "meeting_combined",
        }


        summary_layout.addWidget(self.summaryTabWidget)


        self.transcriptionTabWidget.addTab(summary_tab, "Summary")
        self.transcriptionTabWidget.addTab(self.audio_ai_tab, "Audio AI")

        dock_layout = QVBoxLayout()
        dock_layout.addWidget(self.transcriptionTabWidget)

        container_widget = QWidget()
        container_widget.setLayout(dock_layout)
        self.main_window.transcriptionDock.addWidget(container_widget)

        voiceSettingsWidget = self.setupVoiceSettingsUI()
        voiceSettingsWidget.setToolTip("Voice settings for AI audio editing")
        self.main_window.editingDock.addWidget(voiceSettingsWidget)

        generatedAudiosWidget = self.createGeneratedAudiosUI()
        self.main_window.editingDock.addWidget(generatedAudiosWidget)
        self.alignspeed.toggled.connect(self.alignspeed_replacement.setChecked)
        self.alignspeed_replacement.toggled.connect(self.alignspeed.setChecked)

        docks = {
            'videoPlayerDock': self.main_window.videoPlayerDock,
            'transcriptionDock': self.main_window.transcriptionDock,
            'editingDock': self.main_window.editingDock,
            'recordingDock': self.main_window.recordingDock,
            'audioDock': self.main_window.audioDock,
            'videoPlayerOutput': self.main_window.videoPlayerOutput,
            'projectDock': self.projectDock,
            'videoNotesDock': self.main_window.videoNotesDock,
            'infoExtractionDock': self.main_window.infoExtractionDock,
            'chatDock': self.chatDock
        }

        self.statusBar = QStatusBar()
        self.main_window.setStatusBar(self.statusBar)
        self.statusBar.setStyleSheet("QStatusBar { padding: 1px; } QStatusBar::item { border: none; }")
        self.statusLabel = QLabel("Ready")
        self.statusLabel.setToolTip("Shows the current status of the application")
        self.statusBar.addWidget(self.statusLabel, 1)

        self.progressBar = QProgressBar(self.main_window)
        self.progressBar.setToolTip("Shows the progress of ongoing operations")
        self.progressBar.setMaximumWidth(300)
        self.progressBar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progressBar)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setToolTip("Cancel the current operation")
        self.cancelButton.setFixedWidth(100)
        self.cancelButton.setVisible(False)
        self.statusBar.addPermanentWidget(self.cancelButton)

        mainToolbar = QToolBar("Main Toolbar")
        mainToolbar.setToolTip("Main toolbar for actions")
        self.main_window.addToolBar(mainToolbar)

        mainToolbar.addSeparator()

        self.summarizeMeetingAction = QAction(QIcon(get_resource("meet_sum.png")), 'Summarize Meeting', self.main_window)
        self.summarizeMeetingAction.setStatusTip('Create a structured summary of a meeting transcription')
        mainToolbar.addAction(self.summarizeMeetingAction)

        self.summarizeAction = QAction(QIcon(get_resource("text_sum.png")), 'Summarize Text', self.main_window)
        self.summarizeAction.setStatusTip('Generate a summary of the text using AI')
        mainToolbar.addAction(self.summarizeAction)

        self.fixTextAction = QAction(QIcon(get_resource("text_fix.png")), 'Correct Text', self.main_window)
        self.fixTextAction.setStatusTip('Fix and improve the text using AI')
        mainToolbar.addAction(self.fixTextAction)

        self.generatePptxAction = QAction(QIcon(get_resource("powerpoint.png")), 'Generate Presentation', self.main_window)
        self.generatePptxAction.setStatusTip('Create a PowerPoint presentation from the text')
        mainToolbar.addAction(self.generatePptxAction)

        workspaceToolbar = QToolBar("Workspace Toolbar")
        workspaceToolbar.setToolTip("Toolbar for layouts and settings")
        self.main_window.addToolBar(workspaceToolbar)

        self.recordingLayoutAction = QAction(QIcon(get_resource("rec.png")), 'Recording', self.main_window)
        self.recordingLayoutAction.setToolTip("Layout for recording")
        workspaceToolbar.addAction(self.recordingLayoutAction)

        self.comparisonLayoutAction = QAction(QIcon(get_resource("compare.png")), 'Comparison', self.main_window)
        self.comparisonLayoutAction.setToolTip("Layout for comparison")
        workspaceToolbar.addAction(self.comparisonLayoutAction)

        self.transcriptionLayoutAction = QAction(QIcon(get_resource("script.png")), 'Transcription', self.main_window)
        self.transcriptionLayoutAction.setToolTip("Layout for transcription")
        workspaceToolbar.addAction(self.transcriptionLayoutAction)

        self.defaultLayoutAction = QAction(QIcon(get_resource("default.png")), 'Default', self.main_window)
        self.defaultLayoutAction.setToolTip("Default layout")
        workspaceToolbar.addAction(self.defaultLayoutAction)
        workspaceToolbar.addSeparator()

        serviceToolbar = QToolBar("Rec Toolbar")
        serviceToolbar.setToolTip("Service bar")
        self.main_window.addToolBar(serviceToolbar)

        self.shareAction = QAction(QIcon(get_resource("share.png")), "Share Video", self.main_window)
        self.shareAction.setToolTip("Share the currently loaded video")
        serviceToolbar.addAction(self.shareAction)

        self.settingsAction = QAction(QIcon(get_resource("gear.png")), "Settings", self.main_window)
        self.settingsAction.setToolTip("Open the application settings")
        serviceToolbar.addAction(self.settingsAction)

        serviceToolbar.addSeparator()

        self.findAction = QAction("Search", self.main_window)
        self.findAction.setShortcut("Ctrl+F")
        self.main_window.addAction(self.findAction)

        self.setupMenuBar()

        if hasattr(self.main_window, 'applyDarkMode'):
            self.main_window.applyDarkMode()

        self.main_window.applyStyleToAllDocks()
        self.main_window.apply_and_save_font_settings()

    def createVideoNotesDock(self):
        """Creates the video notes dock."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.main_window.videoNotesListWidget = QListWidget()
        self.main_window.videoNotesListWidget.setToolTip("List of video notes. Double-click to go to the timecode.")
        layout.addWidget(self.main_window.videoNotesListWidget)

        buttons_layout = QHBoxLayout()
        self.main_window.editNoteButton = QPushButton("Edit Note")
        self.main_window.editNoteButton.setToolTip("Edit the selected note.")
        buttons_layout.addWidget(self.main_window.editNoteButton)

        self.main_window.deleteNoteButton = QPushButton("Delete Note")
        self.main_window.deleteNoteButton.setToolTip("Delete the selected note.")
        buttons_layout.addWidget(self.main_window.deleteNoteButton)

        layout.addLayout(buttons_layout)
        self.main_window.videoNotesDock.addWidget(widget)

    def setupMenuBar(self):
        menuBar = self.main_window.menuBar()
        fileMenu = menuBar.addMenu('&File')

        openProjectAction = QAction('&Open Project...', self.main_window)
        openProjectAction.setStatusTip('Open a .gnai project file')
        fileMenu.addAction(openProjectAction)

        newProjectAction = QAction('&New Project...', self.main_window)
        newProjectAction.setStatusTip('Create a new project')
        fileMenu.addAction(newProjectAction)

        saveProjectAction = QAction('&Save Project', self.main_window)
        saveProjectAction.setShortcut('Ctrl+S')
        saveProjectAction.setStatusTip('Save the current project')
        fileMenu.addAction(saveProjectAction)

        closeProjectAction = QAction('&Close Project', self.main_window)
        closeProjectAction.setStatusTip('Close the current project and clear the workspace')
        fileMenu.addAction(closeProjectAction)

        fileMenu.addSeparator()

        openAction = QAction('&Open Video/Audio', self.main_window)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open video')

        openActionOutput = QAction('&Open as Output Video', self.main_window)
        openAction.setShortcut('Ctrl+I')
        openActionOutput.setStatusTip('Open Output Video')

        fileMenu.addAction(openAction)
        fileMenu.addAction(openActionOutput)

        saveAsAction = QAction('&Save Output Video As...', self.main_window)
        saveAsAction.setShortcut('Ctrl+S')
        saveAsAction.setStatusTip('Save the current video from the Output Video Player')
        fileMenu.addAction(saveAsAction)

        openRootFolderAction = QAction('&Open Main Folder', self.main_window)
        openRootFolderAction.setShortcut('Ctrl+R')
        openRootFolderAction.setStatusTip('Open the main folder of the software')
        fileMenu.addAction(openRootFolderAction)

        fileMenu.addSeparator()

        releaseSourceAction = QAction(QIcon(get_resource("reset.png")), "Unload Video Source", self.main_window)
        fileMenu.addAction(releaseSourceAction)

        releaseOutputAction = QAction(QIcon(get_resource("reset.png")), "Unload Output Video", self.main_window)
        fileMenu.addAction(releaseOutputAction)

        fileMenu.addSeparator()

        exitAction = QAction('&Exit', self.main_window)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit the application')
        fileMenu.addAction(exitAction)

        fileMenu.addSeparator()
        self.main_window.recentMenu = fileMenu.addMenu("Recent")
        self.main_window.recentProjectsMenu = fileMenu.addMenu("Recent Projects")

        importMenu = menuBar.addMenu('&Import')
        importUrlAction = QAction('Import from URL...', self.main_window)
        importUrlAction.setStatusTip('Import video or audio from a URL (e.g. YouTube)')
        importMenu.addAction(importUrlAction)

        importVideoAction = QAction('Import Videos into Project...', self.main_window)
        importVideoAction.setStatusTip('Import local video files into the current project')
        importMenu.addAction(importVideoAction)

        importAudioAction = QAction('Import Audio into Project...', self.main_window)
        importAudioAction.setStatusTip('Import local audio files into the current project')
        importMenu.addAction(importAudioAction)

        importDocAction = QAction('Import document...', self.main_window)
        importDocAction.setStatusTip('Import a PDF or DOCX document to supplement the summary')
        importMenu.addAction(importDocAction)

        viewMenu = menuBar.addMenu('&View')
        workspaceMenu = menuBar.addMenu('&Workspace')
        workspaceMenu.addAction(self.defaultLayoutAction)
        workspaceMenu.addAction(self.recordingLayoutAction)
        workspaceMenu.addAction(self.comparisonLayoutAction)
        workspaceMenu.addAction(self.transcriptionLayoutAction)

        workflowsMenu = menuBar.addMenu('&AI Actions')
        workflowsMenu.addAction(self.summarizeMeetingAction)
        workflowsMenu.addAction(self.summarizeAction)
        workflowsMenu.addAction(self.fixTextAction)
        workflowsMenu.addAction(self.generatePptxAction)

        exportMenu = menuBar.addMenu('&Export')
        exportAction = QAction('Export Summary...', self.main_window)
        exportMenu.addAction(exportAction)

        insertMenu = menuBar.addMenu('&Insert')
        addMediaAction = QAction('Add Media/Text...', self.main_window)
        addMediaAction.setStatusTip('Add text or images to the video')
        insertMenu.addAction(addMediaAction)

        self.main_window.setupViewMenuActions(viewMenu)

        aboutMenu = menuBar.addMenu('&About')
        aboutAction = QAction('&About', self.main_window)
        aboutAction.setStatusTip('About the application')
        aboutMenu.addAction(aboutAction)

    def createInfoExtractionDock(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.infoExtractionResultArea = CustomTextEdit(self.main_window)
        self.infoExtractionResultArea.setPlaceholderText("The search results will appear here...")
        layout.addWidget(self.infoExtractionResultArea)

        player_selection_layout = QHBoxLayout()
        player_selection_layout.addWidget(QLabel("Target Player:"))
        self.analysisPlayerSelectionCombo = QComboBox()
        self.analysisPlayerSelectionCombo.addItems(["Input Player", "Output Player"])
        player_selection_layout.addWidget(self.analysisPlayerSelectionCombo)
        layout.addLayout(player_selection_layout)

        frame_count_layout = QHBoxLayout()
        frame_count_layout.addWidget(QLabel("Number of frames to analyze:"))
        self.analysisFrameCountSpin = QSpinBox()
        self.analysisFrameCountSpin.setRange(1, 500)
        self.analysisFrameCountSpin.setValue(20)
        frame_count_layout.addWidget(self.analysisFrameCountSpin)
        layout.addLayout(frame_count_layout)

        self.smartExtractionCheckbox = QCheckBox("Use smart frame extraction")
        self.smartExtractionCheckbox.setToolTip("Analyze only frames with significant interface changes.")
        layout.addWidget(self.smartExtractionCheckbox)

        search_layout = QHBoxLayout()
        self.searchQueryInput = QLineEdit()
        self.searchQueryInput.setPlaceholderText("E.g.: a person waving, a red car...")
        search_layout.addWidget(QLabel("What do you want to search for?"))
        search_layout.addWidget(self.searchQueryInput)
        layout.addLayout(search_layout)

        self.runAnalysisButton = QPushButton("Search")
        layout.addWidget(self.runAnalysisButton)

        self.specificObjectSearchButton = QPushButton("Search for a specific object")
        layout.addWidget(self.specificObjectSearchButton)


        self.main_window.infoExtractionDock.addWidget(widget)

    def createAudioDock(self):
        dock = CustomDock("Audio and Video Management", closable=True)
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        player_selection_group = QGroupBox("Apply to")
        player_selection_layout = QHBoxLayout(player_selection_group)

        self.main_window.player_input_button = QPushButton(QIcon(get_resource("rec.png")), "Input")
        self.main_window.player_input_button.setCheckable(True)
        self.main_window.player_input_button.setChecked(True)
        self.main_window.player_input_button.setToolTip("Apply operations to the Input Video Player")
        player_selection_layout.addWidget(self.main_window.player_input_button)

        self.main_window.player_output_button = QPushButton(QIcon(get_resource("play.png")), "Output")
        self.main_window.player_output_button.setCheckable(True)
        self.main_window.player_output_button.setToolTip("Apply operations to the Output Video Player")
        player_selection_layout.addWidget(self.main_window.player_output_button)

        self.main_window.player_button_group = QButtonGroup(self.main_window)
        self.main_window.player_button_group.addButton(self.main_window.player_input_button)
        self.main_window.player_button_group.addButton(self.main_window.player_output_button)
        self.main_window.player_button_group.setExclusive(True)

        main_layout.addWidget(player_selection_group)
        tab_widget = QTabWidget()
        add_pause_tab = QWidget()
        add_pause_layout = QVBoxLayout(add_pause_tab)

        audioPauseGroup = self.createAudioPauseGroup()
        videoPauseGroup = self.createVideoPauseGroup()
        silenceRemoverGroup = self.createSilenceRemoverGroup()

        add_pause_layout.addWidget(audioPauseGroup)
        add_pause_layout.addWidget(videoPauseGroup)
        add_pause_layout.addWidget(silenceRemoverGroup)
        add_pause_layout.addStretch()
        tab_widget.addTab(add_pause_tab, "Add/Pause")

        audio_selection_tab = QWidget()
        audio_selection_layout = QVBoxLayout(audio_selection_tab)

        audioReplacementGroup = self.createAudioReplacementGroup()
        backgroundAudioGroup = self.createBackgroundAudioGroup()

        audio_selection_layout.addWidget(audioReplacementGroup)
        audio_selection_layout.addWidget(backgroundAudioGroup)
        tab_widget.addTab(audio_selection_tab, "Audio Selection")

        video_merge_tab = QWidget()
        video_merge_layout = QVBoxLayout(video_merge_tab)

        mergeGroup = QGroupBox("Video Merge Options")
        grid_layout = QGridLayout(mergeGroup)
        grid_layout.setSpacing(10)

        self.main_window.mergeVideoPathLineEdit = QLineEdit()
        self.main_window.mergeVideoPathLineEdit.setReadOnly(True)
        self.main_window.mergeVideoPathLineEdit.setPlaceholderText("Select the video to add...")
        browseMergeVideoButton = QPushButton('Browse...')
        projectMergeVideoButton = QPushButton('From Project')

        grid_layout.addWidget(QLabel("Video to merge:"), 0, 0)
        grid_layout.addWidget(self.main_window.mergeVideoPathLineEdit, 0, 1)
        grid_layout.addWidget(browseMergeVideoButton, 0, 2)
        grid_layout.addWidget(projectMergeVideoButton, 0, 3)

        resolution_group = QGroupBox("Resolution Management")
        resolution_layout = QVBoxLayout(resolution_group)
        self.main_window.adaptResolutionRadio = QRadioButton("Adapt resolutions")
        self.main_window.adaptResolutionRadio.setChecked(True)
        self.main_window.maintainResolutionRadio = QRadioButton("Maintain original resolutions")
        resolution_layout.addWidget(self.main_window.adaptResolutionRadio)
        resolution_layout.addWidget(self.main_window.maintainResolutionRadio)
        grid_layout.addWidget(resolution_group, 1, 0, 1, 4)

        mergeButton = QPushButton('Merge Video')
        mergeButton.setStyleSheet("padding: 10px; font-weight: bold;")
        grid_layout.addWidget(mergeButton, 2, 0, 1, 4)

        video_merge_layout.addWidget(mergeGroup)
        video_merge_tab.setLayout(video_merge_layout)
        tab_widget.addTab(video_merge_tab, "Merge Video")

        main_layout.addWidget(tab_widget)
        dock.addWidget(main_widget)
        return dock

    def createAudioPauseGroup(self):
        audioPauseGroup = QGroupBox("Add pause")
        layout = QVBoxLayout()

        duration_layout = QHBoxLayout()
        duration_label = QLabel("Pause Duration (s):")
        self.main_window.pauseAudioDurationLineEdit = QLineEdit()
        self.main_window.pauseAudioDurationLineEdit.setPlaceholderText("Pause Duration (seconds)")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.main_window.pauseAudioDurationLineEdit)
        layout.addLayout(duration_layout)

        applyPauseButton = QPushButton('Apply Audio Pause')
        layout.addWidget(applyPauseButton)

        audioPauseGroup.setLayout(layout)
        return audioPauseGroup

    def createVideoPauseGroup(self):
        videoPauseGroup = QGroupBox("Apply video pause")
        layout = QVBoxLayout()

        duration_layout = QHBoxLayout()
        duration_label = QLabel("Pause Duration (s):")
        self.main_window.pauseVideoDurationLineEdit = QLineEdit()
        self.main_window.pauseVideoDurationLineEdit.setPlaceholderText("Pause Duration (seconds)")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.main_window.pauseVideoDurationLineEdit)
        layout.addLayout(duration_layout)

        applyVideoPauseButton = QPushButton('Apply Video Pause')
        layout.addWidget(applyVideoPauseButton)

        videoPauseGroup.setLayout(layout)
        return videoPauseGroup

    def createSilenceRemoverGroup(self):
        silence_remover_group = QGroupBox("Remove Silences")
        silence_remover_layout = QVBoxLayout(silence_remover_group)

        silence_remover_layout.addWidget(QLabel("Silence Threshold (dBFS):"))
        self.main_window.silence_threshold_spinbox = QDoubleSpinBox()
        self.main_window.silence_threshold_spinbox.setRange(-100.0, 0.0)
        self.main_window.silence_threshold_spinbox.setValue(-40.0)
        self.main_window.silence_threshold_spinbox.setSuffix(" dB")
        self.main_window.silence_threshold_spinbox.setToolTip("Volume level below which audio is considered silent. Lower values (e.g. -50dB) are stricter.")
        silence_remover_layout.addWidget(self.main_window.silence_threshold_spinbox)

        silence_remover_layout.addWidget(QLabel("Minimum Silence Duration (ms):"))
        self.main_window.min_silence_duration_spinbox = QSpinBox()
        self.main_window.min_silence_duration_spinbox.setRange(100, 10000)
        self.main_window.min_silence_duration_spinbox.setValue(500)
        self.main_window.min_silence_duration_spinbox.setSuffix(" ms")
        self.main_window.min_silence_duration_spinbox.setToolTip("The minimum duration of a silence to be removed. Useful for not cutting out the natural pauses in speech.")
        silence_remover_layout.addWidget(self.main_window.min_silence_duration_spinbox)

        self.main_window.start_silence_removal_button = QPushButton("Start Silence Removal Processing")
        self.main_window.start_silence_removal_button.setIcon(QIcon(get_resource("taglia.png")))
        self.main_window.start_silence_removal_button.setToolTip("Start the process of removing silences from the video loaded in the Input Player.")
        silence_remover_layout.addWidget(self.main_window.start_silence_removal_button)

        return silence_remover_group

    def createAudioReplacementGroup(self):
        audioReplacementGroup = QGroupBox("Main audio replacement")
        layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.main_window.audioPathLineEdit = QLineEdit()
        self.main_window.audioPathLineEdit.setReadOnly(True)
        browseAudioButton = QPushButton('Browse...')
        projectAudioButton = QPushButton('From Project')
        file_layout.addWidget(self.main_window.audioPathLineEdit)
        file_layout.addWidget(browseAudioButton)
        file_layout.addWidget(projectAudioButton)
        layout.addLayout(file_layout)

        applyAudioButton = QPushButton('Apply Main Audio')

        self.alignspeed_replacement = QCheckBox("Align video speed with audio")
        self.alignspeed_replacement.setChecked(True)
        layout.addWidget(self.alignspeed_replacement)
        layout.addWidget(applyAudioButton)

        audioReplacementGroup.setLayout(layout)
        return audioReplacementGroup

    def createBackgroundAudioGroup(self):
        backgroundAudioGroup = QGroupBox("Background Audio Management")
        layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.main_window.backgroundAudioPathLineEdit = QLineEdit()
        self.main_window.backgroundAudioPathLineEdit.setReadOnly(True)
        browseBackgroundAudioButton = QPushButton('Choose Background')
        file_layout.addWidget(self.main_window.backgroundAudioPathLineEdit)
        file_layout.addWidget(browseBackgroundAudioButton)
        layout.addLayout(file_layout)

        volume_layout = QHBoxLayout()
        volume_label = QLabel("Background Volume:")
        self.main_window.volumeSliderBack = QSlider(Qt.Orientation.Horizontal)
        self.main_window.volumeSliderBack.setRange(0, 1000)
        self.main_window.volumeSliderBack.setValue(6)
        self.main_window.volumeLabelBack = QLabel(f"{self.main_window.volumeSliderBack.value() / 1000:.3f}")
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.main_window.volumeSliderBack)
        volume_layout.addWidget(self.main_window.volumeLabelBack)
        layout.addLayout(volume_layout)

        self.main_window.loopBackgroundAudioCheckBox = QCheckBox("Loop Background if shorter than video")
        self.main_window.loopBackgroundAudioCheckBox.setChecked(True)
        layout.addWidget(self.main_window.loopBackgroundAudioCheckBox)

        applyBackgroundButton = QPushButton('Apply Background to Video')
        layout.addWidget(applyBackgroundButton)

        backgroundAudioGroup.setLayout(layout)
        return backgroundAudioGroup

    def createRecordingDock(self):
        dock =CustomDock("Recording", closable=True)
        infoGroup = QGroupBox("Info")
        infoLayout = QGridLayout(infoGroup)

        self.main_window.timecodeLabel = QLabel('00:00:00')
        self.main_window.timecodeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.timecodeLabel.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
                font-size: 28pt;
                font-weight: bold;
                color: #00FF00;
                background-color: #000000;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        infoLayout.addWidget(self.main_window.timecodeLabel, 0, 0, 1, 2)

        self.main_window.recordingStatusLabel = QLabel("Status: Ready")
        infoLayout.addWidget(self.main_window.recordingStatusLabel, 1, 0, 1, 2)

        self.main_window.selectedMonitorLabel = QLabel("Monitor: N/A")
        infoLayout.addWidget(self.main_window.selectedMonitorLabel, 2, 0, 1, 2)

        self.main_window.outputFileLabel = QLabel("File: N/A")
        infoLayout.addWidget(self.main_window.outputFileLabel, 3, 0, 1, 2)

        self.main_window.fpsLabel = QLabel("FPS: N/A")
        infoLayout.addWidget(self.main_window.fpsLabel, 4, 0)

        self.main_window.fileSizeLabel = QLabel("Size: N/A")
        infoLayout.addWidget(self.main_window.fileSizeLabel, 4, 1)

        self.main_window.bitrateLabel = QLabel("Bitrate: N/A")
        infoLayout.addWidget(self.main_window.bitrateLabel, 5, 0)

        self.main_window.audioTestResultLabel = QLabel("Audio Test: N/A")
        infoLayout.addWidget(self.main_window.audioTestResultLabel, 5, 1)

        label_style = "font-size: 9pt; color: #cccccc;"
        self.main_window.recordingStatusLabel.setStyleSheet(label_style)
        self.main_window.selectedMonitorLabel.setStyleSheet(label_style)
        self.main_window.outputFileLabel.setStyleSheet(label_style)
        self.main_window.fpsLabel.setStyleSheet(label_style)
        self.main_window.fileSizeLabel.setStyleSheet(label_style)
        self.main_window.bitrateLabel.setStyleSheet(label_style)
        self.main_window.audioTestResultLabel.setStyleSheet(label_style)

        recordingLayout = QVBoxLayout()
        screensGroupBox = QGroupBox("Select Screen")
        screensLayout = QGridLayout(screensGroupBox)

        self.main_window.screen_buttons = []

        recordingLayout.addWidget(screensGroupBox)

        audioGroupBox = QGroupBox("Select Audio")
        mainAudioLayout = QVBoxLayout(audioGroupBox)
        mainAudioLayout.addWidget(self.main_window.audioTestResultLabel)

        self.main_window.audio_checkbox_container = QWidget()
        self.main_window.audio_device_layout = QVBoxLayout(self.main_window.audio_checkbox_container)
        mainAudioLayout.addWidget(self.main_window.audio_checkbox_container)

        recordingLayout.addWidget(audioGroupBox)

        saveOptionsGroup = QGroupBox("Save Options")
        saveOptionsLayout = QVBoxLayout(saveOptionsGroup)

        self.main_window.folderPathLineEdit = QLineEdit()
        self.main_window.folderPathLineEdit.setPlaceholderText("Enter the path of the destination folder")

        self.main_window.saveVideoOnlyCheckBox = QCheckBox("Record video only")
        self.main_window.saveAudioOnlyCheckBox = QCheckBox("Record audio only")

        saveOptionsLayout.addWidget(self.main_window.saveVideoOnlyCheckBox)
        saveOptionsLayout.addWidget(self.main_window.saveAudioOnlyCheckBox)
        saveOptionsLayout.addWidget(QLabel("File Path:"))

        saveOptionsLayout.addWidget(self.main_window.folderPathLineEdit)

        buttonsLayout = QHBoxLayout()
        browseButton = QPushButton('Browse')
        buttonsLayout.addWidget(browseButton)

        open_folder_button = QPushButton('Open Folder')
        buttonsLayout.addWidget(open_folder_button)

        self.main_window.recordingNameLineEdit = QLineEdit()
        self.main_window.recordingNameLineEdit.setPlaceholderText("Enter the name of the recording")
        saveOptionsLayout.addLayout(buttonsLayout)

        saveOptionsLayout.addWidget(QLabel("Recording Name:"))
        saveOptionsLayout.addWidget(self.main_window.recordingNameLineEdit)

        recordingLayout.addWidget(saveOptionsGroup)

        self.main_window.autoRecordTeamsCheckBox = QCheckBox("Enable automatic recording for Teams")

        self.startRecordingButton = QPushButton("")
        self.startRecordingButton.setIcon(QIcon(get_resource("rec.png")))
        self.startRecordingButton.setToolTip("Start recording")

        self.stopRecordingButton = QPushButton("")
        self.stopRecordingButton.setIcon(QIcon(get_resource("stop.png")))
        self.stopRecordingButton.setToolTip("Stop recording")

        self.pauseRecordingButton = QPushButton("")
        self.pauseRecordingButton.setIcon(QIcon(get_resource("pausa_play.png")))
        self.pauseRecordingButton.setToolTip("Pause/Resume recording")
        self.pauseRecordingButton.setEnabled(False)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.startRecordingButton)
        buttonLayout.addWidget(self.stopRecordingButton)
        buttonLayout.addWidget(self.pauseRecordingButton)

        recordingLayout.addLayout(buttonLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(infoGroup)
        mainLayout.addLayout(recordingLayout)

        widget = QWidget()
        widget.setLayout(mainLayout)

        dock.addWidget(widget)
        return dock

    def setupVoiceSettingsUI(self):
        voiceSettingsGroup = QGroupBox("Voice Settings")
        layout = QVBoxLayout()

        self.main_window.voiceSelectionComboBox = QComboBox()
        self.main_window.voiceSelectionComboBox.setEditable(True)

        layout.addWidget(self.main_window.voiceSelectionComboBox)

        self.main_window.voiceIdInput = QLineEdit()
        self.main_window.voiceIdInput.setPlaceholderText("Voice ID")
        layout.addWidget(self.main_window.voiceIdInput)

        self.main_window.addVoiceButton = QPushButton('Add Custom Voice')
        layout.addWidget(self.main_window.addVoiceButton)

        stabilityLabel = QLabel("Stability:")
        self.main_window.stabilitySlider = QSlider(Qt.Orientation.Horizontal)
        self.main_window.stabilitySlider.setMinimum(0)
        self.main_window.stabilitySlider.setMaximum(100)
        self.main_window.stabilitySlider.setToolTip(
            "Regulates emotion and consistency. Lower for more emotion, higher for consistency.")
        self.main_window.stabilityValueLabel = QLabel("50%")
        layout.addWidget(stabilityLabel)
        layout.addWidget(self.main_window.stabilitySlider)
        layout.addWidget(self.main_window.stabilityValueLabel)

        similarityLabel = QLabel("Similarity:")
        self.main_window.similaritySlider = QSlider(Qt.Orientation.Horizontal)
        self.main_window.similaritySlider.setMinimum(0)
        self.main_window.similaritySlider.setMaximum(100)
        self.main_window.similaritySlider.setToolTip(
            "Determines how closely the AI voice resembles the original. High values may include artifacts.")
        self.main_window.similarityValueLabel = QLabel("80%")
        layout.addWidget(similarityLabel)
        layout.addWidget(self.main_window.similaritySlider)
        layout.addWidget(self.main_window.similarityValueLabel)

        styleLabel = QLabel("Style Exaggeration:")
        self.main_window.styleSlider = QSlider(Qt.Orientation.Horizontal)
        self.main_window.styleSlider.setMinimum(0)
        self.main_window.styleSlider.setMaximum(10)
        self.main_window.styleSlider.setToolTip("Amplifies the original speaker's style. Set to 0 for greater stability.")
        self.main_window.styleValueLabel = QLabel("0")
        layout.addWidget(styleLabel)
        layout.addWidget(self.main_window.styleSlider)
        layout.addWidget(self.main_window.styleValueLabel)

        self.main_window.speakerBoostCheckBox = QCheckBox("Use Speaker Boost")
        self.main_window.speakerBoostCheckBox.setChecked(True)
        self.main_window.speakerBoostCheckBox.setToolTip(
            "Enhances similarity to the original speaker at the cost of greater resources.")
        layout.addWidget(self.main_window.speakerBoostCheckBox)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.main_window.useWav2LipCheckbox = QCheckBox("Lip sync")
        layout.addWidget(self.main_window.useWav2LipCheckbox)
        self.main_window.useWav2LipCheckbox.setVisible(False)

        self.main_window.generateAudioButton = QPushButton('Generate and Apply Audio with AI')

        self.alignspeed = QCheckBox("Align video speed with audio")
        self.alignspeed.setChecked(True)
        layout.addWidget(self.alignspeed)
        layout.addWidget(self.main_window.generateAudioButton)

        voiceSettingsGroup.setLayout(layout)
        return voiceSettingsGroup

    def createGeneratedAudiosUI(self):
        generatedAudiosGroup = QGroupBox("Generated Audios for this Video")
        layout = QVBoxLayout()

        self.main_window.generatedAudiosListWidget = QListWidget()
        self.main_window.generatedAudiosListWidget.setToolTip("List of audios generated for the current video.")
        self.main_window.generatedAudiosListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.main_window.generatedAudiosListWidget)

        buttons_layout = QHBoxLayout()
        applyButton = QPushButton("Apply Selected")
        applyButton.setToolTip("Apply the selected audio to the video.")
        buttons_layout.addWidget(applyButton)

        deleteButton = QPushButton("Delete Selected")
        deleteButton.setToolTip("Delete the selected audio (the file will be deleted).")
        buttons_layout.addWidget(deleteButton)

        layout.addLayout(buttons_layout)
        generatedAudiosGroup.setLayout(layout)
        return generatedAudiosGroup

    def setupMenuBar(self):
        menuBar = self.main_window.menuBar()
        # File Menu
        fileMenu = menuBar.addMenu('&File')

        # Project submenu
        projectMenu = fileMenu.addMenu(QIcon(get_resource("project.png")), "&Progetto")

        self.newProjectAction = QAction(QIcon(get_resource("new_project.png")), '&Nuovo Progetto', self.main_window)
        self.newProjectAction.setShortcut('Ctrl+N')
        self.newProjectAction.setStatusTip('Crea un nuovo progetto')
        projectMenu.addAction(self.newProjectAction)

        self.loadProjectAction = QAction(QIcon(get_resource("load_project.png")), '&Apri Progetto', self.main_window)
        self.loadProjectAction.setShortcut('Ctrl+O')
        self.loadProjectAction.setStatusTip('Apri un progetto esistente')
        projectMenu.addAction(self.loadProjectAction)

        self.saveProjectAction = QAction(QIcon(get_resource("save.png")), '&Salva Progetto', self.main_window)
        self.saveProjectAction.setShortcut('Ctrl+S')
        self.saveProjectAction.setStatusTip('Salva il progetto corrente')
        projectMenu.addAction(self.saveProjectAction)

        self.closeProjectAction = QAction(QIcon(get_resource("close.png")), "Chiudi Progetto", self.main_window)
        self.closeProjectAction.setStatusTip("Chiude il progetto attualmente aperto")
        projectMenu.addAction(self.closeProjectAction)

        fileMenu.addSeparator()

        self.importVideoAction = QAction(QIcon(get_resource("import_video.png")), 'Importa Video nel Progetto', self.main_window)
        self.importVideoAction.setStatusTip('Importa un file video esistente nel progetto corrente')
        fileMenu.addAction(self.importVideoAction)

        self.downloadVideoAction = QAction(QIcon(get_resource("download.png")), "Scarica Video da URL", self.main_window)
        self.downloadVideoAction.setStatusTip("Scarica un video da un URL e lo aggiunge al progetto")
        fileMenu.addAction(self.downloadVideoAction)

        fileMenu.addSeparator()

        self.exportMenu = fileMenu.addMenu(QIcon(get_resource("export.png")), "Esporta")

        self.exportToTxtAction = QAction(QIcon(get_resource("txt.png")), "Esporta in TXT", self.main_window)
        self.exportMenu.addAction(self.exportToTxtAction)

        self.exportToDocxAction = QAction(QIcon(get_resource("word.png")), "Esporta in DOCX", self.main_window)
        self.exportMenu.addAction(self.exportToDocxAction)

        self.exportToPdfAction = QAction(QIcon(get_resource("pdf.png")), "Esporta in PDF", self.main_window)
        self.exportMenu.addAction(self.exportToPdfAction)

        fileMenu.addSeparator()
        self.exitAction = QAction(QIcon(get_resource("exit.png")), 'Esci', self.main_window)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.setStatusTip("Esci dall'applicazione")
        fileMenu.addAction(self.exitAction)

        # Edit Menu
        editMenu = menuBar.addMenu('&Modifica')
        self.undoAction = QAction('Annulla', self.main_window)
        self.undoAction.setShortcut('Ctrl+Z')
        editMenu.addAction(self.undoAction)

        self.redoAction = QAction('Ripristina', self.main_window)
        self.redoAction.setShortcut('Ctrl+Y')
        editMenu.addAction(self.redoAction)

        editMenu.addSeparator()

        self.cutAction = QAction('Taglia', self.main_window)
        self.cutAction.setShortcut('Ctrl+X')
        editMenu.addAction(self.cutAction)

        self.copyAction = QAction('Copia', self.main_window)
        self.copyAction.setShortcut('Ctrl+C')
        editMenu.addAction(self.copyAction)

        self.pasteAction = QAction('Incolla', self.main_window)
        self.pasteAction.setShortcut('Ctrl+V')
        editMenu.addAction(self.pasteAction)

        editMenu.addSeparator()

        self.findActionMenu = QAction('Trova', self.main_window)
        self.findActionMenu.setShortcut('Ctrl+F')
        editMenu.addAction(self.findActionMenu)


        # View Menu
        viewMenu = menuBar.addMenu('&Visualizza')
        self.toggleVideoPlayerDockAction = QAction('Dock Video Player', self.main_window, checkable=True)
        self.toggleVideoPlayerDockAction.setChecked(True)
        viewMenu.addAction(self.toggleVideoPlayerDockAction)

        self.toggleTranscriptionDockAction = QAction('Dock Trascrizione', self.main_window, checkable=True)
        self.toggleTranscriptionDockAction.setChecked(True)
        viewMenu.addAction(self.toggleTranscriptionDockAction)

        self.toggleEditingDockAction = QAction('Dock Editing', self.main_window, checkable=True)
        self.toggleEditingDockAction.setChecked(True)
        viewMenu.addAction(self.toggleEditingDockAction)

        self.toggleRecordingDockAction = QAction('Dock Registrazione', self.main_window, checkable=True)
        self.toggleRecordingDockAction.setChecked(True)
        viewMenu.addAction(self.toggleRecordingDockAction)

        self.toggleAudioDockAction = QAction('Dock Audio', self.main_window, checkable=True)
        self.toggleAudioDockAction.setChecked(True)
        viewMenu.addAction(self.toggleAudioDockAction)

        self.toggleVideoPlayerOutputDockAction = QAction('Dock Video Player Output', self.main_window, checkable=True)
        self.toggleVideoPlayerOutputDockAction.setChecked(True)
        viewMenu.addAction(self.toggleVideoPlayerOutputDockAction)

        self.toggleProjectDockAction = QAction('Dock Progetto', self.main_window, checkable=True)
        self.toggleProjectDockAction.setChecked(True)
        viewMenu.addAction(self.toggleProjectDockAction)

        self.toggleVideoNotesDockAction = QAction('Dock Note Video', self.main_window, checkable=True)
        self.toggleVideoNotesDockAction.setChecked(True)
        viewMenu.addAction(self.toggleVideoNotesDockAction)

        self.toggleInfoExtractionDockAction = QAction('Dock Estrazione Info', self.main_window, checkable=True)
        self.toggleInfoExtractionDockAction.setChecked(True)
        viewMenu.addAction(self.toggleInfoExtractionDockAction)

        self.toggleChatDockAction = QAction('Dock Chat', self.main_window, checkable=True)
        self.toggleChatDockAction.setChecked(True)
        viewMenu.addAction(self.toggleChatDockAction)


        # Layout Menu
        self.layoutMenu = menuBar.addMenu('&Layout')
        self.saveLayoutAction = QAction('Salva Layout', self.main_window)
        self.layoutMenu.addAction(self.saveLayoutAction)
        # self.loadLayoutAction = QAction('Carica Layout', self.main_window)
        # self.layoutMenu.addAction(self.loadLayoutAction)
        self.resetLayoutAction = QAction('Ripristina Layout', self.main_window)
        self.layoutMenu.addAction(self.resetLayoutAction)


        # Tools Menu
        toolsMenu = menuBar.addMenu('&Strumenti')
        self.settingsActionMenu = QAction('Impostazioni', self.main_window)
        toolsMenu.addAction(self.settingsActionMenu)

        # Help Menu
        helpMenu = menuBar.addMenu('&Aiuto')
        self.aboutAction = QAction('Informazioni', self.main_window)
        helpMenu.addAction(self.aboutAction)
