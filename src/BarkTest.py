from typing import Optional, Union, Dict
import numpy as np
from bark.generation import generate_text_semantic
from bark.api import semantic_to_waveform
from bark import generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import nltk
"""
[laughter]
[laughs]
[sighs]
[music]
[gasps]
[clears throat]
— or … for hesitations
♪ for song lyrics
CAPITALIZATION for emphasis of a word
[MAN] and [WOMAN] to bias Bark toward male and female speakers, respectively
"""
# Serpdotai/Bark-with-voice-clone
nltk.download('punkt')
preload_models()

long_string = """
in MFD il Report di dettaglio[laughs] per le sole strutture NON si puo' fare, [laughs]
mentre a livello del prospetto Ctp Risk View è [laughs] possibile aprirlo per le strutture e secondo me[sighs] per errore viene lasciato abilitato il drilldown NOP. """
sentences = nltk.sent_tokenize(long_string)

# Set up sample rate
SAMPLE_RATE = 22050
HISTORY_PROMPT = "v2/it_speaker_4"
MIN_EOS_P = 0.05  # Adjust this parameter to improve short text audio quality

# Generate audio for each prompt
audio_arrays = []
for sentence in sentences:
    # Generate semantic tokens with a lower min_eos_p to improve short text handling
    semantic_tokens = generate_text_semantic(sentence, history_prompt=HISTORY_PROMPT, min_eos_p=MIN_EOS_P)
    audio_array = semantic_to_waveform(semantic_tokens, history_prompt=HISTORY_PROMPT)
    audio_arrays.append(audio_array)

# Add a quarter second of silence between each sentence
silence = np.zeros(int(0.25 * SAMPLE_RATE))
pieces = []
for audio_array in audio_arrays:
    pieces += [audio_array, silence.copy()]

# Combine the audio files
combined_audio = np.concatenate(pieces)

# Write the combined audio to a file
write_wav("combined_audio1.wav", SAMPLE_RATE, combined_audio)

