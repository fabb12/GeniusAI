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
        self.dock_area = self.main_window.centralWidget()
        if not isinstance(self.dock_area, DockArea):
            raise TypeError("Main window's central widget is not a DockArea.")
        self.loaded_state = None

    def save_settings(self):
        """
        Saves the main window's geometry and the complete state of the DockArea.
        """
        try:
            state = self.dock_area.saveState()
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
        Loads the main window's geometry and reads the dock state into memory,
        but does not apply it immediately.
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

            if 'dock_area_state' in settings:
                state_str = settings['dock_area_state']
                self.loaded_state = QByteArray.fromBase64(state_str.encode('ascii'))
                logging.info("Dock state loaded into memory.")
            else:
                logging.warning("Dock area state not found in settings file.")

        except FileNotFoundError:
            logging.info("Settings file not found. Will use default layout.")
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logging.error(f"Error loading settings file '{settings_file}': {e}. Will use default layout.")
            self.loaded_state = None

    def apply_settings(self):
        """
        Applies the loaded dock state. If no state was loaded or if restoring fails,
        it applies the default layout. This should be called after the main window is shown.
        """
        if self.loaded_state:
            try:
                self.dock_area.restoreState(self.loaded_state, restore_sizes=True)
                logging.info("Dock settings applied successfully.")
            except Exception as e:
                logging.error(f"Failed to apply loaded dock state: {e}. Falling back to default.")
                self.loadDefaultLayout()
        else:
            logging.info("No saved state to apply. Loading default layout.")
            self.loadDefaultLayout()

        # Always update the view menu after attempting to apply any layout.
        self.main_window.updateViewMenu()

    def set_workspace(self, workspace_name):
        """Imposta la visibilità dei dock in base al workspace selezionato."""
        for dock in self.docks.values():
            dock.hideDock()

        if workspace_name == "Registrazione":
            self.docks['recordingDock'].showDock()
            self.docks['videoPlayerOutput'].showDock()
        elif workspace_name == "Confronto":
            self.docks['videoPlayerDock'].showDock()
            self.docks['videoPlayerOutput'].showDock()
        elif workspace_name == "Trascrizione":
            self.docks['videoPlayerDock'].showDock()
            self.docks['transcriptionDock'].showDock()
        elif workspace_name == "Default":
            self.loadDefaultLayout()

        self.main_window.updateViewMenu()

    def loadRecordingLayout(self):
        self.set_workspace("Registrazione")

    def loadComparisonLayout(self):
        self.set_workspace("Confronto")

    def loadTranscriptionLayout(self):
        self.set_workspace("Trascrizione")

    def loadDefaultLayout(self):
        """
        Carica un layout di default esplicito, mostrando i dock principali.
        """
        for name, dock in self.docks.items():
            # Show only the most common docks by default
            if name in ['videoPlayerDock', 'videoPlayerOutput', 'transcriptionDock', 'editingDock']:
                dock.showDock()
            else:
                dock.hideDock()
        self.main_window.updateViewMenu()