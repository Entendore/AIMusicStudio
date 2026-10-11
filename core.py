"""Core plugin management and audio file utilities."""
import logging
import os
import pkgutil
import soundfile as sf
import importlib
from backend import MusicBackend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.active_backend: MusicBackend = None

    @staticmethod
    def discover_available_backends() -> list:
        """Scan the backend package directory and return a list of available backend names.

        Each Python module inside the ``backend`` package that contains a ``Plugin``
        class inheriting from :class:`MusicBackend` is considered a valid backend.
        """
        available = []
        try:
            import backend as _pkg
            pkg_path = os.path.dirname(_pkg.__file__)
            for _importer, modname, ispkg in pkgutil.iter_modules([pkg_path]):
                try:
                    module = importlib.import_module(f"backend.{modname}")
                    cls = getattr(module, "Plugin", None)
                    if cls is not None and issubclass(cls, MusicBackend) and cls is not MusicBackend:
                        available.append(modname)
                except Exception as exc:
                    logger.debug(f"Skipping backend '{modname}': {exc}")
        except ImportError:
            # Backend package not importable — return empty; plugins self-register
            available = []
        return sorted(available)

    @staticmethod
    def get_backend_metadata() -> dict:
        """Return a {backend_name: metadata_dict} mapping for every discovered backend.

        Metadata is read from each backend's ``Plugin.get_metadata()`` classmethod,
        so no AI-model-specific information lives outside the backend package.
        """
        metadata = {}
        try:
            import backend as _pkg
            pkg_path = os.path.dirname(_pkg.__file__)
            for _importer, modname, ispkg in pkgutil.iter_modules([pkg_path]):
                try:
                    module = importlib.import_module(f"backend.{modname}")
                    cls = getattr(module, "Plugin", None)
                    if cls is not None and issubclass(cls, MusicBackend) and cls is not MusicBackend:
                        metadata[modname] = cls.get_metadata()
                except Exception as exc:
                    logger.debug(f"Skipping backend metadata '{modname}': {exc}")
        except ImportError:
            pass
        return metadata

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