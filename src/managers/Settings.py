# File: managers/Settings.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget,
    QDialogButtonBox, QLabel, QComboBox, QGridLayout,
    QLineEdit, QFormLayout, QCheckBox,
    QSizePolicy, QPushButton, QFileDialog, QSpinBox, QHBoxLayout,
    QFontComboBox
)
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont
from src.config import ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT, WATERMARK_IMAGE, HIGHLIGHT_COLORS

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Impostazioni Applicazione")
        self.settings = QSettings("Genius", "GeniusAI")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.model_combos = {}
        self.api_key_edits = {}

        # Usa la configurazione centralizzata dei colori
        self.highlight_colors = HIGHLIGHT_COLORS

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setUsesScrollButtons(False)
        tabs.addTab(self.createApiKeySettingsTab(), "API Keys")
        tabs.addTab(self.createModelSettingsWidget(), "Modelli AI")
        tabs.addTab(self.createCursorSettingsTab(), "Cursore")
        tabs.addTab(self.createRecordingSettingsTab(), "Registrazione")
        tabs.addTab(self.createEditorSettingsTab(), "Editor")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.saveSettings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.loadSettings()

    def createApiKeySettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.api_key_edits['elevenlabs'] = QLineEdit(echoMode=QLineEdit.EchoMode.Password, toolTip="API Key di ElevenLabs.")
        layout.addRow("ElevenLabs API Key:", self.api_key_edits['elevenlabs'])
        self.api_key_edits['anthropic'] = QLineEdit(echoMode=QLineEdit.EchoMode.Password, toolTip="API Key di Anthropic (Claude).")
        layout.addRow("Anthropic (Claude) API Key:", self.api_key_edits['anthropic'])
        self.api_key_edits['google'] = QLineEdit(echoMode=QLineEdit.EchoMode.Password, toolTip="API Key di Google AI (Gemini).")
        layout.addRow("Google AI (Gemini) API Key:", self.api_key_edits['google'])
        self.api_key_edits['openai'] = QLineEdit(echoMode=QLineEdit.EchoMode.Password, toolTip="API Key di OpenAI (GPT).")
        layout.addRow("OpenAI (GPT) API Key:", self.api_key_edits['openai'])
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addRow(spacer)
        return widget

    def createModelSettingsWidget(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.addWidget(QLabel("<b>Seleziona il Modello AI per ogni Azione:</b>"), 0, 0, 1, 2)
        row = 1
        for action, config in ACTION_MODELS_CONFIG.items():
            if not config.get('allowed') or not config.get('setting_key'): continue
            label = QLabel(f"{config.get('display_name', action.replace('_', ' ').title())}:")
            combo = QComboBox(toolTip=f"Modello per: {config.get('display_name')}")
            combo.addItems(config.get('allowed', []))
            layout.addWidget(label, row, 0)
            layout.addWidget(combo, row, 1)
            self.model_combos[action] = combo
            row += 1
        layout.setRowStretch(row, 1)
        if any("ollama:" in m for cfg in ACTION_MODELS_CONFIG.values() for m in cfg.get('allowed', [])):
            ollama_note = QLabel(f"<i>Nota: I modelli 'ollama:' richiedono Ollama in esecuzione (default: {OLLAMA_ENDPOINT}).</i>")
            ollama_note.setWordWrap(True)
            layout.addWidget(ollama_note, row, 0, 1, 2)
            layout.setRowStretch(row + 1, 1)
        return widget

    def createCursorSettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.showRedDot = QCheckBox()
        layout.addRow("Mostra Punto Rosso:", self.showRedDot)
        return widget

    def createRecordingSettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.enableWatermark = QCheckBox()
        layout.addRow("Abilita Watermark:", self.enableWatermark)
        self.watermarkPathEdit = QLineEdit(readOnly=True)
        browseButton = QPushButton("Sfoglia...")
        browseButton.clicked.connect(self.browseWatermark)
        pathLayout = QHBoxLayout()
        pathLayout.addWidget(self.watermarkPathEdit)
        pathLayout.addWidget(browseButton)
        layout.addRow("File Watermark:", pathLayout)
        self.watermarkSizeSpinBox = QSpinBox(minimum=1, maximum=200, suffix=" %")
        layout.addRow("Dimensione Watermark:", self.watermarkSizeSpinBox)
        self.watermarkPositionComboBox = QComboBox()
        self.watermarkPositionComboBox.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        layout.addRow("Posizione Watermark:", self.watermarkPositionComboBox)
        self.useVBCableCheckBox = QCheckBox(toolTip="Abilita VB-CABLE per la registrazione audio (utile per cuffie bluetooth).")
        layout.addRow("Abilita VB-CABLE:", self.useVBCableCheckBox)
        return widget

    def browseWatermark(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Watermark", "", "Images (*.png *.jpg)")
        if filePath:
            self.watermarkPathEdit.setText(filePath)

    def createEditorSettingsTab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.fontFamilyComboBox = QFontComboBox(toolTip="Famiglia di caratteri per l'editor.")
        layout.addRow("Font Family:", self.fontFamilyComboBox)
        self.fontSizeSpinBox = QSpinBox(minimum=6, maximum=72, suffix=" pt", toolTip="Dimensione del carattere.")
        layout.addRow("Font Size:", self.fontSizeSpinBox)
        self.highlightColorComboBox = QComboBox(toolTip="Colore per l'evidenziazione del testo.")
        self.highlightColorComboBox.addItems(self.highlight_colors.keys())
        layout.addRow("Colore Evidenziatore:", self.highlightColorComboBox)
        return widget

    def loadSettings(self):
        for key, edit in self.api_key_edits.items():
            edit.setText(self.settings.value(f"api_keys_dialog/{key}", ""))
        for action, config in ACTION_MODELS_CONFIG.items():
            if combo := self.model_combos.get(action):
                saved_model = self.settings.value(config['setting_key'], config['default'])
                self._setComboBoxValue(combo, saved_model)
        self.showRedDot.setChecked(self.settings.value("cursor/showRedDot", True, type=bool))
        self.enableWatermark.setChecked(self.settings.value("recording/enableWatermark", True, type=bool))
        self.watermarkPathEdit.setText(self.settings.value("recording/watermarkPath", WATERMARK_IMAGE))
        self.watermarkSizeSpinBox.setValue(self.settings.value("recording/watermarkSize", 10, type=int))
        self.watermarkPositionComboBox.setCurrentText(self.settings.value("recording/watermarkPosition", "Bottom Right"))
        self.useVBCableCheckBox.setChecked(self.settings.value("recording/useVBCable", False, type=bool))
        self.fontFamilyComboBox.setCurrentFont(QFont(self.settings.value("editor/fontFamily", "Arial")))
        self.fontSizeSpinBox.setValue(self.settings.value("editor/fontSize", 14, type=int))
        self.highlightColorComboBox.setCurrentText(self.settings.value("editor/highlightColor", "Giallo"))

    def _setComboBoxValue(self, combo, value):
        index = combo.findText(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
        if index < 0:
            print(f"Attenzione: Modello '{value}' non trovato per {combo.toolTip()}. Impostato default.")

    def saveSettings(self):
        for key, edit in self.api_key_edits.items():
            self.settings.setValue(f"api_keys_dialog/{key}", edit.text())
        for action, config in ACTION_MODELS_CONFIG.items():
            if combo := self.model_combos.get(action):
                self.settings.setValue(config['setting_key'], combo.currentText())
        self.settings.setValue("cursor/showRedDot", self.showRedDot.isChecked())
        self.settings.setValue("recording/enableWatermark", self.enableWatermark.isChecked())
        self.settings.setValue("recording/watermarkPath", self.watermarkPathEdit.text())
        self.settings.setValue("recording/watermarkSize", self.watermarkSizeSpinBox.value())
        self.settings.setValue("recording/watermarkPosition", self.watermarkPositionComboBox.currentText())
        self.settings.setValue("recording/useVBCable", self.useVBCableCheckBox.isChecked())
        self.settings.setValue("editor/fontFamily", self.fontFamilyComboBox.currentFont().family())
        self.settings.setValue("editor/fontSize", self.fontSizeSpinBox.value())
        self.settings.setValue("editor/highlightColor", self.highlightColorComboBox.currentText())
        self.accept()