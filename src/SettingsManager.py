import json
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QPoint, QSize


class DockSettingsManager:
    def __init__(self, main_window, docks, parent):
        self.parent = parent
        self.main_window = main_window
        self.docks = docks  # Dizionario dei docks: {nome_dock: istanza_dock}
        self.settings_file = './dock_settings.json'  # File per il salvataggio delle impostazioni

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

            # Carica le impostazioni della finestra principale
            main_window_settings = settings.get('main_window', {})
            self.main_window.resize(
                QSize(main_window_settings.get('width', 800), main_window_settings.get('height', 600)))
            self.main_window.move(QPoint(main_window_settings.get('x', 100), main_window_settings.get('y', 100)))

            # Carica le impostazioni per ciascun dock
            for name, dock in self.docks.items():
                dock_settings = settings.get(name, {})
                dock.setVisible(dock_settings.get('visible', True))
                dock.resize(QSize(dock_settings.get('width', 200), dock_settings.get('height', 200)))
                dock.move(QPoint(dock_settings.get('x', 100), dock_settings.get('y', 100)))

            self.main_window.updateViewMenu()

        except FileNotFoundError:
            logging.debug("Settings file not found. Using default settings.")

    def apply_visibility(self, name, visible):
        if name in self.docks:
            self.docks[name].setVisible(visible)

    def loadDockSettingsUser1(self):

        self.docks['videoPlayerOutput'].setVisible(True)
        self.docks['recordingDock'].setVisible(True)

        self.docks['videoPlayerDock'].setVisible(False)
        self.docks['audioDock'].setVisible(False)
        self.docks['transcriptionDock'].setVisible(False)
        self.docks['editingDock'].setVisible(False)
        self.docks['downloadDock'].setVisible(False)
        self.docks['videoMergeDock'].setVisible(False)

    def resetAll(self):
        self.docks['recordingDock'].setVisible(False)
        self.docks['videoPlayerOutput'].setVisible(False)

        self.docks['videoPlayerDock'].setVisible(False)
        self.docks['audioDock'].setVisible(False)
        self.docks['transcriptionDock'].setVisible(False)
        self.docks['editingDock'].setVisible(False)
        self.docks['downloadDock'].setVisible(False)
        self.docks['videoMergeDock'].setVisible(False)

    def loadDockSettingsUser2(self):
        self.resetAll()

        self.docks['videoPlayerDock'].setVisible(True)
        self.docks['transcriptionDock'].setVisible(True)

        self.docks['videoPlayerOutput'].setVisible(False)
        self.docks['audioDock'].setVisible(False)
        self.docks['editingDock'].setVisible(False)
        self.docks['downloadDock'].setVisible(False)
        self.docks['recordingDock'].setVisible(False)
        self.docks['videoMergeDock'].setVisible(False)
