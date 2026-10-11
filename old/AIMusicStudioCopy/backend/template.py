"""Template backend plugin for demonstration and as a reference implementation."""
import logging
import time
import numpy as np
from backend.base import MusicBackend

logger = logging.getLogger(__name__)


class Plugin(MusicBackend):
    """Template backend that simulates generation with cancellable chunks."""

    @classmethod
    def get_settings_schema(cls):
        return [
            {'id': 'style', 'type': 'dropdown',
             'options': ['Orchestral', 'Electronic', 'Jazz'],
             'default': 'Electronic', 'label': 'Music Style'},
            {'id': 'intensity', 'type': 'slider', 'min': 1.0, 'max': 10.0,
             'default': 5.0, 'step': 1.0, 'label': 'Intensity'},
        ]

    def load_model(self, config: dict):
        logger.info("[Template] Initializing Template Backend...")
        logger.info(f"[Template] Using device: {config['hardware'].get('device', 'cpu')}")
        time.sleep(1)
        self.model = "TemplateModelInstance"
        logger.info("[Template] Model ready.")

    def generate(self, prompt: str, duration: int, params: dict,
                 progress_callback=None, stop_check=None) -> dict:
        logger.info(f"[Template] Generating '{prompt}' with params: {params}")

        chunks = 10
        sample_rate = 44100
        audio_data = np.array([], dtype=np.float32)

        for i in range(chunks):
            if stop_check and stop_check():
                logger.warning("[Template] Generation cancelled by user.")
                return None

            time.sleep(0.2)
            chunk_audio = np.random.rand(
                int(sample_rate * (duration / chunks))
            ).astype(np.float32)
            audio_data = np.concatenate((audio_data, chunk_audio))

            if progress_callback:
                progress_callback(int((i + 1) / chunks * 100))

        logger.info("[Template] Generation complete.")
        return {'audio': audio_data, 'sample_rate': sample_rate}

    def unload(self):
        logger.info("[Template] Unloading model...")
        self.model = None