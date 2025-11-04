import asyncio
import sys
from googletrans import Translator, LANGUAGES

class TranslationService:
    def __init__(self):
        self.translator = Translator()

    def get_supported_languages(self):
        """Restituisce un dizionario delle lingue supportate."""
        return LANGUAGES

    async def _translate_batch_async(self, texts, dest_language):
        """Traduci in modo asincrono un batch di testi."""
        if not texts:
            return []

        # googletrans può gestire una lista di stringhe direttamente
        translations = await self.translator.translate(texts, dest=dest_language)
        if isinstance(translations, list):
            return [t.text for t in translations]
        # Se viene passata una sola stringa, restituisce un singolo oggetto
        return [translations.text]

    def translate_texts_sync(self, texts, dest_language):
        """
        Wrapper sincrono per tradurre una lista di testi.
        :param texts: Una lista di stringhe da tradurre.
        :param dest_language: Il codice della lingua di destinazione (es. 'en', 'es').
        :return: Una lista di stringhe tradotte o una stringa di errore.
        """
        try:
            # Mappa per ricordare la posizione originale dei testi non vuoti
            original_indices = {i: text for i, text in enumerate(texts) if text and text.strip()}
            texts_to_translate = list(original_indices.values())

            if not texts_to_translate:
                return [""] * len(texts)

            supported_langs = self.get_supported_languages()
            if dest_language not in supported_langs:
                return f"Errore: Lingua di destinazione non supportata: {dest_language}"

            # Esegui la funzione di traduzione asincrona
            translated_texts = asyncio.run(self._translate_batch_async(texts_to_translate, dest_language))

            # Ricostruisci la lista con le traduzioni nelle posizioni originali
            result = [""] * len(texts)
            translated_iter = iter(translated_texts)
            for i in range(len(texts)):
                if i in original_indices:
                    try:
                        result[i] = next(translated_iter)
                    except StopIteration:
                        pass
            return result

        except Exception as e:
            # Gestione di un problema noto con asyncio su Windows
            if "Event loop is closed" in str(e) and sys.platform == "win32":
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                    return self.translate_texts_sync(texts, dest_language)
                except Exception as retry_e:
                    return f"Errore durante la traduzione (retry): {retry_e}"
            return f"Errore durante la traduzione: {e}"
