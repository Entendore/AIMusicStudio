"""Abstract base class and public data contracts for music-generation backends.

This module is the *only* file inside the ``backend`` package that the
main application ever needs to know about.  Everything specific to a
particular AI model — its name, icon, settings schema, prompt format,
hardware requirements — is declared inside the model's own backend
module and surfaced through the :class:`MusicBackend` interface defined
here.  Consequently, adding, removing, or modifying a backend never
requires touching the GUI or the plugin manager.

A backend is a Python module inside ``backend/`` that defines a class
named ``Plugin`` subclassing :class:`MusicBackend`.  The plugin manager
discovers such modules automatically at startup — no registration
elsewhere is required.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, TypedDict

logger = logging.getLogger(__name__)


# ── Public type aliases ──────────────────────────────────────────────
# Callable signatures shared between the GUI worker thread and backends.

ProgressCallback = Callable[[int], None]
"""Called with an integer 0–100 to report generation progress."""

StopCheck = Callable[[], bool]
"""Polled by the backend; returning True requests cancellation."""


# ── Domain exceptions ────────────────────────────────────────────────

class BackendError(RuntimeError):
    """Base class for all errors originating inside a backend."""


class BackendNotLoadedError(BackendError):
    """Raised when generation is requested before :meth:`MusicBackend.load_model`."""


# ── Data contracts ───────────────────────────────────────────────────
# These TypedDicts document the shape of the plain ``dict`` objects that
# flow between the backend and the GUI.  They are *advisory* — existing
# backends returning ordinary dicts continue to work unchanged.

class SettingItem(TypedDict, total=False):
    """Declarative description of a single UI control.

    Required keys: ``id``, ``type`` (one of ``'slider'``, ``'dropdown'``,
    ``'text'``, ``'spinbox'``).  All other keys are optional and only
    meaningful for specific control types.
    """
    id: str
    type: str
    label: str
    description: str
    category: str
    default: Any
    min: float
    max: float
    step: float
    options: List[str]
    placeholder: str


class PromptSchema(TypedDict, total=False):
    """Describes the prompt input expected by a backend."""
    required: bool
    title: Optional[str]
    description: Optional[str]
    placeholder: Optional[str]


class BackendMetadata(TypedDict, total=False):
    """Display metadata shown in the backend selector dropdown."""
    name: str
    description: str
    details: str
    icon: str
    requirements: str


class GenerationResult(TypedDict):
    """Successful output of :meth:`MusicBackend.generate`.

    ``audio`` is a mono float32 numpy array; ``sample_rate`` is in Hz.
    The numpy type is kept as ``Any`` here so that importing this module
    does not require numpy to be installed.
    """
    audio: Any
    sample_rate: int


# ── Abstract backend ─────────────────────────────────────────────────

class MusicBackend(ABC):
    """Abstract interface every music-generation plugin must implement.

    Subclasses **must** override:
        * :meth:`get_metadata`   — at least set a non-empty ``name``
        * :meth:`load_model`
        * :meth:`generate`
        * :meth:`unload`

    Subclasses **may** override:
        * :meth:`get_settings_schema` — default: no settings
        * :meth:`get_prompt_schema`   — default: text prompt required
    """

    # ── Lifecycle (abstract) ────────────────────────────────────────

    @abstractmethod
    def load_model(self, config: dict) -> None:
        """Initialise model weights / external resources from ``config``.

        Called once after the backend is selected by the user.  Should
        raise :class:`BackendError` (or a subclass) on failure.
        """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        duration: int,
        params: dict,
        progress_callback: Optional[ProgressCallback] = None,
        stop_check: Optional[StopCheck] = None,
    ) -> Optional[GenerationResult]:
        """Generate audio.

        Parameters
        ----------
        prompt:
            Free-form text (lyrics, description, etc.) — may be empty
            when :meth:`get_prompt_schema` declares ``required=False``.
        duration:
            Target length in seconds.
        params:
            Values chosen by the user in the settings UI; keys match
            the ``id`` fields of :meth:`get_settings_schema`.
        progress_callback:
            Optional callback receiving an integer 0–100.
        stop_check:
            Optional callable returning True if the user requested
            cancellation; the backend should poll it periodically.

        Returns
        -------
        GenerationResult or None
            A dict with ``audio`` and ``sample_rate`` keys on success,
            or ``None`` if generation was cancelled or failed softly.
        """

    @abstractmethod
    def unload(self) -> None:
        """Release VRAM, file handles, subprocesses, etc."""

    # ── Optional schema hooks ───────────────────────────────────────

    @classmethod
    def get_settings_schema(cls) -> List[SettingItem]:
        """Return the list of UI setting definitions for this backend."""
        return []

    @classmethod
    def get_prompt_schema(cls) -> PromptSchema:
        """Describe the prompt input this backend expects.

        Backends that don't need text input should override this and
        set ``required`` to ``False``.
        """
        return {
            'required': True,
            'title': '📝 Prompt',
            'description': 'Enter a text prompt for generation.',
            'placeholder': 'Enter your prompt here...',
        }

    @classmethod
    def get_metadata(cls) -> BackendMetadata:
        """Return display metadata shown in the backend selector.

        Every backend should override this to provide a meaningful
        ``name`` and ``description``; the defaults are intentionally
        generic so the GUI still works if an author forgets.
        """
        return {
            'name': cls.__name__,
            'description': '',
            'details': '',
            'icon': '📦',
            'requirements': '',
        }

    # ── Convenience accessors ───────────────────────────────────────

    @property
    def display_name(self) -> str:
        """Short human-readable name (from :meth:`get_metadata`)."""
        return str(self.get_metadata().get('name') or type(self).__name__)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.display_name!r}>"

    # ── Subclass sanity check ───────────────────────────────────────

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Warn (once, at class-definition time) if a concrete backend
        # hasn't bothered to override get_metadata — the resulting
        # dropdown entry would just show the raw class name with no icon.
        if cls.get_metadata.__func__ is MusicBackend.get_metadata.__func__:
            logger.warning(
                "Backend %s does not override get_metadata(); "
                "the GUI will show generic defaults.",
                cls.__name__,
            )