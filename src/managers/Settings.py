# File: managers/Settings.py
# Corretto per QSizePolicy.Policy.Expanding e include il tab API Keys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget,
    QDialogButtonBox, QLabel, QComboBox, QGridLayout,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox,
    QSizePolicy, QPushButton, QFileDialog, QSpinBox, QHBoxLayout
)
from PyQt6.QtCore import QSettings
# Importa la configurazione delle azioni e, se necessario, l'endpoint di Ollama per info
from src.config import ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT, WATERMARK_IMAGE

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

        # Tab per il Salvataggio
        tabs.addTab(self.createSavingSettingsTab(), "Salvataggio")

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


        return widget

    def browseWatermark(self):
        # Open a file dialog to select an image
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Immagine Watermark", "", "Images (*.png *.jpg *.jpeg)")
        if filePath:
            self.watermarkPathEdit.setText(filePath)

    def createSavingSettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.saveWithPlaybackSpeed = QCheckBox()
        self.saveWithPlaybackSpeed.setToolTip("Se abilitato, il video verrà salvato con la velocità di riproduzione corrente.")
        layout.addRow("Salva video con la velocità di riproduzione:", self.saveWithPlaybackSpeed)

        return widget

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
        self.showRedDot.setChecked(self.settings.value("cursor/showRedDot", True, type=bool))
        self.showYellowTriangle.setChecked(self.settings.value("cursor/showYellowTriangle", True, type=bool))

        # --- Carica Impostazioni Registrazione ---
        self.enableWatermark.setChecked(self.settings.value("recording/enableWatermark", True, type=bool))
        self.watermarkPathEdit.setText(self.settings.value("recording/watermarkPath", WATERMARK_IMAGE))
        self.watermarkSizeSpinBox.setValue(self.settings.value("recording/watermarkSize", 10, type=int))
        self.watermarkPositionComboBox.setCurrentText(self.settings.value("recording/watermarkPosition", "Bottom Right"))
        self.useVBCableCheckBox.setChecked(self.settings.value("recording/useVBCable", False, type=bool))

        # --- Carica Impostazioni Salvataggio ---
        self.saveWithPlaybackSpeed.setChecked(self.settings.value("saving/saveWithPlaybackSpeed", False, type=bool))


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
        self.settings.setValue("cursor/showRedDot", self.showRedDot.isChecked())
        self.settings.setValue("cursor/showYellowTriangle", self.showYellowTriangle.isChecked())

        # --- Salva Impostazioni Registrazione ---
        self.settings.setValue("recording/enableWatermark", self.enableWatermark.isChecked())
        self.settings.setValue("recording/watermarkPath", self.watermarkPathEdit.text())
        self.settings.setValue("recording/watermarkSize", self.watermarkSizeSpinBox.value())
        self.settings.setValue("recording/watermarkPosition", self.watermarkPositionComboBox.currentText())
        self.settings.setValue("recording/useVBCable", self.useVBCableCheckBox.isChecked())

        # --- Salva Impostazioni Salvataggio ---
        self.settings.setValue("saving/saveWithPlaybackSpeed", self.saveWithPlaybackSpeed.isChecked())

        # --- Accetta e chiudi dialogo ---
        self.accept()