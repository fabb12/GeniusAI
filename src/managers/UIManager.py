from PyQt6.QtWidgets import QMainWindow

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QCheckBox, QRadioButton, QLineEdit, QHBoxLayout, QGroupBox, QComboBox, QSpinBox, QFileDialog, QMessageBox, QSizePolicy, QProgressDialog, QToolBar, QSlider, QProgressBar, QTabWidget, QDialog, QTextEdit, QInputDialog, QDoubleSpinBox, QFrame, QStatusBar, QListWidget, QListWidgetItem, QMenu, QButtonGroup, QDialogButtonBox
from PyQt6.QtCore import Qt, QUrl, QEvent, QTimer, QPoint, QTime, QSettings, QBuffer, QIODevice
import os
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QImage, QPixmap, QFont, QColor, QTextCharFormat, QTextCursor, QTextDocument
from pyqtgraph.dockarea import DockArea
from src.ui.CustomDock import CustomDock
from src.ui.VideoOverlay import VideoOverlay
from src.ui.CustVideoWidget import CropVideoWidget
from src.ui.CustomSlider import CustomSlider
from src.ui.CustomTextEdit import CustomTextEdit
from src.ui.ProjectDock import ProjectDock
from src.ui.ChatDock import ChatDock
from src.config import get_resource, HIGHLIGHT_COLORS
from src.managers.SettingsManager import DockSettingsManager


class UIManager:
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window

    def setup_ui(self):
        mw = self.main_window
        mw.setWindowIcon(QIcon(get_resource('eye.png')))

        area = DockArea()
        mw.setCentralWidget(area)
        mw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.setToolTip("Area principale dei dock")
        mw.videoPlayerDock = CustomDock("Video Player Input", closable=True)
        mw.videoPlayerDock.setStyleSheet(mw.styleSheet())
        mw.videoPlayerDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoPlayerDock.setToolTip("Dock per la riproduzione video di input")
        area.addDock(mw.videoPlayerDock, 'left')

        mw.videoPlayerOutput = CustomDock("Video Player Output", closable=True)
        mw.videoPlayerOutput.setStyleSheet(mw.styleSheet())
        mw.videoPlayerOutput.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoPlayerOutput.setToolTip("Dock per la riproduzione video di output")
        area.addDock(mw.videoPlayerOutput, 'left')

        mw.transcriptionDock = CustomDock("Trascrizione e Sintesi Audio", closable=True)
        mw.transcriptionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.transcriptionDock.setStyleSheet(mw.styleSheet())
        mw.transcriptionDock.setToolTip("Dock per la trascrizione e sintesi audio")
        area.addDock(mw.transcriptionDock, 'right')

        mw.editingDock = CustomDock("Generazione Audio AI", closable=True)
        mw.editingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.editingDock.setStyleSheet(mw.styleSheet())
        mw.editingDock.setToolTip("Dock per la generazione audio assistita da AI")
        area.addDock(mw.editingDock, 'right')

        mw.recordingDock = mw.createRecordingDock()
        mw.recordingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.recordingDock.setStyleSheet(mw.styleSheet())
        mw.recordingDock.setToolTip("Dock per la registrazione")
        area.addDock(mw.recordingDock, 'right')

        mw.audioDock = mw.createAudioDock()
        mw.audioDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.audioDock.setStyleSheet(mw.styleSheet())
        mw.audioDock.setToolTip("Dock per la gestione Audio/Video")
        area.addDock(mw.audioDock, 'left')

        mw.projectDock = ProjectDock()
        mw.projectDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.projectDock.setStyleSheet(mw.styleSheet())
        area.addDock(mw.projectDock, 'right', mw.transcriptionDock)
        mw.projectDock.clip_selected.connect(mw.load_project_clip)
        mw.projectDock.open_folder_requested.connect(mw.open_project_folder)
        mw.projectDock.delete_clip_requested.connect(mw.delete_project_clip)
        mw.projectDock.project_clips_folder_changed.connect(mw.sync_project_clips_folder)
        mw.projectDock.open_in_input_player_requested.connect(mw.loadVideo)
        mw.projectDock.open_in_output_player_requested.connect(mw.loadVideoOutput)
        mw.projectDock.rename_clip_requested.connect(mw.rename_project_clip)
        mw.projectDock.rename_from_summary_requested.connect(mw.rename_clip_from_summary)
        mw.projectDock.relink_clip_requested.connect(mw.relink_project_clip)
        mw.projectDock.batch_transcribe_requested.connect(mw.start_batch_transcription)
        mw.projectDock.batch_summarize_requested.connect(mw.start_batch_summarization)
        mw.projectDock.separate_audio_requested.connect(mw.separate_audio_from_video)

        mw.videoNotesDock = CustomDock("Note Video", closable=True)
        mw.videoNotesDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoNotesDock.setStyleSheet(mw.styleSheet())
        mw.videoNotesDock.setToolTip("Dock per le note video")
        area.addDock(mw.videoNotesDock, 'bottom', mw.transcriptionDock)
        mw.createVideoNotesDock()


        mw.infoExtractionDock = CustomDock("Estrazione Info Video", closable=True)
        mw.infoExtractionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.infoExtractionDock.setToolTip("Dock per l'estrazione di informazioni da video")
        area.addDock(mw.infoExtractionDock, 'right')
        mw.createInfoExtractionDock()

        mw.chatDock = ChatDock()
        mw.chatDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.addDock(mw.chatDock, 'right', mw.transcriptionDock)
        mw.chatDock.sendMessage.connect(mw.handle_chat_message)
        mw.chatDock.history_text_edit.timestampDoubleClicked.connect(mw.sincronizza_video)

        # ---------------------
        # PLAYER INPUT
        # ---------------------
        mw.videoContainer = QWidget()
        mw.videoContainer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoContainer.setToolTip("Video container for panning and zooming")

        mw.videoCropWidget = CropVideoWidget(parent=mw.videoContainer)
        mw.videoCropWidget.setAcceptDrops(True)
        mw.videoCropWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoCropWidget.setToolTip("Area di visualizzazione e ritaglio video input")
        mw.player.setVideoOutput(mw.videoCropWidget)
        mw.videoCropWidget.spacePressed.connect(mw.togglePlayPause)

        # Aggiungi un QLabel per l'immagine "Solo audio"
        mw.audioOnlyLabel = QLabel(mw.videoContainer)
        mw.audioOnlyLabel.setPixmap(QPixmap(get_resource("audio_only.png")).scaled(
            mw.videoContainer.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        mw.audioOnlyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mw.audioOnlyLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.audioOnlyLabel.setVisible(False) # Inizialmente nascosto

        mw.videoOverlay = VideoOverlay(mw, parent=mw.videoContainer)
        mw.videoOverlay.show()
        mw.videoOverlay.raise_()

        mw.zoom_level = 1.0
        mw.is_panning = False
        mw.last_mouse_position = QPoint()

        mw.videoOverlay.panned.connect(mw.handle_pan)
        mw.videoOverlay.zoomed.connect(mw.handle_zoom)
        mw.videoOverlay.view_reset.connect(mw.reset_view)
        mw.videoOverlay.installEventFilter(mw)

        mw.videoSlider = CustomSlider(Qt.Orientation.Horizontal)
        mw.videoSlider.setToolTip("Slider per navigare all'interno del video input")

        mw.fileNameLabel = QLabel("Nessun video caricato")
        mw.fileNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mw.fileNameLabel.setStyleSheet("QLabel { font-weight: bold; }")
        mw.fileNameLabel.setToolTip("Nome del file video attualmente caricato nel Player Input")

        mw.playButton = QPushButton('')
        mw.playButton.setIcon(QIcon(get_resource("play.png")))
        mw.playButton.setToolTip("Riproduci/Pausa il video input")
        mw.playButton.clicked.connect(mw.togglePlayPause)

        mw.stopButton = QPushButton('')
        mw.stopButton.setIcon(QIcon(get_resource("stop.png")))
        mw.stopButton.setToolTip("Ferma la riproduzione del video input")

        mw.setStartBookmarkButton = QPushButton('')
        mw.setStartBookmarkButton.setIcon(QIcon(get_resource("bookmark_1.png")))
        mw.setStartBookmarkButton.setToolTip("Imposta segnalibro di inizio sul video input")

        mw.setEndBookmarkButton = QPushButton('')
        mw.setEndBookmarkButton.setIcon(QIcon(get_resource("bookmark_2.png")))
        mw.setEndBookmarkButton.setToolTip("Imposta segnalibro di fine sul video input")

        mw.clearBookmarksButton = QPushButton('')
        mw.clearBookmarksButton.setIcon(QIcon(get_resource("reset.png")))
        mw.clearBookmarksButton.setToolTip("Cancella tutti i segnalibri")

        mw.cutButton = QPushButton('')
        mw.cutButton.setIcon(QIcon(get_resource("taglia.png")))
        mw.cutButton.setToolTip("Taglia il video tra i segnalibri impostati")

        mw.cropButton = QPushButton('')
        mw.cropButton.setIcon(QIcon(get_resource("crop.png")))
        mw.cropButton.setToolTip("Apre la finestra di dialogo per ritagliare il video")


        mw.rewindButton = QPushButton('<< 5s')
        mw.rewindButton.setIcon(QIcon(get_resource("rewind.png")))
        mw.rewindButton.setToolTip("Riavvolgi il video di 5 secondi")

        mw.frameBackwardButton = QPushButton('|<')
        mw.frameBackwardButton.setToolTip("Indietro di un frame")

        mw.forwardButton = QPushButton('>> 5s')
        mw.forwardButton.setIcon(QIcon(get_resource("forward.png")))
        mw.forwardButton.setToolTip("Avanza il video di 5 secondi")

        mw.frameForwardButton = QPushButton('>|')
        mw.frameForwardButton.setToolTip("Avanti di un frame")

        mw.deleteButton = QPushButton('')
        mw.deleteButton.setIcon(QIcon(get_resource("trash-bin.png")))
        mw.deleteButton.setToolTip("Cancella la parte selezionata del video")

        mw.transferToOutputButton = QPushButton('')
        mw.transferToOutputButton.setIcon(QIcon(get_resource("change.png")))
        mw.transferToOutputButton.setToolTip("Sposta il video dall'input all'output")
        mw.transferToOutputButton.clicked.connect(
            lambda: mw.loadVideoOutput(mw.videoPathLineEdit) if mw.videoPathLineEdit else None
        )

        mw.stopButton.clicked.connect(mw.stopVideo)
        mw.setStartBookmarkButton.clicked.connect(mw.setStartBookmark)
        mw.setEndBookmarkButton.clicked.connect(mw.setEndBookmark)
        mw.clearBookmarksButton.clicked.connect(mw.clearBookmarks)
        mw.cutButton.clicked.connect(mw.bookmark_manager.cut_all_bookmarks)
        mw.cropButton.clicked.connect(mw.open_crop_dialog)
        mw.rewindButton.clicked.connect(mw.rewind5Seconds)
        mw.forwardButton.clicked.connect(mw.forward5Seconds)
        mw.frameBackwardButton.clicked.connect(mw.frameBackward)
        mw.frameForwardButton.clicked.connect(mw.frameForward)
        mw.deleteButton.clicked.connect(mw.bookmark_manager.delete_all_bookmarks)

        mw.totalTimeLabel = QLabel('/ 00:00:00:000')
        mw.totalTimeLabel.setToolTip("Mostra la durata totale del video input")

        # ---------------------
        # PLAYER OUTPUT
        # ---------------------
        mw.videoOutputWidget = CropVideoWidget()
        mw.videoOutputWidget.setAcceptDrops(True)
        mw.videoOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoOutputWidget.setToolTip("Area di visualizzazione e ritaglio video output")
        mw.videoOutputWidget.spacePressed.connect(mw.togglePlayPauseOutput)

        mw.playerOutput.setAudioOutput(mw.audioOutputOutput)
        mw.playerOutput.setVideoOutput(mw.videoOutputWidget)


        mw.playButtonOutput = QPushButton('')
        mw.playButtonOutput.setIcon(QIcon(get_resource("play.png")))
        mw.playButtonOutput.setToolTip("Riproduci/Pausa il video output")
        mw.playButtonOutput.clicked.connect(mw.togglePlayPauseOutput)

        stopButtonOutput = QPushButton('')
        stopButtonOutput.setIcon(QIcon(get_resource("stop.png")))
        stopButtonOutput.setToolTip("Ferma la riproduzione del video output")

        changeButtonOutput = QPushButton('')
        changeButtonOutput.setIcon(QIcon(get_resource("change.png")))
        changeButtonOutput.setToolTip("Sposta il video output nel Video Player Input")
        changeButtonOutput.clicked.connect(
            lambda: mw.loadVideo(mw.videoPathLineOutputEdit, os.path.basename(mw.videoPathLineOutputEdit))
        )

        syncPositionButton = QPushButton('Sync Position')
        syncPositionButton.setIcon(QIcon(get_resource("sync.png")))
        syncPositionButton.setToolTip('Sincronizza la posizione del video output con quella del video source')
        syncPositionButton.clicked.connect(mw.syncOutputWithSourcePosition)

        stopButtonOutput.clicked.connect(lambda: mw.playerOutput.stop())

        playbackControlLayoutOutput = QHBoxLayout()
        playbackControlLayoutOutput.addWidget(mw.playButtonOutput)
        playbackControlLayoutOutput.addWidget(stopButtonOutput)
        playbackControlLayoutOutput.addWidget(changeButtonOutput)
        playbackControlLayoutOutput.addWidget(syncPositionButton)

        videoSliderOutput = CustomSlider(Qt.Orientation.Horizontal)
        videoSliderOutput.setRange(0, 1000)  # Range di esempio
        videoSliderOutput.setToolTip("Slider per navigare all'interno del video output")
        videoSliderOutput.sliderMoved.connect(lambda position: mw.playerOutput.setPosition(position))

        mw.currentTimeLabelOutput = QLabel('00:00')
        mw.currentTimeLabelOutput.setToolTip("Mostra il tempo corrente del video output")
        mw.totalTimeLabelOutput = QLabel('/ 00:00')
        mw.totalTimeLabelOutput.setToolTip("Mostra la durata totale del video output")
        timecodeLayoutOutput = QHBoxLayout()
        timecodeLayoutOutput.addWidget(mw.currentTimeLabelOutput)
        timecodeLayoutOutput.addWidget(mw.totalTimeLabelOutput)

        mw.timecodeEnabled = False

        mw.fileNameLabelOutput = QLabel("Nessun video caricato")
        mw.fileNameLabelOutput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mw.fileNameLabelOutput.setStyleSheet("QLabel { font-weight: bold; }")
        mw.fileNameLabelOutput.setToolTip("Nome del file video attualmente caricato nel Player Output")

        videoOutputLayout = QVBoxLayout()
        videoOutputLayout.addWidget(mw.fileNameLabelOutput)
        videoOutputLayout.addWidget(mw.videoOutputWidget)
        videoOutputLayout.addLayout(timecodeLayoutOutput)
        videoOutputLayout.addWidget(videoSliderOutput)

        # Speed control for output player
        speedLayoutOutput = QHBoxLayout()
        speedLayoutOutput.addWidget(QLabel("Velocità:"))
        mw.speedSpinBoxOutput = QDoubleSpinBox()
        mw.speedSpinBoxOutput.setRange(-20.0, 20.0)
        mw.speedSpinBoxOutput.setSuffix("x")
        mw.speedSpinBoxOutput.setValue(1.0)
        mw.speedSpinBoxOutput.setSingleStep(0.1)
        mw.speedSpinBoxOutput.valueChanged.connect(mw.setPlaybackRateOutput)
        speedLayoutOutput.addWidget(mw.speedSpinBoxOutput)
        videoOutputLayout.addLayout(speedLayoutOutput)

        videoOutputLayout.addLayout(playbackControlLayoutOutput)

        mw.playerOutput.durationChanged.connect(mw.updateDurationOutput)
        mw.playerOutput.positionChanged.connect(mw.updateTimeCodeOutput)
        mw.playerOutput.playbackStateChanged.connect(mw.updatePlayButtonIconOutput)

        videoPlayerOutputWidget = QWidget()
        videoPlayerOutputWidget.setLayout(videoOutputLayout)
        videoPlayerOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mw.videoPlayerOutput.addWidget(videoPlayerOutputWidget)

        mw.playerOutput.durationChanged.connect(lambda duration: videoSliderOutput.setRange(0, duration))
        mw.playerOutput.positionChanged.connect(lambda position: videoSliderOutput.setValue(position))

        # Pulsante per trascrivere il video
        mw.transcribeButton = QPushButton('Trascrivi Video')
        mw.transcribeButton.setToolTip("Avvia la trascrizione del video attualmente caricato")
        mw.transcribeButton.clicked.connect(mw.transcribeVideo)

        # Layout di playback del Player Input
        playbackControlLayout = QHBoxLayout()
        playbackControlLayout.addWidget(mw.rewindButton)
        playbackControlLayout.addWidget(mw.frameBackwardButton)
        playbackControlLayout.addWidget(mw.playButton)
        playbackControlLayout.addWidget(mw.stopButton)
        playbackControlLayout.addWidget(mw.forwardButton)
        playbackControlLayout.addWidget(mw.frameForwardButton)
        playbackControlLayout.addWidget(mw.setStartBookmarkButton)
        playbackControlLayout.addWidget(mw.setEndBookmarkButton)
        playbackControlLayout.addWidget(mw.cutButton)
        playbackControlLayout.addWidget(mw.cropButton)
        playbackControlLayout.addWidget(mw.deleteButton)
        playbackControlLayout.addWidget(mw.transferToOutputButton)

        # Layout principale del Player Input
        videoPlayerLayout = QVBoxLayout()
        videoPlayerLayout.addWidget(mw.fileNameLabel)
        videoPlayerLayout.addWidget(mw.videoContainer)
        # Timecode input / display
        timecode_layout = QHBoxLayout()
        mw.timecodeInput = QLineEdit()
        mw.timecodeInput.setToolTip("Tempo corrente / Vai al timecode (Premi Invio o clicca Go)")
        mw.timecodeInput.returnPressed.connect(mw.goToTimecode) # Connect Enter key
        timecode_layout.addWidget(mw.timecodeInput)
        timecode_layout.addWidget(mw.totalTimeLabel)

        go_button = QPushButton("Go")
        go_button.setToolTip("Vai al timecode specificato")
        go_button.clicked.connect(mw.goToTimecode)
        timecode_layout.addWidget(go_button)
        videoPlayerLayout.addLayout(timecode_layout)

        videoPlayerLayout.addWidget(mw.videoSlider)

        # Speed control
        speedLayout = QHBoxLayout()
        speedLayout.addWidget(QLabel("Velocità:"))
        mw.speedSpinBox = QDoubleSpinBox()
        mw.speedSpinBox.setRange(-20.0, 20.0)
        mw.speedSpinBox.setSuffix("x")
        mw.speedSpinBox.setValue(1.0)
        mw.speedSpinBox.setSingleStep(0.1)
        mw.speedSpinBox.valueChanged.connect(mw.setPlaybackRateInput)
        speedLayout.addWidget(mw.speedSpinBox)

        mw.reverseButton = QPushButton('')
        mw.reverseButton.setIcon(QIcon(get_resource("rewind_play.png")))
        mw.reverseButton.setToolTip("Inverti riproduzione audio/video")
        mw.reverseButton.clicked.connect(mw.toggleReversePlayback)
        mw.reverseButton.setFixedSize(32, 32)
        speedLayout.addWidget(mw.reverseButton)

        videoPlayerLayout.addLayout(speedLayout)

        videoPlayerLayout.addLayout(playbackControlLayout)

        # Controlli volume input e velocità
        mw.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        mw.volumeSlider.setRange(0, 100)
        mw.volumeSlider.setValue(int(mw.audioOutput.volume() * 100))
        mw.volumeSlider.setToolTip("Regola il volume dell'audio input")
        mw.volumeSlider.valueChanged.connect(mw.setVolume)

        mw.volumeSliderOutput = QSlider(Qt.Orientation.Horizontal)
        mw.volumeSliderOutput.setRange(0, 100)
        mw.volumeSliderOutput.setValue(int(mw.audioOutputOutput.volume() * 100))
        mw.volumeSliderOutput.setToolTip("Regola il volume dell'audio output")
        mw.volumeSliderOutput.valueChanged.connect(mw.setVolumeOutput)

        videoOutputLayout.addWidget(QLabel("Volume"))
        videoOutputLayout.addWidget(mw.volumeSliderOutput)

        videoPlayerWidget = QWidget()
        videoPlayerWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        videoPlayerWidget.setLayout(videoPlayerLayout)
        mw.videoPlayerDock.addWidget(videoPlayerWidget)

        # =================================================================================
        # DOCK DI TRASCRIZIONE E RIASSUNTO (CON TAB WIDGET)
        # =================================================================================
        mw.transcriptionTabWidget = QTabWidget()
        mw.transcriptionTabWidget.setToolTip("Gestisci la trascrizione e i riassunti generati.")

        # --- Tab Trascrizione ---
        transcription_tab = QWidget()
        transcription_layout = QVBoxLayout(transcription_tab)

        trans_controls_group = QGroupBox("Controlli Trascrizione")
        main_controls_layout = QVBoxLayout(trans_controls_group)

        # --- Riga 1: Lingua ---
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Seleziona lingua video:"))
        mw.languageComboBox = QComboBox()
        mw.languageComboBox.addItems(["Rilevamento Automatico", "Italiano", "Inglese", "Francese", "Spagnolo", "Tedesco"])
        mw.languageComboBox.setItemData(0, "auto")
        mw.languageComboBox.setItemData(1, "it")
        mw.languageComboBox.setItemData(2, "en")
        mw.languageComboBox.setItemData(3, "fr")
        mw.languageComboBox.setItemData(4, "es")
        mw.languageComboBox.setItemData(5, "de")
        language_layout.addWidget(mw.languageComboBox)
        language_layout.addStretch()
        mw.transcriptionLanguageLabel = QLabel("Lingua rilevata: N/A")
        language_layout.addWidget(mw.transcriptionLanguageLabel)
        main_controls_layout.addLayout(language_layout)

        # Translation controls
        translation_layout = QHBoxLayout()
        translation_layout.addWidget(QLabel("Traduci in:"))
        mw.translationComboBox = QComboBox()
        supported_langs = mw.translation_service.get_supported_languages()
        for code, name in supported_langs.items():
            mw.translationComboBox.addItem(name.title(), code)
        mw.translationComboBox.setCurrentText("English")
        translation_layout.addWidget(mw.translationComboBox)
        mw.translateTranscriptionButton = QPushButton("Traduci Trascrizione")
        mw.translateTranscriptionButton.clicked.connect(mw.translate_transcription)
        translation_layout.addWidget(mw.translateTranscriptionButton)
        main_controls_layout.addLayout(translation_layout)

        # --- Riga 2: Modalità di Trascrizione (Online/Offline) ---
        mode_layout = QHBoxLayout()
        mw.onlineModeCheckbox = QCheckBox("Online (Google)")
        mw.offlineModeCheckbox = QCheckBox("Offline (Whisper)")
        mw.transcriptionModeGroup = QButtonGroup(mw)
        mw.transcriptionModeGroup.addButton(mw.onlineModeCheckbox)
        mw.transcriptionModeGroup.addButton(mw.offlineModeCheckbox)
        mw.transcriptionModeGroup.setExclusive(True)
        mw.offlineModeCheckbox.setChecked(True) # Default to offline
        mode_layout.addWidget(QLabel("Modalità:"))
        mode_layout.addWidget(mw.onlineModeCheckbox)
        mode_layout.addWidget(mw.offlineModeCheckbox)
        mode_layout.addStretch()
        main_controls_layout.addLayout(mode_layout)

        # --- Riga 4: Gruppi di Controlli Affiancati ---
        groups_layout = QHBoxLayout()

        # --- Gruppo 1: Azioni sui File ---
        file_actions_group = QGroupBox("File")
        file_actions_layout = QHBoxLayout(file_actions_group)

        mw.transcribeButton = QPushButton('')
        mw.transcribeButton.setIcon(QIcon(get_resource("script.png")))
        mw.transcribeButton.setFixedSize(32, 32)
        mw.transcribeButton.setToolTip("Trascrivi Video")
        mw.transcribeButton.clicked.connect(mw.transcribeVideo)
        file_actions_layout.addWidget(mw.transcribeButton)

        mw.loadButton = QPushButton('')
        mw.loadButton.setIcon(QIcon(get_resource("load.png")))
        mw.loadButton.setFixedSize(32, 32)
        mw.loadButton.setToolTip("Carica Testo")
        mw.loadButton.clicked.connect(mw.loadText)
        file_actions_layout.addWidget(mw.loadButton)

        mw.saveTranscriptionButton = QPushButton('')
        mw.saveTranscriptionButton.setIcon(QIcon(get_resource("save.png")))
        mw.saveTranscriptionButton.setFixedSize(32, 32)
        mw.saveTranscriptionButton.setToolTip("Salva Trascrizione nel JSON associato")
        mw.saveTranscriptionButton.clicked.connect(mw.save_transcription_to_json)
        file_actions_layout.addWidget(mw.saveTranscriptionButton)

        mw.resetButton = QPushButton('')
        mw.resetButton.setIcon(QIcon(get_resource("reset.png")))
        mw.resetButton.setFixedSize(32, 32)
        mw.resetButton.setToolTip("Pulisci")
        mw.resetButton.clicked.connect(lambda: mw.singleTranscriptionTextArea.clear())
        file_actions_layout.addWidget(mw.resetButton)

        mw.fixTranscriptionButton = QPushButton('')
        mw.fixTranscriptionButton.setIcon(QIcon(get_resource("text_fix.png")))
        mw.fixTranscriptionButton.setFixedSize(32, 32)
        mw.fixTranscriptionButton.setToolTip("Correggi Testo Trascrizione")
        mw.fixTranscriptionButton.clicked.connect(mw.fixTranscriptionWithAI)
        file_actions_layout.addWidget(mw.fixTranscriptionButton)

        # Pulsante per incollare nella tab Audio AI
        mw.pasteToAudioAIButton = QPushButton('')
        mw.pasteToAudioAIButton.setIcon(QIcon(get_resource("paste.png")))
        mw.pasteToAudioAIButton.setFixedSize(32, 32)
        mw.pasteToAudioAIButton.setToolTip("Incolla nella tab Audio AI")
        mw.pasteToAudioAIButton.clicked.connect(lambda: mw.paste_to_audio_ai(mw.singleTranscriptionTextArea))
        file_actions_layout.addWidget(mw.pasteToAudioAIButton)

        search_button = QPushButton('')
        search_button.setIcon(QIcon(get_resource("find.png")))
        search_button.setFixedSize(32, 32)
        search_button.setToolTip("Apre il dialogo di ricerca per il testo attivo (Ctrl+F)")
        search_button.clicked.connect(mw.open_search_dialog)
        file_actions_layout.addWidget(search_button)

        groups_layout.addWidget(file_actions_group)

        # --- Gruppo 2: Strumenti ---
        tools_group = QGroupBox("Strumenti")
        tools_grid_layout = QGridLayout(tools_group)

        mw.timecodeCheckbox = QCheckBox("Inserisci timecode audio")
        mw.timecodeCheckbox.toggled.connect(mw.handleTimecodeToggle)
        tools_grid_layout.addWidget(mw.timecodeCheckbox, 0, 0)

        mw.syncButton = QPushButton('')
        mw.syncButton.setIcon(QIcon(get_resource("sync.png")))
        mw.syncButton.setFixedSize(32, 32)
        mw.syncButton.setToolTip("Sincronizza Video da Timecode Vicino")
        mw.syncButton.clicked.connect(mw.sync_video_to_transcription)
        tools_grid_layout.addWidget(mw.syncButton, 0, 1)

        mw.pauseTimeEdit = QLineEdit()
        mw.pauseTimeEdit.setPlaceholderText("Durata pausa (es. 1.0s)")
        tools_grid_layout.addWidget(mw.pauseTimeEdit, 1, 0)

        mw.insertPauseButton = QPushButton("Inserisci Pausa")
        mw.insertPauseButton.clicked.connect(mw.insertPause)
        tools_grid_layout.addWidget(mw.insertPauseButton, 1, 1)

        mw.saveAudioAIButton = QPushButton('')
        mw.saveAudioAIButton.setIcon(QIcon(get_resource("save.png")))
        mw.saveAudioAIButton.setFixedSize(32, 32)
        mw.saveAudioAIButton.setToolTip("Salva Testo Audio AI nel JSON associato")
        mw.saveAudioAIButton.clicked.connect(mw.save_audio_ai_to_json)
        tools_grid_layout.addWidget(mw.saveAudioAIButton, 0, 2)

        mw.generateGuideButton = QPushButton('')
        mw.generateGuideButton.setIcon(QIcon(get_resource("script.png")))
        mw.generateGuideButton.setFixedSize(32, 32)
        mw.generateGuideButton.setToolTip("Genera Guida Operativa dal Video")
        mw.generateGuideButton.clicked.connect(mw.generate_operational_guide)
        tools_grid_layout.addWidget(mw.generateGuideButton, 0, 3)

        # groups_layout.addWidget(tools_group)

        # LA SEGUENTE RIGA È STATA RIMOSSA PER PERMETTERE L'ESPANSIONE
        # groups_layout.addStretch()

        main_controls_layout.addLayout(groups_layout)

        # --- Riga 3: Toggle per la visualizzazione ---
        view_options_layout = QHBoxLayout()
        mw.transcriptionViewToggle = QCheckBox("Mostra testo corretto")
        mw.transcriptionViewToggle.setToolTip("Attiva/Disattiva la visualizzazione del testo corretto.")
        mw.transcriptionViewToggle.setEnabled(False) # Disabilitato di default
        mw.transcriptionViewToggle.toggled.connect(mw.toggle_transcription_view)
        view_options_layout.addWidget(mw.transcriptionViewToggle)
        view_options_layout.addStretch()
        main_controls_layout.addLayout(view_options_layout)

        transcription_layout.addWidget(trans_controls_group)

        #--------------------

        # Crea il QTabWidget annidato per le trascrizioni
        mw.transcriptionTabs = QTabWidget()
        mw.transcriptionTabs.setToolTip("Visualizza la trascrizione singola o multipla.")

        # Tab per la Trascrizione Singola
        mw.singleTranscriptionTextArea = CustomTextEdit(mw)
        mw.singleTranscriptionTextArea.setPlaceholderText("La trascrizione del video corrente apparirà qui...")
        mw.singleTranscriptionTextArea.textChanged.connect(mw.handleTextChange)
        mw.singleTranscriptionTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.singleTranscriptionTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.singleTranscriptionTextArea, timestamp, pos)
        )
        mw.transcriptionTabs.addTab(mw.singleTranscriptionTextArea, "Trascrizione Singola")

        # Tab per la Trascrizione Multipla
        mw.batchTranscriptionTextArea = CustomTextEdit(mw)
        mw.batchTranscriptionTextArea.setPlaceholderText("I risultati della trascrizione multipla appariranno qui...")
        mw.batchTranscriptionTextArea.setReadOnly(True) # Inizialmente in sola lettura
        mw.batchTranscriptionTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.transcriptionTabs.addTab(mw.batchTranscriptionTextArea, "Trascrizione Multipla")

        transcription_layout.addWidget(mw.transcriptionTabs)

        mw.transcriptionTabWidget.addTab(transcription_tab, "Trascrizione")

        # --- Tab Audio AI ---
        mw.audio_ai_tab = QWidget()
        audio_ai_layout = QVBoxLayout(mw.audio_ai_tab)

        # Sposta il gruppo "Strumenti" qui
        audio_ai_layout.addWidget(tools_group)

        mw.audioAiTextArea = CustomTextEdit(mw)
        mw.audioAiTextArea.setPlaceholderText("Incolla qui il testo da usare per la generazione audio o altre funzioni AI...")
        audio_ai_layout.addWidget(mw.audioAiTextArea)

        # --- Tab Riassunto ---
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)

        summary_controls_group = QGroupBox("Controlli Riassunto e AI")
        summary_controls_layout = QVBoxLayout(summary_controls_group)

        # Layout orizzontale per tutti i pulsanti e controlli in linea
        top_controls_layout = QHBoxLayout()

        # Pulsanti Azioni AI
        summarize_button = QPushButton('')
        summarize_button.setIcon(QIcon(get_resource("text_sum.png")))
        summarize_button.setFixedSize(32, 32)
        summarize_button.setToolTip("Riassumi Testo")
        summarize_button.clicked.connect(mw.processTextWithAI)
        top_controls_layout.addWidget(summarize_button)

        #fix_text_button = QPushButton('')
        #fix_text_button.setIcon(QIcon(get_resource("text_fix.png")))
        #fix_text_button.setFixedSize(32, 32)
        #fix_text_button.setToolTip("Correggi Testo")
        #fix_text_button.clicked.connect(mw.fixTextWithAI)
        #top_controls_layout.addWidget(fix_text_button)

        summarize_meeting_button = QPushButton('')
        summarize_meeting_button.setIcon(QIcon(get_resource("meet_sum.png")))
        summarize_meeting_button.setFixedSize(32, 32)
        summarize_meeting_button.setToolTip("Riassumi Riunione")
        summarize_meeting_button.clicked.connect(mw.summarizeMeeting)
        top_controls_layout.addWidget(summarize_meeting_button)

        mw.generatePptxActionBtn = QPushButton('')
        mw.generatePptxActionBtn.setIcon(QIcon(get_resource("powerpoint.png")))
        mw.generatePptxActionBtn.setFixedSize(32, 32)
        mw.generatePptxActionBtn.setToolTip("Genera Presentazione")
        mw.generatePptxActionBtn.clicked.connect(mw.openPptxDialog)
        top_controls_layout.addWidget(mw.generatePptxActionBtn)

        mw.highlightTextButton = QPushButton('')
        mw.highlightTextButton.setIcon(QIcon(get_resource("key.png")))
        mw.highlightTextButton.setFixedSize(32, 32)
        mw.highlightTextButton.setToolTip("Evidenzia Testo Selezionato")
        mw.highlightTextButton.clicked.connect(mw.highlight_selected_text)
        top_controls_layout.addWidget(mw.highlightTextButton)

        # Pulsante per incollare il riassunto nella tab Audio AI
        mw.pasteSummaryToAudioAIButton = QPushButton('')
        mw.pasteSummaryToAudioAIButton.setIcon(QIcon(get_resource("paste.png")))
        mw.pasteSummaryToAudioAIButton.setFixedSize(32, 32)
        mw.pasteSummaryToAudioAIButton.setToolTip("Incolla riassunto nella tab Audio AI")
        mw.pasteSummaryToAudioAIButton.clicked.connect(lambda: mw.paste_to_audio_ai(mw.get_current_summary_text_area()))
        top_controls_layout.addWidget(mw.pasteSummaryToAudioAIButton)

        mw.saveSummaryButton = QPushButton('')
        mw.saveSummaryButton.setIcon(QIcon(get_resource("save.png")))
        mw.saveSummaryButton.setFixedSize(32, 32)
        mw.saveSummaryButton.setToolTip("Salva Riassunto nel JSON associato")
        mw.saveSummaryButton.clicked.connect(mw.save_summary_to_json)
        top_controls_layout.addWidget(mw.saveSummaryButton)

        # Separatore
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        top_controls_layout.addWidget(separator)

        # Controlli di estrazione
        mw.integraInfoButton = QPushButton("")
        mw.integraInfoButton.setIcon(QIcon(get_resource("frame_get.png")))
        mw.integraInfoButton.setFixedSize(32, 32)
        mw.integraInfoButton.setToolTip("Integra info dal video nel riassunto (con estrazione smart)")
        mw.integraInfoButton.clicked.connect(mw.integraInfoVideo)
        top_controls_layout.addWidget(mw.integraInfoButton)

        top_controls_layout.addStretch()
        summary_controls_layout.addLayout(top_controls_layout)

        # Layout orizzontale per le checkbox
        bottom_controls_layout = QHBoxLayout()
        mw.showTimecodeSummaryCheckbox = QCheckBox("Mostra timecode")
        mw.showTimecodeSummaryCheckbox.setChecked(True)
        mw.showTimecodeSummaryCheckbox.toggled.connect(mw._update_summary_view)
        bottom_controls_layout.addWidget(mw.showTimecodeSummaryCheckbox)

        bottom_controls_layout.addStretch()
        summary_controls_layout.addLayout(bottom_controls_layout)

        summary_layout.addWidget(summary_controls_group)

        # Crea il QTabWidget per i riassunti
        mw.summaryTabWidget = QTabWidget()
        mw.summaryTabWidget.setToolTip("Visualizza i diversi tipi di riassunto generati.")

        # Tab per il Riassunto Dettagliato
        mw.summaryDetailedTextArea = CustomTextEdit(mw)
        mw.summaryDetailedTextArea.setPlaceholderText("Il riassunto dettagliato apparirà qui...")
        mw.summaryDetailedTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.summaryDetailedTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.summaryDetailedTextArea, timestamp, pos)
        )
        mw.summaryDetailedTextArea.textChanged.connect(mw._on_summary_text_changed)
        mw.summaryTabWidget.addTab(mw.summaryDetailedTextArea, "Dettagliato")

        # Tab per le Note Riunione
        mw.summaryMeetingTextArea = CustomTextEdit(mw)
        mw.summaryMeetingTextArea.setPlaceholderText("Le note della riunione appariranno qui...")
        mw.summaryMeetingTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.summaryMeetingTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.summaryMeetingTextArea, timestamp, pos)
        )
        mw.summaryMeetingTextArea.textChanged.connect(mw._on_summary_text_changed)
        mw.summaryTabWidget.addTab(mw.summaryMeetingTextArea, "Note Riunione")

        # Tab per il Riassunto Dettagliato (Integrato)
        mw.summaryDetailedIntegratedTextArea = CustomTextEdit(mw)
        mw.summaryDetailedIntegratedTextArea.setPlaceholderText("Il riassunto dettagliato integrato con le informazioni del video apparirà qui...")
        mw.summaryDetailedIntegratedTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.summaryDetailedIntegratedTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.summaryDetailedIntegratedTextArea, timestamp, pos)
        )
        mw.summaryDetailedIntegratedTextArea.textChanged.connect(mw._on_summary_text_changed)
        mw.summaryTabWidget.addTab(mw.summaryDetailedIntegratedTextArea, "Dettagliato (Integrato)")

        # Tab per le Note Riunione (Integrato)
        mw.summaryMeetingIntegratedTextArea = CustomTextEdit(mw)
        mw.summaryMeetingIntegratedTextArea.setPlaceholderText("Le note della riunione integrate con le informazioni del video appariranno qui...")
        mw.summaryMeetingIntegratedTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.summaryMeetingIntegratedTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.summaryMeetingIntegratedTextArea, timestamp, pos)
        )
        mw.summaryMeetingIntegratedTextArea.textChanged.connect(mw._on_summary_text_changed)
        mw.summaryTabWidget.addTab(mw.summaryMeetingIntegratedTextArea, "Note Riunione (Integrato)")

        # Tab per il Riassunto Dettagliato Combinato
        mw.summaryCombinedDetailedTextArea = CustomTextEdit(mw)
        mw.summaryCombinedDetailedTextArea.setPlaceholderText("Il riassunto dettagliato combinato apparirà qui...")
        mw.summaryCombinedDetailedTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.summaryCombinedDetailedTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.summaryCombinedDetailedTextArea, timestamp, pos)
        )
        mw.summaryCombinedDetailedTextArea.textChanged.connect(mw._on_summary_text_changed)
        mw.summaryTabWidget.addTab(mw.summaryCombinedDetailedTextArea, "Dettagliato Combinato")

        # Tab per le Note Riunione Combinato
        mw.summaryCombinedMeetingTextArea = CustomTextEdit(mw)
        mw.summaryCombinedMeetingTextArea.setPlaceholderText("Le note della riunione combinate appariranno qui...")
        mw.summaryCombinedMeetingTextArea.timestampDoubleClicked.connect(mw.sincronizza_video)
        mw.summaryCombinedMeetingTextArea.insert_frame_requested.connect(
            lambda timestamp, pos: mw.handle_insert_frame_request(mw.summaryCombinedMeetingTextArea, timestamp, pos)
        )
        mw.summaryCombinedMeetingTextArea.textChanged.connect(mw._on_summary_text_changed)
        mw.summaryTabWidget.addTab(mw.summaryCombinedMeetingTextArea, "Note Riunione Combinato")

        # Connect frame edit signals
        mw.singleTranscriptionTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)
        mw.summaryDetailedTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)
        mw.summaryMeetingTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)
        mw.summaryDetailedIntegratedTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)
        mw.summaryMeetingIntegratedTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)
        mw.summaryCombinedDetailedTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)
        mw.summaryCombinedMeetingTextArea.frame_edit_requested.connect(mw.handle_frame_edit_request)


        # Connect the tab change signal to the update function
        mw.summaryTabWidget.currentChanged.connect(mw._update_summary_view)

        # Map widgets to their data keys for easier management
        mw.summary_widget_map = {
            mw.summaryDetailedTextArea: "detailed",
            mw.summaryMeetingTextArea: "meeting",
            mw.summaryDetailedIntegratedTextArea: "detailed_integrated",
            mw.summaryMeetingIntegratedTextArea: "meeting_integrated",
            mw.summaryCombinedDetailedTextArea: "detailed_combined",
            mw.summaryCombinedMeetingTextArea: "meeting_combined",
        }

        summary_layout.addWidget(mw.summaryTabWidget)


        mw.transcriptionTabWidget.addTab(summary_tab, "Riassunto")
        mw.transcriptionTabWidget.addTab(mw.audio_ai_tab, "Audio AI")

        # Aggiungi il tab widget e la barra dei pulsanti al layout del dock
        dock_layout = QVBoxLayout()
        dock_layout.addWidget(mw.transcriptionTabWidget)

        # Il widget contenitore per il layout del dock
        container_widget = QWidget()
        container_widget.setLayout(dock_layout)
        mw.transcriptionDock.addWidget(container_widget)


        # Impostazioni voce per l'editing audio AI
        voiceSettingsWidget = mw.setupVoiceSettingsUI()
        voiceSettingsWidget.setToolTip("Impostazioni voce per l'editing audio AI")
        mw.editingDock.addWidget(voiceSettingsWidget)

        # Aggiungi la UI per gli audio generati
        generatedAudiosWidget = mw.createGeneratedAudiosUI()
        mw.editingDock.addWidget(generatedAudiosWidget)

        # Sincronizza i checkbox di allineamento
        mw.alignspeed.toggled.connect(mw.alignspeed_replacement.setChecked)
        mw.alignspeed_replacement.toggled.connect(mw.alignspeed.setChecked)

        # Dizionario per la gestione dei dock
        docks = {
            'videoPlayerDock': mw.videoPlayerDock,
            'transcriptionDock': mw.transcriptionDock,
            'editingDock': mw.editingDock,
            'recordingDock': mw.recordingDock,
            'audioDock': mw.audioDock,
            'videoPlayerOutput': mw.videoPlayerOutput,
            'projectDock': mw.projectDock,
            'videoNotesDock': mw.videoNotesDock,
            'infoExtractionDock': mw.infoExtractionDock,
            'chatDock': mw.chatDock
        }
        mw.dockSettingsManager = DockSettingsManager(mw, docks, mw)

        # Collegamenti dei segnali del player
        mw.player.durationChanged.connect(mw.durationChanged)
        mw.player.positionChanged.connect(mw.positionChanged)
        mw.player.playbackStateChanged.connect(mw.updatePlayButtonIcon)
        mw.videoSlider.sliderMoved.connect(mw.setPosition)




        # --- STATUS BAR ---
        mw.statusBar = QStatusBar()
        mw.setStatusBar(mw.statusBar)
        mw.statusBar.setStyleSheet("QStatusBar { padding: 1px; } QStatusBar::item { border: none; }")
        mw.statusLabel = QLabel("Pronto")
        mw.statusLabel.setToolTip("Mostra lo stato corrente dell'applicazione")
        mw.statusBar.addWidget(mw.statusLabel, 1) # Il secondo argomento è lo stretch factor

        mw.progressBar = QProgressBar(mw)
        mw.progressBar.setToolTip("Mostra il progresso delle operazioni in corso")
        mw.progressBar.setMaximumWidth(300)
        mw.progressBar.setVisible(False)
        mw.statusBar.addPermanentWidget(mw.progressBar)

        mw.cancelButton = QPushButton("Annulla")
        mw.cancelButton.setToolTip("Annulla l'operazione corrente")
        mw.cancelButton.setFixedWidth(100)
        mw.cancelButton.setVisible(False)
        mw.statusBar.addPermanentWidget(mw.cancelButton)


        # --- TOOLBAR (Principale) ---
        mainToolbar = QToolBar("Main Toolbar")
        mainToolbar.setToolTip("Barra degli strumenti principale per le azioni")
        mw.addToolBar(mainToolbar)

        mainToolbar.addSeparator()

        # Workflow Actions (Azioni AI)
        mw.summarizeMeetingAction = QAction(QIcon(get_resource("meet_sum.png")), 'Riassumi Riunione', mw)
        mw.summarizeMeetingAction.setStatusTip('Crea un riassunto strutturato della trascrizione di una riunione')
        mw.summarizeMeetingAction.triggered.connect(mw.summarizeMeeting)
        mainToolbar.addAction(mw.summarizeMeetingAction)

        mw.summarizeAction = QAction(QIcon(get_resource("text_sum.png")), 'Riassumi Testo', mw)
        mw.summarizeAction.setStatusTip('Genera un riassunto del testo tramite AI')
        mw.summarizeAction.triggered.connect(mw.processTextWithAI)
        mainToolbar.addAction(mw.summarizeAction)

        mw.fixTextAction = QAction(QIcon(get_resource("text_fix.png")), 'Correggi Testo', mw)
        mw.fixTextAction.setStatusTip('Sistema e migliora il testo tramite AI')
        mw.fixTextAction.triggered.connect(mw.fixTextWithAI)
        mainToolbar.addAction(mw.fixTextAction)

        mw.generatePptxAction = QAction(QIcon(get_resource("powerpoint.png")), 'Genera Presentazione', mw)
        mw.generatePptxAction.setStatusTip('Crea una presentazione PowerPoint dal testo')
        mw.generatePptxAction.triggered.connect(mw.openPptxDialog)
        mainToolbar.addAction(mw.generatePptxAction)

        # --- SECONDA TOOLBAR (Workspace e Impostazioni) ---
        workspaceToolbar = QToolBar("Workspace Toolbar")
        workspaceToolbar.setToolTip("Barra degli strumenti per layout e impostazioni")
        mw.addToolBar(workspaceToolbar)

        # Workspace Actions (Layouts)


        mw.recordingLayoutAction = QAction(QIcon(get_resource("rec.png")), 'Registrazione', mw)
        mw.recordingLayoutAction.setToolTip("Layout per la registrazione")
        mw.recordingLayoutAction.triggered.connect(mw.dockSettingsManager.loadRecordingLayout)
        workspaceToolbar.addAction(mw.recordingLayoutAction)

        mw.comparisonLayoutAction = QAction(QIcon(get_resource("compare.png")), 'Confronto', mw)
        mw.comparisonLayoutAction.setToolTip("Layout per il confronto")
        mw.comparisonLayoutAction.triggered.connect(mw.dockSettingsManager.loadComparisonLayout)
        workspaceToolbar.addAction(mw.comparisonLayoutAction)

        mw.transcriptionLayoutAction = QAction(QIcon(get_resource("script.png")), 'Trascrizione', mw)
        mw.transcriptionLayoutAction.setToolTip("Layout per la trascrizione")
        mw.transcriptionLayoutAction.triggered.connect(mw.dockSettingsManager.loadTranscriptionLayout)
        workspaceToolbar.addAction(mw.transcriptionLayoutAction)

        mw.defaultLayoutAction = QAction(QIcon(get_resource("default.png")), 'Default', mw)
        mw.defaultLayoutAction.setToolTip("Layout di default")
        mw.defaultLayoutAction.triggered.connect(mw.dockSettingsManager.loadDefaultLayout)
        workspaceToolbar.addAction(mw.defaultLayoutAction)
        workspaceToolbar.addSeparator()

        serviceToolbar = QToolBar("Rec Toolbar")
        serviceToolbar.setToolTip("Barra servizio")
        mw.addToolBar(serviceToolbar)

        # Aggiungi l'indicatore di registrazione lampeggiante
        #serviceToolbar.addWidget(mw.recording_indicator)

        # Azione di condivisione
        shareAction = QAction(QIcon(get_resource("share.png")), "Condividi Video", mw)
        shareAction.setToolTip("Condividi il video attualmente caricato")
        shareAction.triggered.connect(mw.onShareButtonClicked)
        serviceToolbar.addAction(shareAction)

        # Azione Impostazioni
        settingsAction = QAction(QIcon(get_resource("gear.png")), "Impostazioni", mw)
        settingsAction.setToolTip("Apri le impostazioni dell'applicazione")
        settingsAction.triggered.connect(mw.showSettingsDialog)
        serviceToolbar.addAction(settingsAction)

        serviceToolbar.addSeparator()

        # Azione di ricerca centralizzata
        findAction = QAction("Cerca", mw)
        findAction.setShortcut("Ctrl+F")
        findAction.triggered.connect(mw.open_search_dialog)
        mw.addAction(findAction)

        # Configurazione della menu bar (questa parte rimane invariata)
        mw.setupMenuBar()

        # Applica il tema scuro, se disponibile
        if hasattr(mw, 'applyDarkMode'):
            mw.applyDarkMode()

        # Applica lo stile a tutti i dock
        mw.applyStyleToAllDocks()

        # Applica le impostazioni del font
        mw.apply_and_save_font_settings()
        mw.action_manager.setup_connections()
        mw.player_manager.setup_connections()
