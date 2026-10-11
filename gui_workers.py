"""Background worker thread and Qt logging bridge components."""
import datetime
import logging
from PySide6.QtCore import QObject, Signal, Slot


# ── Logging Bridge ──────────────────────────────────────────────────

class LogEmitter(QObject):
    """Thread-safe bridge: emits log records as Qt signals."""
    log_message = Signal(str)


class QtLogHandler(logging.Handler):
    """Redirects Python log records into a LogEmitter signal."""

    def __init__(self, emitter: LogEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record):
        msg = self.format(record)
        self.emitter.log_message.emit(msg)


# ── Generation Worker ──────────────────────────────────────────────

class Worker(QObject):
    """Runs audio generation on a background QThread."""
    finished = Signal()
    error = Signal(str)
    success = Signal(dict, str)
    progress = Signal(int)

    def __init__(self, backend, prompt, duration, params, config):
        super().__init__()
        self.backend = backend
        self.prompt = prompt
        self.duration = duration
        self.params = params
        self.config = config
        self._is_cancelled = False

    def stop(self):
        """Request cancellation of the running generation."""
        self._is_cancelled = True

    @Slot()
    def run_generation(self):
        """Execute the generation loop; emit signals for progress/result."""
        try:
            result = self.backend.generate(
                self.prompt,
                self.duration,
                self.params,
                progress_callback=self.progress.emit,
                stop_check=lambda: self._is_cancelled,
            )

            if result is not None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_prompt = "".join(
                    c if c.isalnum() else "_" for c in self.prompt
                )[:20]
                filename = f"{timestamp}_{safe_prompt}"
                self.success.emit(result, filename)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()