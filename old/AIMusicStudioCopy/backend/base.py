"""Abstract base class for all music generation backends."""
from abc import ABC, abstractmethod


class MusicBackend(ABC):
    """Interface that every plugin backend must implement."""

    @abstractmethod
    def load_model(self, config: dict):
        """Load model weights into memory using the given configuration."""
        pass

    @abstractmethod
    def generate(self, prompt: str, duration: int, params: dict,
                 progress_callback=None, stop_check=None) -> dict:
        """Generate audio. Returns {'audio': ndarray, 'sample_rate': int}."""
        pass

    @abstractmethod
    def unload(self):
        """Release all model resources."""
        pass

    @classmethod
    @abstractmethod
    def get_settings_schema(cls) -> list:
        """Return UI control definitions for this backend."""
        pass