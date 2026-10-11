"""Main application window and GUI entry-point."""
import sys
import os
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QGroupBox, QTextEdit,
    QSplitter, QMessageBox, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, QThread, Slot, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from core import PluginManager
from gui_components import SettingsDialog, build_settings_widgets, clear_layout
from gui_workers import Worker, LogEmitter, QtLogHandler

logger = logging.getLogger(__name__)


class MusicStudioApp(QMainWindow):
    """Primary application window for AI Music Studio."""

    def __init__(self, manager: PluginManager, config: dict):
        super().__init__()
        self.manager = manager
        self.config = config
        self.thread = None
        self.worker = None
        self.settings_widgets = {}

        self.setWindowTitle("AI Music Studio (HeartMuLa & MathSynth)")
        self.resize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)

        self.splitter = QSplitter(Qt.Horizontal)
        root = QHBoxLayout(central)
        root.addWidget(self.splitter)

        # Left — controls
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)
        self.splitter.addWidget(self.control_panel)

        # Right — console log
        self.log_panel = QWidget()
        self.log_layout = QVBoxLayout(self.log_panel)
        self.splitter.addWidget(self.log_panel)
        self.splitter.setSizes([350, 650])

        self._build_ui()
        self._setup_logging()
        
        # Setup Media Player
        self.last_saved_path = None
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._update_playback_state)

        QApplication.processEvents()
        self.load_backend()

    # ── UI Construction ────────────────────────────────────────────

    def _build_ui(self):
        self._build_input_section()
        self._build_settings_section()
        self._build_controls_section()
        self._build_playback_section()
        self.control_layout.addStretch()
        self._build_log_section()

    def _build_input_section(self):
        group = QGroupBox("Lyrics / Prompt Input")
        layout = QVBoxLayout(group)
        
        layout.addWidget(QLabel("Prompt (Lyrics for HeartMuLa, Desc for MathSynth):"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("[Intro]\n\n[Verse]\nLyrics here...")
        self.prompt_input.setMaximumHeight(150)
        layout.addWidget(self.prompt_input)

        row = QHBoxLayout()
        row.addWidget(QLabel("Duration (sec):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 240)
        self.duration_spin.setValue(30)
        row.addWidget(self.duration_spin)
        row.addStretch()
        layout.addLayout(row)

        self.control_layout.addWidget(group)

    def _build_settings_section(self):
        self.settings_group = QGroupBox("Backend Settings")
        self.settings_layout = QVBoxLayout(self.settings_group)
        self.control_layout.addWidget(self.settings_group)

    def _build_controls_section(self):
        group = QGroupBox("Controls")
        layout = QVBoxLayout(group)

        self.btn_generate = QPushButton("🎵 Generate Music")
        self.btn_generate.setStyleSheet("font-weight: bold; height: 30px;")
        self.btn_generate.clicked.connect(self.start_generation)
        layout.addWidget(self.btn_generate)

        self.btn_stop = QPushButton("🛑 Stop Generation")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #ffcccc; color: black;")
        self.btn_stop.clicked.connect(self.stop_generation)
        layout.addWidget(self.btn_stop)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        row = QHBoxLayout()
        self.btn_reload = QPushButton("Reload Backend")
        self.btn_reload.clicked.connect(self.reload_backend)
        row.addWidget(self.btn_reload)
        self.btn_settings = QPushButton("Settings (Ckpt Paths)")
        self.btn_settings.clicked.connect(self.open_settings)
        row.addWidget(self.btn_settings)
        layout.addLayout(row)

        self.control_layout.addWidget(group)

    def _build_playback_section(self):
        group = QGroupBox("Playback")
        layout = QHBoxLayout(group)

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.play_audio)
        layout.addWidget(self.btn_play)

        self.btn_stop_play = QPushButton("⏹ Stop")
        self.btn_stop_play.setEnabled(False)
        self.btn_stop_play.clicked.connect(self.stop_audio)
        layout.addWidget(self.btn_stop_play)

        self.lbl_playback_status = QLabel("No audio loaded")
        layout.addWidget(self.lbl_playback_status)

        self.control_layout.addWidget(group)

    def _build_log_section(self):
        lbl = QLabel("Console Output")
        lbl.setStyleSheet("font-weight: bold;")
        self.log_layout.addWidget(lbl)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 12px;"
        )
        self.log_layout.addWidget(self.log_text)

    def _setup_logging(self):
        self.log_emitter = LogEmitter()
        self.log_emitter.log_message.connect(self.append_log)
        handler = QtLogHandler(self.log_emitter)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        )
        logging.getLogger().addHandler(handler)

    # ── Settings ──────────────────────────────────────────────────

    def open_settings(self):
        SettingsDialog(self.config, self).exec()

    def populate_settings(self):
        clear_layout(self.settings_layout)
        self.settings_widgets = {}
        if not self.manager.active_backend:
            return
        schema = self.manager.active_backend.__class__.get_settings_schema()
        build_settings_widgets(schema, self.settings_layout, self.settings_widgets)

    # ── Backend lifecycle ─────────────────────────────────────────

    def load_backend(self):
        plugin_name = self.config['plugins']['active_plugin']
        try:
            self.manager.load_plugin(plugin_name, self.config)
            self.populate_settings()
            self.btn_generate.setEnabled(True)
        except Exception as e:
            logging.error(f"Failed to load: {e}")
            self.btn_generate.setEnabled(False)

    def reload_backend(self):
        if self.manager.active_backend:
            self.manager.active_backend.unload()
        self.load_backend()

    # ── Generation ────────────────────────────────────────────────

    def start_generation(self):
        if self.thread and self.thread.isRunning():
            return

        self.stop_audio()  # Stop any current playback before starting new generation

        params = self._collect_params()
        prompt = self.prompt_input.toPlainText() 

        self.thread = QThread()
        self.worker = Worker(
            self.manager.active_backend,
            prompt,
            self.duration_spin.value(),
            params,
            self.config,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run_generation)
        self.worker.finished.connect(self.on_finished)
        self.worker.success.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.progress.connect(self.update_progress)

        self.thread.start()
        self.btn_generate.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)

    def _collect_params(self):
        params = {}
        for key, w in self.settings_widgets.items():
            if isinstance(w, tuple):
                # It's a Slider (tuple contains slider widget and label widget)
                params[key] = w[0].value() / 10.0
            elif isinstance(w, QComboBox):
                # It's a Dropdown
                params[key] = w.currentText()
            elif isinstance(w, QLineEdit):
                # It's a Text Box (like the Tags field)
                params[key] = w.text()
            else:
                # Fallback
                params[key] = str(w)
        return params

    def stop_generation(self):
        if self.worker:
            self.worker.stop()
            logging.info("Sending stop signal...")

    # ── Media Playback ────────────────────────────────────────────

    def play_audio(self):
        if self.last_saved_path:
            self.player.setSource(QUrl.fromLocalFile(self.last_saved_path))
            self.player.play()

    def stop_audio(self):
        self.player.stop()

    def _update_playback_state(self, state):
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.btn_play.setEnabled(not is_playing and self.last_saved_path is not None)
        self.btn_stop_play.setEnabled(is_playing)
        if is_playing:
            self.lbl_playback_status.setText(f"Playing: {os.path.basename(self.last_saved_path)}")
        else:
            self.lbl_playback_status.setText("Stopped")

    # ── Slots ─────────────────────────────────────────────────────

    @Slot(str)
    def append_log(self, message):
        self.log_text.append(message)

    @Slot(int)
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    @Slot(dict, str)
    def on_success(self, result, filename):
        output_dir = self.config.get('settings', {}).get('output_dir', 'output')
        try:
            path = self.manager.save_audio(result, filename, output_dir)
            self.last_saved_path = path
            self.btn_play.setEnabled(True)
            self.append_log(f"✅ Saved to: {path}")
            self.play_audio() # Auto-play
        except Exception as e:
            logging.error(f"Save error: {e}")

    @Slot(str)
    def on_error(self, err_msg):
        QMessageBox.critical(self, "Error", f"Generation failed:\n{err_msg}")

    @Slot()
    def on_finished(self):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread.deleteLater()
            self.worker.deleteLater()
            self.thread = None
            self.worker = None
        self.btn_generate.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def closeEvent(self, event):
        self.stop_audio()
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
        event.accept()


def launch_gui(manager: PluginManager, config: dict):
    """Create the QApplication and show the main window."""
    app = QApplication(sys.argv)
    window = MusicStudioApp(manager, config)
    window.show()
    sys.exit(app.exec())