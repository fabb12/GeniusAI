
import sys
import os
import unittest

# Aggiungi il percorso 'src' al PYTHONPATH per permettere l'importazione
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config import ACTION_MODELS_CONFIG, OLLAMA_GEMMA_LATEST

class TestConfig(unittest.TestCase):
    def test_gemma_model_is_available(self):
        """
        Verifica che il nuovo modello Gemma sia presente in almeno una delle liste
        di modelli categorizzati in ACTION_MODELS_CONFIG.
        """
        found_model = False
        # Itera attraverso tutte le azioni definite nella configurazione
        for action_config in ACTION_MODELS_CONFIG.values():
            # Controlla se 'categorized_source' esiste per questa azione
            if 'categorized_source' in action_config:
                categorized_models = action_config['categorized_source']
                # Controlla se 'Ollama' è una categoria e se il modello è presente
                if 'Ollama' in categorized_models and OLLAMA_GEMMA_LATEST in categorized_models['Ollama']:
                    found_model = True
                    break  # Il modello è stato trovato, non serve continuare

        # Il test fallirà se, dopo aver controllato tutte le azioni, il modello non è stato trovato
        self.assertTrue(found_model, f"Il modello '{OLLAMA_GEMMA_LATEST}' non è stato trovato in nessuna delle configurazioni dei modelli per le azioni.")

if __name__ == '__main__':
    unittest.main()
