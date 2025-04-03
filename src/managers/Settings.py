# START OF MODIFICATION (managers/Settings.py)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QRadioButton,
    QButtonGroup, QDialogButtonBox, QLabel, QComboBox, QGridLayout
)
from PyQt6.QtCore import QSettings
# Importa solo la configurazione delle azioni e, se necessario, l'endpoint di Ollama per info
from src.config import ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.settings = QSettings("ThemaConsulting", "GeniusAI")
        # Dizionario per tenere traccia delle ComboBox create dinamicamente
        self.model_combos = {}

        layout = QVBoxLayout(self)

        # Creazione del widget tab
        tabs = QTabWidget()
        tabs.addTab(self.createTTSSettingsTab(), "Motori TTS")
        tabs.addTab(self.createModelSettingsTab(), "Modelli AI per Azione") # Titolo tab aggiornato

        layout.addWidget(tabs)

        # Aggiunta dei pulsanti OK e Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.saveSettings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Carica le impostazioni salvate
        self.loadSettings()

    def createTTSSettingsTab(self):
        # Questa funzione rimane invariata
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.elevenLabsRadio = QRadioButton("Eleven Labs")
        self.internalRadio = QRadioButton("Motore Interno (Non implementato)")
        self.internalRadio.setEnabled(False) # Disabilita se non implementato

        self.ttsButtonGroup = QButtonGroup()
        self.ttsButtonGroup.addButton(self.elevenLabsRadio)
        self.ttsButtonGroup.addButton(self.internalRadio)

        layout.addWidget(QLabel("Seleziona il motore TTS da utilizzare:"))
        layout.addWidget(self.elevenLabsRadio)
        layout.addWidget(self.internalRadio)
        layout.addStretch(1)

        # Imposta il default
        tts_engine = self.settings.value("tts/engine", "elevenlabs")
        if tts_engine == "elevenlabs":
            self.elevenLabsRadio.setChecked(True)
        else:
            # Se mai implementerai quello interno
            # self.internalRadio.setChecked(True)
            self.elevenLabsRadio.setChecked(True) # Fallback a elevenlabs

        return tab

    def createModelSettingsTab(self):
        tab = QWidget()
        layout = QGridLayout(tab)

        # Aggiungi un'intestazione
        layout.addWidget(QLabel("<b>Seleziona il Modello AI per ogni Azione Specifica:</b>"), 0, 0, 1, 2)

        # Itera sulla configurazione definita in config.py
        current_row = 1
        for action_key, config in ACTION_MODELS_CONFIG.items():
            display_name = config.get('display_name', action_key.replace('_', ' ').title())
            allowed_models = config.get('allowed', []) # Ottieni i modelli permessi per questa azione
            setting_key = config.get('setting_key')

            if not allowed_models or not setting_key:
                # Salta questa configurazione se mancano informazioni essenziali
                continue

            # Crea Label e ComboBox
            label = QLabel(f"{display_name}:")
            combo = QComboBox()
            combo.addItems(allowed_models) # Popola solo con i modelli permessi
            combo.setToolTip(f"Modello da usare per: {display_name}")

            # Aggiungi al layout
            layout.addWidget(label, current_row, 0)
            layout.addWidget(combo, current_row, 1)

            # Memorizza il riferimento alla ComboBox usando la action_key
            self.model_combos[action_key] = combo

            current_row += 1

        # Aggiunge spazio in fondo
        layout.setRowStretch(current_row, 1)

        # Aggiungi una nota sull'uso di Ollama se presente
        has_ollama = any("ollama:" in m for cfg in ACTION_MODELS_CONFIG.values() for m in cfg.get('allowed',[]))
        if has_ollama:
            ollama_note = QLabel(f"<i>Nota: I modelli 'ollama:' richiedono che Ollama sia in esecuzione (default: {OLLAMA_ENDPOINT}).</i>")
            ollama_note.setWordWrap(True)
            layout.addWidget(ollama_note, current_row, 0, 1, 2)
            layout.setRowStretch(current_row + 1, 1)


        tab.setLayout(layout)
        return tab

    def loadSettings(self):
        # Carica le impostazioni TTS (già gestito in createTTSSettingsTab)
        # tts_engine = self.settings.value("tts/engine", "elevenlabs")
        # if tts_engine == "elevenlabs":
        #     self.elevenLabsRadio.setChecked(True)
        # else:
        #     self.internalRadio.setChecked(True)

        # Carica le impostazioni per ciascuna azione AI
        for action_key, config in ACTION_MODELS_CONFIG.items():
            setting_key = config.get('setting_key')
            default_model = config.get('default')
            combo = self.model_combos.get(action_key)

            if setting_key and default_model and combo:
                # Leggi il valore salvato, usando il default da config se non esiste
                saved_model = self.settings.value(setting_key, default_model)
                self._setComboBoxValue(combo, saved_model)
            elif combo:
                # Se manca la config, prova a impostare un valore di default se possibile
                if combo.count() > 0:
                    combo.setCurrentIndex(0)

    def _setComboBoxValue(self, combo_box, value):
        """Imposta il valore corrente della ComboBox se il valore è presente."""
        index = combo_box.findText(value)
        if index >= 0:
            combo_box.setCurrentIndex(index)
        else:
            # Se il valore salvato non è più tra quelli permessi, imposta il primo disponibile
            if combo_box.count() > 0:
                combo_box.setCurrentIndex(0)
                print(f"Attenzione: Il modello salvato '{value}' non è più disponibile per {combo_box.toolTip()}. Impostato il primo modello disponibile.")


    def saveSettings(self):
        # Salva le impostazioni TTS
        tts_engine = "elevenlabs" if self.elevenLabsRadio.isChecked() else "internal"
        self.settings.setValue("tts/engine", tts_engine)

        # Salva le impostazioni per ciascuna azione AI
        for action_key, config in ACTION_MODELS_CONFIG.items():
            setting_key = config.get('setting_key')
            combo = self.model_combos.get(action_key)

            if setting_key and combo:
                current_model = combo.currentText()
                self.settings.setValue(setting_key, current_model)

        self.accept()

# END OF MODIFICATION (managers/Settings.py)