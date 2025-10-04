import os
import subprocess
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
from src.config import CONTACTS_FILE

class VideoSharingManager:
    def __init__(self, parent):
        self.parent = parent  # Riferimento alla finestra principale per mostrare i messaggi

    def shareVideo(self, video_path):
        if not video_path or not os.path.exists(video_path):
            if self.parent and hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message("Non c'è nessun video caricato da condividere.", error=True)
            return

        try:
            self.shareOnTeams(video_path)
        except Exception as e:
            QMessageBox.critical(self.parent, "Errore durante la condivisione", str(e))

    def shareOnTeams(self, file_path):
        try:
            contacts = self.get_contacts_from_txt()
            if not contacts:
                if self.parent and hasattr(self.parent, 'show_status_message'):
                    self.parent.show_status_message("Elenco contatti non trovato o vuoto.", error=True)
                return

            dialog = ContactSelectionDialog(contacts, self.parent)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_contact = dialog.get_selected_contact()
                if selected_contact:
                    contact_email = selected_contact.split('(')[-1][:-1]
                    file_message = f"Ti condivido questo video --> {file_path}"
                    teams_url = f"msteams://teams.microsoft.com/l/chat/0/0?users={contact_email}&message={file_message}"
                    os.startfile(teams_url)
                    self.open_file_explorer_at_file(file_path)
                else:
                    if self.parent and hasattr(self.parent, 'show_status_message'):
                        self.parent.show_status_message("Nessun contatto selezionato.", error=True)
        except Exception as e:
            QMessageBox.critical(self.parent, "Errore", f"Errore durante la condivisione su Teams: {str(e)}")

    def shareOnWhatsApp(self, file_path):
        try:
            # Numero di telefono destinatario (deve includere il prefisso internazionale, es: +39 per l'Italia)
            recipient_phone_number = "+391234567890"

            # Usa pywhatkit per inviare il video (immagine)
            kit.sendwhats_image(recipient_phone_number, file_path, "Ecco il video che ti volevo condividere!")

            QMessageBox.information(self.parent, "Condivisione WhatsApp", "Video condiviso su WhatsApp.")
        except Exception as e:
            QMessageBox.critical(self.parent, "Errore", f"Errore durante la condivisione su WhatsApp: {str(e)}")

    def get_contacts_from_txt(self):
        """Funzione per caricare i contatti da un file .txt"""
        contacts = []
        try:
            with open(CONTACTS_FILE, mode='r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line:  # Salta le righe vuote
                        continue
                    try:
                        name, email = line.split(',')
                        contacts.append({
                            "displayName": name.strip(),
                            "email": email.strip()
                        })
                    except ValueError:
                        print(f"Skipping malformed line: {line}")

        except FileNotFoundError:
            QMessageBox.critical(self.parent, "Errore", f"File dei contatti non trovato: {CONTACTS_FILE}")
            return [] # Ritorna una lista vuota se il file non esiste
        except Exception as e:
            QMessageBox.critical(self.parent, "Errore", f"Errore durante la lettura del file dei contatti: {e}")
            return [] # Ritorna una lista vuota in caso di altri errori
        return contacts

    def open_file_explorer_at_file(self, file_path):
        """Apre il file explorer e seleziona il file specificato"""
        try:
            # Apre il file explorer con il file selezionato
            subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
        except Exception as e:
            QMessageBox.critical(self.parent, "Errore", f"Impossibile aprire il file explorer: {str(e)}")


class ContactSelectionDialog(QDialog):
    def __init__(self, contacts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleziona un contatto")

        # Layout
        layout = QVBoxLayout()

        # Lista di contatti
        self.contact_list = QListWidget()
        for contact in contacts:
            self.contact_list.addItem(f"{contact['displayName']} ({contact['email']})")
        layout.addWidget(self.contact_list)

        # Aggiungi pulsanti OK e Annulla
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_selected_contact(self):
        selected_item = self.contact_list.currentItem()
        if selected_item:
            return selected_item.text()
        return None
