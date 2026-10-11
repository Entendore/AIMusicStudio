"""Math & Noise Synthesizer Backend.
Generates audio using pure math functions (Sine, Sawtooth, Square, FM Synth) 
and noise algorithms (White Noise, Brown Noise).
"""
import numpy as np
import logging
import time
from backend.base import MusicBackend

logger = logging.getLogger(__name__)


class Plugin(MusicBackend):
    """Generates audio from mathematical waveforms and noise functions."""

    def __init__(self):
        self.model = None

    @classmethod
    def get_settings_schema(cls):
        return [
            {'id': 'waveform_type', 'type': 'dropdown', 
             'options': ['Sine', 'White Noise', 'Brown Noise', 'Sawtooth', 'Square', 'FM Synth'], 
             'default': 'Sine', 'label': 'Waveform / Noise Type'},
            {'id': 'frequency', 'type': 'slider', 'min': 20.0, 'max': 2000.0,
             'default': 440.0, 'step': 1.0, 'label': 'Frequency (Hz) (Ignored for Noise)'},
            {'id': 'amplitude', 'type': 'slider', 'min': 0.0, 'max': 1.0,
             'default': 0.8, 'step': 0.05, 'label': 'Amplitude'}
        ]

    def load_model(self, config: dict):
        logger.info("[MathSynth] Initializing Synthesizer Backend...")
        logger.info(f"[MathSynth] Using device: {config['hardware'].get('device', 'cpu')}")
        time.sleep(0.2)
        self.model = "MathSynthEngine"
        logger.info("[MathSynth] Ready.")

    def _apply_envelope(self, audio: np.ndarray, sample_rate: int, fade_ms: int = 50) -> np.ndarray:
        """Apply a fade-in/fade-out envelope to prevent audio clicking."""
        fade_len = int(sample_rate * fade_ms / 1000)
        if fade_len > 0 and len(audio) > 2 * fade_len:
            audio[:fade_len] *= np.linspace(0, 1, fade_len)
            audio[-fade_len:] *= np.linspace(1, 0, fade_len)
        return audio

    def generate(self, prompt: str, duration: int, params: dict,
                 progress_callback=None, stop_check=None) -> dict:
        
        waveform = params.get('waveform_type', 'Sine')
        freq = params.get('frequency', 440.0)
        amp = params.get('amplitude', 0.8)
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        
        audio = np.zeros(n_samples, dtype=np.float32)
        chunks = 10
        chunk_size = n_samples // chunks

        logger.info(f"[MathSynth] Generating {waveform} at {freq}Hz for {duration}s")

        for i in range(chunks):
            if stop_check and stop_check():
                logger.warning("[MathSynth] Generation cancelled by user.")
                return None

            time.sleep(0.05) # Simulate processing delay

            start = i * chunk_size
            end = start + chunk_size
            if i == chunks - 1:
                end = n_samples # Ensure we fill the exact duration

            t = np.linspace(start / sample_rate, end / sample_rate, end - start, endpoint=False)
            chunk_audio = np.zeros(end - start, dtype=np.float32)

            # --- Waveform & Noise Math ---
            if waveform == 'Sine':
                chunk_audio = np.sin(2 * np.pi * freq * t)
            
            elif waveform == 'White Noise':
                # Uniform random distribution between -1 and 1
                chunk_audio = np.random.uniform(-1, 1, len(t))
            
            elif waveform == 'Brown Noise':
                # Brownian motion (random walk)
                white = np.random.uniform(-1, 1, len(t))
                chunk_audio = np.cumsum(white) / 50.0 # Scale down to prevent clipping
                max_val = np.max(np.abs(chunk_audio))
                if max_val > 0:
                    chunk_audio = chunk_audio / max_val # Normalize
            
            elif waveform == 'Sawtooth':
                # 2 * (f*t mod 1) - 1
                chunk_audio = 2 * (freq * t % 1) - 1
            
            elif waveform == 'Square':
                # sign of sine wave
                chunk_audio = np.sign(np.sin(2 * np.pi * freq * t))
            
            elif waveform == 'FM Synth':
                # Frequency Modulation: carrier + modulator
                mod_index = 5.0
                mod_freq = freq * 1.5 # Perfect fifth
                chunk_audio = np.sin(2 * np.pi * freq * t + mod_index * np.sin(2 * np.pi * mod_freq * t))
                max_val = np.max(np.abs(chunk_audio))
                if max_val > 0:
                    chunk_audio = chunk_audio / max_val # Normalize FM which can spike

            # Apply amplitude
            audio[start:end] = chunk_audio * amp

            if progress_callback:
                progress_callback(int((i + 1) / chunks * 100))

        # Apply envelope to the whole audio buffer to avoid popping at start/end
        audio = self._apply_envelope(audio, sample_rate)

        logger.info("[MathSynth] Generation complete.")
        return {'audio': audio, 'sample_rate': sample_rate}

    def unload(self):
        logger.info("[MathSynth] Unloading model...")
        self.model = None