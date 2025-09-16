# File: managers/Settings.py
import subprocess
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget,
    QDialogButtonBox, QLabel, QComboBox, QGridLayout,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox,
    QSizePolicy, QPushButton, QFileDialog, QSpinBox, QHBoxLayout
)
from PyQt6.QtCore import QSettings
from src.config import ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT, FFMPEG_PATH

def get_video_devices():
    """Esegue ffmpeg per ottenere un elenco dei dispositivi video dshow."""
    try:
        ffmpeg_cmd = [
            FFMPEG_PATH,
            '-list_devices', 'true',
            '-f', 'dshow',
            '-i', 'dummy'
        ]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Esegui il comando catturando sia stdout che stderr
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)

        # Concatena stdout e stderr per una diagnosi completa
        output = result.stdout + "\n" + result.stderr

        # Stampa l'output completo di ffmpeg per il debug, questo sarà visibile nella console
        print("--- Inizio Output Rilevamento Dispositivi FFMPEG ---")
        print(output)
        print("--- Fine Output Rilevamento Dispositivi FFMPEG ---")

        devices = []
        in_video_devices_section = False
        for line in output.splitlines():
            # Cerca l'inizio della sezione dei dispositivi video
            if "DirectShow video devices" in line:
                in_video_devices_section = True
                continue
            # Esci se raggiungi la sezione audio
            if "DirectShow audio devices" in line:
                break

            # Se siamo nella sezione giusta, cerca i nomi dei dispositivi
            if in_video_devices_section:
                match = re.search(r'\"(.*?)\"', line)
                if match:
                    device_name = match.group(1)
                    # A volte ffmpeg elenca nomi alternativi, evitiamo di aggiungerli
                    if not device_name.startswith('@'):
                        devices.append(device_name)

        print(f"Dispositivi video rilevati: {devices}")
        return devices
    except FileNotFoundError:
        print(f"ERRORE CRITICO: ffmpeg.exe non trovato al percorso: {FFMPEG_PATH}")
        return ["ERRORE: ffmpeg.exe non trovato"]
    except Exception as e:
        print(f"ERRORE CRITICO durante l'elenco dei dispositivi video: {e}")
        return [f"ERRORE: {e}"]

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Impostazioni Applicazione") # Titolo più generale
        self.settings = QSettings("ThemaConsulting", "GeniusAI")

        # Dizionari per tenere traccia dei controlli UI
        self.model_combos = {}
        self.api_key_edits = {} # Per memorizzare i QLineEdit delle API key

        layout = QVBoxLayout(self)

        # --- Ristrutturazione con QTabWidget ---
        tabs = QTabWidget()

        # Tab per le API Keys (Nuovo)
        tabs.addTab(self.createApiKeySettingsTab(), "API Keys")

        # Tab per i Modelli AI (Esistente, ora come secondo tab)
        tabs.addTab(self.createModelSettingsWidget(), "Modelli AI per Azione")

        # Tab per il Cursore
        tabs.addTab(self.createCursorSettingsTab(), "Cursore")

        # Tab per la Registrazione
        tabs.addTab(self.createRecordingSettingsTab(), "Registrazione")

        layout.addWidget(tabs)
        # --- Fine Ristrutturazione con QTabWidget ---

        # Aggiunta dei pulsanti OK e Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.saveSettings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Carica tutte le impostazioni salvate (API Keys + Modelli)
        self.loadSettings()

    def createApiKeySettingsTab(self):
        """Crea il widget per il tab delle impostazioni delle API Keys."""
        widget = QWidget()
        layout = QFormLayout(widget) # Usiamo QFormLayout per coppie label-input

        # --- Campi Input API Key ---
        self.api_key_edits['elevenlabs'] = QLineEdit()
        self.api_key_edits['elevenlabs'].setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edits['elevenlabs'].setToolTip("Inserisci la tua API Key di ElevenLabs per la sintesi vocale.")
        layout.addRow("ElevenLabs API Key:", self.api_key_edits['elevenlabs'])

        self.api_key_edits['anthropic'] = QLineEdit()
        self.api_key_edits['anthropic'].setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edits['anthropic'].setToolTip("Inserisci la tua API Key di Anthropic (Claude) per i modelli Claude.")
        layout.addRow("Anthropic (Claude) API Key:", self.api_key_edits['anthropic'])

        self.api_key_edits['google'] = QLineEdit()
        self.api_key_edits['google'].setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edits['google'].setToolTip("Inserisci la tua API Key di Google AI (Gemini) per i modelli Gemini.")
        layout.addRow("Google AI (Gemini) API Key:", self.api_key_edits['google'])

        self.api_key_edits['openai'] = QLineEdit()
        self.api_key_edits['openai'].setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edits['openai'].setToolTip("Inserisci la tua API Key di OpenAI (GPT) se intendi usare i modelli GPT.")
        layout.addRow("OpenAI (GPT) API Key:", self.api_key_edits['openai'])

        # --- Avviso Sicurezza ---
        """warningLabel = QLabel(
            "<font color='orange'><b>Attenzione:</b> Salvare le API keys nelle impostazioni "
            "dell'applicazione potrebbe essere meno sicuro rispetto all'uso di variabili d'ambiente "
            "(.env). Le chiavi qui inserite vengono salvate localmente.</font>"
        )
        warningLabel.setWordWrap(True)
        layout.addRow(warningLabel) # Aggiunge l'avviso al layout
        """
        # Aggiunge uno spaziatore verticale alla fine del QFormLayout
        spacer = QWidget()
        # --- CORREZIONE APPLICATA QUI ---
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # --- FINE CORREZIONE ---
        layout.addRow(spacer)

        return widget

    def createModelSettingsWidget(self): # Contenuto invariato, crea solo il widget
        widget = QWidget()
        layout = QGridLayout(widget) # Applica il layout al QWidget

        layout.addWidget(QLabel("<b>Seleziona il Modello AI per ogni Azione Specifica:</b>"), 0, 0, 1, 2)

        current_row = 1
        for action_key, config in ACTION_MODELS_CONFIG.items():
            display_name = config.get('display_name', action_key.replace('_', ' ').title())
            allowed_models = config.get('allowed', [])
            setting_key = config.get('setting_key')

            if not allowed_models or not setting_key:
                continue

            label = QLabel(f"{display_name}:")
            combo = QComboBox()
            combo.addItems(allowed_models)
            combo.setToolTip(f"Modello da usare per: {display_name}")

            layout.addWidget(label, current_row, 0)
            layout.addWidget(combo, current_row, 1)
            self.model_combos[action_key] = combo
            current_row += 1

        layout.setRowStretch(current_row, 1)

        has_ollama = any("ollama:" in m for cfg in ACTION_MODELS_CONFIG.values() for m in cfg.get('allowed',[]))
        if has_ollama:
            ollama_note = QLabel(f"<i>Nota: I modelli 'ollama:' richiedono che Ollama sia in esecuzione (default: {OLLAMA_ENDPOINT}).</i>")
            ollama_note.setWordWrap(True)
            layout.addWidget(ollama_note, current_row, 0, 1, 2)
            layout.setRowStretch(current_row + 1, 1)

        return widget

    def createCursorSettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.enableCursorHighlight = QCheckBox()
        layout.addRow("Abilita Evidenziazione Cursore:", self.enableCursorHighlight)

        self.showRedDot = QCheckBox()
        layout.addRow("Mostra Punto Rosso:", self.showRedDot)

        self.showYellowTriangle = QCheckBox()
        layout.addRow("Mostra Triangolo Giallo:", self.showYellowTriangle)

        return widget

    def createRecordingSettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.enableWatermark = QCheckBox()
        layout.addRow("Abilita Watermark:", self.enableWatermark)

        # Add new controls for watermark path
        self.watermarkPathEdit = QLineEdit()
        self.watermarkPathEdit.setReadOnly(True)
        browseButton = QPushButton("Sfoglia...")
        browseButton.clicked.connect(self.browseWatermark)
        pathLayout = QHBoxLayout()
        pathLayout.addWidget(self.watermarkPathEdit)
        pathLayout.addWidget(browseButton)
        layout.addRow("File Watermark:", pathLayout)

        # Add new control for watermark size
        self.watermarkSizeSpinBox = QSpinBox()
        self.watermarkSizeSpinBox.setRange(1, 200)
        self.watermarkSizeSpinBox.setSuffix(" %")
        layout.addRow("Dimensione Watermark:", self.watermarkSizeSpinBox)

        # Add new control for watermark position
        self.watermarkPositionComboBox = QComboBox()
        self.watermarkPositionComboBox.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        layout.addRow("Posizione Watermark:", self.watermarkPositionComboBox)

        # Add new control for VB-Cable
        self.useVBCableCheckBox = QCheckBox()
        self.useVBCableCheckBox.setToolTip("Se abilitato, mostra l'opzione VB-CABLE per la registrazione audio, utile per cuffie bluetooth.")
        layout.addRow("Abilita VB-CABLE (cuffie):", self.useVBCableCheckBox)

        # --- Webcam Picture-in-Picture Settings ---
        self.enableWebcamPip = QCheckBox()
        layout.addRow("Abilita Webcam Picture-in-Picture:", self.enableWebcamPip)

        self.webcamDeviceComboBox = QComboBox()
        self.webcamDeviceComboBox.setToolTip("Seleziona il dispositivo webcam da usare.")
        # Popola la combobox con i dispositivi video trovati
        video_devices = get_video_devices()
        if video_devices:
            self.webcamDeviceComboBox.addItems(video_devices)
        else:
            self.webcamDeviceComboBox.addItem("Nessun dispositivo video trovato")
            self.webcamDeviceComboBox.setEnabled(False)
        layout.addRow("Dispositivo Webcam:", self.webcamDeviceComboBox)

        self.webcamPipPositionComboBox = QComboBox()
        self.webcamPipPositionComboBox.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        layout.addRow("Posizione Webcam PiP:", self.webcamPipPositionComboBox)

        # --- Performance Settings ---
        self.videoCodecComboBox = QComboBox()
        self.videoCodecComboBox.setToolTip("Scegli un codec video. I codec hardware (NVENC, QSV) offrono prestazioni migliori se supportati.")
        self.videoCodecComboBox.addItem("libx264 (Software, Compatibile)", "libx264")
        self.videoCodecComboBox.addItem("h264_nvenc (NVIDIA GPU, Veloce)", "h264_nvenc")
        self.videoCodecComboBox.addItem("h264_qsv (Intel GPU, Veloce)", "h264_qsv")
        self.videoCodecComboBox.addItem("h264_amf (AMD GPU, Veloce)", "h264_amf")
        layout.addRow("Codec Video:", self.videoCodecComboBox)


        return widget

    def browseWatermark(self):
        # Open a file dialog to select an image
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Immagine Watermark", "", "Images (*.png *.jpg *.jpeg)")
        if filePath:
            self.watermarkPathEdit.setText(filePath)

    def loadSettings(self):
        """Carica sia le API Keys che le impostazioni dei modelli."""

        # --- Carica API Keys ---
        for key_name, line_edit in self.api_key_edits.items():
            # Usa una chiave QSettings specifica per le API keys nel dialogo
            settings_key = f"api_keys_dialog/{key_name}"
            saved_key = self.settings.value(settings_key, "") # Default a stringa vuota
            line_edit.setText(saved_key)

        # --- Carica Modelli per Azione ---
        for action_key, config in ACTION_MODELS_CONFIG.items():
            setting_key = config.get('setting_key')
            default_model = config.get('default')
            combo = self.model_combos.get(action_key)

            if setting_key and default_model and combo:
                saved_model = self.settings.value(setting_key, default_model)
                self._setComboBoxValue(combo, saved_model)
            elif combo and combo.count() > 0:
                 combo.setCurrentIndex(0)

        # --- Carica Impostazioni Cursore ---
        self.enableCursorHighlight.setChecked(self.settings.value("cursor/enableHighlight", False, type=bool))
        self.showRedDot.setChecked(self.settings.value("cursor/showRedDot", True, type=bool))
        self.showYellowTriangle.setChecked(self.settings.value("cursor/showYellowTriangle", True, type=bool))

        # --- Carica Impostazioni Registrazione ---
        self.enableWatermark.setChecked(self.settings.value("recording/enableWatermark", True, type=bool))
        self.watermarkPathEdit.setText(self.settings.value("recording/watermarkPath", "res/watermark.png"))
        self.watermarkSizeSpinBox.setValue(self.settings.value("recording/watermarkSize", 10, type=int))
        self.watermarkPositionComboBox.setCurrentText(self.settings.value("recording/watermarkPosition", "Bottom Right"))
        self.useVBCableCheckBox.setChecked(self.settings.value("recording/useVBCable", False, type=bool))

        # --- Carica Impostazioni Webcam PiP ---
        self.enableWebcamPip.setChecked(self.settings.value("recording/enableWebcamPip", False, type=bool))
        saved_webcam = self.settings.value("recording/webcamDevice", "")
        if saved_webcam and self.webcamDeviceComboBox.findText(saved_webcam) != -1:
            self.webcamDeviceComboBox.setCurrentText(saved_webcam)
        self.webcamPipPositionComboBox.setCurrentText(self.settings.value("recording/webcamPipPosition", "Bottom Right"))

        # --- Carica Impostazioni Performance ---
        saved_codec = self.settings.value("recording/videoCodec", "libx264")
        codec_index = self.videoCodecComboBox.findData(saved_codec)
        if codec_index != -1:
            self.videoCodecComboBox.setCurrentIndex(codec_index)


    def _setComboBoxValue(self, combo_box, value):
        """Imposta il valore corrente della ComboBox se il valore è presente."""
        index = combo_box.findText(value)
        if index >= 0:
            combo_box.setCurrentIndex(index)
        else:
            if combo_box.count() > 0:
                combo_box.setCurrentIndex(0)
                print(f"Attenzione: Il modello salvato '{value}' non è più disponibile per {combo_box.toolTip()}. Impostato il primo modello disponibile.")

    def saveSettings(self):
        """Salva sia le API Keys che le impostazioni dei modelli."""

        # --- Salva API Keys ---
        for key_name, line_edit in self.api_key_edits.items():
            # Usa una chiave QSettings specifica per le API keys nel dialogo
            settings_key = f"api_keys_dialog/{key_name}"
            self.settings.setValue(settings_key, line_edit.text())

        # --- Salva Modelli per Azione ---
        for action_key, config in ACTION_MODELS_CONFIG.items():
            setting_key = config.get('setting_key')
            combo = self.model_combos.get(action_key)

            if setting_key and combo:
                current_model = combo.currentText()
                self.settings.setValue(setting_key, current_model)

        # --- Salva Impostazioni Cursore ---
        self.settings.setValue("cursor/enableHighlight", self.enableCursorHighlight.isChecked())
        self.settings.setValue("cursor/showRedDot", self.showRedDot.isChecked())
        self.settings.setValue("cursor/showYellowTriangle", self.showYellowTriangle.isChecked())

        # --- Salva Impostazioni Registrazione ---
        self.settings.setValue("recording/enableWatermark", self.enableWatermark.isChecked())
        self.settings.setValue("recording/watermarkPath", self.watermarkPathEdit.text())
        self.settings.setValue("recording/watermarkSize", self.watermarkSizeSpinBox.value())
        self.settings.setValue("recording/watermarkPosition", self.watermarkPositionComboBox.currentText())
        self.settings.setValue("recording/useVBCable", self.useVBCableCheckBox.isChecked())

        # --- Salva Impostazioni Webcam PiP ---
        self.settings.setValue("recording/enableWebcamPip", self.enableWebcamPip.isChecked())
        self.settings.setValue("recording/webcamDevice", self.webcamDeviceComboBox.currentText())
        self.settings.setValue("recording/webcamPipPosition", self.webcamPipPositionComboBox.currentText())

        # --- Salva Impostazioni Performance ---
        self.settings.setValue("recording/videoCodec", self.videoCodecComboBox.currentData())

        # --- Accetta e chiudi dialogo ---
        self.accept()