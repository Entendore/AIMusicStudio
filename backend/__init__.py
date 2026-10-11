"""Music-generation backend package.

This package is the *only* boundary the main application should import
from when it needs to talk to a backend.  All AI-model-specific
information (name, settings, prompt format, hardware requirements) is
declared inside individual backend modules and surfaced through the
:class:`MusicBackend` interface defined in :mod:`backend.base`.

To add a new backend
--------------------
1. Create ``backend/<your_backend>.py``.
2. Define a class named ``Plugin`` that subclasses :class:`MusicBackend`.
3. Override :meth:`MusicBackend.get_metadata`, :meth:`MusicBackend.load_model`,
   :meth:`MusicBackend.generate`, and :meth:`MusicBackend.unload`.
4. (Optional) Override :meth:`MusicBackend.get_settings_schema`
   and :meth:`MusicBackend.get_prompt_schema`.

The plugin manager discovers modules automatically — no registration
elsewhere is required.
"""
from .base import (
    # Core abstract class
    MusicBackend,
    # Data contracts
    SettingItem,
    PromptSchema,
    BackendMetadata,
    GenerationResult,
    # Callback type aliases
    ProgressCallback,
    StopCheck,
    # Domain exceptions
    BackendError,
    BackendNotLoadedError,
)

__all__ = [
    'MusicBackend',
    'SettingItem',
    'PromptSchema',
    'BackendMetadata',
    'GenerationResult',
    'ProgressCallback',
    'StopCheck',
    'BackendError',
    'BackendNotLoadedError',
]

__version__ = '1.0'