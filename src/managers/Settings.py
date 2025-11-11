# File: managers/Settings.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget,
    QDialogButtonBox, QLabel, QComboBox, QGridLayout,
    QLineEdit, QFormLayout, QCheckBox,
    QSizePolicy, QPushButton, QFileDialog, QSpinBox, QHBoxLayout,
    QFontComboBox
)
import os
import whisper
import torch
from PyQt6.QtCore import QSettings, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from src.config import ACTION_MODELS_CONFIG, OLLAMA_ENDPOINT, WATERMARK_IMAGE, HIGHLIGHT_COLORS
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QProgressBar, QMessageBox, QGroupBox

class ModelDownloaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model_name, cache_dir):
        super().__init__()
        self.model_name = model_name
        self.cache_dir = cache_dir

    def run(self):
        try:
            whisper._download(whisper._MODELS[self.model_name], self.cache_dir, self.progress.emit)
            self.finished.emit(self.model_name)
        except Exception as e:
            self.error.emit(str(e))

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
        tabs.addTab(self.createWhisperSettingsTab(), "Whisper")
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

            # Popola la ComboBox con i modelli categorizzati
            categorized_models = config.get('categorized_source')
            if categorized_models:
                for category, models in categorized_models.items():
                    # Aggiungi un separatore con il nome della categoria
                    combo.insertSeparator(combo.count())
                    header_font = QFont()
                    header_font.setBold(True)
                    combo.setItemData(combo.count() - 1, header_font, role=Qt.ItemDataRole.FontRole)
                    combo.setItemData(combo.count() - 1, QColor("gray"), role=Qt.ItemDataRole.ForegroundRole)
                    combo.model().item(combo.count() - 1).setFlags(Qt.ItemFlag.NoItemFlags)
                    combo.model().item(combo.count() - 1).setText(f"--- {category} ---")

                    # Aggiungi i modelli per la categoria
                    combo.addItems(models)
            else:
                # Fallback per la lista piatta se non ci sono categorie
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

        self.titleFontSizeSpinBox = QSpinBox(minimum=8, maximum=96, suffix=" pt", toolTip="Dimensione del carattere per i titoli (H1, H2).")
        layout.addRow("Dimensione Titoli:", self.titleFontSizeSpinBox)

        self.subtitleFontSizeSpinBox = QSpinBox(minimum=7, maximum=84, suffix=" pt", toolTip="Dimensione del carattere per i sottotitoli (H3, H4, ecc.).")
        layout.addRow("Dimensione Sottotitoli:", self.subtitleFontSizeSpinBox)

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
        self.titleFontSizeSpinBox.setValue(self.settings.value("editor/titleFontSize", 22, type=int))
        self.subtitleFontSizeSpinBox.setValue(self.settings.value("editor/subtitleFontSize", 18, type=int))
        self.highlightColorComboBox.setCurrentText(self.settings.value("editor/highlightColor", "Giallo"))
        # Carica impostazioni Whisper
        self.whisperModelComboBox.setCurrentText(self.settings.value("whisper/model", "base"))
        self.gpuCheckbox.setChecked(self.settings.value("whisper/use_gpu", torch.cuda.is_available(), type=bool))


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
        self.settings.setValue("editor/titleFontSize", self.titleFontSizeSpinBox.value())
        self.settings.setValue("editor/subtitleFontSize", self.subtitleFontSizeSpinBox.value())
        self.settings.setValue("editor/highlightColor", self.highlightColorComboBox.currentText())
        # Salva impostazioni Whisper
        self.settings.setValue("whisper/model", self.whisperModelComboBox.currentText())
        self.settings.setValue("whisper/use_gpu", self.gpuCheckbox.isChecked())
        self.accept()

    def createWhisperSettingsTab(self):
        widget = QWidget()
        self.whisperLayout = QVBoxLayout(widget)

        # Gruppo per le impostazioni del modello
        settings_group = QGroupBox("Impostazioni di Trascrizione")
        settings_layout = QFormLayout(settings_group)

        self.whisperModelComboBox = QComboBox()
        self.whisperModelComboBox.addItems(["tiny", "base", "small", "medium", "large"])
        settings_layout.addRow("Modello di default:", self.whisperModelComboBox)

        self.gpuCheckbox = QCheckBox("Usa GPU (CUDA) se disponibile")
        self.gpuCheckbox.setEnabled(torch.cuda.is_available())
        settings_layout.addRow(self.gpuCheckbox)
        self.whisperLayout.addWidget(settings_group)

        # Gruppo per la gestione dei modelli
        management_group = QGroupBox("Gestione Modelli Scaricati")
        management_layout = QVBoxLayout(management_group)

        self.listWidget = QListWidget()
        management_layout.addWidget(self.listWidget)

        self.progressBar = QProgressBar()
        self.progressBar.setVisible(False)
        self.whisperLayout.addWidget(self.progressBar)

        self.buttonLayout = QHBoxLayout()
        self.downloadButton = QPushButton("Download Selezionato")
        self.deleteButton = QPushButton("Elimina Selezionato")
        self.buttonLayout.addWidget(self.downloadButton)
        self.buttonLayout.addWidget(self.deleteButton)
        management_layout.addLayout(self.buttonLayout) # Aggiungi a questo layout
        self.whisperLayout.addWidget(management_group) # Aggiungi il gruppo principale


        self.downloadButton.clicked.connect(self.download_model)
        self.deleteButton.clicked.connect(self.delete_model)

        self.populate_models()
        return widget

    def get_cache_dir(self):
        """Returns the application's cache directory for Whisper models."""
        models_dir = "models"
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
        return models_dir

    def populate_models(self):
        self.listWidget.clear()
        cache_dir = self.get_cache_dir()
        for model_name in whisper.available_models():
            item = QListWidgetItem(model_name)
            is_downloaded = os.path.exists(os.path.join(cache_dir, f"{model_name}.pt"))
            item.setText(f"{model_name} {'(scaricato)' if is_downloaded else ''}")
            item.setData(Qt.ItemDataRole.UserRole, is_downloaded)
            self.listWidget.addItem(item)

    def download_model(self):
        selected_item = self.listWidget.currentItem()
        if not selected_item:
            return

        model_name = selected_item.text().split(' ')[0]
        is_downloaded = selected_item.data(Qt.ItemDataRole.UserRole)

        if is_downloaded:
            QMessageBox.information(self, "Modello già scaricato", "Il modello selezionato è già stato scaricato.")
            return

        self.downloadButton.setEnabled(False)
        self.deleteButton.setEnabled(False)
        self.progressBar.setVisible(True)

        self.downloader = ModelDownloaderThread(model_name, self.get_cache_dir())
        self.downloader.progress.connect(self.progressBar.setValue)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(self.on_download_error)
        self.downloader.start()

    def on_download_finished(self, model_name):
        self.progressBar.setVisible(False)
        self.downloadButton.setEnabled(True)
        self.deleteButton.setEnabled(True)
        QMessageBox.information(self, "Download completato", f"Il modello '{model_name}' è stato scaricato con successo.")
        self.populate_models()

    def on_download_error(self, error_message):
        self.progressBar.setVisible(False)
        self.downloadButton.setEnabled(True)
        self.deleteButton.setEnabled(True)
        QMessageBox.critical(self, "Errore di download", f"Errore durante il download del modello: {error_message}")

    def delete_model(self):
        selected_item = self.listWidget.currentItem()
        if not selected_item:
            return

        model_name = selected_item.text().split(' ')[0]
        is_downloaded = selected_item.data(Qt.ItemDataRole.UserRole)

        if not is_downloaded:
            QMessageBox.information(self, "Modello non presente", "Il modello selezionato non è presente sul disco.")
            return

        reply = QMessageBox.question(self, "Conferma eliminazione", f"Sei sicuro di voler eliminare il modello '{model_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                model_path = os.path.join(self.get_cache_dir(), f"{model_name}.pt")
                os.remove(model_path)
                QMessageBox.information(self, "Eliminazione completata", f"Il modello '{model_name}' è stato eliminato.")
                self.populate_models()
            except Exception as e:
                QMessageBox.critical(self, "Errore di eliminazione", f"Errore durante l'eliminazione del modello: {e}")