import os
from pathlib import Path
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Directory base dell'applicazione
BASE_DIR = Path(__file__).resolve().parent

# API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# AI Models - Claude (solo modelli base)
MODEL_3_7_SONNET = os.getenv("MODEL_3_7_SONNET", "claude-3-7-sonnet-20250219")
MODEL_3_5_HAIKU = os.getenv("MODEL_3_5_HAIKU", "claude-3-5-haiku-20241022")
MODEL_3_5_SONNET_V2 = os.getenv("MODEL_3_5_SONNET_V2", "claude-3-5-sonnet-20241022")
MODEL_3_5_SONNET = os.getenv("MODEL_3_5_SONNET", "claude-3-5-sonnet-20240620")
MODEL_3_OPUS = os.getenv("MODEL_3_OPUS", "claude-3-opus-20240229")
MODEL_3_SONNET = os.getenv("MODEL_3_SONNET", "claude-3-sonnet-20240229")
MODEL_3_HAIKU = os.getenv("MODEL_3_HAIKU", "claude-3-haiku-20240307")

# Modelli per componenti specifici
CLAUDE_MODEL_FRAME_EXTRACTOR = os.getenv("CLAUDE_MODEL_FRAME_EXTRACTOR", MODEL_3_7_SONNET)
CLAUDE_MODEL_TEXT_PROCESSING = os.getenv("CLAUDE_MODEL_TEXT_PROCESSING", MODEL_3_5_SONNET)
CLAUDE_MODEL_PPTX_GENERATION = os.getenv("CLAUDE_MODEL_PPTX_GENERATION", MODEL_3_5_SONNET)
CLAUDE_MODEL_BROWSER_AGENT = os.getenv("CLAUDE_MODEL_BROWSER_AGENT", MODEL_3_HAIKU)
CLAUDE_MODEL_SUMMARY = os.getenv("CLAUDE_MODEL_SUMMARY", MODEL_3_5_SONNET)

# File Paths
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg/bin/ffmpeg.exe")
FFMPEG_PATH_DOWNLOAD = os.getenv("FFMPEG_PATH_DOWNLOAD", "ffmpeg/bin")
VERSION_FILE = os.path.join(BASE_DIR, "version_info.txt")
CONTACTS_FILE = os.path.join(BASE_DIR, "../contatti_teams.txt")
DOCK_SETTINGS_FILE = os.path.join(BASE_DIR, "../dock_settings.json")
LOG_FILE = os.path.join(BASE_DIR, "../console_log.txt")

# Resource Paths
RESOURCES_DIR = os.path.join(BASE_DIR, "res")
SPLASH_IMAGES_DIR = os.path.join(RESOURCES_DIR, "splash_images")
MUSIC_DIR = os.path.join(RESOURCES_DIR, "music")
WATERMARK_IMAGE = os.path.join(RESOURCES_DIR, "watermark.png")

# Default Settings
DEFAULT_FRAME_COUNT = 5
DEFAULT_STABILITY = 50
DEFAULT_SIMILARITY = 80
DEFAULT_STYLE = 0
DEFAULT_FRAME_RATE = 25
DEFAULT_AUDIO_CHANNELS = 2

# UI Settings
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# Prompt Files
PROMPT_FRAMES_EXTRACTION = os.path.join(BASE_DIR, "services", "prompt_frames_extraction.txt")
PROMPT_FRAMES_FOR_AGENT = os.path.join(BASE_DIR, "services", "prompt_frames_for_agent.txt")

# Voice Settings
DEFAULT_VOICES = {
    "Alessio": "BTpQARcEj1XqVxdZjTI7",
    "Marco": "GcAgjAjkhWsmUd4GlPiv",
    "Matilda": "atq1BFi5ZHt88WgSOJRB",
    "Mika": "B2j2knC2POvVW0XJE6Hi"
}