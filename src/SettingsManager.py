import json
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QPoint, QSize


class DockSettingsManager:
    def __init__(self, main_window, docks):
        self.main_window = main_window
        self.docks = docks  # Dizionario dei docks: {nome_dock: istanza_dock}
        self.settings_file = '../dock_settings.json'  # File per il salvataggio delle impostazioni


    def save_settings(self):
        self.settings.beginGroup("DockLayout")
        for dock_name, dock in self.docks.items():
            self.settings.setValue(f"{dock_name}/geometry", dock.saveGeometry())
            self.settings.setValue(f"{dock_name}/visible", dock.isVisible())
        self.settings.endGroup()

    def load_settings(self):
        try:
            for dock in self.docks.values():
                dock.setVisible(False)

            with open(self.settings_file, 'r') as file:
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
            print("Settings file not found. Using default settings.")

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
                # Aggiungi qui il salvataggio dell'area se gestibile
                # 'area': self.main_window.getDockArea(dock)
            }
        with open(self.settings_file, 'w') as file:
            json.dump(settings, file, indent=4)

    def apply_visibility(self, name, visible):
        if name in self.docks:
            self.docks[name].setVisible(visible)
