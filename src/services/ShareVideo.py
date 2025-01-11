import os
import subprocess
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QListWidget, QDialogButtonBox


class VideoSharingManager:
    def __init__(self, parent):
        self.parent = parent  # Riferimento alla finestra principale per mostrare i messaggi

    def shareVideo(self, video_path):
        # Verifica se il video esiste
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self.parent, "Errore", "Non c'è nessun video caricato da condividere.")
            return

        try:
            # Condivisione su Teams
            self.shareOnTeams(video_path)

            # Condivisione su WhatsApp
            # self.shareOnWhatsApp(video_path)

        except Exception as e:
            QMessageBox.critical(self.parent, "Errore durante la condivisione", str(e))

    def shareOnTeams(self, file_path):
        try:
            # Carica i contatti dal file .txt
            contacts = self.get_contacts_from_txt('../contatti_teams.txt')

            # Mostra la finestra di dialogo per la selezione dei contatti
            dialog = ContactSelectionDialog(contacts, self.parent)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_contact = dialog.get_selected_contact()
                if selected_contact:
                    # Estrai l'email dal contatto selezionato
                    contact_email = selected_contact.split('(')[-1][:-1]  # Ottiene l'email tra parentesi

                    # Costruisci l'URL per Teams
                    file_message = f"Ti condivido questo video --> {file_path}"
                    teams_url = f"msteams://teams.microsoft.com/l/chat/0/0?users={contact_email}&message={file_message}"

                    # Usa os.startfile per aprire Teams con il messaggio precompilato
                    os.startfile(teams_url)

                    # Apri automaticamente il file explorer con il file video selezionato
                    self.open_file_explorer_at_file(file_path)

                else:
                    QMessageBox.warning(self.parent, "Errore", "Nessun contatto selezionato.")
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

    def get_contacts_from_txt(self, file_path):
        """Funzione per caricare i contatti da un file .txt"""
        contacts = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                for line in file:
                    name, email = line.strip().split(',')
                    contacts.append({
                        "displayName": name,
                        "email": email
                    })
        except Exception as e:
            QMessageBox.critical(self.parent, "Errore", f"Errore durante la lettura del file: {e}")
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
