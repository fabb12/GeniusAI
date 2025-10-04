import json
from PyQt6.QtCore import QPoint, QSize
import logging
from src.config import DOCK_SETTINGS_FILE
from src.config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

class DockSettingsManager:
    def __init__(self, main_window, docks, parent):
        self.parent = parent
        self.main_window = main_window
        self.docks = docks  # Dizionario dei docks: {nome_dock: istanza_dock}
        self.settings_file = DOCK_SETTINGS_FILE

    def save_settings(self):
        settings = {'main_window': {
            'width': self.main_window.size().width(),
            'height': self.main_window.size().height(),
            'x': self.main_window.pos().x(),
            'y': self.main_window.pos().y()
        }}
        for name, dock in self.docks.items():
            settings[name] = {
                'visible': dock.isVisible(),
                'x': dock.pos().x(),
                'y': dock.pos().y(),
                'width': dock.size().width(),
                'height': dock.size().height()
            }
        with open(self.settings_file, 'w') as file:
            json.dump(settings, file, indent=4)

    def load_settings(self, settings_file=None):
        if not settings_file:
            settings_file = self.settings_file

        try:
            for dock in self.docks.values():
                dock.setVisible(False)

            with open(settings_file, 'r') as file:
                settings = json.load(file)

            main_window_settings = settings.get('main_window', {})
            self.main_window.resize(
                QSize(main_window_settings.get('width', DEFAULT_WINDOW_WIDTH),
                      main_window_settings.get('height', DEFAULT_WINDOW_HEIGHT)))
            self.main_window.move(QPoint(main_window_settings.get('x', 100), main_window_settings.get('y', 100)))

            for name, dock in self.docks.items():
                dock_settings = settings.get(name, {})
                dock.setVisible(dock_settings.get('visible', True))
                dock.resize(QSize(dock_settings.get('width', 600), dock_settings.get('height', 200)))
                dock.move(QPoint(dock_settings.get('x', 100), dock_settings.get('y', 100)))

            self.main_window.updateViewMenu()

        except FileNotFoundError:
            logging.debug("Settings file not found. Using default settings.")
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
            self.docks['videoNotesDock'].setVisible(True)
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
