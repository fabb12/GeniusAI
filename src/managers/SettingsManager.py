import json
import base64
from PyQt6.QtCore import QPoint, QSize, QByteArray
import logging
from src.config import DOCK_SETTINGS_FILE
from src.config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

class DockSettingsManager:
    def __init__(self, main_window, docks, parent):
        self.parent = parent
        self.main_window = main_window
        self.docks = docks
        self.settings_file = DOCK_SETTINGS_FILE

    def save_settings(self):
        """
        Salva la geometria della finestra principale e lo stato completo dei dock.
        Lo stato viene codificato in Base64 per essere serializzabile in JSON.
        """
        state = self.main_window.saveState()
        state_base64 = base64.b64encode(state.data()).decode('ascii')

        settings = {
            'main_window': {
                'width': self.main_window.size().width(),
                'height': self.main_window.size().height(),
                'x': self.main_window.pos().x(),
                'y': self.main_window.pos().y()
            },
            'dock_state_base64': state_base64
        }
        with open(self.settings_file, 'w') as file:
            json.dump(settings, file, indent=4)
        logging.info("Impostazioni del layout dei dock salvate.")

    def load_settings(self, settings_file=None):
        """
        Carica e applica la geometria della finestra principale e lo stato dei dock.
        Lo stato viene decodificato da Base64 prima di essere ripristinato.
        """
        if not settings_file:
            settings_file = self.settings_file

        try:
            with open(settings_file, 'r') as file:
                settings = json.load(file)

            main_window_settings = settings.get('main_window', {})
            self.main_window.resize(
                QSize(main_window_settings.get('width', DEFAULT_WINDOW_WIDTH),
                      main_window_settings.get('height', DEFAULT_WINDOW_HEIGHT)))
            self.main_window.move(QPoint(main_window_settings.get('x', 100), main_window_settings.get('y', 100)))

            state_base64 = settings.get('dock_state_base64')
            if state_base64:
                state_data = base64.b64decode(state_base64)
                self.main_window.restoreState(QByteArray(state_data))
                logging.info("Layout dei dock ripristinato dal file di impostazioni.")
            else:
                logging.warning("Nessuno stato dei dock trovato nel file. Caricamento del layout di default.")
                self.loadDefaultLayout()

            self.main_window.updateViewMenu()

        except (FileNotFoundError, json.JSONDecodeError, KeyError, binascii.Error) as e:
            logging.warning(f"File di impostazioni non trovato o corrotto ({e}). Caricamento del layout di default.")
            self.loadDefaultLayout()

    def set_workspace(self, workspace_name):
        """Imposta la visibilità dei dock in base al workspace selezionato."""

        # Nascondi tutti i dock prima di impostare il nuovo layout
        for dock in self.docks.values():
            dock.setVisible(False)

        if workspace_name == "Registrazione":
            self.docks['recordingDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
            self.docks['projectDock'].setVisible(True)
        elif workspace_name == "Confronto":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
        elif workspace_name == "Trascrizione":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['transcriptionDock'].setVisible(True)
            self.docks['projectDock'].setVisible(True)
        elif workspace_name == "Default":
            self.docks['videoNotesDock'].setVisible(True)
            self.docks['projectDock'].setVisible(True)
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
            self.docks['transcriptionDock'].setVisible(True)
            self.docks['editingDock'].setVisible(True)
            self.docks['audioDock'].setVisible(True)

        self.main_window.updateViewMenu()

    def loadRecordingLayout(self):
        """Carica il layout per la registrazione video."""
        self.set_workspace("Registrazione")

    def loadComparisonLayout(self):
        """Carica il layout per confrontare due video."""
        self.set_workspace("Confronto")

    def loadTranscriptionLayout(self):
        """Carica il layout per la trascrizione."""
        self.set_workspace("Trascrizione")

    def loadDefaultLayout(self):
        """Carica il layout di default con i dock principali."""
        self.set_workspace("Default")
