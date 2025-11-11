
# File: config.py

import os
import sys
import logging
from PyQt6.QtCore import QSettings
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# --- Funzioni Utilità Percorso ---
def get_app_path():
    """Determina il percorso base dell'applicazione, sia in modalità di sviluppo che compilata"""
    if getattr(sys, 'frozen', False):
        # Se l'app è compilata con PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # In modalità di sviluppo
        # Assumendo che config.py sia in src/
        return os.path.dirname(os.path.abspath(__file__))

def get_application_path():
    """Alias per get_app_path, può essere utile mantenere per compatibilità"""
    return get_app_path()

# --- Impostazione Variabile Ambiente Playwright (solo per bundle) ---
if getattr(sys, 'frozen', False):
    application_path = get_application_path()
    bundled_browser_path = os.path.join(application_path, 'ms-playwright')
    # Log per debug durante l'esecuzione del bundle
    print(f"[Config Init] App bundled. Setting PLAYWRIGHT_BROWSERS_PATH to: {bundled_browser_path}")
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = bundled_browser_path
    # Verifica opzionale (per debug)
    # if not os.path.exists(bundled_browser_path):
    #     print(f"[Config Init] WARNING: Bundled browser path does not exist: {bundled_browser_path}")
    # else:
    #     print(f"[Config Init] Bundled browser path verified.")

# --- Directory Base ---
BASE_DIR = get_app_path()

# --- API Keys ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")    # Se usi OpenAI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")    # Per Gemini Cloud

# --- Funzione Centralizzata per Recupero API Key ---
def get_api_key(service_name: str) -> str:
    """
    Recupera una API key dando priorità a QSettings e fallback a .env.

    Args:
        service_name (str): Il nome del servizio (es. 'google', 'anthropic', 'elevenlabs').

    Returns:
        str: La API key trovata.
    """
    settings = QSettings("Genius", "GeniusAI")

    # 1. Prova a leggere da QSettings
    settings_key = f"api_keys_dialog/{service_name.lower()}"
    stored_key = settings.value(settings_key, "")

    if stored_key:
        logging.debug(f"API key for '{service_name}' found in QSettings.")
        return stored_key

    # 2. Se non trovata in QSettings, usa il fallback da .env (caricato in config)
    logging.debug(f"API key for '{service_name}' not found in QSettings, falling back to environment variable.")
    fallback_keys = {
        "google": GOOGLE_API_KEY,
        "anthropic": ANTHROPIC_API_KEY,
        "elevenlabs": ELEVENLABS_API_KEY,
        "openai": OPENAI_API_KEY
    }

    return fallback_keys.get(service_name.lower(), "")

# --- Definizione Identificatori Modello ---
# Claude (Anthropic) - Modelli stabili a Ottobre 2025

# Serie 4.x (I più recenti e potenti)
MODEL_4_5_SONNET = "claude-sonnet-4-5-20250929"  # Il modello di punta per agenti complessi e coding
MODEL_4_1_OPUS = "claude-opus-4-1-20250805"      # Eccezionale per compiti specializzati e ragionamento avanzato
MODEL_4_OPUS = "claude-opus-4-20250514"
MODEL_4_SONNET = "claude-sonnet-4-20250514"

# Serie 3.x (Ancora validi e performanti)
MODEL_3_7_SONNET = "claude-3-7-sonnet-20250219"
MODEL_3_5_SONNET = "claude-3-5-sonnet-20240620"
MODEL_3_5_HAIKU = "claude-3-5-haiku-20241022"
MODEL_3_OPUS = "claude-3-opus-20240229"
MODEL_3_SONNET = "claude-3-sonnet-20240229"
MODEL_3_HAIKU = "claude-3-haiku-20240307"

# Gemini (Google Cloud) - Modelli stabili a Ottobre 2025
# Serie 2.5 (I più recenti e raccomandati)
GEMINI_25_PRO = "gemini-2.5-pro"        # Modello di punta per compiti complessi e alta qualità.
GEMINI_25_FLASH = "gemini-2.5-flash"      # Ottimo bilanciamento tra velocità e capacità.
GEMINI_25_FLASH_LITE = "gemini-2.5-flash-lite" # Ideale per risposte rapide e a bassa latenza.

# Serie 2.0 (Stabili e affidabili)
GEMINI_20_FLASH = "gemini-2.0-flash"        # Alias che punta alla versione stabile più recente di Flash 2.0.
GEMINI_20_FLASH_LITE = "gemini-2.0-flash-lite"  # Alias che punta alla versione stabile più recente di Flash Lite 2.0.

# Mappatura dei vecchi nomi di variabili ai nuovi modelli per mantenere la compatibilità.
# Questi alias verranno rimossi in un secondo momento per pulire il codice.
GEMINI_15_PRO = GEMINI_25_PRO               # Deprecato, mappato al successore.
GEMINI_15_FLASH = GEMINI_25_FLASH           # Deprecato e rinominato, mappato al successore.
GEMINI_15_FLASH_8B = GEMINI_25_FLASH_LITE   # Deprecato, mappato al modello leggero equivalente.

# OpenAI (Esempi se li integri)
# GPT_4_TURBO = "gpt-4-turbo"
# GPT_4O = "gpt-4o"
# GPT_4O_MINI = "gpt-4o-mini"

# Modelli Locali (via Ollama)
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434") # Default Ollama endpoint
OLLAMA_GEMMA_2B = "ollama:gemma:2b"
OLLAMA_GEMMA_7B = "ollama:gemma:7b"
OLLAMA_GEMMA2_9B = "ollama:gemma2:9B"
OLLAMA_GEMMA3_4B = "ollama:gemma3:4b"
OLLAMA_GEMMA_LATEST = "ollama:gemma:latest"
OLLAMA_LLAMA3_8B = "ollama:llama3:8b"
OLLAMA_MISTRAL_7B = "ollama:mistral:7b" # Esempio Mistral
OLLAMA_LLAVA = "ollama:llava:latest"  # Modello Vision

# ElevenLabs (TTS) - Modelli a Novembre 2025
ELEVENLABS_V2_MULTILINGUAL = "eleven_multilingual_v2" # Raccomandato, alta qualità
ELEVENLABS_V2_TURBO = "eleven_turbo_v2"           # Bassa latenza
ELEVENLABS_V3 = "eleven_v3"                   # Alpha, alta espressività

# --- Struttura Dati Categoria Modelli ---
# Dizionari che raggruppano i modelli per provider per una migliore visualizzazione nella UI

def _flatten_model_dict(d):
    """Funzione helper per appiattire un dizionario di modelli in una lista."""
    return [model for models in d.values() for model in models]

def _merge_categorized_dicts(*dicts):
    merged = {}
    for d in dicts:
        for category, models in d.items():
            if category not in merged:
                merged[category] = []
            # Add only unique models
            for model in models:
                if model not in merged[category]:
                    merged[category].append(model)
    return merged

_CATEGORIZED_MODELS_WITH_VISION_BASE = {
    "Anthropic": [
        MODEL_4_5_SONNET, MODEL_4_1_OPUS, MODEL_4_OPUS, MODEL_4_SONNET,
        MODEL_3_7_SONNET, MODEL_3_5_SONNET, MODEL_3_5_HAIKU, MODEL_3_OPUS,
        MODEL_3_SONNET, MODEL_3_HAIKU
    ],
    "Google": [
        GEMINI_25_PRO, GEMINI_25_FLASH, GEMINI_25_FLASH_LITE,
        GEMINI_20_FLASH, GEMINI_20_FLASH_LITE
    ],
}

_CATEGORIZED_OLLAMA_VISION = {
    "Ollama (Vision)": [
        OLLAMA_LLAVA,
        OLLAMA_GEMMA_LATEST,
        OLLAMA_GEMMA3_4B,
        OLLAMA_GEMMA2_9B,
        OLLAMA_GEMMA_7B,
        OLLAMA_GEMMA_2B
    ]
}

# Unisci i modelli vision cloud e locali
CATEGORIZED_MODELS_WITH_VISION = _merge_categorized_dicts(_CATEGORIZED_MODELS_WITH_VISION_BASE, _CATEGORIZED_OLLAMA_VISION)

CATEGORIZED_FAST_TEXT_MODELS = {
    "Anthropic": [MODEL_3_5_HAIKU, MODEL_3_HAIKU],
    "Google": [
        GEMINI_25_FLASH, GEMINI_25_FLASH_LITE,
        GEMINI_20_FLASH, GEMINI_20_FLASH_LITE
    ],
    "Ollama": [
        OLLAMA_GEMMA_LATEST, OLLAMA_GEMMA3_4B, OLLAMA_GEMMA2_9B, OLLAMA_GEMMA_7B, OLLAMA_GEMMA_2B,
        OLLAMA_LLAMA3_8B, OLLAMA_MISTRAL_7B
    ]
}

CATEGORIZED_POWERFUL_TEXT_MODELS = {
    "Anthropic": [
        MODEL_4_5_SONNET, MODEL_4_1_OPUS, MODEL_4_OPUS, MODEL_4_SONNET,
        MODEL_3_7_SONNET, MODEL_3_5_SONNET, MODEL_3_OPUS, MODEL_3_SONNET
    ],
    "Google": [GEMINI_25_PRO]
}

CATEGORIZED_TTS_MODELS = {
    "ElevenLabs": [
        ELEVENLABS_V2_MULTILINGUAL,
        ELEVENLABS_V2_TURBO,
        ELEVENLABS_V3
    ]
}

# --- Liste Piatte per Compatibilità ---
# Queste liste mantengono la compatibilità con il codice esistente, generate dinamicamente.
MODELS_WITH_VISION = _flatten_model_dict(CATEGORIZED_MODELS_WITH_VISION)
FAST_TEXT_MODELS = _flatten_model_dict(CATEGORIZED_FAST_TEXT_MODELS)
POWERFUL_TEXT_MODELS = _flatten_model_dict(CATEGORIZED_POWERFUL_TEXT_MODELS)

# Tutti i modelli Text/Multimodal conosciuti (per fallback o liste complete)
ALL_KNOWN_MODELS = list(set(FAST_TEXT_MODELS + POWERFUL_TEXT_MODELS + MODELS_WITH_VISION)) # Usa set per rimuovere duplicati

# --- Configurazione Modelli per Azione Specifica ---

# Definizioni di gruppi di modelli categorizzati per azioni complesse
_CATEGORIZED_ALL_TEXT_MODELS = _merge_categorized_dicts(CATEGORIZED_FAST_TEXT_MODELS, CATEGORIZED_POWERFUL_TEXT_MODELS)
_powerful_vision_models_by_provider = {
    provider: [model for model in models if model in POWERFUL_TEXT_MODELS]
    for provider, models in CATEGORIZED_MODELS_WITH_VISION.items()
}
_powerful_vision_models_by_provider = {k: v for k, v in _powerful_vision_models_by_provider.items() if v}
_CATEGORIZED_BROWSER_AGENT_MODELS = _merge_categorized_dicts(CATEGORIZED_FAST_TEXT_MODELS, _powerful_vision_models_by_provider)

ACTION_MODELS_CONFIG = {
    # Identificatore unico per l'azione
    'frame_extractor': {
        'display_name': "Estrazione Frame (Visione)", # Etichetta UI
        'setting_key': "models/frame_extractor",    # Chiave QSettings
        'default': os.getenv("DEFAULT_MODEL_FRAME_EXTRACTOR", GEMINI_25_FLASH), # Modello di fallback
        'allowed': MODELS_WITH_VISION, # Lista di modelli permessi (per compatibilità)
        'categorized_source': CATEGORIZED_MODELS_WITH_VISION
    },
    'text_processing': {
        'display_name': "Elaborazione Testo (Summary/Fix)",
        'setting_key': "models/text_processing",
        'default': os.getenv("DEFAULT_MODEL_TEXT_PROCESSING", GEMINI_25_FLASH),
        'allowed': list(set(FAST_TEXT_MODELS + POWERFUL_TEXT_MODELS)), # Permette tutti i modelli testuali
        'categorized_source': _CATEGORIZED_ALL_TEXT_MODELS
    },
    'pptx_generation': {
        'display_name': "Generazione Presentazioni",
        'setting_key': "models/pptx_generation",
        'default': os.getenv("DEFAULT_MODEL_PPTX_GENERATION", MODEL_4_5_SONNET),
        'allowed': POWERFUL_TEXT_MODELS, # Preferibilmente modelli potenti
        'categorized_source': CATEGORIZED_POWERFUL_TEXT_MODELS
    },
    'browser_agent': {
        'display_name': "Browser Agent",
        'setting_key': "models/browser_agent",
        'default': os.getenv("DEFAULT_MODEL_BROWSER_AGENT", GEMINI_25_FLASH),
        'allowed': list(set(FAST_TEXT_MODELS + [m for m in POWERFUL_TEXT_MODELS if m in MODELS_WITH_VISION])),
        'categorized_source': _CATEGORIZED_BROWSER_AGENT_MODELS
    },
    'summary': { # Usato da MeetingSummarizer
        'display_name': "Riassunto Meeting",
        'setting_key': "models/summary",
        'default': os.getenv("DEFAULT_MODEL_SUMMARY", GEMINI_25_FLASH),
        'allowed': list(set(FAST_TEXT_MODELS + POWERFUL_TEXT_MODELS)), # Tutti i modelli testuali vanno bene
        'categorized_source': _CATEGORIZED_ALL_TEXT_MODELS
    },
    'tts_generation': {
        'display_name': "Sintesi Vocale (TTS)",
        'setting_key': "models/tts_generation",
        'default': os.getenv("DEFAULT_MODEL_TTS", ELEVENLABS_V2_MULTILINGUAL),
        'allowed': _flatten_model_dict(CATEGORIZED_TTS_MODELS),
        'categorized_source': CATEGORIZED_TTS_MODELS
    },
    # Esempio: Se avessi una generazione specifica per la guida operativa
    # 'operational_guide': {
    #     'display_name': "Guida Operativa (da Visione)",
    #     'setting_key': "models/operational_guide",
    #     'default': os.getenv("DEFAULT_MODEL_OPERATIONAL_GUIDE", GEMINI_25_PRO),
    #     'allowed': [m for m in POWERFUL_TEXT_MODELS if m in MODELS_WITH_VISION] # Modelli potenti con visione
    # }
}

# --- Percorsi File e Prompt ---
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg", "bin", "ffmpeg.exe")
FFMPEG_PATH_DOWNLOAD = os.path.join(BASE_DIR, "ffmpeg", "bin") # Usato da yt-dlp
VERSION_FILE = os.path.join(BASE_DIR, "version_info.txt")
CONTACTS_FILE = os.path.join(BASE_DIR, "contatti_teams.txt")
DOCK_SETTINGS_FILE = os.path.join(BASE_DIR, "dock_settings.json")
LOG_FILE = os.path.join(BASE_DIR, "console_log.txt")

# --- Livello di Log ---
LOG_LEVEL = logging.INFO

# --- Directory e Percorsi Prompt ---
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

def get_prompt_path(filename):
    """Funzione helper per ottenere il percorso di un prompt e verificare se esiste."""
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        logging.warning(f"File prompt non trovato: {path}")
    return path

PROMPT_FRAMES_ANALYSIS = get_prompt_path("frames_analysis_prompt.txt")
PROMPT_VIDEO_SUMMARY = get_prompt_path("video_summary_prompt.txt")
PROMPT_COMBINED_ANALYSIS = get_prompt_path("combined_analysis_prompt.txt")
PROMPT_COMBINED_SUMMARY_TEXT_ONLY = get_prompt_path("combined_summary_text_only_prompt.txt")
PROMPT_PPTX_GENERATION = get_prompt_path("pptx_generation_prompt.txt")
PROMPT_TEXT_SUMMARY = get_prompt_path("text_summary_prompt.txt")
PROMPT_TEXT_FIX = get_prompt_path("text_fix_prompt.txt")
PROMPT_BROWSER_GUIDE = get_prompt_path("browser_guide_prompt.txt")
PROMPT_YOUTUBE_SUMMARY = get_prompt_path("youtube_summary.txt")
PROMPT_VIDEO_INTEGRATION = get_prompt_path("video_integration_prompt.txt")
PROMPT_MEETING_SUMMARY = get_prompt_path("meeting_summary_prompt.txt")
PROMPT_OPERATIONAL_GUIDE = get_prompt_path("prompt_operational_guide.txt")
PROMPT_TTS = get_prompt_path("tts_prompt.txt") # Se esiste
PROMPT_GENERATE_FILENAME = get_prompt_path("generate_filename_prompt.txt")
PROMPT_SPECIFIC_OBJECT_RECOGNITION = get_prompt_path("specific_object_recognition_prompt.txt")
PROMPT_DOCUMENT_INTEGRATION = get_prompt_path("document_integration_prompt.txt")
PROMPT_CHAT_SUMMARY = get_prompt_path("chat_summary_prompt.txt")

# --- Percorsi Risorse ---
RESOURCES_DIR = os.path.join(BASE_DIR, "res")

def get_resource(relative_path: str) -> str:
    """
    Costruisce un percorso assoluto per una risorsa nella cartella 'res'.

    Args:
        relative_path (str): Il percorso relativo all'interno della cartella 'res' (es. 'icons/icon.png').

    Returns:
        str: Il percorso assoluto della risorsa.
    """
    return os.path.join(RESOURCES_DIR, relative_path)

def get_splash_images_dir():
    """Ottiene il percorso della cartella splash_images in modo compatibile."""
    return os.path.join(RESOURCES_DIR, "splash_images")

SPLASH_IMAGES_DIR = get_splash_images_dir()
MUSIC_DIR = os.path.join(RESOURCES_DIR, "music")
WATERMARK_IMAGE = os.path.join(RESOURCES_DIR, "watermark.png")

# --- Colori per Evidenziazione ---
# Centralizzati per coerenza tra UI (QColor) e export (python-docx)
from PyQt6.QtGui import QColor
from docx.enum.text import WD_COLOR_INDEX

HIGHLIGHT_COLORS = {
    "Giallo Intenso": {"qcolor": QColor("#FFD700"), "docx": WD_COLOR_INDEX.YELLOW, "hex": "#ffd700"},
    "Verde Brillante": {"qcolor": QColor("#32CD32"), "docx": WD_COLOR_INDEX.BRIGHT_GREEN, "hex": "#32cd32"},
    "Ciano": {"qcolor": QColor("#00FFFF"), "docx": WD_COLOR_INDEX.TURQUOISE, "hex": "#00ffff"},
    "Magenta": {"qcolor": QColor("#FF00FF"), "docx": WD_COLOR_INDEX.PINK, "hex": "#ff00ff"},
    "Arancione Vivo": {"qcolor": QColor("#FF8C00"), "docx": WD_COLOR_INDEX.DARK_YELLOW, "hex": "#ff8c00"},
    "Azzurro Cielo": {"qcolor": QColor("#87CEEB"), "docx": WD_COLOR_INDEX.TEAL, "hex": "#87ceeb"},
    "Viola": {"qcolor": QColor("#9370DB"), "docx": WD_COLOR_INDEX.VIOLET, "hex": "#9370db"},
    "Rosso Chiaro": {"qcolor": QColor("#F08080"), "docx": WD_COLOR_INDEX.RED, "hex": "#f08080"},
    "Blu Timecode": {"qcolor": QColor("#ADD8E6"), "docx": None, "hex": "#add8e6"},
}

# --- Impostazioni Default Generali ---
DEFAULT_FRAME_COUNT = 5
DEFAULT_STABILITY = 50
DEFAULT_SIMILARITY = 80
DEFAULT_STYLE = 0
DEFAULT_FRAME_RATE = 25
DEFAULT_AUDIO_CHANNELS = 2

# --- Impostazioni UI ---
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# --- Impostazioni Voci (ElevenLabs) ---
DEFAULT_VOICES = {
    "Lily": "pFZP5JQG7iQjIQuC4Bku",
    "Giovanni": "zcAOhNBS3c14rBihAFp1",
    "Carmelo": "pWHqWjkaSNybDOvgMt58",
    "Tosca": "fNmw8sukfGuvWVOp33Ge"
    # Aggiungere altre voci predefinite se necessario
}

def get_default_voices():
    """Restituisce il dizionario delle voci predefinite di ElevenLabs."""
    return DEFAULT_VOICES

# --- Funzione per recuperare il modello per un'azione specifica ---
def get_model_for_action(action_name: str) -> str:
    """
    Recupera il modello configurato per una specifica azione, con fallback al default.

    Args:
        action_name (str): L'identificatore dell'azione (es. 'summary', 'frame_extractor').

    Returns:
        str: Il nome del modello da utilizzare.
    """
    if action_name not in ACTION_MODELS_CONFIG:
        logging.error(f"Azione '{action_name}' non trovata in ACTION_MODELS_CONFIG.")
        # Fallback di emergenza se l'azione non è definita
        return GEMINI_15_FLASH

    config = ACTION_MODELS_CONFIG[action_name]
    settings_key = config['setting_key']
    default_model = config['default']

    settings = QSettings("Genius", "GeniusAI")

    # Legge il valore dalle impostazioni; se non c'è, usa il default
    model = settings.value(settings_key, defaultValue=default_model)

    logging.debug(f"Modello per l'azione '{action_name}': {model} (Default: {default_model})")

    return model

# --- Funzione di Diagnostica ---
def debug_config():
    """Stampa la configurazione corrente per diagnosi."""
    print("--- [Config Debug] Percorsi Principali ---")
    paths = {
        "BASE_DIR": BASE_DIR,
        "FFMPEG_PATH": FFMPEG_PATH,
        "PROMPTS_DIR": PROMPTS_DIR,
        "RESOURCES_DIR": RESOURCES_DIR,
        "SPLASH_IMAGES_DIR": SPLASH_IMAGES_DIR,
        "MUSIC_DIR": MUSIC_DIR,
        "WATERMARK_IMAGE": WATERMARK_IMAGE,
        "VERSION_FILE": VERSION_FILE,
        "LOG_FILE": LOG_FILE,
        "OLLAMA_ENDPOINT": OLLAMA_ENDPOINT,
        # API Keys Status
        "ELEVENLABS_API_KEY": "Impostata" if ELEVENLABS_API_KEY else "NON Impostata",
        "ANTHROPIC_API_KEY": "Impostata" if ANTHROPIC_API_KEY else "NON Impostata",
        "GOOGLE_API_KEY": "Impostata" if GOOGLE_API_KEY else "NON Impostata",
        "OPENAI_API_KEY": "Impostata" if OPENAI_API_KEY else "NON Impostata",
    }
    for name, value in paths.items():
        # Verifica esistenza per i percorsi file/dir
        exists_str = ""
        if name not in ["OLLAMA_ENDPOINT"] and "API_KEY" not in name:
             if isinstance(value, str) and os.path.exists(value):
                 exists_str = "- ESISTE"
             elif isinstance(value, str):
                 exists_str = "- MANCANTE!"
        print(f"{name}: {value} {exists_str}")

    print("\n--- [Config Debug] Configurazione Modelli per Azione ---")
    for action, config in ACTION_MODELS_CONFIG.items():
        print(f"Azione: '{action}' (UI: '{config.get('display_name', 'N/D')}')")
        print(f"  Setting Key: '{config['setting_key']}'")
        print(f"  Default: '{config['default']}'")
        print(f"  Modelli Permessi ({len(config['allowed'])}): {config['allowed']}")
        print("-" * 20)

    print("\n--- [Config Debug] Tutti i Modelli Noti ---")
    print(ALL_KNOWN_MODELS)

    return paths, ACTION_MODELS_CONFIG

# Esempio di come chiamare la funzione di debug alla fine del file,
# utile durante lo sviluppo per verificare che tutto sia corretto.
if __name__ == "__main__":
    print("Esecuzione debug_config() da config.py...")
    debug_config()

