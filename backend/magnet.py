"""MAGNeT Backend.
Wraps Meta's MAGNeT (Masked Audio Generation using a Single Non-Autoregressive Transformer)
for fast, high-quality text-to-music and text-to-audio generation.
"""
import logging
import time
import torch
import numpy as np
from backend.base import MusicBackend

logger = logging.getLogger(__name__)


class Plugin(MusicBackend):
    """Text-to-music/audio using Meta's MAGNeT (non-autoregressive)."""

    MODEL_MAP = {
        'music_small':  'facebook/magnet-small-10secs',
        'music_medium': 'facebook/magnet-medium-10secs',
        'music_large':  'facebook/magnet-large-10secs',
        'audio_8s':     'facebook/audio-magnet-medium',
    }

    # Maximum durations each variant supports (seconds)
    MAX_DURATION = {
        'music_small':  10,
        'music_medium': 10,
        'music_large':  10,
        'audio_8s':     8,
    }

    def __init__(self):
        self.model = None
        self.model_variant = 'music_medium'
        self.device = 'cpu'

    @classmethod
    def get_metadata(cls):
        return {
            'name': 'MAGNeT',
            'description': 'Fast non-autoregressive audio generation',
            'details': 'Meta\'s MAGNeT — music (small/medium/large) and audio (8s) variants. '
                       'Non-autoregressive = faster than MusicGen.',
            'icon': '🧲',
            'requirements': 'pip install audiocraft',
        }

    @classmethod
    def get_prompt_schema(cls):
        return {
            'required': True,
            'title': '📝 Prompt',
            'description': 'Describe the music or audio you want to generate. '
                           'MAGNeT works well for both instrumental music and sound textures.',
            'placeholder': (
                'An upbeat lo-fi hip hop beat with a mellow piano melody, '
                'soft drums, and vinyl crackle'
            ),
        }

    @classmethod
    def get_settings_schema(cls):
        return [
            # ── Model Selection ──────────────────────
            {'id': 'model_variant', 'type': 'dropdown',
             'options': ['music_small', 'music_medium', 'music_large', 'audio_8s'],
             'default': 'music_medium',
             'category': 'Model',
             'label': '📦 Variant',
             'description': 'music_small: Fast, low VRAM. music_medium: Best balance. '
                            'music_large: Highest quality, 12GB+ VRAM. audio_8s: Sound effects, 8s max.'},

            # ── Sampling ─────────────────────────────
            {'id': 'temperature', 'type': 'slider', 'min': 0.1, 'max': 2.0,
             'default': 1.0, 'step': 0.1,
             'category': 'Sampling',
             'label': '🌡 Temperature',
             'description': 'Controls randomness. Lower = predictable. Higher = creative/varied.'},
            {'id': 'topk', 'type': 'slider', 'min': 0, 'max': 1000,
             'default': 0, 'step': 10,
             'category': 'Sampling',
             'label': '🎯 Top-K',
             'description': 'Top-K filtering. 0 = disabled. Try 250-500 for focused results.'},
            {'id': 'topp', 'type': 'slider', 'min': 0.0, 'max': 1.0,
             'default': 0.9, 'step': 0.05,
             'category': 'Sampling',
             'label': '🎯 Top-P',
             'description': 'Nucleus sampling. 0.0 = disabled. 0.9 = sample from 90% probability mass.'},

            # ── Guidance ─────────────────────────────
            {'id': 'cfg_coef', 'type': 'slider', 'min': 1.0, 'max': 20.0,
             'default': 10.0, 'step': 0.5,
             'category': 'Guidance',
             'label': '⚖ Guidance Scale',
             'description': 'Classifier-free guidance. MAGNeT benefits from higher values (8-15). '
                            'Too high can cause distortion.'},

            # ── Decoding ─────────────────────────────
            {'id': 'decoding_steps', 'type': 'dropdown',
             'options': ['100', '200', '300', '500'], 'default': '200',
             'category': 'Decoding',
             'label': '🔄 Decoding Steps',
             'description': 'Number of non-autoregressive decoding iterations. '
                            'More steps = better quality but slower. 200 is a good default.'},

            # ── Performance ──────────────────────────
            {'id': 'use_fp16', 'type': 'dropdown',
             'options': ['true', 'false'], 'default': 'true',
             'category': 'Performance',
             'label': '⚡ FP16',
             'description': 'Half-precision inference. Cuts VRAM usage ~50% with minimal quality loss.'},
        ]

    def load_model(self, config: dict):
        from audiocraft.models import MAGNeT

        self.device = config['hardware'].get('device', 'cuda')
        repo_id = self.MODEL_MAP[self.model_variant]

        logger.info(f"[MAGNeT] Loading {repo_id} on {self.device}...")

        self.model = MAGNeT.get_pretrained(repo_id)

        if self.device == 'cuda' and torch.cuda.is_available():
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"[MAGNeT] GPU: {torch.cuda.get_device_name(0)} ({total_mem:.1f} GB)")

        logger.info("[MAGNeT] Ready.")

    def generate(self, prompt: str, duration: int, params: dict,
                 progress_callback=None, stop_check=None) -> dict:
        model_variant = params.get('model_variant', 'music_medium')
        temperature = float(params.get('temperature', 1.0))
        topk = int(params.get('topk', 0))
        topp = float(params.get('topp', 0.9))
        cfg_coef = float(params.get('cfg_coef', 10.0))
        decoding_steps = int(params.get('decoding_steps', 200))
        use_fp16 = params.get('use_fp16', 'true') == 'true'

        # Clamp duration to model max
        max_dur = self.MAX_DURATION.get(model_variant, 10)
        effective_duration = min(duration, max_dur)
        if effective_duration < duration:
            logger.warning(f"[MAGNeT] Duration clamped from {duration}s to {max_dur}s (model limit).")

        # Reload if variant changed
        if model_variant != self.model_variant:
            logger.info(f"[MAGNeT] Switching variant to {model_variant}...")
            from audiocraft.models import MAGNeT
            repo_id = self.MODEL_MAP[model_variant]
            self.model = MAGNeT.get_pretrained(repo_id)
            self.model_variant = model_variant

        self.model.set_generation_params(
            duration=effective_duration,
            temperature=temperature,
            topk=topk if topk > 0 else None,
            topp=topp if topp > 0 else None,
            cfg_coef=cfg_coef,
        )

        logger.info(f"[MAGNeT] Generating: \"{prompt[:80]}...\" ({effective_duration}s, {decoding_steps} steps)")
        if progress_callback:
            progress_callback(10)

        if stop_check and stop_check():
            return None

        dtype = torch.float16 if use_fp16 and self.device == 'cuda' else torch.float32

        with torch.autocast(device_type=self.device, dtype=dtype, enabled=use_fp16):
            wav = self.model.generate(
                [prompt],
                decoding_steps=decoding_steps,
            )[0]

        audio_np = wav.cpu().numpy()
        if audio_np.ndim == 3:
            audio_np = audio_np[0]
        if audio_np.shape[0] > 1:
            audio_np = audio_np[0]
        audio_np = audio_np.astype(np.float32)

        if progress_callback:
            progress_callback(100)

        logger.info("[MAGNeT] Generation complete.")
        return {'audio': audio_np, 'sample_rate': self.model.sample_rate}

    def unload(self):
        if self.model is not None:
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        logger.info("[MAGNeT] Unloaded.")
