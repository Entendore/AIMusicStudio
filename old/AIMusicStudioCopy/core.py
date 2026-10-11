"""Core plugin management and audio file utilities."""
import logging
import os
import soundfile as sf
import importlib
from backend.base import MusicBackend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.active_backend: MusicBackend = None

    def load_plugin(self, plugin_name: str, config: dict):
        try:
            module = importlib.import_module(f"backend.{plugin_name}")
            backend = module.Plugin()
            logger.info(f"Loading plugin: {plugin_name}...")
            backend.load_model(config)
            self.active_backend = backend
            return backend
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            raise

    def save_audio(self, audio_data: dict, filename: str, output_dir: str):
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        path = os.path.abspath(os.path.join(output_dir, f"{filename}.wav"))
        sf.write(path, audio_data['audio'], audio_data['sample_rate'])
        logger.info(f"Saved audio to: {path}")
        return path