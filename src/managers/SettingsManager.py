import json
from PyQt6.QtCore import QPoint, QSize, QByteArray
import logging
from src.config import DOCK_SETTINGS_FILE
from src.config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
from pyqtgraph.dockarea.DockArea import DockArea

class DockSettingsManager:
    def __init__(self, main_window, docks, parent):
        self.parent = parent
        self.main_window = main_window
        self.docks = docks
        self.settings_file = DOCK_SETTINGS_FILE
        # Get the DockArea instance from the main window's central widget
        self.dock_area = self.main_window.centralWidget()
        if not isinstance(self.dock_area, DockArea):
            raise TypeError("Main window's central widget is not a DockArea.")

    def save_settings(self):
        """
        Saves the main window's geometry and the complete state of the DockArea,
        including the state of all docks (both docked and floating).
        """
        try:
            state = self.dock_area.saveState()
            # The state can be converted to a string for JSON serialization.
            # QByteArray.toBase64() returns a QByteArray, so we need to decode it to a string.
            state_str = bytes(state.toBase64()).decode('ascii')

            settings = {
                'main_window': {
                    'width': self.main_window.size().width(),
                    'height': self.main_window.size().height(),
                    'x': self.main_window.pos().x(),
                    'y': self.main_window.pos().y()
                },
                'dock_area_state': state_str
            }
            with open(self.settings_file, 'w') as file:
                json.dump(settings, file, indent=4)
            logging.info("Dock settings saved successfully.")
        except Exception as e:
            logging.error(f"Error saving dock settings: {e}")

    def load_settings(self, settings_file=None):
        """
        Loads the main window's geometry and restores the state of the DockArea.
        """
        if not settings_file:
            settings_file = self.settings_file

        try:
            with open(settings_file, 'r') as file:
                settings = json.load(file)

            # Restore main window geometry
            main_window_settings = settings.get('main_window', {})
            self.main_window.resize(
                QSize(main_window_settings.get('width', DEFAULT_WINDOW_WIDTH),
                      main_window_settings.get('height', DEFAULT_WINDOW_HEIGHT)))
            self.main_window.move(QPoint(main_window_settings.get('x', 100), main_window_settings.get('y', 100)))

            # Restore DockArea state
            if 'dock_area_state' in settings:
                state_str = settings['dock_area_state']
                # The state needs to be converted back from a Base64 string to a QByteArray.
                state = QByteArray.fromBase64(state_str.encode('ascii'))
                self.dock_area.restoreState(state, restore_sizes=True)
                logging.info("Dock settings loaded successfully.")
            else:
                logging.warning("Dock area state not found in settings file. Loading default layout.")
                self.loadDefaultLayout()

            self.main_window.updateViewMenu()

        except FileNotFoundError:
            logging.info("Settings file not found. Using default layout.")
            self.loadDefaultLayout()
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logging.error(f"Error loading settings file '{settings_file}': {e}. Using default layout.")
            # If the file is corrupted or has an unexpected format, load defaults.
            self.loadDefaultLayout()


    def set_workspace(self, workspace_name):
        """Imposta la visibilità dei dock in base al workspace selezionato."""

        # Nascondi tutti i dock prima di impostare il nuovo layout
        for dock in self.docks.values():
            dock.setVisible(False)

        if workspace_name == "Registrazione":
            self.docks['recordingDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
        elif workspace_name == "Confronto":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
        elif workspace_name == "Trascrizione":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['transcriptionDock'].setVisible(True)
        elif workspace_name == "Default":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
            self.docks['transcriptionDock'].setVisible(True)
            self.docks['editingDock'].setVisible(True)
            self.docks['downloadDock'].setVisible(True)
            self.docks['recordingDock'].setVisible(True)
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