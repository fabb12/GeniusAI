# File: managers/Settings.py
# Corretto per QSizePolicy.Policy.Expanding e include il tab API Keys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget,
    QDialogButtonBox, QLabel, QComboBox, QGridLayout,
    QLineEdit, QFormLayout, QMessageBox,
    QSizePolicy # Importazione necessaria per lo spaziatore
)
from PyQt6.QtCore import QSettings
# Importa la configurazione delle azioni e, se necessario, l'endpoint di Ollama per info
from src.config import ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT

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
        warningLabel = QLabel(
            "<font color='orange'><b>Attenzione:</b> Salvare le API keys nelle impostazioni "
            "dell'applicazione potrebbe essere meno sicuro rispetto all'uso di variabili d'ambiente "
            "(.env). Le chiavi qui inserite vengono salvate localmente.</font>"
        )
        warningLabel.setWordWrap(True)
        layout.addRow(warningLabel) # Aggiunge l'avviso al layout

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

        # --- Accetta e chiudi dialogo ---
        self.accept()