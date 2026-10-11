"""AudioGen Backend.
Wraps Meta's AudioGen model for text-conditional audio generation.
Supports small (300M), medium (1.5B), and large (3.3B) variants.
"""
import logging
import time
import torch
import numpy as np
from backend.base import MusicBackend

logger = logging.getLogger(__name__)


class Plugin(MusicBackend):
    """Text-to-audio generation using Meta's AudioGen."""

    MODEL_MAP = {
        'small':  'facebook/audiogen-medium',   # renamed by Meta but commonly called 'small'
        'medium': 'facebook/audiogen-medium',
        'large':  'facebook/audiogen-large',
    }

    def __init__(self):
        self.model = None
        self.model_size = 'medium'
        self.device = 'cpu'

    @classmethod
    def get_metadata(cls):
        return {
            'name': 'AudioGen',
            'description': 'Text to audio & sound effects',
            'details': 'Meta\'s AudioGen — small/medium/large variants. '
                       'Best for environmental sounds, SFX, and short audio clips.',
            'icon': '🔊',
            'requirements': 'pip install audiocraft',
        }

    @classmethod
    def get_prompt_schema(cls):
        return {
            'required': True,
            'title': '📝 Prompt',
            'description': 'Describe the sound or audio you want to generate. '
                           'Works best with descriptive sound-effect prompts.',
            'placeholder': (
                'A thunderstorm with heavy rain and distant lightning'
            ),
        }

    @classmethod
    def get_settings_schema(cls):
        return [
            # ── Model Selection ──────────────────────
            {'id': 'model_size', 'type': 'dropdown',
             'options': ['small', 'medium', 'large'], 'default': 'medium',
             'category': 'Model',
             'label': '📦 Model Size',
             'description': 'small (~300M): Fast, low VRAM. medium (~1.5B): Good balance. '
                            'large (~3.3B): Best quality, needs 12GB+ VRAM.'},

            # ── Sampling ─────────────────────────────
            {'id': 'temperature', 'type': 'slider', 'min': 0.1, 'max': 2.0,
             'default': 1.0, 'step': 0.1,
             'category': 'Sampling',
             'label': '🌡 Temperature',
             'description': 'Controls randomness. Lower = more deterministic. '
                            'Higher = more varied/creative.'},
            {'id': 'topk', 'type': 'slider', 'min': 0, 'max': 1000,
             'default': 250, 'step': 10,
             'category': 'Sampling',
             'label': '🎯 Top-K',
             'description': 'Number of top tokens to sample from. 0 = no top-k filtering. '
                            'Higher = more diverse outputs.'},
            {'id': 'topp', 'type': 'slider', 'min': 0.0, 'max': 1.0,
             'default': 0.0, 'step': 0.05,
             'category': 'Sampling',
             'label': '🎯 Top-P',
             'description': 'Nucleus sampling threshold. 0.0 = disabled. '
                            '0.9 = sample from top 90% of probability mass.'},

            # ── Generation ───────────────────────────
            {'id': 'cfg_coef', 'type': 'slider', 'min': 1.0, 'max': 15.0,
             'default': 3.0, 'step': 0.5,
             'category': 'Guidance',
             'label': '⚖ Guidance Scale',
             'description': 'Classifier-free guidance coefficient. Higher = closer to prompt. '
                            'Too high can cause artifacts.'},

            # ── Performance ──────────────────────────
            {'id': 'use_fp16', 'type': 'dropdown',
             'options': ['true', 'false'], 'default': 'true',
             'category': 'Performance',
             'label': '⚡ FP16',
             'description': 'Use half-precision to reduce VRAM by ~50% with minimal quality loss.'},
        ]

    def load_model(self, config: dict):
        from audiocraft.models import AudioGen
        from audiocraft.data.audio import audio_write

        self.device = config['hardware'].get('device', 'cuda')
        self.model_size = 'medium'
        repo_id = self.MODEL_MAP[self.model_size]

        logger.info(f"[AudioGen] Loading {repo_id} on {self.device}...")

        self.model = AudioGen.get_pretrained(repo_id)
        self.model.set_generation_params(duration=5)  # default, overridden in generate()

        if self.device == 'cuda' and torch.cuda.is_available():
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"[AudioGen] GPU: {torch.cuda.get_device_name(0)} ({total_mem:.1f} GB)")

        logger.info("[AudioGen] Ready.")

    def generate(self, prompt: str, duration: int, params: dict,
                 progress_callback=None, stop_check=None) -> dict:
        model_size = params.get('model_size', 'medium')
        temperature = float(params.get('temperature', 1.0))
        topk = int(params.get('topk', 250))
        topp = float(params.get('topp', 0.0))
        cfg_coef = float(params.get('cfg_coef', 3.0))
        use_fp16 = params.get('use_fp16', 'true') == 'true'

        # Reload model if size changed
        if model_size != self.model_size:
            logger.info(f"[AudioGen] Switching model size to {model_size}...")
            from audiocraft.models import AudioGen
            repo_id = self.MODEL_MAP[model_size]
            self.model = AudioGen.get_pretrained(repo_id)
            self.model_size = model_size

        self.model.set_generation_params(
            duration=duration,
            temperature=temperature,
            topk=topk if topk > 0 else None,
            topp=topp if topp > 0 else None,
            cfg_coef=cfg_coef,
        )

        logger.info(f"[AudioGen] Generating: \"{prompt[:80]}...\" ({duration}s)")
        if progress_callback:
            progress_callback(10)

        if stop_check and stop_check():
            return None

        dtype = torch.float16 if use_fp16 and self.device == 'cuda' else torch.float32

        with torch.autocast(device_type=self.device, dtype=dtype, enabled=use_fp16):
            wav = self.model.generate([prompt], progress=True)[0]

        # audiocraft returns (batch, channels, samples) on CPU as float32
        audio_np = wav.cpu().numpy()
        if audio_np.ndim == 3:
            audio_np = audio_np[0]  # (channels, samples)
        if audio_np.shape[0] > 1:
            audio_np = audio_np[0]   # mono downmix
        audio_np = audio_np.astype(np.float32)

        if progress_callback:
            progress_callback(100)

        logger.info("[AudioGen] Generation complete.")
        return {'audio': audio_np, 'sample_rate': self.model.sample_rate}

    def unload(self):
        if self.model is not None:
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        logger.info("[AudioGen] Unloaded.")
