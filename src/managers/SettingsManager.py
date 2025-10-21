import json
from PyQt6.QtCore import QByteArray
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import logging
from src.config import DOCK_SETTINGS_FILE


class DockSettingsManager:
    def __init__(self, main_window, docks, parent):
        self.parent = parent
        self.main_window = main_window
        self.docks = docks
        self.settings_file = DOCK_SETTINGS_FILE

    def save_settings(self, settings_file=None):
        """
        Salva la geometria e lo stato della finestra principale, lo stato dell'area dei dock
        e la visibilità di ogni singolo dock.
        """
        if not settings_file:
            settings_file = self.settings_file

        area = self.main_window.centralWidget()
        dock_state = area.saveState()

        docks_visibility = {name: dock.isVisible() for name, dock in self.docks.items()}

        settings = {
            'main_window_geometry': self.main_window.saveGeometry().data().hex(),
            'main_window_state': self.main_window.saveState().data().hex(),
            'dock_state': dock_state,
            'docks_visibility': docks_visibility
        }
        try:
            with open(settings_file, 'w') as file:
                json.dump(settings, file, indent=4)
            logging.info(f"Impostazioni del layout salvate in {settings_file}.")
            return True
        except IOError as e:
            logging.error(f"Errore durante il salvataggio del file di layout {settings_file}: {e}")
            return False

    def load_settings(self, settings_file=None):
        """
        Carica e applica la geometria e lo stato della finestra principale, la visibilità dei dock
        e lo stato dell'area dei dock.
        """
        if not settings_file:
            settings_file = self.settings_file

        try:
            with open(settings_file, 'r') as file:
                settings = json.load(file)

            # 1. Ripristina la geometria e lo stato della finestra principale.
            if 'main_window_geometry' in settings:
                self.main_window.restoreGeometry(QByteArray.fromHex(settings['main_window_geometry'].encode()))
            if 'main_window_state' in settings:
                self.main_window.restoreState(QByteArray.fromHex(settings['main_window_state'].encode()))

            # 2. Imposta la visibilità dei dock PRIMA di ripristinare lo stato dell'area.
            docks_visibility = settings.get('docks_visibility')
            if docks_visibility:
                for name, is_visible in docks_visibility.items():
                    if name in self.docks:
                        self.docks[name].setVisible(is_visible)

            # 3. Ripristina lo stato dell'area dei dock.
            dock_state = settings.get('dock_state')
            if dock_state:
                area = self.main_window.centralWidget()
                area.restoreState(dock_state)
                logging.info("Stato dell'area dei dock ripristinato.")

            self.main_window.updateViewMenu()
            self.main_window.updateGeometry()


        except FileNotFoundError:
            logging.warning(f"File di impostazioni '{settings_file}' non trovato. Caricamento del layout di default.")
            self.loadDefaultLayout()
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logging.error(f"File di impostazioni '{settings_file}' corrotto o malformato ({e}). Caricamento del layout di default.")
            QMessageBox.critical(self.main_window, "Errore di Caricamento",
                                 f"Il file di layout '{settings_file}' è corrotto o non valido.\n"
                                 "Verrà caricato il layout di default.")
            self.loadDefaultLayout()

    def save_layout_as(self):
        """Apre un dialogo per salvare il layout corrente in un file JSON."""
        filePath, _ = QFileDialog.getSaveFileName(self.main_window, "Salva Layout", "", "JSON Files (*.json)")
        if filePath:
            if self.save_settings(filePath):
                QMessageBox.information(self.main_window, "Successo", f"Layout salvato con successo in:\n{filePath}")
            else:
                QMessageBox.critical(self.main_window, "Errore", f"Impossibile salvare il layout in:\n{filePath}")

    def load_layout_from(self):
        """Apre un dialogo per caricare un layout da un file JSON."""
        filePath, _ = QFileDialog.getOpenFileName(self.main_window, "Carica Layout", "", "JSON Files (*.json)")
        if filePath:
            self.load_settings(filePath)

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
        self.main_window.centralWidget().updateGeometry()

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
