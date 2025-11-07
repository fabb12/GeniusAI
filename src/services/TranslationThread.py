from PyQt6.QtCore import QThread, pyqtSignal
from bs4 import BeautifulSoup
from .Translator import TranslationService

class TranslationThread(QThread):
    """
    Esegue la traduzione in un thread separato per non bloccare l'UI.
    Gestisce la traduzione di contenuto HTML preservando la formattazione.
    """
    completed = pyqtSignal(str)  # Emette l'HTML tradotto
    error = pyqtSignal(str)

    def __init__(self, html_content, dest_language, parent=None):
        super().__init__(parent)
        self.html_content = html_content
        self.dest_language = dest_language
        self.translation_service = TranslationService()

    def run(self):
        try:
            soup = BeautifulSoup(self.html_content, 'html.parser')

            # Estrai tutti i nodi di testo che non sono vuoti
            text_nodes = [node for node in soup.find_all(string=True) if node.strip()]
            original_texts = [str(node) for node in text_nodes]

            if not original_texts:
                self.completed.emit(self.html_content) # Restituisce l'originale se non c'è testo
                return

            # Traduci i testi
            translated_texts = self.translation_service.translate_texts_sync(
                original_texts, self.dest_language
            )

            if isinstance(translated_texts, str) and translated_texts.startswith("Errore"):
                raise Exception(translated_texts)

            # Sostituisci il testo originale con quello tradotto
            translated_iter = iter(translated_texts)
            for node in text_nodes:
                try:
                    new_text = next(translated_iter)
                    # Preserva gli spazi bianchi iniziali/finali
                    if node.startswith(' ') and not new_text.startswith(' '):
                        new_text = ' ' + new_text
                    if node.endswith(' ') and not new_text.endswith(' '):
                        new_text = new_text + ' '
                    node.replace_with(new_text)
                except StopIteration:
                    break # Dovrebbe esserci una corrispondenza 1:1

            # Emetti l'HTML tradotto
            self.completed.emit(str(soup))

        except Exception as e:
            self.error.emit(str(e))
