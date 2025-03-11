import sys
import re
import shutil
import subprocess
import tempfile
import datetime
import time
import logging
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Librerie PyQt6
from PyQt6.QtCore import (Qt, QUrl, QEvent, QTimer, QPoint, QTime)
from PyQt6.QtGui import (QIcon, QAction, QDesktopServices)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QRadioButton, QLineEdit,
    QHBoxLayout, QGroupBox, QComboBox, QSpinBox, QFileDialog,
    QMessageBox, QSizePolicy, QProgressDialog, QToolBar, QSlider, QTabWidget
)

# PyQtGraph (docking)
from pyqtgraph.dockarea.DockArea import DockArea
from ui.CustomDock import CustomDock

from moviepy.editor import (
    ImageClip, CompositeVideoClip, concatenate_audioclips,
    concatenate_videoclips, VideoFileClip, AudioFileClip, vfx
)
from moviepy.audio.AudioClip import CompositeAudioClip
from pydub import AudioSegment

import numpy as np
import pyaudio
from screeninfo import get_monitors
from bs4 import BeautifulSoup
from num2words import num2words
from langdetect import detect, LangDetectException
import pycountry
from difflib import SequenceMatcher

from services.DownloadVideo import DownloadThread
from services.AudioTranscript import TranscriptionThread
from services.AudioGenerationREST import AudioGenerationThread
from services.VideoCutting import VideoCuttingThread
from recorder.ScreenRecorder import ScreenRecorder
from managers.SettingsManager import DockSettingsManager
from ui.CustVideoWidget import CropVideoWidget
from ui.CustomSlider import CustomSlider
from managers.SettingsDialog import ApiKeyDialog
from managers.Settings import SettingsDialog
from ui.ScreenButton import ScreenButton
from ui.CustumTextEdit import CustomTextEdit
from services.PptxGeneration import PptxGeneration
from services.ProcessTextAI import ProcessTextAI
from ui.SplashScreen import SplashScreen
from services.ShareVideo import VideoSharingManager
from managers.StreamToLogger import setup_logging
from services.FrameExtractor import FrameExtractor
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from config import (ELEVENLABS_API_KEY, ANTHROPIC_API_KEY, FFMPEG_PATH, FFMPEG_PATH_DOWNLOAD, VERSION_FILE)
from config import MUSIC_DIR
from config import DEFAULT_FRAME_COUNT, DEFAULT_AUDIO_CHANNELS,DEFAULT_STABILITY,\
    DEFAULT_SIMILARITY, DEFAULT_STYLE, DEFAULT_FRAME_RATE,DEFAULT_VOICES
import os
from config import SPLASH_IMAGES_DIR
from config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
AudioSegment.converter = FFMPEG_PATH

class VideoAudioManager(QMainWindow):
    def __init__(self):
        super().__init__()


        setup_logging()

        # File di versione
        self.version_file = VERSION_FILE

        # Carica le informazioni di versione dal file esterno
        self.version, self.build_date = self.load_version_info()

        # Imposta il titolo della finestra con la versione e la data di build
        self.setWindowTitle(f"GeniusAI - {self.version} (Build Date: {self.build_date})")

        self.api_key = ELEVENLABS_API_KEY
        self.api_llm = ANTHROPIC_API_KEY

        self.setGeometry(500, 500, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.player = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        self.playerOutput = QMediaPlayer()
        self.audioOutputOutput = QAudioOutput()

        self.player.setAudioOutput(self.audioOutput)
        self.audioOutput.setVolume(1.0)
        self.recentFiles = []
        self.initUI()
        self.setupDockSettingsManager()
        self.bookmarkStart = None
        self.bookmarkEnd = None
        self.currentPosition = 0
        self.videoPathLineEdit = ''
        self.videoPathLineOutputEdit = ''
        self.is_recording = False
        self.video_writer = None
        self.current_video_path = None
        self.current_audio_path = None
        self.updateViewMenu()
        self.videoSharingManager = VideoSharingManager(self)

        # Aggiungi l'istanza di TeamsCallRecorder
        #self.teams_call_recorder = TeamsCallRecorder(self)

        # Avvia la registrazione automatica delle chiamate
        #self.teams_call_recorder.start()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def initUI(self):
        """
        Inizializza l'interfaccia utente creando e configurando l'area dei dock,
        impostando i dock principali (video input, video output, trascrizione, editing AI, ecc.)
        e definendo la sezione di trascrizione con QTabWidget e area di testo sempre visibile.
        """
        # Impostazione dell'icona della finestra
        self.setWindowIcon(QIcon('./res/eye.png'))

        # Creazione dell'area dei dock
        area = DockArea()
        self.setCentralWidget(area)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.setToolTip("Area principale dei dock")

        # ---------------------
        # CREAZIONE DOCK PRINCIPALI (invariati)
        # ---------------------
        self.videoPlayerDock = CustomDock("Video Player Input", closable=True)
        self.videoPlayerDock.setStyleSheet(self.styleSheet())
        self.videoPlayerDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoPlayerDock.setToolTip("Dock per la riproduzione video di input")
        area.addDock(self.videoPlayerDock, 'left')

        self.videoPlayerOutput = CustomDock("Video Player Output", closable=True)
        self.videoPlayerOutput.setStyleSheet(self.styleSheet())
        self.videoPlayerOutput.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoPlayerOutput.setToolTip("Dock per la riproduzione video di output")
        area.addDock(self.videoPlayerOutput, 'left')

        self.transcriptionDock = CustomDock("Trascrizione e Sintesi Audio", closable=True)
        self.transcriptionDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.transcriptionDock.setStyleSheet(self.styleSheet())
        self.transcriptionDock.setToolTip("Dock per la trascrizione e sintesi audio")
        area.addDock(self.transcriptionDock, 'right')

        self.editingDock = CustomDock("Generazione Audio AI di Editing", closable=True)
        self.editingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.editingDock.setStyleSheet(self.styleSheet())
        self.editingDock.setToolTip("Dock per la generazione audio assistita da AI")
        area.addDock(self.editingDock, 'right')

        self.downloadDock = self.createDownloadDock()
        self.downloadDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.downloadDock.setStyleSheet(self.styleSheet())
        self.downloadDock.setToolTip("Dock per il download dei contenuti video/audio")
        area.addDock(self.downloadDock, 'top')

        self.recordingDock = self.createRecordingDock()
        self.recordingDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.recordingDock.setStyleSheet(self.styleSheet())
        self.recordingDock.setToolTip("Dock per la registrazione")
        area.addDock(self.recordingDock, 'right')

        self.audioDock = self.createAudioDock()
        self.audioDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.audioDock.setStyleSheet(self.styleSheet())
        self.audioDock.setToolTip("Dock per la gestione audio")
        area.addDock(self.audioDock, 'left')

        self.videoMergeDock = self.createVideoMergeDock()
        self.videoMergeDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoMergeDock.setStyleSheet(self.styleSheet())
        self.videoMergeDock.setToolTip("Dock per l'unione di più video")
        area.addDock(self.videoMergeDock, 'top')

        self.generazioneAIDock = CustomDock("Generazione AI", closable=True)
        self.generazioneAIDock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.generazioneAIDock.setToolTip("Dock per la generazione di contenuti con AI")
        area.addDock(self.generazioneAIDock, 'right')

        # ---------------------
        # DOCK GENERAZIONE AI (invariato)
        # ---------------------
        generazioneAIDockWidget = QGroupBox("Impostazioni Generazione AI")
        generazioneAIDockWidget.setToolTip("Impostazioni per generare testo e presentazioni con AI")
        generazioneAILayout = QVBoxLayout()

        self.numSlidesLabel = QLabel("Numero di Slide:")
        self.numSlidesLabel.setToolTip("Specifica il numero di slide da generare")
        self.numSlidesInput = QLineEdit()
        self.numSlidesInput.setPlaceholderText("Inserisci numero di slide")
        self.numSlidesInput.setToolTip("Inserisci il numero di diapositive che vuoi generare")
        generazioneAILayout.addWidget(self.numSlidesLabel)
        generazioneAILayout.addWidget(self.numSlidesInput)

        self.companyNameLabel = QLabel("Nome della Compagnia:")
        self.companyNameLabel.setToolTip("Nome della compagnia per cui generare la presentazione")
        self.companyNameInput = QLineEdit()
        self.companyNameInput.setPlaceholderText("Inserisci nome della compagnia")
        self.companyNameInput.setToolTip("Inserisci il nome della compagnia per personalizzare la presentazione")
        generazioneAILayout.addWidget(self.companyNameLabel)
        generazioneAILayout.addWidget(self.companyNameInput)

        self.languageLabel = QLabel("Lingua:")
        self.languageLabel.setToolTip("Lingua in cui generare la presentazione")
        self.languageInput = QComboBox()
        self.languageInput.addItems(["Italiano", "Inglese", "Francese", "Spagnolo", "Tedesco"])
        self.languageInput.setToolTip("Seleziona la lingua desiderata per la presentazione generata")
        generazioneAILayout.addWidget(self.languageLabel)
        generazioneAILayout.addWidget(self.languageInput)

        self.generateTextButton = QPushButton('Genera Testo per Presentazione con AI ')
        self.generateTextButton.setToolTip("Clicca per generare il testo per la presentazione tramite AI")
        self.generateTextButton.clicked.connect(self.generateTextForPresentation)
        generazioneAILayout.addWidget(self.generateTextButton)

        self.generatePresentationButton = QPushButton('Genera Presentazione')
        self.generatePresentationButton.setToolTip("Clicca per generare la presentazione completa con AI")
        self.generatePresentationButton.clicked.connect(self.generateAIPresentation)
        generazioneAILayout.addWidget(self.generatePresentationButton)

        generazioneAIDockWidget.setLayout(generazioneAILayout)
        self.generazioneAIDock.addWidget(generazioneAIDockWidget)

        # ---------------------
        # PLAYER INPUT
        # ---------------------
        self.videoCropWidget = CropVideoWidget()
        self.videoCropWidget.setAcceptDrops(True)
        self.videoCropWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoCropWidget.setToolTip("Area di visualizzazione e ritaglio video input")
        self.player.setVideoOutput(self.videoCropWidget)

        self.zoom_level = 1.0
        self.videoCropWidget.installEventFilter(self)
        self.is_panning = False
        self.last_mouse_position = QPoint()

        self.videoSlider = CustomSlider(Qt.Orientation.Horizontal)
        self.videoSlider.setToolTip("Slider per navigare all'interno del video input")

        self.fileNameLabel = QLabel("Nessun video caricato")
        self.fileNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fileNameLabel.setStyleSheet("QLabel { font-weight: bold; }")
        self.fileNameLabel.setToolTip("Nome del file video attualmente caricato nel Player Input")

        self.playButton = QPushButton('')
        self.playButton.setIcon(QIcon("./res/play.png"))
        self.playButton.setToolTip("Riproduci/Pausa il video input")
        self.playButton.clicked.connect(self.togglePlayPause)

        self.stopButton = QPushButton('')
        self.stopButton.setIcon(QIcon("./res/stop.png"))
        self.stopButton.setToolTip("Ferma la riproduzione del video input")

        self.setStartBookmarkButton = QPushButton('')
        self.setStartBookmarkButton.setIcon(QIcon("./res/bookmark_1.png"))
        self.setStartBookmarkButton.setToolTip("Imposta segnalibro di inizio sul video input")

        self.setEndBookmarkButton = QPushButton('')
        self.setEndBookmarkButton.setIcon(QIcon("./res/bookmark_2.png"))
        self.setEndBookmarkButton.setToolTip("Imposta segnalibro di fine sul video input")

        self.cutButton = QPushButton('')
        self.cutButton.setIcon(QIcon("./res/taglia.png"))
        self.cutButton.setToolTip("Taglia il video tra i segnalibri impostati")

        self.rewindButton = QPushButton('<< 5s')
        self.rewindButton.setIcon(QIcon("./res/rewind.png"))
        self.rewindButton.setToolTip("Riavvolgi il video di 5 secondi")

        self.forwardButton = QPushButton('>> 5s')
        self.forwardButton.setIcon(QIcon("./res/forward.png"))
        self.forwardButton.setToolTip("Avanza il video di 5 secondi")

        self.deleteButton = QPushButton('')
        self.deleteButton.setIcon(QIcon("./res/trash-bin.png"))
        self.deleteButton.setToolTip("Cancella la parte selezionata del video")

        self.stopButton.clicked.connect(self.stopVideo)
        self.setStartBookmarkButton.clicked.connect(self.setStartBookmark)
        self.setEndBookmarkButton.clicked.connect(self.setEndBookmark)
        self.cutButton.clicked.connect(self.cutVideoBetweenBookmarks)
        self.rewindButton.clicked.connect(self.rewind5Seconds)
        self.forwardButton.clicked.connect(self.forward5Seconds)
        self.deleteButton.clicked.connect(self.deleteVideoSegment)

        self.currentTimeLabel = QLabel('00:00')
        self.currentTimeLabel.setToolTip("Mostra il tempo corrente del video input")
        self.totalTimeLabel = QLabel('/ 00:00')
        self.totalTimeLabel.setToolTip("Mostra la durata totale del video input")
        timecodeLayout = QHBoxLayout()
        timecodeLayout.addWidget(self.currentTimeLabel)
        timecodeLayout.addWidget(self.totalTimeLabel)

        # ---------------------
        # PLAYER OUTPUT
        # ---------------------
        self.videoOutputWidget = CropVideoWidget()
        self.videoOutputWidget.setAcceptDrops(True)
        self.videoOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoOutputWidget.setToolTip("Area di visualizzazione e ritaglio video output")

        self.playerOutput.setAudioOutput(self.audioOutputOutput)
        self.playerOutput.setVideoOutput(self.videoOutputWidget)

        self.playButtonOutput = QPushButton('')
        self.playButtonOutput.setIcon(QIcon("./res/play.png"))
        self.playButtonOutput.setToolTip("Riproduci/Pausa il video output")
        self.playButtonOutput.clicked.connect(self.togglePlayPauseOutput)

        stopButtonOutput = QPushButton('')
        stopButtonOutput.setIcon(QIcon("./res/stop.png"))
        stopButtonOutput.setToolTip("Ferma la riproduzione del video output")

        changeButtonOutput = QPushButton('')
        changeButtonOutput.setIcon(QIcon("./res/change.png"))
        changeButtonOutput.setToolTip("Sposta il video output nel Video Player Input")
        changeButtonOutput.clicked.connect(
            lambda: self.loadVideo(self.videoPathLineOutputEdit, os.path.basename(self.videoPathLineOutputEdit))
        )

        syncPositionButton = QPushButton('Sync Position')
        syncPositionButton.setIcon(QIcon("./res/sync.png"))
        syncPositionButton.setToolTip('Sincronizza la posizione del video output con quella del video source')
        syncPositionButton.clicked.connect(self.syncOutputWithSourcePosition)

        stopButtonOutput.clicked.connect(lambda: self.playerOutput.stop())

        playbackControlLayoutOutput = QHBoxLayout()
        playbackControlLayoutOutput.addWidget(self.playButtonOutput)
        playbackControlLayoutOutput.addWidget(stopButtonOutput)
        playbackControlLayoutOutput.addWidget(changeButtonOutput)
        playbackControlLayoutOutput.addWidget(syncPositionButton)

        videoSliderOutput = CustomSlider(Qt.Orientation.Horizontal)
        videoSliderOutput.setRange(0, 1000)  # Range di esempio
        videoSliderOutput.setToolTip("Slider per navigare all'interno del video output")
        videoSliderOutput.sliderMoved.connect(lambda position: self.playerOutput.setPosition(position))

        self.currentTimeLabelOutput = QLabel('00:00')
        self.currentTimeLabelOutput.setToolTip("Mostra il tempo corrente del video output")
        self.totalTimeLabelOutput = QLabel('/ 00:00')
        self.totalTimeLabelOutput.setToolTip("Mostra la durata totale del video output")
        timecodeLayoutOutput = QHBoxLayout()
        timecodeLayoutOutput.addWidget(self.currentTimeLabelOutput)
        timecodeLayoutOutput.addWidget(self.totalTimeLabelOutput)

        self.timecodeEnabled = False

        self.fileNameLabelOutput = QLabel("Nessun video caricato")
        self.fileNameLabelOutput.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fileNameLabelOutput.setStyleSheet("QLabel { font-weight: bold; }")
        self.fileNameLabelOutput.setToolTip("Nome del file video attualmente caricato nel Player Output")

        videoOutputLayout = QVBoxLayout()
        videoOutputLayout.addWidget(self.fileNameLabelOutput)
        videoOutputLayout.addWidget(self.videoOutputWidget)
        videoOutputLayout.addLayout(timecodeLayoutOutput)
        videoOutputLayout.addWidget(videoSliderOutput)
        videoOutputLayout.addLayout(playbackControlLayoutOutput)

        self.playerOutput.durationChanged.connect(self.updateDurationOutput)
        self.playerOutput.positionChanged.connect(self.updateTimeCodeOutput)

        videoPlayerOutputWidget = QWidget()
        videoPlayerOutputWidget.setLayout(videoOutputLayout)
        videoPlayerOutputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.videoPlayerOutput.addWidget(videoPlayerOutputWidget)

        self.playerOutput.durationChanged.connect(lambda duration: videoSliderOutput.setRange(0, duration))
        self.playerOutput.positionChanged.connect(lambda position: videoSliderOutput.setValue(position))

        # Pulsante per trascrivere il video
        self.transcribeButton = QPushButton('Trascrivi Video')
        self.transcribeButton.setToolTip("Avvia la trascrizione del video attualmente caricato")
        self.transcribeButton.clicked.connect(self.transcribeVideo)

        # Layout di playback del Player Input
        playbackControlLayout = QHBoxLayout()
        playbackControlLayout.addWidget(self.rewindButton)
        playbackControlLayout.addWidget(self.playButton)
        playbackControlLayout.addWidget(self.stopButton)
        playbackControlLayout.addWidget(self.forwardButton)
        playbackControlLayout.addWidget(self.setStartBookmarkButton)
        playbackControlLayout.addWidget(self.setEndBookmarkButton)
        playbackControlLayout.addWidget(self.cutButton)
        playbackControlLayout.addWidget(self.deleteButton)

        # Layout principale del Player Input
        videoPlayerLayout = QVBoxLayout()
        videoPlayerLayout.addWidget(self.fileNameLabel)
        videoPlayerLayout.addWidget(self.videoCropWidget)
        videoPlayerLayout.addLayout(timecodeLayout)
        videoPlayerLayout.addWidget(self.videoSlider)
        videoPlayerLayout.addLayout(playbackControlLayout)

        # Controlli volume input e velocità
        self.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(int(self.audioOutput.volume() * 100))
        self.volumeSlider.setToolTip("Regola il volume dell'audio input")
        self.volumeSlider.valueChanged.connect(self.setVolume)

        self.volumeSliderOutput = QSlider(Qt.Orientation.Horizontal)
        self.volumeSliderOutput.setRange(0, 100)
        self.volumeSliderOutput.setValue(int(self.audioOutputOutput.volume() * 100))
        self.volumeSliderOutput.setToolTip("Regola il volume dell'audio output")
        self.volumeSliderOutput.valueChanged.connect(self.setVolumeOutput)

        videoOutputLayout.addWidget(QLabel("Volume"))
        videoOutputLayout.addWidget(self.volumeSliderOutput)

        videoPlayerWidget = QWidget()
        videoPlayerWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        videoPlayerWidget.setLayout(videoPlayerLayout)
        self.videoPlayerDock.addWidget(videoPlayerWidget)

        #
        # TRASCRIZIONE: QTabWidget con 2 tab (Strumenti Base e Strumenti Avanzati),
        # e la transcriptionTextArea sempre visibile sotto i tab
        #
        transGroupBox = QGroupBox("Gestione Trascrizione")
        transGroupBox.setToolTip("Strumenti per trascrizione, incolla, salva e modifica testo")

        # Creiamo un QTabWidget
        tabWidget = QTabWidget()

        # --- TAB 1: Strumenti Base (usando QGridLayout) ---
        tabBase = QWidget()
        gridLayoutBase = QGridLayout()
        # Posizioniamo la label e la combo per la lingua
        langLabel = QLabel("Seleziona lingua video:")
        langLabel.setToolTip("Seleziona la lingua del video per la trascrizione")
        self.languageComboBox = QComboBox()
        self.languageComboBox.addItem("Italiano", "it")
        self.languageComboBox.addItem("Inglese", "en")
        self.languageComboBox.addItem("Francese", "fr")
        self.languageComboBox.addItem("Spagnolo", "es")
        self.languageComboBox.addItem("Tedesco", "de")
        self.languageComboBox.setToolTip("Seleziona la lingua corretta per il video")
        self.video_download_language = None

        gridLayoutBase.addWidget(langLabel, 0, 0)
        gridLayoutBase.addWidget(self.languageComboBox, 0, 1)
        # Aggiungiamo la label della lingua rilevata
        self.transcriptionLanguageLabel = QLabel("Lingua rilevata: Nessuna")
        gridLayoutBase.addWidget(self.transcriptionLanguageLabel, 0, 2, 1, 2)
        # Per i pulsanti base, usiamo un QHBoxLayout e lo inseriamo in una cella della griglia
        buttonsLayoutBase2 = QHBoxLayout()
        self.resetButton = QPushButton()
        self.resetButton.setIcon(QIcon("./res/reset.png"))
        self.resetButton.setFixedSize(24, 24)
        self.resetButton.setToolTip("Ripulisce la trascrizione")
        self.resetButton.clicked.connect(lambda: self.transcriptionTextArea.clear())
        self.pasteButton = QPushButton()
        self.pasteButton.setIcon(QIcon("./res/paste.png"))
        self.pasteButton.setFixedSize(24, 24)
        self.pasteButton.setToolTip("Incolla il testo dagli appunti")
        self.pasteButton.clicked.connect(lambda: self.transcriptionTextArea.paste())
        self.saveButton = QPushButton()
        self.saveButton.setIcon(QIcon("./res/save.png"))
        self.saveButton.setFixedSize(24, 24)
        self.saveButton.setToolTip("Salva la trascrizione su file")
        self.saveButton.clicked.connect(self.saveText)
        self.loadButton = QPushButton()
        self.loadButton.setIcon(QIcon("./res/load.png"))
        self.loadButton.setFixedSize(24, 24)
        self.loadButton.setToolTip("Carica una trascrizione da file")
        self.loadButton.clicked.connect(self.loadText)
        self.transcribeButton = QPushButton('Trascrivi Video')
        self.transcribeButton.setToolTip("Avvia la trascrizione del video attualmente caricato")
        self.transcribeButton.clicked.connect(self.transcribeVideo)
        buttonsLayoutBase2.addWidget(self.resetButton)
        buttonsLayoutBase2.addWidget(self.pasteButton)
        buttonsLayoutBase2.addWidget(self.loadButton)
        buttonsLayoutBase2.addWidget(self.saveButton)
        buttonsLayoutBase2.addWidget(self.transcribeButton)
        gridLayoutBase.addLayout(buttonsLayoutBase2, 2, 0, 1, 2)
        tabBase.setLayout(gridLayoutBase)
        tabWidget.addTab(tabBase, "Strumenti Base")

        # --- TAB 2: Strumenti Avanzati (usando QGridLayout) ---
        tabAdvanced = QWidget()
        gridLayoutAdv = QGridLayout()
        # Row 0: frameCountSpin
        self.frameCountSpin = QSpinBox()
        self.frameCountSpin.setMinimum(1)
        self.frameCountSpin.setMaximum(30)
        self.frameCountSpin.setValue(DEFAULT_FRAME_COUNT)
        self.frameCountSpin.setToolTip("Imposta il numero di frame da estrarre")
        # Nota: il bottone extractFramesButton è stato spostato nel menu Workflows
        gridLayoutAdv.addWidget(QLabel("Numero frame:"), 0, 0)
        gridLayoutAdv.addWidget(self.frameCountSpin, 0, 1)
        # Row 1: timecodeCheckbox ed syncButton
        self.timecodeCheckbox = QCheckBox("Inserisci timecode audio")
        self.timecodeCheckbox.setChecked(False)
        self.timecodeCheckbox.setToolTip("Aggiunge i timecode all'audio durante la trascrizione")
        self.timecodeCheckbox.toggled.connect(self.handleTimecodeToggle)
        self.syncButton = QPushButton('Sincronizza Video')
        self.syncButton.setToolTip("Sincronizza la posizione del video con la trascrizione")
        self.syncButton.clicked.connect(self.sync_video_to_transcription)
        gridLayoutAdv.addWidget(self.timecodeCheckbox, 1, 0)
        gridLayoutAdv.addWidget(self.syncButton, 1, 1)
        # Row 3: pauseTimeEdit ed insertPauseButton
        self.pauseTimeEdit = QLineEdit()
        self.pauseTimeEdit.setPlaceholderText("Inserisci durata pausa (es. 1.0s)")
        self.pauseTimeEdit.setToolTip("Specifica la durata di una pausa in secondi")
        self.insertPauseButton = QPushButton('Inserisci Pausa')
        self.insertPauseButton.setToolTip("Inserisci una pausa nel testo")
        self.insertPauseButton.clicked.connect(self.insertPause)
        gridLayoutAdv.addWidget(self.pauseTimeEdit, 3, 0)
        gridLayoutAdv.addWidget(self.insertPauseButton, 3, 1)
        tabAdvanced.setLayout(gridLayoutAdv)
        tabAdvanced.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        tabWidget.addTab(tabAdvanced, "Strumenti Avanzati")

        # Layout finale nella sezione di trascrizione: il QTabWidget in alto e la text area sotto
        finalTransLayout = QVBoxLayout()
        tabWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        finalTransLayout.addWidget(tabWidget, 0)
        self.transcriptionTextArea = CustomTextEdit(self)
        self.transcriptionTextArea.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.transcriptionTextArea.setReadOnly(False)
        self.transcriptionTextArea.setUndoRedoEnabled(True)
        self.transcriptionTextArea.setStyleSheet("""
            QTextEdit {
                color: white;
                font-size: 12pt;
                font-family: 'Arial';
                background-color: #333;
            }
        """)
        self.transcriptionTextArea.setPlaceholderText("Incolla qui la tua trascrizione...")
        self.transcriptionTextArea.setToolTip("Area di testo per la trascrizione")
        self.transcriptionTextArea.textChanged.connect(self.handleTextChange)
        finalTransLayout.addWidget(self.transcriptionTextArea, 1)

        transGroupBox.setLayout(finalTransLayout)
        widgetTranscription = QWidget()
        widgetLayout = QVBoxLayout()
        widgetLayout.addWidget(transGroupBox)
        widgetTranscription.setLayout(widgetLayout)
        self.transcriptionDock.addWidget(widgetTranscription)

        # Impostazioni voce per l'editing audio AI
        voiceSettingsWidget = self.setupVoiceSettingsUI()
        voiceSettingsWidget.setToolTip("Impostazioni voce per l'editing audio AI")
        self.editingDock.addWidget(voiceSettingsWidget)

        # Configurazione della menu bar
        self.setupMenuBar()

        # Collegamenti dei segnali del player
        self.player.durationChanged.connect(self.durationChanged)
        self.player.positionChanged.connect(self.positionChanged)
        self.videoSlider.sliderMoved.connect(self.setPosition)

        # Dizionario per la gestione dei dock
        docks = {
            'videoPlayerDock': self.videoPlayerDock,
            'transcriptionDock': self.transcriptionDock,
            'editingDock': self.editingDock,
            'downloadDock': self.downloadDock,
            'recordingDock': self.recordingDock,
            'audioDock': self.audioDock,
            'videoPlayerOutput': self.videoPlayerOutput,
            'videoMergeDock': self.videoMergeDock,
            'generazioneAIDock': self.generazioneAIDock
        }
        self.dockSettingsManager = DockSettingsManager(self, docks, self)

        # Creazione e configurazione della toolbar principale
        toolbar = QToolBar("Main Toolbar")
        toolbar.setToolTip("Barra degli strumenti principale")
        self.addToolBar(toolbar)

        loadDockSettings1Action = QAction(QIcon("./res/load1.png"), "User1", self)
        loadDockSettings1Action.setToolTip("Carica le impostazioni dei dock per l'utente 1")
        loadDockSettings1Action.triggered.connect(self.dockSettingsManager.loadDockSettingsUser1)
        toolbar.addAction(loadDockSettings1Action)

        loadDockSettings2Action = QAction(QIcon("./res/load2.png"), "User2", self)
        loadDockSettings2Action.setToolTip("Carica le impostazioni dei dock per l'utente 2")
        loadDockSettings2Action.triggered.connect(self.dockSettingsManager.loadDockSettingsUser2)
        toolbar.addAction(loadDockSettings2Action)

        apiKeyAction = QAction(QIcon("./res/key.png"), "Imposta API Key", self)
        apiKeyAction.setToolTip("Imposta la chiave API per le funzionalità AI")
        apiKeyAction.triggered.connect(self.showApiKeyDialog)
        toolbar.addAction(apiKeyAction)

        settingsAction = QAction(QIcon("./res/gear.png"), "Impostazioni", self)
        settingsAction.setToolTip("Apri le impostazioni dell'applicazione")
        settingsAction.triggered.connect(self.showSettingsDialog)
        toolbar.addAction(settingsAction)

        shareAction = QAction(QIcon("./res/share.png"), "Condividi Video", self)
        shareAction.setToolTip("Condividi il video attualmente caricato")
        shareAction.triggered.connect(self.onShareButtonClicked)
        toolbar.addAction(shareAction)

        # Applica il tema scuro, se disponibile
        if hasattr(self, 'applyDarkMode'):
            self.applyDarkMode()

        # Applica lo stile a tutti i dock
        self.applyStyleToAllDocks()

    def createWorkflow(self):
        # Implementazione per creare un nuovo workflow
        print("Funzione createWorkflow da implementare")
        # Qui puoi mostrare un dialogo per creare un nuovo workflow

    def loadWorkflow(self):
        # Implementazione per caricare un workflow esistente
        print("Funzione loadWorkflow da implementare")
        # Qui puoi mostrare un dialogo per selezionare e caricare un workflow esistente

    def configureAgent(self):
        """
        Configura l'agent AI mostrando il dialogo di configurazione
        """
        if not hasattr(self, 'browser_agent'):
            from services.BrowserAgent import BrowserAgent
            self.browser_agent = BrowserAgent(self)

        self.browser_agent.showConfigDialog()

    def runAgent(self):
        """
        Esegue l'agent AI con la configurazione corrente
        """
        if not hasattr(self, 'browser_agent'):
            from services.BrowserAgent import BrowserAgent
            self.browser_agent = BrowserAgent(self)

        self.browser_agent.runAgent()

    def showMediaInfo(self):
        # Implementazione per mostrare informazioni sul media
        print("Funzione showMediaInfo da implementare")
        # Qui puoi mostrare un dialog con le informazioni sul media corrente
    def onExtractFramesClicked(self):
        """
        Passi:
        1) Verifica video caricato
        2) Istanzia FrameExtractor
        3) Estrae i frame
        4) Ottiene frame_data (descrizioni di ogni frame)
        5) Genera un discorso finale dell'intero video
        6) Mostra il risultato nella transcriptionTextArea
        """
        if not self.videoPathLineEdit:
            QMessageBox.warning(self, "Attenzione", "Nessun video caricato. Carica un video prima di estrarre i frame.")
            return

        num_frames = self.frameCountSpin.value()
        api_key = self.api_llm  # Tua variabile con la chiave
        if not api_key:
            QMessageBox.warning(self, "API Key mancante", "Imposta la chiave API prima di estrarre i frame.")
            return

        try:
            # 1) Crea l'extractor
            extractor = FrameExtractor(
                video_path=self.videoPathLineEdit,
                num_frames=num_frames,
                anthropic_api_key=api_key
            )

            # 2) Estrae i frame
            frames = extractor.extract_frames()

            # 3) Analizza i frame => otteniamo un array di { frame_number, description, timestamp }
            frame_data = extractor.analyze_frames_batch(
                frames,
                self.languageInput.currentText()  # "Italian", "English", ...
            )

            # 4) Opzionale: se vuoi mostrare i dettagli di ogni frame
            details_list = []
            for fd in frame_data:
                # "Frame 0 (03:00): <desc>"
                details_list.append(f"Frame {fd['frame_number']} ({fd['timestamp']}): {fd['description']}")
            details_text = "\n".join(details_list)

            # 5) Generiamo un discorso/riassunto finale
            final_discourse = extractor.generate_video_summary(frame_data, self.languageInput.currentText())

            # 6) Creiamo un testo conclusivo
            #    [DETTAGLI FRAME] + [DISCORSO FINALE]
            final_text = (final_discourse or "N/A")

            # Aggiunta all'area di trascrizione
            current_text = self.transcriptionTextArea.toPlainText()
            self.transcriptionTextArea.setPlainText(current_text + "\n\n" + final_text)

            QMessageBox.information(self, "Estrazione completata",
                                    "Testo estratto dai frame e riassunto finale completati.")

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante l'estrazione dei frame:\n{str(e)}")

    def onShareButtonClicked(self):
        # Usa il percorso del video nel dock Video Player Output
        video_path = self.videoPathLineOutputEdit
        self.videoSharingManager.shareVideo(video_path)
    def load_version_info(self):
        """
        Carica le informazioni di versione e data dal file di versione.
        """
        version = "Sconosciuta"
        build_date = "Sconosciuta"

        # Verifica se il file esiste
        if os.path.exists(self.version_file):
            with open(self.version_file, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if "Version" in line:
                        version = line.split(":")[1].strip()  # Estrai la versione
                    elif "Build Date" in line:
                        build_date = line.split(":")[1].strip()  # Estrai la data di build
        else:
            print(f"File {self.version_file} non trovato.")

        return version, build_date

    def togglePlayPauseOutput(self):
        if self.playerOutput.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playerOutput.pause()
            self.playButtonOutput.setIcon(QIcon("./res/play.png"))  # Cambia l'icona in Play
        else:
            self.playerOutput.play()
            self.playButtonOutput.setIcon(QIcon("./res/pausa.png"))  # Cambia l'icona in Pausa

    def togglePlayPause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.playButton.setIcon(QIcon("./res/play.png"))  # Cambia l'icona in Play
        else:
            self.player.play()
            self.playButton.setIcon(QIcon("./res/pausa.png"))  # Cambia l'icona in Pausa

    def syncOutputWithSourcePosition(self):
        source_position = self.player.position()
        self.playerOutput.setPosition(source_position)
        self.playVideo()
        self.playerOutput.play()

    def generateTextForPresentation(self):
        try:
            num_slide = int(self.numSlidesInput.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Errore", "Per favore, inserisci un numero valido per le slide.")
            return

        company = self.companyNameInput.text().strip()
        language = self.languageInput.currentText()

        if not language:
            QMessageBox.warning(self, "Errore", "Seleziona una lingua.")
            return

        testo_attuale = self.transcriptionTextArea.toPlainText()
        if testo_attuale.strip() == "":
            QMessageBox.warning(self, "Attenzione", "Inserisci del testo o seleziona un file di testo.")
            return

        testo_per_slide, input_tokens, output_tokens = PptxGeneration.generaTestoPerSlide(testo_attuale,
                                                                                          num_slide,
                                                                                          company,
                                                                                          language)
        print(f"Token di input utilizzati: {input_tokens}")
        print(f"Token di output utilizzati: {output_tokens}")
        self.transcriptionTextArea.setPlainText(testo_per_slide)

    def processTextWithAI(self):
        # Ottieni il testo corrente dal transcriptionTextArea
        current_text = self.transcriptionTextArea.toPlainText()

        if not current_text.strip():
            QMessageBox.warning(self, "Attenzione", "Inserisci del testo da sistemare.")
            return

        # Mostra un dialogo di progresso
        self.text_ai_thread = ProcessTextAI(
            current_text,
            self.languageComboBox.currentText(),
            mode="summary"
        )
        self.progressDialog = QProgressDialog("Riassunto testo in corso...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Sistemazione Testo")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.show()

        # Esegui il thread per il processo AI
        self.text_ai_thread = ProcessTextAI(current_text, self.languageComboBox.currentText())
        self.text_ai_thread.update_progress.connect(self.updateProgressDialog)
        self.text_ai_thread.process_complete.connect(self.onProcessComplete)
        self.text_ai_thread.process_error.connect(self.onProcessError)
        self.text_ai_thread.start()

    def fixTextWithAI(self):
        # Ottieni il testo corrente dal transcriptionTextArea
        current_text = self.transcriptionTextArea.toPlainText()

        if not current_text.strip():
            QMessageBox.warning(self, "Attenzione", "Inserisci del testo da sistemare.")
            return

        # Mostra un dialogo di progresso
        self.progressDialog = QProgressDialog("Sistemazione testo in corso...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Sistemazione Testo")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.show()

        # Esegui il thread per il processo AI
        self.text_ai_thread = ProcessTextAI(
            current_text,
            self.languageComboBox.currentText(),
            mode="fix"
        )

        self.text_ai_thread.update_progress.connect(self.updateProgressDialog)
        self.text_ai_thread.process_complete.connect(self.onProcessComplete)
        self.text_ai_thread.process_error.connect(self.onProcessError)
        self.text_ai_thread.start()
    def handleTimecodeToggle(self, checked):
        self.transcriptionTextArea.setReadOnly(
            checked)  # Disabilita la modifica del testo quando la checkbox è abilitata
        # Update the timecode insertion enabled state based on checkbox
        self.timecodeEnabled = checked

        # Trigger text change processing to update timecodes
        current_html = self.transcriptionTextArea.toHtml()
        if checked:
            self.original_text_html = current_html
            self.handleTextChange()
        else:
            self.transcriptionTextArea.setHtml(self.original_text_html)


    def updateProgressDialog(self, value, label):
        if not self.progressDialog.wasCanceled():
            self.progressDialog.setValue(value)
            self.progressDialog.setLabelText(label)

    def onProcessComplete(self, result):
        self.progressDialog.close()
        self.transcriptionTextArea.setPlainText(result)

    def onProcessError(self, error_message):
        self.progressDialog.close()
        QMessageBox.critical(self, "Errore", error_message)

    def generateAIPresentation(self):
        try:
            num_slide = int(self.numSlidesInput.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Errore", "Per favore, inserisci un numero valido per le slide.")
            return

        company = self.companyNameInput.text().strip()
        language = self.languageInput.currentText()

        #if not company:
        #    QMessageBox.warning(self, "Errore", "Il campo 'Nome della Compagnia' non può essere vuoto.")
        #    return

        if not language:
            QMessageBox.warning(self, "Errore", "Seleziona una lingua.")
            return

        testo_attuale = self.transcriptionTextArea.toPlainText()
        if testo_attuale.strip() == "":
            file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona File di Testo", "", "Text Files (*.txt)")
            if file_path:
                PptxGeneration.createPresentationFromFile(self, file_path, num_slide, company, language)
            else:
                QMessageBox.warning(self, "Attenzione", "Nessun testo inserito e nessun file selezionato.")
        else:
            save_path, _ = QFileDialog.getSaveFileName(self, "Salva Presentazione", "",
                                                       "PowerPoint Presentation (*.pptx)")
            if save_path:
                PptxGeneration.createPresentationFromText(self, testo_attuale, save_path)
            else:
                QMessageBox.warning(self, "Attenzione", "Salvataggio annullato. Nessun file selezionato.")

    def showSettingsDialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def set_default_dock_layout(self):

        # Set default visibility
        self.videoPlayerOutput.setVisible(True)
        self.recordingDock.setVisible(True)

        # Set other docks as invisible
        self.videoPlayerDock.setVisible(False)
        self.audioDock.setVisible(False)
        self.transcriptionDock.setVisible(False)
        self.editingDock.setVisible(False)
        self.downloadDock.setVisible(False)
        self.videoMergeDock.setVisible(False)
        self.generazioneAIDock.setVisible(False)

    def openRootFolder(self):
        root_folder_path = os.path.dirname(os.path.abspath(__file__))
        QDesktopServices.openUrl(QUrl.fromLocalFile(root_folder_path))

    def deleteVideoSegment(self):
        if self.videoSlider.bookmarkStart is None or self.videoSlider.bookmarkEnd is None:
            QMessageBox.warning(self, "Errore", "Per favore, imposta entrambi i bookmark prima di eliminare.")
            return

        video_path = self.videoPathLineEdit
        if not video_path:
            QMessageBox.warning(self, "Attenzione", "Per favore, seleziona un file prima di eliminarne una parte.")
            return

        try:
            video = VideoFileClip(video_path)
            audio = video.audio

            # Calcola i tempi di inizio e fine per la parte da eliminare
            start_time = self.videoSlider.bookmarkStart / 1000.0
            end_time = self.videoSlider.bookmarkEnd / 1000.0

            # Assicurati che il tempo di fine non sia oltre la durata del video
            end_time = min(end_time, video.duration)

            # Crea due parti: prima e dopo la parte da eliminare
            video_clips = []
            audio_clips = []

            if start_time > 0:
                video_clips.append(video.subclip(0, start_time))
                audio_clips.append(audio.subclip(0, start_time))
            if end_time < video.duration:
                video_clips.append(video.subclip(end_time))
                audio_clips.append(audio.subclip(end_time))

            if not video_clips:
                QMessageBox.warning(self, "Errore", "Impossibile creare il video finale. Verifica i bookmark.")
                return

            # Concatenale per creare il video finale senza la parte da eliminare
            final_video = concatenate_videoclips(video_clips)
            final_audio = concatenate_audioclips(audio_clips)

            # Sincronizza il video con l'audio
            final_video = final_video.set_audio(final_audio)

            # Genera un nome di file univoco usando un timestamp con precisione al millisecondo
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            output_dir = os.path.dirname(video_path)
            output_name = f"video_modified_{timestamp}.mp4"
            output_path = os.path.join(output_dir, output_name)

            final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

            QMessageBox.information(self, "Successo", f"Parte del video eliminata. Video salvato in: {output_path}")

            self.loadVideoOutput(output_path)
        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'eliminazione", str(e))
    def showApiKeyDialog(self):
        dialog = ApiKeyDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.api_key = dialog.get_api_key()
            logging.debug(f"API Key impostata: {self.api_key}")
    def insertPause(self):
        cursor = self.transcriptionTextArea.textCursor()
        pause_time = self.pauseTimeEdit.text().strip()

        if not re.match(r'^\d+(\.\d+)?s$', pause_time):
            QMessageBox.warning(self, "Errore", "Inserisci un formato valido per la pausa (es. 1.0s)")
            return

        pause_tag = f'<break time="{pause_time}" />'
        cursor.insertText(f' {pause_tag} ')
        self.transcriptionTextArea.setTextCursor(cursor)

    def rewind5Seconds(self):
        current_position = self.player.position()
        new_position = max(0, current_position - 5000)  # Indietro di 5000 ms = 5 secondi
        self.player.setPosition(new_position)

    def forward5Seconds(self):
        current_position = self.player.position()
        new_position = current_position + 5000  # Avanti di 5000 ms = 5 secondi
        self.player.setPosition(new_position)

    def releaseSourceVideo(self):
        self.player.stop()
        time.sleep(.01)
        self.currentTimeLabel.setText('00:00')
        self.totalTimeLabel.setText('00:00')
        self.player.setSource(QUrl())
        self.videoPathLineEdit = ''
        self.fileNameLabel.setText("Nessun video caricato")
    def releaseOutputVideo(self):
        self.playerOutput.stop()
        time.sleep(.01)
        self.currentTimeLabelOutput.setText('00:00')
        self.totalTimeLabelOutput.setText('00:00')
        self.playerOutput.setSource(QUrl())
        self.videoPathLineOutputEdit = ''
        self.fileNameLabelOutput.setText("Nessun video caricato")

    def get_nearest_timecode(self):
        # Posizione attuale del cursore nella trascrizione
        cursor_position = self.transcriptionTextArea.textCursor().position()
        text = self.transcriptionTextArea.toPlainText()

        # Trova tutti i timecode nel testo
        timecode_pattern = re.compile(r'\[(\d{2}):(\d{2})\]')
        matches = list(timecode_pattern.finditer(text))

        if not matches:
            logging.debug("Nessun timecode trovato nella trascrizione.")
            return None

        nearest_timecode = None
        min_distance = float('inf')

        for match in matches:
            start, end = match.span()  # Ottieni la posizione del timecode
            distance = abs(cursor_position - start)  # Distanza dal cursore

            if distance < min_distance:
                min_distance = distance
                nearest_timecode = match

        if nearest_timecode:
            try:
                minutes, seconds = map(int, nearest_timecode.groups())
                timecode_seconds = minutes * 60 + seconds
                logging.debug(f"Timecode più vicino: {timecode_seconds} secondi")
                return timecode_seconds
            except ValueError:
                logging.error("Errore durante la conversione del timecode in secondi.")
                return None

        logging.debug("Nessun timecode valido trovato.")
        return None

        return None

    def sync_video_to_transcription(self):
        timecode_seconds = self.get_nearest_timecode()

        if timecode_seconds is not None:
            try:
                self.player.setPosition(timecode_seconds * 1000)  # Converti in millisecondi
                logging.info(f"Video sincronizzato al timecode: {timecode_seconds} secondi")
            except Exception as e:
                logging.error(f"Errore durante la sincronizzazione del video: {e}")
                QMessageBox.critical(self, "Errore", "Impossibile sincronizzare il video.")
        else:
            logging.warning("Nessun timecode trovato o cursore posizionato in un'area senza timecode.")
            QMessageBox.warning(self, "Attenzione", "Nessun timecode trovato nella trascrizione.")

    def setStartBookmark(self):
        self.videoSlider.setBookmarkStart(self.player.position())

    def setEndBookmark(self):
        self.videoSlider.setBookmarkEnd(self.player.position())

    def cutVideoBetweenBookmarks(self):
        if self.videoSlider.bookmarkStart is None or self.videoSlider.bookmarkEnd is None:
            QMessageBox.warning(self, "Errore", "Per favore, imposta entrambi i bookmark prima di tagliare.")
            return

        media_path = self.videoPathLineEdit
        if not media_path:
            QMessageBox.warning(self, "Attenzione", "Per favore, seleziona un file prima di tagliarlo.")
            return

        if media_path.lower().endswith(('.mp4', '.mov', '.avi')):
            is_audio = False
        elif media_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac')):
            is_audio = True
        else:
            QMessageBox.warning(self, "Errore", "Formato file non supportato.")
            return

        start_time = self.videoSlider.bookmarkStart / 1000.0  # Converti in secondi
        end_time = self.videoSlider.bookmarkEnd / 1000.0  # Converti in secondi

        base_name = os.path.splitext(os.path.basename(media_path))[0]
        directory = os.path.dirname(media_path)
        ext = 'mp4' if not is_audio else 'mp3'
        output_path = os.path.join(directory, f"{base_name}_cut.{ext}")

        self.progressDialog = QProgressDialog("Taglio del file in corso...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Taglio")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.show()

        self.cutting_thread = VideoCuttingThread(media_path, start_time, end_time, output_path)
        self.cutting_thread.progress.connect(self.progressDialog.setValue)
        self.cutting_thread.completed.connect(self.onCutCompleted)
        self.cutting_thread.error.connect(self.onCutError)

        self.cutting_thread.start()

    def eventFilter(self, source, event):
        if source == self.videoCropWidget:
            if event.type() == QEvent.Type.Wheel:
                self.handleWheelEvent(event)
                return True
            elif event.type() == QEvent.Type.MouseButtonPress and event.buttons() & Qt.MouseButton.LeftButton:
                self.is_panning = True
                self.last_mouse_position = event.position().toPoint()
                return True
            elif event.type() == QEvent.Type.MouseMove and self.is_panning:
                self.handlePanEvent(event)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.is_panning = False
                return True
        return super().eventFilter(source, event)

    def handleWheelEvent(self, event):
        mouse_pos = event.position().toPoint()
        widget_pos = self.videoCropWidget.pos()
        mouse_x_in_widget = mouse_pos.x() - widget_pos.x()
        mouse_y_in_widget = mouse_pos.y() - widget_pos.y()

        # Calcola la variazione di zoom basata sul delta dello scroll della rotellina del mouse
        delta = event.angleDelta().y()
        old_zoom_level = self.zoom_level
        if delta > 0:
            self.zoom_level *= 1.1
        elif delta < 0:
            self.zoom_level *= 0.9

        self.applyVideoZoom(mouse_x_in_widget, mouse_y_in_widget, old_zoom_level)

    def applyVideoZoom(self, mouse_x, mouse_y, old_zoom_level):
        # Calcola le nuove dimensioni basate sul livello di zoom attuale
        original_size = self.videoCropWidget.sizeHint()
        new_width = int(original_size.width() * self.zoom_level)
        new_height = int(original_size.height() * self.zoom_level)
        self.videoCropWidget.resize(new_width, new_height)

        # Calcola la nuova posizione per centrare lo zoom attorno al mouse
        scale_change = self.zoom_level / old_zoom_level
        new_x = mouse_x * scale_change - mouse_x
        new_y = mouse_y * scale_change - mouse_y
        current_pos = self.videoCropWidget.pos()
        new_pos = QPoint(current_pos.x() - int(new_x), current_pos.y() - int(new_y))
        self.videoCropWidget.move(new_pos)

    def handlePanEvent(self, event):
        # Calcola la differenza di movimento
        current_position = event.position().toPoint()
        delta = current_position - self.last_mouse_position
        self.last_mouse_position = current_position

        # Sposta il contenuto del widget di video
        new_pos = self.videoCropWidget.pos() + delta
        self.videoCropWidget.move(new_pos)

    def setVolume(self, value):
        self.audioOutput.setVolume(value / 100.0)

    def setVolumeOutput(self, value):
        self.audioOutputOutput.setVolume(value / 100.0)

    def updateTimeCodeOutput(self, position):
        # Aggiorna il timecode corrente del video output
        hours, remainder = divmod(position // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.currentTimeLabelOutput.setText(f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}')

    def updateDurationOutput(self, duration):
        # Aggiorna la durata totale del video output
        hours, remainder = divmod(duration // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.totalTimeLabelOutput.setText(f' / {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}')

    def applyCrop(self):
        if not self.videoPathLineEdit or not os.path.exists(self.videoPathLineEdit):
            QMessageBox.warning(self, "Errore", "Carica un video prima di applicare il ritaglio.")
            return

        cropRect = self.videoCropWidget.getCropRect()
        logging.debug(cropRect)
        if cropRect.isEmpty():
            QMessageBox.warning(self, "Errore", "Seleziona un'area da ritagliare.")
            return

        try:
            video = VideoFileClip(self.videoPathLineEdit)
            cropped_video = video.crop(x1=cropRect.x(), y1=cropRect.y(), x2=cropRect.x() + cropRect.width(),
                                       y2=cropRect.y() + cropRect.height())
            output_path = tempfile.mktemp(suffix='.mp4')
            cropped_video.write_videofile(output_path, codec='libx264')
            QMessageBox.information(self, "Successo", f"Il video ritagliato è stato salvato in {output_path}")

            self.loadVideoOutput(output_path)
        except Exception as e:
            QMessageBox.critical(self, "Errore durante il ritaglio", str(e))

    def applyStyleToAllDocks(self):
        style = self.getDarkStyle()
        self.videoPlayerDock.setStyleSheet(style)
        self.transcriptionDock.setStyleSheet(style)
        self.editingDock.setStyleSheet(style)
        self.downloadDock.setStyleSheet(style)
        self.recordingDock.setStyleSheet(style)
        self.audioDock.setStyleSheet(style)
        self.videoPlayerOutput.setStyleSheet(style)
        self.videoMergeDock.setStyleSheet(style)
        self.generazioneAIDock.setStyleSheet(style)

    def getDarkStyle(self):
        return """
        QWidget {
            background-color: #2b2b2b;
            color: #dcdcdc;
        }
        QPushButton {
            background-color: #555555;
            border: 1px solid #666666;
            border-radius: 2px;
            padding: 5px;
            color: #ffffff;
        }
        QPushButton:hover {
            background-color: #666666;
        }
        QPushButton:pressed {
            background-color: #777777;
        }
        QLabel {
            color: #cccccc;
        }
        QLineEdit {
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 2px;
            padding: 5px;
            color: #ffffff;
        }
        """

    def setupVoiceSettingsUI(self):
        voiceSettingsGroup = QGroupBox("Impostazioni Voce")
        layout = QVBoxLayout()

        # QComboBox per la selezione della voce con opzione per inserire custom ID
        self.voiceSelectionComboBox = QComboBox()
        self.voiceSelectionComboBox.setEditable(True)
        for name, voice_id in DEFAULT_VOICES.items():
            self.voiceSelectionComboBox.addItem(name, voice_id)

        layout.addWidget(self.voiceSelectionComboBox)

        # Campo di input per ID voce
        self.voiceIdInput = QLineEdit()
        self.voiceIdInput.setPlaceholderText("ID Voce")
        layout.addWidget(self.voiceIdInput)

        # Pulsante per aggiungere la voce personalizzata
        self.addVoiceButton = QPushButton('Aggiungi Voce Personalizzata')
        self.addVoiceButton.clicked.connect(self.addCustomVoice)
        layout.addWidget(self.addVoiceButton)

        # Radio buttons per la selezione del genere vocale

        # Slider per la stabilità
        stabilityLabel = QLabel("Stabilità:")
        self.stabilitySlider = QSlider(Qt.Orientation.Horizontal)
        self.stabilitySlider.setMinimum(0)
        self.stabilitySlider.setMaximum(100)
        self.stabilitySlider.setValue(DEFAULT_STABILITY)
        self.stabilitySlider.setToolTip(
            "Regola l'emozione e la coerenza. Minore per più emozione, maggiore per coerenza.")
        self.stabilityValueLabel = QLabel("50%")  # Visualizza il valore corrente
        self.stabilitySlider.valueChanged.connect(lambda value: self.stabilityValueLabel.setText(f"{value}%"))
        layout.addWidget(stabilityLabel)
        layout.addWidget(self.stabilitySlider)
        layout.addWidget(self.stabilityValueLabel)

        # Slider per la similarità
        similarityLabel = QLabel("Similarità:")
        self.similaritySlider = QSlider(Qt.Orientation.Horizontal)
        self.similaritySlider.setMinimum(0)
        self.similaritySlider.setMaximum(100)
        self.similaritySlider.setValue(DEFAULT_SIMILARITY)
        self.similaritySlider.setToolTip(
            "Determina quanto la voce AI si avvicina all'originale. Alti valori possono includere artefatti.")
        self.similarityValueLabel = QLabel("80%")  # Visualizza il valore corrente
        self.similaritySlider.valueChanged.connect(lambda value: self.similarityValueLabel.setText(f"{value}%"))
        layout.addWidget(similarityLabel)
        layout.addWidget(self.similaritySlider)
        layout.addWidget(self.similarityValueLabel)

        # Slider per l'esagerazione dello stile
        styleLabel = QLabel("Esagerazione Stile:")
        self.styleSlider = QSlider(Qt.Orientation.Horizontal)
        self.styleSlider.setMinimum(0)
        self.styleSlider.setMaximum(10)
        self.styleSlider.setValue(DEFAULT_STYLE)
        self.styleSlider.setToolTip("Amplifica lo stile del parlante originale. Impostare a 0 per maggiore stabilità.")
        self.styleValueLabel = QLabel("0")  # Visualizza il valore corrente
        self.styleSlider.valueChanged.connect(lambda value: self.styleValueLabel.setText(f"{value}"))
        layout.addWidget(styleLabel)
        layout.addWidget(self.styleSlider)
        layout.addWidget(self.styleValueLabel)

        # Checkbox per l'uso di speaker boost
        self.speakerBoostCheckBox = QCheckBox("Usa Speaker Boost")
        self.speakerBoostCheckBox.setChecked(True)
        self.speakerBoostCheckBox.setToolTip(
            "Potenzia la somiglianza col parlante originale a costo di maggiori risorse.")
        layout.addWidget(self.speakerBoostCheckBox)

        # Sincronizzazione labiale
        self.useWav2LipCheckbox = QCheckBox("Sincronizzazione labiale")
        layout.addWidget(self.useWav2LipCheckbox)
        self.useWav2LipCheckbox.setVisible(False)

        # Pulsanti per le diverse funzionalità
        self.generateAudioButton = QPushButton('Genera Audio con AI')
        self.generateAudioButton.clicked.connect(self.generateAudioWithElevenLabs)
        layout.addWidget(self.generateAudioButton)

        voiceSettingsGroup.setLayout(layout)
        return voiceSettingsGroup

    def addCustomVoice(self):
        custom_name = self.voiceSelectionComboBox.currentText().strip()
        voice_id = self.voiceIdInput.text().strip()
        if custom_name and voice_id:
            self.voiceSelectionComboBox.addItem(custom_name, voice_id)
            self.voiceSelectionComboBox.setCurrentText(custom_name)
            self.voiceIdInput.clear()
        else:
            QMessageBox.warning(self, "Errore",
                                "Entrambi i campi devono essere compilati per aggiungere una voce personalizzata.")


    def applyFreezeFramePause(self):
        video_path = self.videoPathLineEdit
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "Errore", "Carica un video prima di applicare una pausa.")
            return

        try:
            # Estrazione del timecode e della durata della pausa
            timecode = self.timecodeVideoPauseLineEdit.text()
            pause_duration = int(self.pauseVideoDurationLineEdit.text())
            hours, minutes, seconds = map(int, timecode.split(':'))
            start_time = hours * 3600 + minutes * 60 + seconds

            # Caricamento del video
            video_clip = VideoFileClip(video_path)

            # Ottenere l'ultimo frame dal timecode specificato
            freeze_frame = video_clip.get_frame(start_time)

            # Creare un clip di immagine dal frame congelato e impostare la sua durata
            freeze_clip = ImageClip(freeze_frame).set_duration(pause_duration).set_fps(video_clip.fps)

            # Utilizzare il metodo `fx` per evitare subclip multipli
            original_video_part1 = video_clip.subclip(0, start_time).fx(vfx.freeze, t=start_time,
                                                                        freeze_duration=pause_duration)

            # Creazione del video finale con audio originale
            final_video = concatenate_videoclips([original_video_part1, freeze_clip, video_clip.subclip(start_time)],
                                                 method="compose")
            final_video = final_video.set_audio(video_clip.audio)

            # Salvataggio del video finale
            output_path = tempfile.mktemp(suffix='.mp4')
            final_video.write_videofile(output_path, codec='libx264')
            QMessageBox.information(self, "Successo", f"Video con pausa frame congelato salvato in {output_path}")
            self.loadVideoOutput(output_path)
        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'applicazione della pausa frame congelato", str(e))

    def createAudioDock(self):
        dock =CustomDock("Gestione Audio", closable=True)
        layout = QGridLayout()

        # GroupBox per la sostituzione dell'audio principale
        audioReplacementGroup = self.createAudioReplacementGroup()
        layout.addWidget(audioReplacementGroup, 1, 1, 1, 1)

        # GroupBox per l'applicazione delle pause audio
        audioPauseGroup = self.createAudioPauseGroup()
        layout.addWidget(audioPauseGroup, 1, 0)

        # GroupBox per l'applicazione delle pause video
        videoPauseGroup = self.createVideoPauseGroup()
        layout.addWidget(videoPauseGroup, 2, 0)

        # GroupBox per la gestione dell'audio di sottofondo
        backgroundAudioGroup = self.createBackgroundAudioGroup()
        layout.addWidget(backgroundAudioGroup, 2, 1, 1, 1)  # Estendi questo widget su 3 righe

        widget = QWidget()
        widget.setLayout(layout)
        dock.addWidget(widget)

        return dock

    def createAudioReplacementGroup(self):
        audioReplacementGroup = QGroupBox("Sostituzione Audio Principale")
        layout = QVBoxLayout()

        self.audioPathLineEdit = QLineEdit()
        self.audioPathLineEdit.setReadOnly(True)

        browseAudioButton = QPushButton('Scegli Audio Principale')
        browseAudioButton.clicked.connect(self.browseAudio)

        self.alignAudioVideoCheckBox = QCheckBox('Allinea video e audio')

        applyAudioButton = QPushButton('Applica Audio Principale')
        applyAudioButton.clicked.connect(
            lambda: self.applyNewAudioToVideo(self.videoPathLineEdit, self.audioPathLineEdit.text(),
                                              self.alignAudioVideoCheckBox.isChecked()))

        layout.addWidget(self.audioPathLineEdit)
        layout.addWidget(browseAudioButton)
        layout.addWidget(self.alignAudioVideoCheckBox)
        layout.addWidget(applyAudioButton)
        audioReplacementGroup.setLayout(layout)

        return audioReplacementGroup

    def createAudioPauseGroup(self):
        audioPauseGroup = QGroupBox("Applica Pause Audio")
        layout = QVBoxLayout()

        # User enters the timecode for the audio pause start
        self.timecodePauseLineEdit = QLineEdit()
        self.timecodePauseLineEdit.setPlaceholderText("Inserisci Timecode (hh:mm:ss)")

        # Pulsante per prelevare il timecode dalla slider
        getTimecodeButton = QPushButton("Preleva Timecode")
        getTimecodeButton.clicked.connect(self.setTimecodePauseFromSlider)

        # Layout orizzontale per il timecode e il pulsante
        timecodeLayout = QHBoxLayout()
        timecodeLayout.addWidget(self.timecodePauseLineEdit)
        timecodeLayout.addWidget(getTimecodeButton)

        layout.addWidget(QLabel("Timecode Inizio Pausa:"))
        layout.addLayout(timecodeLayout)

        # User enters the duration of the pause here in seconds
        self.pauseAudioDurationLineEdit = QLineEdit()
        self.pauseAudioDurationLineEdit.setPlaceholderText("Durata Pausa (secondi)")
        layout.addWidget(QLabel("Durata Pausa (s):"))
        layout.addWidget(self.pauseAudioDurationLineEdit)

        # Button to apply the pause
        applyPauseButton = QPushButton('Applica Pause Audio')
        applyPauseButton.clicked.connect(self.applyAudioWithPauses)
        layout.addWidget(applyPauseButton)
        audioPauseGroup.setLayout(layout)

        return audioPauseGroup

    def createVideoPauseGroup(self):
        videoPauseGroup = QGroupBox("Applica Pausa Video")
        layout = QVBoxLayout()

        self.timecodeVideoPauseLineEdit = QLineEdit()
        self.timecodeVideoPauseLineEdit.setPlaceholderText("Inserisci Timecode (hh:mm:ss)")

        # Pulsante per prelevare il timecode dalla slider
        getTimecodeButton = QPushButton("Preleva Timecode")
        getTimecodeButton.clicked.connect(self.setTimecodeVideoFromSlider)

        # Layout orizzontale per il timecode e il pulsante
        timecodeLayout = QHBoxLayout()
        timecodeLayout.addWidget(self.timecodeVideoPauseLineEdit)
        timecodeLayout.addWidget(getTimecodeButton)

        layout.addWidget(QLabel("Timecode Inizio Pausa:"))
        layout.addLayout(timecodeLayout)

        self.pauseVideoDurationLineEdit = QLineEdit()
        self.pauseVideoDurationLineEdit.setPlaceholderText("Durata Pausa (secondi)")
        layout.addWidget(QLabel("Durata Pausa (s):"))
        layout.addWidget(self.pauseVideoDurationLineEdit)
        applyVideoPauseButton = QPushButton('Applica Pausa Video')
        applyVideoPauseButton.clicked.connect(self.applyFreezeFramePause)
        layout.addWidget(applyVideoPauseButton)
        videoPauseGroup.setLayout(layout)

        return videoPauseGroup

    def createBackgroundAudioGroup(self):
        backgroundAudioGroup = QGroupBox("Gestione Audio di Sottofondo")
        layout = QVBoxLayout()

        self.backgroundAudioPathLineEdit = QLineEdit()
        self.backgroundAudioPathLineEdit.setReadOnly(True)
        browseBackgroundAudioButton = QPushButton('Scegli Sottofondo')
        browseBackgroundAudioButton.clicked.connect(self.browseBackgroundAudio)
        self.volumeSliderBack = QSlider(Qt.Orientation.Horizontal)
        self.volumeSliderBack.setRange(0, 1000)
        self.volumeSliderBack.setValue(6)
        self.volumeSliderBack.valueChanged.connect(self.adjustBackgroundVolume)

        self.volumeLabelBack = QLabel(f"Volume Sottofondo: {self.volumeSliderBack.value() / 1000:.3f}")

        applyBackgroundButton = QPushButton('Applica Sottofondo al Video')
        applyBackgroundButton.clicked.connect(self.applyBackgroundAudioToVideo)

        layout.addWidget(self.backgroundAudioPathLineEdit)
        layout.addWidget(browseBackgroundAudioButton)
        layout.addWidget(QLabel("Volume Sottofondo:"))
        layout.addWidget(self.volumeSliderBack)
        layout.addWidget(self.volumeLabelBack)
        layout.addWidget(applyBackgroundButton)
        backgroundAudioGroup.setLayout(layout)

        return backgroundAudioGroup

    def adjustBackgroundVolume(self):
        slider_value = self.volumeSliderBack.value()
        normalized_volume = np.exp(slider_value / 1000 * np.log(2)) - 1
        self.volumeLabelBack.setText(f"Volume Sottofondo: {normalized_volume:.3f}")
    def setTimecodePauseFromSlider(self):
        current_position = self.player.position()
        self.timecodePauseLineEdit.setText(self.formatTimecode(current_position))
    def setTimecodeVideoFromSlider(self):
        current_position = self.player.position()
        self.timecodeVideoPauseLineEdit.setText(self.formatTimecode(current_position))

    def createVideoMergeDock(self):
        """Crea e restituisce il dock per la gestione dell'unione di video."""
        dock =CustomDock("Unione Video", closable=True)

        # GroupBox per organizzare visivamente le opzioni di unione video
        mergeGroup = QGroupBox("Opzioni di Unione Video")
        mergeLayout = QVBoxLayout()

        # Widget per selezionare il video da unire
        self.mergeVideoPathLineEdit = QLineEdit()
        self.mergeVideoPathLineEdit.setReadOnly(True)
        browseMergeVideoButton = QPushButton('Scegli Video da Unire')
        browseMergeVideoButton.clicked.connect(self.browseMergeVideo)

        # Widget per inserire il timecode
        self.timecodeVideoMergeLineEdit = QLineEdit()
        self.timecodeVideoMergeLineEdit.setPlaceholderText("Inserisci il timecode (formato hh:mm:ss)")

        # Pulsante per prelevare il timecode dalla posizione corrente del video
        getTimecodeButton = QPushButton("Preleva Timecode")
        getTimecodeButton.clicked.connect(self.setTimecodeMergeFromSlider)

        # Layout orizzontale per il timecode e il pulsante
        timecodeLayout = QHBoxLayout()
        timecodeLayout.addWidget(self.timecodeVideoMergeLineEdit)
        timecodeLayout.addWidget(getTimecodeButton)

        # Pulsante per unire il video
        mergeButton = QPushButton('Unisci Video')
        mergeButton.clicked.connect(self.mergeVideo)

        # Aggiunta dei controlli al layout della GroupBox
        mergeLayout.addWidget(self.mergeVideoPathLineEdit)
        mergeLayout.addWidget(browseMergeVideoButton)
        mergeLayout.addWidget(QLabel("Timecode Inizio Unione:"))
        mergeLayout.addLayout(timecodeLayout)
        mergeLayout.addWidget(mergeButton)

        # Imposta il layout del GroupBox
        mergeGroup.setLayout(mergeLayout)

        # Widget principale per il dock
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(mergeGroup)
        dock.addWidget(widget)

        return dock

    def setTimecodeMergeFromSlider(self):
        current_position = self.player.position()
        self.timecodeVideoMergeLineEdit.setText(self.formatTimecode(current_position))

    def formatTimecode(self, position_ms):
        hours, remainder = divmod(position_ms // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def mergeVideo(self):
        base_video_path = self.videoPathLineEdit
        merge_video_path = self.mergeVideoPathLineEdit.text()
        timecode = self.timecodeVideoMergeLineEdit.text()

        if not base_video_path or not os.path.exists(base_video_path):
            QMessageBox.warning(self, "Errore", "Carica il video principale prima di unirne un altro.")
            return

        if not merge_video_path or not os.path.exists(merge_video_path):
            QMessageBox.warning(self, "Errore", "Seleziona un video da unire.")
            return

        try:
            base_clip = VideoFileClip(base_video_path)
            merge_clip = VideoFileClip(merge_video_path)
            # Converti il timecode in secondi
            tc_hours, tc_minutes, tc_seconds = map(int, timecode.split(':'))
            tc_seconds_total = tc_hours * 3600 + tc_minutes * 60 + tc_seconds

            # Unisci i video inserendo il secondo video al timecode specificato
            final_clip = concatenate_videoclips([
                base_clip.subclip(0, tc_seconds_total),
                merge_clip,
                base_clip.subclip(tc_seconds_total)
            ], method='compose')

            # Genera il percorso del file di output
            base_dir = os.path.dirname(base_video_path)
            base_name = os.path.splitext(os.path.basename(base_video_path))[0]
            output_path = os.path.join(base_dir, f"{base_name}_merged.mp4")

            final_clip.write_videofile(output_path, codec='libx264')
            QMessageBox.information(self, "Successo", f"Il video unito è stato salvato in {output_path}")

            # Aggiorna il percorso del video per il player
            self.loadVideoOutput(output_path)
        except Exception as e:
            QMessageBox.warning(self, "Errore", "Si è verificato un errore durante l'unione dei video: " + str(e))

    def browseMergeVideo(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video da Unire", "",
                                                  "Video Files (*.mp4 *.mov *.avi)")
        if fileName:
            self.mergeVideoPathLineEdit.setText(fileName)

    def browseBackgroundAudio(self):
        # Imposta il percorso di default per l'apertura della finestra di dialogo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        default_dir = MUSIC_DIR

        # Verifica se la cartella di default esiste
        if not os.path.exists(default_dir):
            QMessageBox.warning(self, "Errore", "La cartella di default non esiste.")
            return

        # Apri la finestra di dialogo per selezionare il file audio
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio di Sottofondo", default_dir,
                                                  "Audio Files (*.mp3 *.wav)")

        # Se un file è stato selezionato, imposta il percorso nel LineEdit
        if fileName:
            self.backgroundAudioPathLineEdit.setText(fileName)
    def setupDockSettingsManager(self):

        settings_file = './dock_settings.json'
        if os.path.exists(settings_file):
            self.dockSettingsManager.load_settings(settings_file)
        else:
            self.set_default_dock_layout()
        self.resetViewMenu()

    def closeEvent(self, event):
        self.dockSettingsManager.save_settings()
        #self.teams_call_recorder.stop()
        event.accept()

    def selectDefaultScreen(self):
        """Seleziona il primo schermo di default."""
        if self.screen_buttons:
            self.selectScreen(0)



    def selectScreen(self, screen_index):
        self.selected_screen_index = screen_index
        for button in self.screen_buttons:
            if button.screen_number == screen_index + 1:
                button.setStyleSheet("QPushButton { background-color: #1a93ec; color: white; }")
            else:
                button.setStyleSheet("QPushButton { background-color: gray; color: white; }")


    def browseFolderLocation(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella")
        if folder:
            self.folderPathLineEdit.setText(folder)
    def openFolder(self):
        folder_path = self.folderPathLineEdit.text() or "screenrecorder"
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def setDefaultAudioDevice(self):
        """Imposta il primo dispositivo audio come predefinito se disponibile."""
        if self.audio_buttons:
            self.audio_buttons[0].setChecked(True)

    def applyBackgroundAudioToVideo(self):
        video_path = self.videoPathLineEdit  # Percorso del video attualmente caricato
        background_audio_path = self.backgroundAudioPathLineEdit.text()  # Percorso dell'audio di sottofondo scelto
        slider_value = self.volumeSliderBack.value()
        background_volume = np.exp(slider_value / 1000 * np.log(2)) - 1  # Normalizza e usa una scala logaritmica

        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "Errore", "Carica un video prima di applicare l'audio di sottofondo.")
            return

        if not background_audio_path or not os.path.exists(background_audio_path):
            QMessageBox.warning(self, "Errore", "Carica un audio di sottofondo prima di applicarlo.")
            return

        try:
            # Carica video e audio di sottofondo
            video_clip = VideoFileClip(video_path)
            background_audio_clip = AudioFileClip(background_audio_path).volumex(background_volume)

            # Verifica che la durata dell'audio di sottofondo sia sufficiente
            if background_audio_clip.duration < video_clip.duration:
                background_audio_clip = background_audio_clip.loop(duration=video_clip.duration)

            # Combina l'audio di sottofondo con l'audio originale del video, se presente
            if video_clip.audio:
                combined_audio = CompositeAudioClip(
                    [video_clip.audio, background_audio_clip.set_duration(video_clip.duration)])
            else:
                combined_audio = background_audio_clip.set_duration(video_clip.duration)

            # Imposta l'audio combinato nel video e salva il nuovo file
            final_clip = video_clip.set_audio(combined_audio)
            output_path = tempfile.mktemp(suffix='.mp4')
            final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')

            QMessageBox.information(self, "Successo",
                                    f"Il video con audio di sottofondo è stato salvato in {output_path}")
            self.loadVideoOutput(output_path)  # Carica il video aggiornato nell'interfaccia
        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'applicazione dell'audio di sottofondo", str(e))

    def applyAudioWithPauses(self):
        video_path = self.videoPathLineEdit  # Path of the currently loaded video

        # Retrieve the timecode and pause duration from user input
        timecode = self.timecodePauseLineEdit.text()
        pause_duration = float(self.pauseAudioDurationLineEdit.text() or 0)

        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "Errore", "Carica un video prima di applicare la pausa audio.")
            return

        try:
            # Estrai l'audio dal video
            video_clip = VideoFileClip(video_path)
            audio_clip = video_clip.audio
            original_audio_path = tempfile.mktemp(suffix='.mp3')  # Temporary path for the audio
            audio_clip.write_audiofile(original_audio_path)  # Save the extracted audio

            # Convert the timecode into seconds
            hours, minutes, seconds = map(int, timecode.split(':'))
            start_time = hours * 3600 + minutes * 60 + seconds

            # Load the audio using moviepy
            original_audio = AudioFileClip(original_audio_path)
            total_duration = original_audio.duration

            # Create the silent audio segment for the pause
            silent_audio_path = tempfile.mktemp(suffix='.mp3')
            silent_audio = AudioSegment.silent(duration=pause_duration * 1000)  # duration in milliseconds
            silent_audio.export(silent_audio_path, format="mp3")

            # Load the silent audio segment using moviepy
            silent_audio_clip = AudioFileClip(silent_audio_path).set_duration(pause_duration)

            # Split the audio and insert the silent segment
            first_part = original_audio.subclip(0, start_time)
            second_part = original_audio.subclip(start_time, total_duration)
            new_audio = concatenate_audioclips([first_part, silent_audio_clip, second_part])

            # Save the modified audio to a temporary path
            temp_audio_path = tempfile.mktemp(suffix='.mp3')
            new_audio.write_audiofile(temp_audio_path)

            # Adapt the speed of the video to match the new audio duration
            output_path = tempfile.mktemp(suffix='.mp4')
            self.adattaVelocitaVideoAAudio(video_path, temp_audio_path, output_path)

            QMessageBox.information(self, "Successo", f"Video con pausa audio salvato in {output_path}")
            self.loadVideoOutput(output_path)

            # Clean up the temporary audio file
            os.remove(temp_audio_path)
            os.remove(original_audio_path)
            os.remove(silent_audio_path)
        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'applicazione della pausa audio", str(e))

    def updateTimecodeRec(self):
        if self.recordingTime is not None:
            self.recordingTime = self.recordingTime.addSecs(1)
            self.timecodeLabel.setText(self.recordingTime.toString("hh:mm:ss"))


    def selectAudioDevice(self):
        selected_audio = None
        device_index = None
        for index, button in enumerate(self.audio_buttons):
            if button.isChecked():
                selected_audio = button.text()
                device_index = index
                break
        self.audio_input = selected_audio  # Update the audio input name
        if selected_audio:
            if device_index is not None and self.test_audio_device(device_index):
                self.audioTestResultLabel.setText(f"Test Audio: Periferica OK")
            else:
                self.audioTestResultLabel.setText(f"Test Audio: Periferica KO")

    def test_audio_device(self, device_index):
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, input_device_index=device_index)
            data = stream.read(1024)
            stream.close()
            if np.frombuffer(data, dtype=np.int16).any():
                return True
            return False
        except Exception as e:
            return False
        finally:
            p.terminate()

    def print_audio_devices(self):
        p = pyaudio.PyAudio()
        num_devices = p.get_device_count()
        audio_devices = {}

        def is_similar(name1, name2, threshold=0.8):
            # Check if two names are similar above a certain threshold
            return SequenceMatcher(None, name1, name2).ratio() > threshold

        for i in range(num_devices):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0 and self.test_audio_device(i):
                # Include only the primary microphone and stereo mix
                if 'microphone' in device_info.get('name').lower() or 'stereo mix' in device_info.get('name').lower():
                    device_name = device_info.get('name')

                    # Check for duplicates with similar names
                    to_add = True
                    to_remove = None
                    for existing_name in audio_devices.keys():
                        if is_similar(device_name, existing_name):
                            if len(device_name) > len(existing_name):
                                to_remove = existing_name
                            else:
                                to_add = False
                            break

                    if to_remove:
                        del audio_devices[to_remove]
                    if to_add:
                        audio_devices[device_name] = device_info.get('name')

        p.terminate()
        return list(audio_devices.keys())  # Convert the dictionary keys back to a list

    def createRecordingDock(self):
        dock =CustomDock("Registrazione", closable=True)
        self.rec_timer = QTimer()
        self.rec_timer.timeout.connect(self.updateTimecodeRec)

        # Group Box for Info
        infoGroup = QGroupBox("Info")
        infoLayout = QVBoxLayout(infoGroup)

        self.timecodeLabel = QLabel('00:00:00')
        self.timecodeLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.timecodeLabel.setStyleSheet("QLabel { font-size: 24pt; }")
        infoLayout.addWidget(self.timecodeLabel)

        self.recordingStatusLabel = QLabel("Stato: Pronto per la registrazione")
        self.recordingStatusLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        infoLayout.addWidget(self.recordingStatusLabel)

        self.audioTestResultLabel = QLabel("Risultato Test Audio: N/A")
        self.audioTestResultLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        infoLayout.addWidget(self.audioTestResultLabel)

        # Main Layout for Recording Management
        recordingLayout = QVBoxLayout()

        # Screen selection grid
        screensGroupBox = QGroupBox("Seleziona Schermo")
        screensLayout = QGridLayout(screensGroupBox)

        self.screen_buttons = []
        for i, monitor in enumerate(get_monitors()):
            screen_button = ScreenButton(f"", i + 1)
            screen_button.clicked.connect(lambda checked, idx=i: self.selectScreen(idx))
            screensLayout.addWidget(screen_button, i // 3, i % 3)
            self.screen_buttons.append(screen_button)

        recordingLayout.addWidget(screensGroupBox)

        # Audio selection group box
        audioGroupBox = QGroupBox("Seleziona Audio")
        audioLayout = QVBoxLayout(audioGroupBox)
        audioLayout.addWidget(self.audioTestResultLabel)

        self.audio_buttons = []
        audio_devices = self.print_audio_devices()
        if audio_devices:
            for device in audio_devices:
                radio_button = QRadioButton(device)
                radio_button.toggled.connect(self.selectAudioDevice)
                audioLayout.addWidget(radio_button)
                self.audio_buttons.append(radio_button)
        else:
            logging.debug("No input audio devices found.")
        recordingLayout.addWidget(audioGroupBox)

        saveOptionsGroup = QGroupBox("Opzioni di Salvataggio")
        saveOptionsLayout = QVBoxLayout(saveOptionsGroup)

        self.folderPathLineEdit = QLineEdit()
        self.folderPathLineEdit.setPlaceholderText("Inserisci il percorso della cartella di destinazione")

        self.saveVideoOnlyCheckBox = QCheckBox("Salva solo il video")
        saveOptionsLayout.addWidget(self.saveVideoOnlyCheckBox)
        saveOptionsLayout.addWidget(QLabel("Percorso File:"))

        saveOptionsLayout.addWidget(self.folderPathLineEdit)

        buttonsLayout = QHBoxLayout()
        browseButton = QPushButton('Sfoglia')
        browseButton.clicked.connect(self.browseFolderLocation)
        buttonsLayout.addWidget(browseButton)

        open_folder_button = QPushButton('Apri Cartella')
        open_folder_button.clicked.connect(self.openFolder)
        buttonsLayout.addWidget(open_folder_button)

        self.recordingNameLineEdit = QLineEdit()
        self.recordingNameLineEdit.setPlaceholderText("Inserisci il nome della registrazione")
        saveOptionsLayout.addLayout(buttonsLayout)

        saveOptionsLayout.addWidget(QLabel("Nome della Registrazione:"))
        saveOptionsLayout.addWidget(self.recordingNameLineEdit)

        recordingLayout.addWidget(saveOptionsGroup)

        # Aggiungi la checkbox per abilitare la registrazione automatica delle chiamate di Teams
        self.autoRecordTeamsCheckBox = QCheckBox("Abilita registrazione automatica per Teams")
        # recordingLayout.addWidget(self.autoRecordTeamsCheckBox)

        self.startRecordingButton = QPushButton("")
        self.startRecordingButton.setIcon(QIcon("./res/rec.png"))
        self.startRecordingButton.setToolTip("Inizia la registrazione")

        self.stopRecordingButton = QPushButton("")
        self.stopRecordingButton.setIcon(QIcon("./res/stop.png"))
        self.stopRecordingButton.setToolTip("Ferma la registrazione")

        self.pauseRecordingButton = QPushButton("")
        self.pauseRecordingButton.setIcon(QIcon("./res/pausa_play.png"))
        self.pauseRecordingButton.setToolTip("Pausa/Riprendi la registrazione")
        self.pauseRecordingButton.setEnabled(False)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.startRecordingButton)
        buttonLayout.addWidget(self.stopRecordingButton)
        buttonLayout.addWidget(self.pauseRecordingButton)

        self.startRecordingButton.clicked.connect(self.startScreenRecording)
        self.stopRecordingButton.clicked.connect(self.stopScreenRecording)
        self.pauseRecordingButton.clicked.connect(self.togglePauseResumeRecording)

        recordingLayout.addLayout(buttonLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(infoGroup)
        mainLayout.addLayout(recordingLayout)

        widget = QWidget()
        widget.setLayout(mainLayout)

        dock.addWidget(widget)

        self.setDefaultAudioDevice()
        self.selectDefaultScreen()
        return dock

    def startScreenRecording(self):
        self.startRecordingButton.setEnabled(False)
        self.pauseRecordingButton.setEnabled(True)
        self.stopRecordingButton.setEnabled(True)
        self.recording_segments = []  # Initialize the list to store recording segments
        self.is_paused = False

        self.recordingTime = QTime(0, 0, 0)
        self.rec_timer.start(1000)
        self._startRecordingSegment()

    def _startRecordingSegment(self):
        selected_audio = None
        for button in self.audio_buttons:
            if button.isChecked():
                selected_audio = button.text()
                break

        folder_path = self.folderPathLineEdit.text().strip()
        save_video_only = self.saveVideoOnlyCheckBox.isChecked()
        self.timecodeLabel.setStyleSheet("QLabel { font-size: 24pt; color: red; }")

        monitor_index = self.selected_screen_index if self.selected_screen_index is not None else 0

        recording_name = self.recordingNameLineEdit.text().strip()
        if not recording_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            recording_name = f"recording_{timestamp}"

        if not folder_path:
            default_folder = os.path.join(os.getcwd(), 'screenrecorder')
        else:
            default_folder = folder_path
        os.makedirs(default_folder, exist_ok=True)

        segment_file_path = os.path.join(default_folder, f"{recording_name}.mp4")

        while os.path.exists(segment_file_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            segment_file_path = os.path.join(default_folder, f"{recording_name}_{timestamp}.mp4")

        ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'
        if not os.path.exists(ffmpeg_path):
            QMessageBox.critical(self, "Errore",
                                 "L'eseguibile ffmpeg.exe non è stato trovato. Assicurati che sia presente nella directory.")
            self.startRecordingButton.setEnabled(True)
            return

        if not save_video_only and not selected_audio:
            QMessageBox.critical(self, "Errore",
                                 "Nessun dispositivo audio selezionato. Seleziona un dispositivo audio o abilita l'opzione 'Salva solo il video'.")
            self.startRecordingButton.setEnabled(True)
            return

        self.recorder_thread = ScreenRecorder(
            output_path=segment_file_path,
            ffmpeg_path=ffmpeg_path,
            monitor_index=monitor_index,
            audio_input=selected_audio if not save_video_only else None,
            audio_channels=DEFAULT_AUDIO_CHANNELS if not save_video_only else 0,
            frames=DEFAULT_FRAME_RATE
        )

        self.recorder_thread.error_signal.connect(self.showError)
        self.recorder_thread.start()

        self.recording_segments.append(segment_file_path)
        self.current_video_path = segment_file_path
        self.recordingStatusLabel.setText(f'Stato: Registrazione iniziata di Schermo {monitor_index + 1}')

    def togglePauseResumeRecording(self):
        if self.is_paused:
            self.resumeScreenRecording()
        else:
            self.pauseScreenRecording()

    def pauseScreenRecording(self):
        if hasattr(self, 'recorder_thread') and self.recorder_thread is not None:
            self.recorder_thread.stop()
            self.recorder_thread.wait()  # Ensure the thread has finished
            self.rec_timer.stop()
            self.recordingStatusLabel.setText('Stato: Registrazione in pausa')
            self.is_paused = True

    def resumeScreenRecording(self):
        self._startRecordingSegment()
        self.rec_timer.start(1000)
        self.recordingStatusLabel.setText('Stato: Registrazione ripresa')

        self.is_paused = False

    def stopScreenRecording(self):
        self.pauseRecordingButton.setEnabled(False)
        self.startRecordingButton.setEnabled(True)
        self.pauseRecordingButton.setEnabled(False)
        self.stopRecordingButton.setEnabled(False)
        self.rec_timer.stop()
        if hasattr(self, 'recorder_thread') and self.recorder_thread is not None:
            self.timecodeLabel.setStyleSheet("QLabel { font-size: 24pt; }")
            self.recorder_thread.stop()
            self.recorder_thread.wait()  # Ensure the thread has finished

        if hasattr(self, 'current_video_path'):
            self._mergeSegments()

        self.recordingStatusLabel.setText("Stato: Registrazione Terminata e video salvato.")
        self.timecodeLabel.setText('00:00:00')

    import datetime

    def _mergeSegments(self):
        if len(self.recording_segments) > 1:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = self.recording_segments[0].rsplit('_', 1)[0] + f'_final_{timestamp}.mp4'
            ffmpeg_path = 'ffmpeg/bin/ffmpeg.exe'

            segments_file = "segments.txt"
            with open(segments_file, "w") as file:
                for segment in self.recording_segments:
                    file.write(f"file '{segment}'\n")

            merge_command = [ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', segments_file, '-c', 'copy', output_path]
            subprocess.run(merge_command)

            QMessageBox.information(self, "File Salvato",
                                    f"Il video finale è stato salvato correttamente:\nVideo: {output_path}")
            self.loadVideoOutput(output_path)
        else:
            output_path = self.recording_segments[0]
            QMessageBox.information(self, "File Salvato",
                                    f"Il video è stato salvato correttamente:\nVideo: {output_path}")
            self.loadVideoOutput(output_path)

    def showError(self, message):
        logging.error("Error recording thread:",message)
        #QMessageBox.critical(self, "Errore", message)

    def saveText(self):
        # Apri il dialogo di salvataggio file e ottieni il percorso del file e il filtro selezionato dall'utente
        path, _ = QFileDialog.getSaveFileName(self, "Salva file", "", "Text files (*.txt);;All files (*.*)")

        # Controlla se l'utente ha effettivamente scelto un file
        if path:
            # Ottieni il testo dal QTextEdit
            text_to_save = self.transcriptionTextArea.toPlainText()

            # Prova a salvare il testo nel file scelto
            try:
                with open(path, 'w') as file:
                    file.write(text_to_save)
                logging.debug("File salvato correttamente!")
            except Exception as e:
                logging.debug("Errore durante il salvataggio del file:", e)

    def loadText(self):
        # Apri il dialogo per la selezione del file da caricare
        path, _ = QFileDialog.getOpenFileName(self, "Carica file", "", "Text files (*.txt);;All files (*.*)")

        # Controlla se l'utente ha effettivamente selezionato un file
        if path:
            try:
                # Leggi il contenuto del file
                with open(path, 'r') as file:
                    text_loaded = file.read()

                # Imposta il contenuto nel QTextEdit
                self.transcriptionTextArea.setPlainText(text_loaded)
                logging.debug("File caricato correttamente!")
            except Exception as e:
                logging.debug("Errore durante il caricamento del file:", e)

    def createDownloadDock(self):
        """Crea e restituisce il dock per il download di video."""
        dock =CustomDock("Download Video", closable=True)

        # GroupBox per organizzare visivamente le opzioni di download
        downloadGroup = QGroupBox("Opzioni di Download Video")
        downloadLayout = QVBoxLayout()

        # Widget per inserire l'URL del video di YouTube
        url_label = QLabel("Inserisci l'URL di YouTube:")
        url_edit = QLineEdit()

        # CheckBox per selezionare se scaricare anche il video
        video_checkbox = QCheckBox("Scarica anche il video")

        # Bottone per iniziare il download
        download_btn = QPushButton("Download Video")
        download_btn.clicked.connect(lambda: self.handleDownload(url_edit.text(), video_checkbox.isChecked(), FFMPEG_PATH_DOWNLOAD))

        # Aggiunta dei controlli al layout della GroupBox
        downloadLayout.addWidget(url_label)
        downloadLayout.addWidget(url_edit)
        downloadLayout.addWidget(video_checkbox)
        downloadLayout.addWidget(download_btn)

        # Imposta il layout del GroupBox
        downloadGroup.setLayout(downloadLayout)

        # Widget principale per il dock
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(downloadGroup)
        dock.addWidget(widget)

        return dock

    def handleDownload(self, url, download_video, ffmpeg_path):
        if url:
            self.downloadThread = DownloadThread(url, download_video, ffmpeg_path)
            self.downloadThread.finished.connect(self.onDownloadFinished)
            self.downloadThread.error.connect(self.onError)
            self.downloadThread.progress.connect(self.updateDownloadProgress)

            # Collega il nuovo segnale per gli URL di streaming
            if hasattr(self.downloadThread, 'stream_url_found'):
                self.downloadThread.stream_url_found.connect(self.onStreamUrlFound)

            self.downloadThread.start()
            self.showDownloadProgress()

    def onStreamUrlFound(self, stream_url):
        """Gestisce l'URL di streaming trovato"""
        logging.debug(f"URL di streaming trovato: {stream_url}")

    def showDownloadProgress(self):
        self.progressDialog = QProgressDialog("Downloading video...", "Abort", 0, 100, self)
        self.progressDialog.setWindowTitle("Download Progress")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.canceled.connect(self.downloadThread.terminate)  # Connect cancel action
        self.progressDialog.show()

    def updateDownloadProgress(self, progress):
        if not self.progressDialog.wasCanceled():
            self.progressDialog.setValue(progress)

    def onDownloadFinished(self, file_path, video_title, video_language):
        self.progressDialog.close()
        QMessageBox.information(self, "Download Complete", f"File saved to {file_path}.")
        self.video_download_language = video_language
        logging.debug(video_language)
        self.loadVideo(file_path, video_title)

    def onError(self, error_message):
        self.progressDialog.close()
        QMessageBox.critical(self, "Download Error", error_message)

    def isAudioOnly(self, file_path):
        """Check if the file is likely audio-only based on the extension."""
        audio_extensions = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg'}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in audio_extensions

    def sourceSetter(self, url):
        self.player.setSource(QUrl.fromLocalFile(url))
        #self.player.play()

    def sourceSetterOutput(self, url):
        self.playerOutput.setSource(QUrl.fromLocalFile(url))
        self.playerOutput.play()

    def loadVideo(self, video_path, video_title = 'Video Track'):
        """Load and play video or audio, updating UI based on file type."""
        # Scarica il video corrente prima di caricarne uno nuovo
        self.player.stop()

        if self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            QTimer.singleShot(1, lambda: self.sourceSetter(video_path))

        self.videoPathLineEdit = video_path

        if self.isAudioOnly(video_path):
            self.fileNameLabel.setText(f"{video_title} - Traccia solo audio")  # Display special message for audio files
        else:
            self.fileNameLabel.setText(os.path.basename(video_path))  # Update label with file name

        self.updateRecentFiles(video_path)  # Update recent files list

    def loadVideoOutput(self, video_path):

        self.playerOutput.stop()

        if self.playerOutput.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            QTimer.singleShot(1, lambda: self.sourceSetterOutput(video_path))

        self.fileNameLabelOutput.setText(os.path.basename(video_path))  # Aggiorna il nome del file sulla label
        self.videoPathLineOutputEdit = video_path
        logging.debug(f"Loaded video output: {video_path}")


    def updateTimeCode(self, position):
        # Calcola ore, minuti e secondi dalla posizione, che è in millisecondi
        hours, remainder = divmod(position // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        # Aggiorna l'etichetta con il nuovo time code
        self.currentTimeLabel.setText(f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}')

    def updateDuration(self, duration):
        # Calcola ore, minuti e secondi dalla durata, che è in millisecondi
        hours, remainder = divmod(duration // 1000, 3600)
        minutes, seconds = divmod(remainder, 60)
        # Aggiorna l'etichetta con la durata totale
        self.totalTimeLabel.setText(f' / {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}')

    def setupMenuBar(self):
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        openAction = QAction('&Open Video/Audio', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open video')
        openAction.triggered.connect(self.browseVideo)

        openActionOutput = QAction('&Open as Output Video', self)
        openAction.setShortcut('Ctrl+I')
        openActionOutput.setStatusTip('Open Video Output')
        openActionOutput.triggered.connect(self.browseVideoOutput)

        fileMenu.addAction(openAction)
        fileMenu.addAction(openActionOutput)

        # New Save As action
        saveAsAction = QAction('&Save Video Output As...', self)
        saveAsAction.setShortcut('Ctrl+S')
        saveAsAction.setStatusTip('Save the current video from Video Player Output')
        saveAsAction.triggered.connect(self.saveVideoAs)
        fileMenu.addAction(saveAsAction)

        # Action to open root folder
        openRootFolderAction = QAction('&Open Root Folder', self)
        openRootFolderAction.setShortcut('Ctrl+R')
        openRootFolderAction.setStatusTip('Open the root folder of the software')
        openRootFolderAction.triggered.connect(self.openRootFolder)
        fileMenu.addAction(openRootFolderAction)

        exitAction = QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)

        fileMenu.addSeparator()
        self.recentMenu = fileMenu.addMenu("Recenti")  # Aggiunge il menu dei file recenti
        self.updateRecentFilesMenu()

        # Creazione del menu View per la gestione della visibilità dei docks
        viewMenu = menuBar.addMenu('&View')

        # Aggiunta del menu Workflows
        workflowsMenu = menuBar.addMenu('&Workflows')

        # Funzionalità spostate da Strumenti Avanzati
        summarizeAction = QAction('&Riassumi Testo', self)
        summarizeAction.setStatusTip('Genera un riassunto del testo tramite AI')
        summarizeAction.triggered.connect(self.processTextWithAI)
        workflowsMenu.addAction(summarizeAction)

        fixTextAction = QAction('&Correggi Testo', self)
        fixTextAction.setStatusTip('Sistema e migliora il testo tramite AI')
        fixTextAction.triggered.connect(self.fixTextWithAI)
        workflowsMenu.addAction(fixTextAction)

        extractTextAction = QAction('&Estrai Testo da Frame', self)
        extractTextAction.setStatusTip('Estrae testo dai frame del video')
        extractTextAction.triggered.connect(self.onExtractFramesClicked)
        workflowsMenu.addAction(extractTextAction)

        # Separatore
        workflowsMenu.addSeparator()

        # Altre funzionalità Workflows
        createWorkflowAction = QAction('&Nuovo Workflow', self)
        createWorkflowAction.setStatusTip('Crea un nuovo workflow personalizzato')
        createWorkflowAction.triggered.connect(self.createWorkflow)  # Dovrai implementare questo metodo
        workflowsMenu.addAction(createWorkflowAction)

        loadWorkflowAction = QAction('&Carica Workflow', self)
        loadWorkflowAction.setStatusTip('Carica un workflow esistente')
        loadWorkflowAction.triggered.connect(self.loadWorkflow)  # Dovrai implementare questo metodo
        workflowsMenu.addAction(loadWorkflowAction)

        agentAIsMenu = menuBar.addMenu('&Agent AIs')

        # Opzioni esistenti
        runAgentAction = QAction('&Esegui Agent', self)
        runAgentAction.setStatusTip('Esegui agent AI sul media corrente')
        runAgentAction.triggered.connect(self.runAgent)
        agentAIsMenu.addAction(runAgentAction)

        # Nuova opzione per la creazione della guida e lancio dell'agente
        agentAIsMenu.addSeparator()  # Aggiungi un separatore per chiarezza
        createGuideAction = QAction('&Crea Guida Operativa', self)
        createGuideAction.setStatusTip('Crea una guida operativa dai frame estratti')
        createGuideAction.triggered.connect(self.createGuideAndRunAgent)
        agentAIsMenu.addAction(createGuideAction)

        videoMenu = menuBar.addMenu('&Video')
        releaseSourceAction = QAction(QIcon("./res/reset.png"), "Unload Video Source", self)
        releaseSourceAction.triggered.connect(self.releaseSourceVideo)
        videoMenu.addAction(releaseSourceAction)

        releaseOutputAction = QAction(QIcon("./res/reset.png"), "Unload Video Output", self)
        releaseOutputAction.triggered.connect(self.releaseOutputVideo)
        videoMenu.addAction(releaseOutputAction)

        viewMenu.aboutToShow.connect(self.updateViewMenu)  # Aggiunta di questo segnale
        self.setupViewMenuActions(viewMenu)

        # Creazione del menu About
        aboutMenu = menuBar.addMenu('&About')
        # Aggiunta di azioni al menu About
        aboutAction = QAction('&About', self)
        aboutAction.setStatusTip('About the application')
        aboutAction.triggered.connect(self.about)
        aboutMenu.addAction(aboutAction)
    def saveVideoAs(self):
        if not self.videoPathLineOutputEdit:
            QMessageBox.warning(self, "Attenzione", "Nessun video caricato nel Video Player Output.")
            return

        fileName, _ = QFileDialog.getSaveFileName(self, "Salva Video con Nome", "", "Video Files (*.mp4 *.mov *.avi)")
        if fileName:
            try:
                # Copy the currently loaded video to the new location
                shutil.copy(self.videoPathLineOutputEdit, fileName)
                QMessageBox.information(self, "Successo", f"Video salvato con successo in: {fileName}")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante il salvataggio del video: {str(e)}")


    def setupViewMenuActions(self, viewMenu):
        # Azione per il Video Player Dock
        self.actionToggleVideoPlayerDock = QAction('Mostra/Nascondi Video Player Input', self, checkable=True)
        self.actionToggleVideoPlayerDock.setChecked(self.videoPlayerDock.isVisible())
        self.actionToggleVideoPlayerDock.triggered.connect(
            lambda: self.toggleDockVisibilityAndUpdateMenu(self.videoPlayerDock,
                                                           self.actionToggleVideoPlayerDock.isChecked()))

        # Azioni simili per gli altri docks...
        self.actionToggleVideoPlayerDockOutput = self.createToggleAction(self.videoPlayerOutput,
                                                                         'Mostra/Nascondi Video Player Output')
        self.actionToggleTranscriptionDock = self.createToggleAction(self.transcriptionDock,
                                                                     'Mostra/Nascondi Trascrizione')
        self.actionToggleEditingDock = self.createToggleAction(self.editingDock, 'Mostra/Nascondi Generazione Audio AI')
        self.actionToggleDownloadDock = self.createToggleAction(self.downloadDock, 'Mostra/Nascondi Download')
        self.actionToggleRecordingDock = self.createToggleAction(self.recordingDock, 'Mostra/Nascondi Registrazione')
        self.actionToggleAudioDock = self.createToggleAction(self.audioDock, 'Mostra/Nascondi Gestione Audio')
        self.actionToggleVideoMergeDock = self.createToggleAction(self.videoMergeDock, 'Mostra/Nascondi Unisci Video')
        self.actionTogglegGenerazioneAIDock = self.createToggleAction(self.generazioneAIDock, 'Mostra/Nascondi Generazione AI')

        # Aggiungi tutte le azioni al menu 'View'
        viewMenu.addAction(self.actionToggleVideoPlayerDock)
        viewMenu.addAction(self.actionToggleVideoPlayerDockOutput)
        viewMenu.addAction(self.actionToggleTranscriptionDock)
        viewMenu.addAction(self.actionToggleEditingDock)
        viewMenu.addAction(self.actionToggleDownloadDock)
        viewMenu.addAction(self.actionToggleRecordingDock)
        viewMenu.addAction(self.actionToggleAudioDock)
        viewMenu.addAction(self.actionToggleVideoMergeDock)
        viewMenu.addAction(self.actionTogglegGenerazioneAIDock)


        # Aggiungi azioni per mostrare/nascondere tutti i docks
        showAllDocksAction = QAction('Mostra tutti i Docks', self)
        hideAllDocksAction = QAction('Nascondi tutti i Docks', self)

        showAllDocksAction.triggered.connect(self.showAllDocks)
        hideAllDocksAction.triggered.connect(self.hideAllDocks)

        viewMenu.addSeparator()  # Aggiunge un separatore per chiarezza
        viewMenu.addAction(showAllDocksAction)
        viewMenu.addAction(hideAllDocksAction)


        # Azione per salvare il layout dei docks
        saveLayoutAction = QAction('Salva Layout dei Docks', self)
        saveLayoutAction.triggered.connect(self.saveDockLayout)
        viewMenu.addSeparator()  # Aggiunge un separatore per chiarezza
        viewMenu.addAction(saveLayoutAction)

        # Aggiorna lo stato iniziale del menu
        self.updateViewMenu()

    def saveDockLayout(self):
        # Assumendo che DockSettingsManager abbia un metodo per salvare le impostazioni
        if hasattr(self, 'dockSettingsManager'):
            self.dockSettingsManager.save_settings()
            QMessageBox.information(self, "Layout Salvato", "Il layout dei docks è stato salvato correttamente.")
        else:
            QMessageBox.warning(self, "Errore", "Gestore delle impostazioni dei dock non trovato.")

    def showAllDocks(self):
        # Imposta tutti i docks visibili
        self.videoPlayerDock.setVisible(True)
        self.videoPlayerOutput.setVisible(True)
        self.audioDock.setVisible(True)
        self.transcriptionDock.setVisible(True)
        self.editingDock.setVisible(True)
        self.downloadDock.setVisible(True)
        self.recordingDock.setVisible(True)
        self.videoMergeDock.setVisible(True)
        self.generazioneAIDock.setVisible(True)
        self.updateViewMenu()  # Aggiorna lo stato dei menu

    def hideAllDocks(self):
        # Nasconde tutti i docks
        self.videoPlayerDock.setVisible(False)
        self.videoPlayerOutput.setVisible(False)
        self.audioDock.setVisible(False)
        self.transcriptionDock.setVisible(False)
        self.editingDock.setVisible(False)
        self.downloadDock.setVisible(False)
        self.recordingDock.setVisible(False)
        self.videoMergeDock.setVisible(False)
        self.generazioneAIDock.setVisible(False)
        self.updateViewMenu()  # Aggiorna lo stato dei menu
    def createToggleAction(self, dock, menuText):
        action = QAction(menuText, self, checkable=True)
        action.setChecked(dock.isVisible())
        action.triggered.connect(lambda checked: self.toggleDockVisibilityAndUpdateMenu(dock, checked))
        return action

    def toggleDockVisibilityAndUpdateMenu(self, dock, visible):
        if visible:
            dock.showDock()
        else:
            dock.hideDock()

        self.updateViewMenu()

    def resetViewMenu(self):

        self.actionToggleVideoPlayerDock.setChecked(True)
        self.actionToggleVideoPlayerDockOutput.setChecked(True)
        self.actionToggleAudioDock.setChecked(True)
        self.actionToggleTranscriptionDock.setChecked(True)
        self.actionToggleEditingDock.setChecked(True)
        self.actionToggleDownloadDock.setChecked(True)
        self.actionToggleRecordingDock.setChecked(True)
        self.actionToggleVideoMergeDock.setChecked(True)
        self.actionTogglegGenerazioneAIDock.setChecked(True)

    def updateViewMenu(self):

        # Aggiorna lo stato dei menu checkable basato sulla visibilità dei dock
        self.actionToggleVideoPlayerDock.setChecked(self.videoPlayerDock.isVisible())
        self.actionToggleVideoPlayerDockOutput.setChecked(self.videoPlayerOutput.isVisible())
        self.actionToggleAudioDock.setChecked(self.audioDock.isVisible())
        self.actionToggleTranscriptionDock.setChecked(self.transcriptionDock.isVisible())
        self.actionToggleEditingDock.setChecked(self.editingDock.isVisible())
        self.actionToggleDownloadDock.setChecked(self.downloadDock.isVisible())
        self.actionToggleRecordingDock.setChecked(self.recordingDock.isVisible())
        self.actionToggleVideoMergeDock.setChecked(self.videoMergeDock.isVisible())
        self.actionTogglegGenerazioneAIDock.setChecked(self.generazioneAIDock.isVisible())

    def about(self):
        QMessageBox.about(self, "TGeniusAI",
                          f"""<b>Genius AI</b> version: {self.version}<br>
                          AI-based video and audio management application.<br>
                          <br>
                          Autore: FFA <br>""")


    def handleTextChange(self):
        current_html = self.transcriptionTextArea.toHtml()
        if current_html.strip():
            if self.timecodeEnabled:
                self.transcriptionTextArea.blockSignals(True)
                updated_html = self.calculateAndDisplayTimeCodeAtEndOfSentences(current_html)
                self.transcriptionTextArea.setHtml(updated_html)
                self.detectAndUpdateLanguage(BeautifulSoup(updated_html, 'html.parser').get_text())
                self.transcriptionTextArea.blockSignals(False)
            else:
                self.detectAndUpdateLanguage(BeautifulSoup(current_html, 'html.parser').get_text())
                self.original_text_html = current_html

    def calculateAndDisplayTimeCodeAtEndOfSentences(self, html_text):
        WPM = 150  # Average words-per-minute rate for spoken language
        words_per_second = WPM / 60

        soup = BeautifulSoup(html_text, 'html.parser')
        paragraphs = soup.find_all('p')

        cumulative_time = 0  # Total time in seconds

        for paragraph in paragraphs:
            text = paragraph.get_text()

            sentences = re.split(r'(?<=[.!?])\s+', text)
            updated_html = []

            for sentence in sentences:
                words = re.findall(r'\b\w+\b', sentence)
                cumulative_time += len(words) / words_per_second

                pause_pattern = re.compile(r'<break time="(\d+(\.\d+)?)s" />')
                pauses = pause_pattern.findall(sentence)
                for pause in pauses:
                    pause_time = float(pause[0])
                    cumulative_time += pause_time

                updated_html.append(sentence)

                minutes = int(cumulative_time // 60)
                seconds = int(cumulative_time % 60)
                updated_html.append(f" <span style='color:lightblue;'>[{minutes:02d}:{seconds:02d}]</span>")

            paragraph.clear()
            paragraph.append(BeautifulSoup(' '.join(updated_html), 'html.parser'))

        return str(soup)

    def detectAndUpdateLanguage(self, text):
        try:
            detected_language_code = detect(text)
            language = pycountry.languages.get(alpha_2=detected_language_code)
            if language:
                detected_language = language.name
                self.updateLanguageComboBox(detected_language_code, detected_language)
                self.updateTranscriptionLanguageDisplay(detected_language)
            else:
                self.updateTranscriptionLanguageDisplay("Lingua non supportata")
        except LangDetectException:
            self.updateTranscriptionLanguageDisplay("Non rilevabile")

    def updateLanguageComboBox(self, language_code, language_name):
        index = self.languageComboBox.findData(language_code)
        if index == -1:
            self.languageComboBox.addItem(language_name, language_code)
            index = self.languageComboBox.count() - 1
        self.languageComboBox.setCurrentIndex(index)

    def updateTranscriptionLanguageDisplay(self, language):
        self.transcriptionLanguageLabel.setText(f"Lingua rilevata: {language}")

    def transcribeVideo(self):
        if not self.videoPathLineEdit:
            QMessageBox.warning(self, "Attenzione", "Nessun video selezionato.")
            return

        self.progressDialog = QProgressDialog("Trascrizione in corso...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Trascrizione")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.canceled.connect(
            self.stopTranscription)  # Connect the cancel button to stop the transcription
        self.progressDialog.show()

        self.thread = TranscriptionThread(self.videoPathLineEdit, self)
        self.thread.update_progress.connect(self.updateProgressDialog(self.progressDialog))
        self.thread.transcription_complete.connect(self.completeTranscription(self.progressDialog))
        self.thread.error_occurred.connect(self.handleErrors(self.progressDialog))
        self.thread.start()

    def stopTranscription(self):
        if self.thread is not None:
            self.thread.stop()  # Ferma il thread di trascrizione
            self.thread.wait()  # Aspetta che il thread finisca
            partial_text = self.thread.get_partial_transcription()  # Ottieni il testo parziale trascritto
            self.transcriptionTextArea.setPlainText(
                partial_text)  # Mostra il testo parziale nell'oggetto transcriptionTextArea
            self.thread = None
            self.progressDialog.close()  # Chiudi il dialogo di progresso

    def updateProgressDialog(self, progress_dialog):
        def update(value, label):
            if not progress_dialog.wasCanceled():
                progress_dialog.setValue(value)
                progress_dialog.setLabelText(label)

        return update

    def completeTranscription(self, progress_dialog):
        """Returns a closure that handles transcription completion."""

        def complete(text, temp_files):
            if not progress_dialog.wasCanceled():
                self.transcriptionTextArea.setText(text)
                progress_dialog.setValue(100)
                progress_dialog.close()
                self.cleanupFiles(temp_files)  # Immediately cleanup after transcription

        return complete

    def cleanupFiles(self, file_paths):
        """Safely removes temporary files used during transcription."""
        for path in file_paths:
            self.removeFileSafe(path)

    def removeFileSafe(self, file_path, attempts=5, delay=0.5):
        """Attempt to safely remove a file with retries and delays."""
        for _ in range(attempts):
            try:
                os.remove(file_path)
                logging.debug(f"File {file_path} successfully removed.")
                break
            except PermissionError:
                logging.debug(f"Warning: File {file_path} is currently in use. Retrying...")
                time.sleep(delay)
            except FileNotFoundError:
                logging.debug(f"The file {file_path} does not exist or has already been removed.")
                break
            except Exception as e:
                logging.debug(f"Unexpected error while removing {file_path}: {e}")
    def handleErrors(self, progress_dialog):
        def error(message):
            QMessageBox.critical(self, "Errore nella Trascrizione",
                                 f"Errore durante la trascrizione del video: {message}")
            progress_dialog.cancel()

        return error

    def generateAudioWithElevenLabs(self):
        if not self.api_key:
            QMessageBox.warning(self, "Attenzione", "Per favore, imposta l'API Key prima di generare l'audio.")
            return

        def convert_numbers_to_words(text):
            text = re.sub(r'(\d+)\.', r'\1 .', text)
            new_text = []
            for word in text.split():
                if word.isdigit():
                    new_word = num2words(word, lang='it')
                    new_text.append(new_word)
                else:
                    new_text.append(word)
            return ' '.join(new_text)

        transcriptionText = self.transcriptionTextArea.toPlainText()
        if not transcriptionText.strip():
            QMessageBox.warning(self, "Attenzione", "Inserisci una trascrizione prima di generare l'audio.")
            return
        transcriptionText = convert_numbers_to_words(transcriptionText)

        voice_id = self.voiceSelectionComboBox.currentData()
        model_id = "eleven_multilingual_v1"

        voice_settings = {
            'stability': self.stabilitySlider.value() / 100.0,
            'similarity_boost': self.similaritySlider.value() / 100.0,
            'style': self.styleSlider.value() / 10.0,
            'use_speaker_boost': self.speakerBoostCheckBox.isChecked()
        }

        self.progressDialog = QProgressDialog("Generazione audio in corso...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Generazione Audio")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)

        # Percorso per salvare il file audio
        base_name = os.path.splitext(os.path.basename(self.videoPathLineEdit))[0]
        audio_save_path = os.path.join(os.path.dirname(self.videoPathLineEdit), f"{base_name}_generated.mp3")

        # Crea il thread con i nuovi parametri
        self.audio_thread = AudioGenerationThread(transcriptionText, voice_id, model_id, voice_settings, self.api_key,
                                                  audio_save_path, self)
        self.audio_thread.progress.connect(self.progressDialog.setValue)
        self.audio_thread.completed.connect(self.onAudioGenerationCompleted)
        self.audio_thread.error.connect(self.onError)
        self.audio_thread.start()

        self.progressDialog.canceled.connect(self.audio_thread.terminate)
        self.progressDialog.show()

    def runWav2Lip(self, video_path, audio_path, output_path):
        command = [
            'python', './Wav2Lip-master/inference.py',
            '--checkpoint_path', './Wav2Lip-master/checkpoints',  # Sostituisci con il percorso al tuo checkpoint
            '--face', video_path,
            '--audio', audio_path,
            '--outfile', output_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Errore nell'esecuzione di Wav2Lip: {result.stderr}")

    def createGuideAndRunAgent(self):
        """
        Crea una guida operativa dai frame estratti e esegue l'agent browser
        """
        if not hasattr(self, 'browser_agent'):
            from services.BrowserAgent import BrowserAgent
            self.browser_agent = BrowserAgent(self)

        self.browser_agent.create_guide_agent()
    def onAudioGenerationCompleted(self, audio_path):
        timecode = self.timecodePauseLineEdit.text()
        pause_duration = float(self.pauseAudioDurationLineEdit.text() or 0)

        if timecode and pause_duration > 0:
            # Convert the timecode into seconds
            hours, minutes, seconds = map(int, timecode.split(':'))
            start_time = hours * 3600 + minutes * 60 + seconds

            # Load the audio using moviepy
            original_audio = AudioFileClip(audio_path)
            total_duration = original_audio.duration

            # Create the silent audio segment for the pause
            silent_audio_path = tempfile.mktemp(suffix='.mp3')
            silent_audio = AudioSegment.silent(duration=pause_duration * 1000)  # duration in milliseconds
            silent_audio.export(silent_audio_path, format="mp3")

            # Load the silent audio segment using moviepy
            silent_audio_clip = AudioFileClip(silent_audio_path).set_duration(pause_duration)

            # Split the audio and insert the silent segment
            first_part = original_audio.subclip(0, start_time)
            second_part = original_audio.subclip(start_time, total_duration)
            new_audio = concatenate_audioclips([first_part, silent_audio_clip, second_part])

            # Save the modified audio to a temporary path
            temp_audio_path = tempfile.mktemp(suffix='.mp3')
            new_audio.write_audiofile(temp_audio_path)
            audio_path = temp_audio_path

            # Clean up the temporary silent audio file
            os.remove(silent_audio_path)

        if self.useWav2LipCheckbox.isChecked():
            base_name = os.path.splitext(os.path.basename(self.videoPathLineEdit))[0]
            timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
            output_video_path = os.path.join(os.path.dirname(self.videoPathLineEdit),
                                             f"{base_name}_Wav2Lip_{timestamp}.mp4")
            try:
                self.runWav2Lip(self.videoPathLineEdit, audio_path, output_video_path)
                QMessageBox.information(self, "Completato",
                                        f"Video generato con successo! Il video è stato salvato in: {output_video_path}")
                self.loadVideoOutput(output_video_path)
            except Exception as e:
                QMessageBox.critical(self, "Errore", str(e))
        else:
            base_name = os.path.splitext(os.path.basename(self.videoPathLineEdit))[0]
            timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
            output_path = os.path.join(os.path.dirname(self.videoPathLineEdit), f"{base_name}_GeniusAI_{timestamp}.mp4")
            self.adattaVelocitaVideoAAudio(self.videoPathLineEdit, audio_path, output_path)

            QMessageBox.information(self, "Completato",
                                    f"Processo completato con successo! L'audio è stato salvato in: {audio_path}")
            self.loadVideoOutput(output_path)

    def onError(self, error_message):
        QMessageBox.critical(self, "Errore", "Errore durante la generazione dell'audio: " + error_message)


    def browseAudio(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio", "", "Audio Files (*.mp3 *.wav)")
        if fileName:
            self.audioPathLineEdit.setText(fileName)

    def extractAudioFromVideo(self, video_path):
        # Estrai l'audio dal video e salvalo temporaneamente
        temp_audio_path = tempfile.mktemp(suffix='.mp3')
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(temp_audio_path)
        return temp_audio_path

    def applyNewAudioToVideo(self, video_path_line_edit, new_audio_path, align_audio_video):
        video_path = video_path_line_edit

        # Migliorata la validazione degli input
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "Attenzione", "Il file video selezionato non esiste.")
            return

        if not new_audio_path or not os.path.exists(new_audio_path):
            QMessageBox.warning(self, "Attenzione", "Il file audio selezionato non esiste.")
            return

        # Crea un percorso di output unico con timestamp per evitare sovrascritture
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.dirname(video_path)
        output_path = os.path.join(output_dir, f"{base_name}_audio_{timestamp}.mp4")

        # Crea un thread per l'elaborazione in background
        class AudioVideoThread(QThread):
            progress = pyqtSignal(int, str)
            completed = pyqtSignal(str)
            error = pyqtSignal(str)

            def __init__(self, video_path, audio_path, output_path, align_speed):
                super().__init__()
                self.video_path = video_path
                self.audio_path = audio_path
                self.output_path = output_path
                self.align_speed = align_speed
                self.running = True

            def run(self):
                try:
                    if self.align_speed:
                        self.alignSpeedAndApplyAudio()
                    else:
                        self.applyAudioOnly()

                    if self.running:
                        self.completed.emit(self.output_path)
                except Exception as e:
                    if self.running:
                        self.error.emit(str(e))

            def alignSpeedAndApplyAudio(self):
                video_clip = None
                audio_clip = None
                video_modified = None
                final_video = None

                try:
                    # Carica i file
                    self.progress.emit(10, "Caricamento video...")
                    video_clip = VideoFileClip(self.video_path)

                    self.progress.emit(20, "Caricamento audio...")
                    audio_clip = AudioFileClip(self.audio_path)

                    # Calcola il fattore di velocità
                    self.progress.emit(30, "Calcolo fattore di velocità...")
                    video_duration = video_clip.duration
                    audio_duration = audio_clip.duration

                    if video_duration <= 0 or audio_duration <= 0:
                        raise ValueError("Durata del video o dell'audio non valida")

                    speed_factor = round(video_duration / audio_duration, 2)

                    # Applica il cambio di velocità
                    self.progress.emit(40, "Applicazione effetto velocità...")
                    video_modified = video_clip.fx(vfx.speedx, speed_factor)

                    # Applica l'audio
                    self.progress.emit(60, "Applicazione audio...")
                    final_video = video_modified.set_audio(audio_clip)

                    # Scrive l'output con impostazioni ottimizzate
                    self.progress.emit(70, "Salvataggio video finale...")
                    final_video.write_videofile(
                        self.output_path,
                        codec="libx264",
                        audio_codec="aac",
                        fps=video_clip.fps,
                        preset="ultrafast",  # Codifica più veloce
                        threads=4,  # Usa più thread
                        logger=None  # Disabilita il logging verboso
                    )

                    self.progress.emit(100, "Completato")

                except Exception as e:
                    raise Exception(f"Errore nell'allineamento audio-video: {str(e)}")
                finally:
                    # Pulizia risorse indipendentemente dall'esito
                    if video_clip:
                        video_clip.close()
                    if audio_clip:
                        audio_clip.close()
                    if video_modified:
                        video_modified.close()
                    if final_video:
                        final_video.close()

            def applyAudioOnly(self):
                video_clip = None
                audio_clip = None
                final_video = None

                try:
                    # Carica i file
                    self.progress.emit(10, "Caricamento video...")
                    video_clip = VideoFileClip(self.video_path)

                    self.progress.emit(30, "Caricamento audio...")
                    audio_clip = AudioFileClip(self.audio_path)

                    # Verifica e gestisci casi in cui la durata dell'audio è diversa dal video
                    if audio_clip.duration > video_clip.duration:
                        self.progress.emit(40, "Taglio audio per adattarlo al video...")
                        audio_clip = audio_clip.subclip(0, video_clip.duration)

                    # Applica l'audio
                    self.progress.emit(50, "Applicazione audio...")
                    final_video = video_clip.set_audio(audio_clip)

                    # Scrive l'output con impostazioni ottimizzate
                    self.progress.emit(70, "Salvataggio video finale...")
                    final_video.write_videofile(
                        self.output_path,
                        codec="libx264",
                        audio_codec="aac",
                        fps=video_clip.fps,
                        preset="ultrafast",
                        threads=4,
                        logger=None
                    )

                    self.progress.emit(100, "Completato")

                except Exception as e:
                    raise Exception(f"Errore nella sostituzione dell'audio: {str(e)}")
                finally:
                    # Pulizia risorse
                    if video_clip:
                        video_clip.close()
                    if audio_clip:
                        audio_clip.close()
                    if final_video:
                        final_video.close()

            def stop(self):
                self.running = False

        # Crea dialog di progresso
        self.progressDialog = QProgressDialog("Preparazione processo...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Processo Audio-Video")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)

        # Crea thread
        self.audio_video_thread = AudioVideoThread(video_path, new_audio_path, output_path, align_audio_video)

        # Collega i segnali
        self.audio_video_thread.progress.connect(self.updateAudioVideoProgress)
        self.audio_video_thread.completed.connect(self.onAudioVideoCompleted)
        self.audio_video_thread.error.connect(self.onAudioVideoError)
        self.progressDialog.canceled.connect(self.audio_video_thread.stop)

        # Avvia thread
        self.audio_video_thread.start()
        self.progressDialog.show()

    def updateAudioVideoProgress(self, value, message):
        """Aggiorna il dialog di progresso con lo stato attuale"""
        if hasattr(self, 'progressDialog') and self.progressDialog is not None:
            self.progressDialog.setValue(value)
            self.progressDialog.setLabelText(message)

    def onAudioVideoCompleted(self, output_path):
        """Gestisce il completamento dell'elaborazione audio-video"""
        self.progressDialog.close()
        QMessageBox.information(self, "Successo", f"Il nuovo audio è stato applicato con successo:\n{output_path}")
        self.loadVideoOutput(output_path)

    def onAudioVideoError(self, error_message):
        """Gestisce gli errori durante l'elaborazione audio-video"""
        self.progressDialog.close()
        QMessageBox.critical(self, "Errore",
                             f"Si è verificato un errore durante l'elaborazione audio-video:\n{error_message}")

    def cutVideo(self):
        media_path = self.videoPathLineEdit
        if not media_path:
            QMessageBox.warning(self, "Attenzione", "Per favore, seleziona un file prima di tagliarlo.")
            return

        if media_path.lower().endswith(('.mp4', '.mov', '.avi')):
            is_audio = False
        elif media_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac')):
            is_audio = True
        else:
            QMessageBox.warning(self, "Errore", "Formato file non supportato.")
            return

        start_time = self.currentPosition / 1000.0  # Converti in secondi

        base_name = os.path.splitext(os.path.basename(media_path))[0]
        directory = os.path.dirname(media_path)
        ext = 'mp4' if not is_audio else 'mp3'
        output_path1 = os.path.join(directory, f"{base_name}_part1.{ext}")
        output_path2 = os.path.join(directory, f"{base_name}_part2.{ext}")

        self.progressDialog = QProgressDialog("Taglio del file in corso...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Taglio")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.show()

        self.cutting_thread = VideoCuttingThread(media_path, start_time, output_path1, output_path2)
        self.cutting_thread.progress.connect(self.progressDialog.setValue)
        self.cutting_thread.completed.connect(self.onCutCompleted)
        self.cutting_thread.error.connect(self.onCutError)


        self.cutting_thread.start()

    def onCutCompleted(self, output_path):
        QMessageBox.information(self, "Successo", f"File tagliato salvato in: {output_path}.")
        self.progressDialog.close()
        self.loadVideoOutput(output_path)

    def onCutError(self, error_message):
        QMessageBox.critical(self, "Errore", error_message)
        self.progressDialog.close()

    def positionChanged(self, position):
        self.videoSlider.setValue(position)
        self.currentPosition = position  # Aggiorna la posizione corrente
        self.updateTimeCode(position)

    # Slot per aggiornare il range massimo dello slider in base alla durata del video
    def durationChanged(self, duration):
        self.videoSlider.setRange(0, duration)
        self.updateDuration(duration)

    # Slot per aggiornare la posizione dello slider in base alla posizione corrente del video

    # Slot per cambiare la posizione del video quando lo slider viene mosso
    def setPosition(self, position):
        self.player.setPosition(position)

    def applyDarkMode(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #dcdcdc;
            }
            QLineEdit {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #555555;
                border: 1px solid #666666;
                border-radius: 2px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #777777;
            }
            QLabel {
                color: #cccccc;
            }
            QFileDialog {
                background-color: #444444;
            }
            QMessageBox {
                background-color: #444444;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        file_urls = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if file_urls:

            self.videoPathLineEdit = file_urls[0]  # Aggiorna il percorso del video memorizzato
            self.loadVideo(self.videoPathLineEdit, os.path.basename(file_urls[0]))

    def browseVideo(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video/Audio Files (*avi *.mp4 *.mov *.mp3 *.wav *.aac *.ogg *.flac *.mkv)")
        if fileName:
           self.loadVideo(fileName)

    def browseVideoOutput(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video/Audio Files (*.avi *.mp4 *.mov *.mp3 *.wav *.aac *.ogg *.flac *.mkv)")
        if fileName:
           self.loadVideoOutput(fileName)

    def updateRecentFiles(self, newFile):
        if newFile not in self.recentFiles:
            self.recentFiles.insert(0, newFile)
            if len(self.recentFiles) > 5:  # Limita la lista ai 5 più recenti
                self.recentFiles.pop()
        self.updateRecentFilesMenu()

    def updateRecentFilesMenu(self):
        self.recentMenu.clear()
        for file in self.recentFiles:
            action = QAction(os.path.basename(file), self)
            action.triggered.connect(lambda checked, f=file: self.openRecentFile(f))
            self.recentMenu.addAction(action)

    def openRecentFile(self, filePath):
        self.videoPathLineEdit = filePath
        self.player.setSource(QUrl.fromLocalFile(filePath))
        self.fileNameLabel.setText(os.path.basename(filePath))

    def playVideo(self):
        self.player.play()

    def pauseVideo(self):
        self.player.pause()

    def adattaVelocitaVideoAAudio(self, video_path, new_audio_path, output_path):
        try:
            # Log dei percorsi dei file
            logging.debug(f"Percorso video: {video_path}")
            logging.debug(f"Percorso nuovo audio: {new_audio_path}")
            logging.debug(f"Percorso output: {output_path}")

            # Carica il nuovo file audio e calcola la sua durata
            new_audio = AudioFileClip(new_audio_path)
            durata_audio = new_audio.duration
            logging.debug(f"Durata audio: {durata_audio} secondi")

            # Carica il video (senza audio) e calcola la sua durata
            video_clip = VideoFileClip(video_path)
            durata_video = video_clip.duration
            logging.debug(f"Durata video: {durata_video} secondi")

            # Calcola il fattore di velocità
            fattore_velocita = round(durata_video / durata_audio, 1)
            logging.debug(f"Fattore di velocità: {fattore_velocita}")

            # Modifica la velocità del video
            video_modificato = video_clip.fx(vfx.speedx, fattore_velocita)

            # Imposta il nuovo audio sul video modificato
            final_video = video_modificato.set_audio(new_audio)

            # Scrivi il video finale mantenendo lo stesso frame rate del video originale
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=video_clip.fps)
            logging.debug('Video elaborato con successo.')

        except Exception as e:
            logging.error(f"Errore durante l'adattamento della velocità del video: {e}")
    def stopVideo(self):
        self.player.stop()


def resource_path(relative_path):
    """Ottiene il percorso assoluto delle risorse, funziona sia in development che in produzione"""
    try:
        # PyInstaller crea una cartella temporanea e memorizza il percorso in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Specifica la cartella delle immagini
    image_folder = resource_path(SPLASH_IMAGES_DIR)

    # Crea la splash screen con un'immagine casuale dalla cartella
    splash = SplashScreen(image_folder)
    splash.show()

    splash.showMessage("Caricamento risorse...")
    time.sleep(1)  # Simula un ritardo

    splash.showMessage("Inizializzazione interfaccia...")
    time.sleep(1)  # Simula un altro ritardo

    window = VideoAudioManager()

    window.show()

    splash.finish(window)

    sys.exit(app.exec())