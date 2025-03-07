from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QRadioButton,
    QButtonGroup, QDialogButtonBox, QLabel, QComboBox, QGridLayout
)
from PyQt6.QtCore import QSettings
from src.config import (
    MODEL_3_7_SONNET, MODEL_3_5_HAIKU, MODEL_3_5_SONNET,
    MODEL_3_5_SONNET_V2, MODEL_3_OPUS, MODEL_3_SONNET,
    MODEL_3_HAIKU,
    CLAUDE_MODEL_FRAME_EXTRACTOR, CLAUDE_MODEL_TEXT_PROCESSING,
    CLAUDE_MODEL_PPTX_GENERATION, CLAUDE_MODEL_BROWSER_AGENT,
    CLAUDE_MODEL_SUMMARY
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.settings = QSettings("ThemaConsulting", "GeniusAI")

        layout = QVBoxLayout(self)

        # Creazione del widget tab
        tabs = QTabWidget()
        tabs.addTab(self.createTTSSettingsTab(), "Motori TTS")
        tabs.addTab(self.createModelSettingsTab(), "Modelli AI")

        layout.addWidget(tabs)

        # Aggiunta dei pulsanti OK e Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.saveSettings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Carica le impostazioni salvate
        self.loadSettings()

    def createTTSSettingsTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.elevenLabsRadio = QRadioButton("Eleven Labs")
        self.internalRadio = QRadioButton("Motore Interno")

        # Gruppo di pulsanti per assicurarsi che solo uno sia selezionato
        self.ttsButtonGroup = QButtonGroup()
        self.ttsButtonGroup.addButton(self.elevenLabsRadio)
        self.ttsButtonGroup.addButton(self.internalRadio)

        layout.addWidget(QLabel("Seleziona il motore TTS da utilizzare:"))
        layout.addWidget(self.elevenLabsRadio)
        layout.addWidget(self.internalRadio)

        # Layout placeholder
        layout.addStretch(1)

        return tab

    def createModelSettingsTab(self):
        tab = QWidget()
        layout = QGridLayout(tab)

        layout.addWidget(QLabel("<b>Impostazioni Modelli Claude</b>"), 0, 0, 1, 2)

        # Lista dei modelli disponibili
        available_models = [
            MODEL_3_7_SONNET,
            MODEL_3_5_HAIKU,
            MODEL_3_5_SONNET_V2,
            MODEL_3_5_SONNET,
            MODEL_3_OPUS,
            MODEL_3_SONNET,
            MODEL_3_HAIKU
        ]

        # ComboBox per Frame Extractor
        layout.addWidget(QLabel("Modello per estrazione frame:"), 1, 0)
        self.frameExtractorCombo = QComboBox()
        self.frameExtractorCombo.addItems(available_models)
        layout.addWidget(self.frameExtractorCombo, 1, 1)

        # ComboBox per Text Processing
        layout.addWidget(QLabel("Modello per elaborazione testo:"), 2, 0)
        self.textProcessingCombo = QComboBox()
        self.textProcessingCombo.addItems(available_models)
        layout.addWidget(self.textProcessingCombo, 2, 1)

        # ComboBox per PPTX Generation
        layout.addWidget(QLabel("Modello per generazione presentazioni:"), 3, 0)
        self.pptxGenCombo = QComboBox()
        self.pptxGenCombo.addItems(available_models)
        layout.addWidget(self.pptxGenCombo, 3, 1)

        # ComboBox per Browser Agent
        layout.addWidget(QLabel("Modello per Browser Agent:"), 4, 0)
        self.browserAgentCombo = QComboBox()
        self.browserAgentCombo.addItems(available_models)
        layout.addWidget(self.browserAgentCombo, 4, 1)

        # ComboBox per Summary
        layout.addWidget(QLabel("Modello per riassunti:"), 5, 0)
        self.summaryCombo = QComboBox()
        self.summaryCombo.addItems(available_models)
        layout.addWidget(self.summaryCombo, 5, 1)

        # Aggiunge spazio in fondo
        layout.setRowStretch(6, 1)

        tab.setLayout(layout)
        return tab

    def loadSettings(self):
        # Carica le impostazioni TTS
        tts_engine = self.settings.value("tts/engine", "elevenlabs")
        if tts_engine == "elevenlabs":
            self.elevenLabsRadio.setChecked(True)
        else:
            self.internalRadio.setChecked(True)

        # Carica le impostazioni dei modelli
        frame_extractor_model = self.settings.value("models/frame_extractor", CLAUDE_MODEL_FRAME_EXTRACTOR)
        text_processing_model = self.settings.value("models/text_processing", CLAUDE_MODEL_TEXT_PROCESSING)
        pptx_gen_model = self.settings.value("models/pptx_generation", CLAUDE_MODEL_PPTX_GENERATION)
        browser_agent_model = self.settings.value("models/browser_agent", CLAUDE_MODEL_BROWSER_AGENT)
        summary_model = self.settings.value("models/summary", CLAUDE_MODEL_SUMMARY)

        # Imposta i valori nelle combo box
        self._setComboBoxValue(self.frameExtractorCombo, frame_extractor_model)
        self._setComboBoxValue(self.textProcessingCombo, text_processing_model)
        self._setComboBoxValue(self.pptxGenCombo, pptx_gen_model)
        self._setComboBoxValue(self.browserAgentCombo, browser_agent_model)
        self._setComboBoxValue(self.summaryCombo, summary_model)

    def _setComboBoxValue(self, combo_box, value):
        index = combo_box.findText(value)
        if index >= 0:
            combo_box.setCurrentIndex(index)

    def saveSettings(self):
        # Salva le impostazioni TTS
        tts_engine = "elevenlabs" if self.elevenLabsRadio.isChecked() else "internal"
        self.settings.setValue("tts/engine", tts_engine)

        # Salva le impostazioni dei modelli
        self.settings.setValue("models/frame_extractor", self.frameExtractorCombo.currentText())
        self.settings.setValue("models/text_processing", self.textProcessingCombo.currentText())
        self.settings.setValue("models/pptx_generation", self.pptxGenCombo.currentText())
        self.settings.setValue("models/browser_agent", self.browserAgentCombo.currentText())
        self.settings.setValue("models/summary", self.summaryCombo.currentText())

        self.accept()