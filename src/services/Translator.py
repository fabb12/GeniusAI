from googletrans import Translator, LANGUAGES

class TranslationService:
    def __init__(self):
        self.translator = Translator()

    def get_supported_languages(self):
        """Restituisce un dizionario delle lingue supportate."""
        return LANGUAGES

    def translate_text(self, text, dest_language):
        """
        Traduci il testo nella lingua di destinazione specificata.
        :param text: Il testo da tradurre.
        :param dest_language: Il codice della lingua di destinazione (es. 'en', 'es').
        :return: Il testo tradotto o un messaggio di errore.
        """
        try:
            if not text.strip():
                return ""

            supported_langs = self.get_supported_languages()
            if dest_language not in supported_langs:
                return f"Errore: Lingua di destinazione non supportata: {dest_language}"

            translation = self.translator.translate(text, dest=dest_language)
            return translation.text
        except Exception as e:
            return f"Errore durante la traduzione: {e}"
