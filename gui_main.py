"""Main application window with minimalist styling."""
import sys
import os
import logging
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QGroupBox, QTextEdit,
    QSplitter, QMessageBox, QProgressBar, QComboBox, QScrollArea,
    QFrame
)
from PySide6.QtCore import Qt, QThread, Slot, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QFont

from core import PluginManager
from gui_components import (
    SettingsDialog, build_settings_widgets, clear_layout,
    apply_global_styles, STYLES, SettingWidget, create_reset_button
)
from gui_workers import Worker, LogEmitter, QtLogHandler
from config import save_config

logger = logging.getLogger(__name__)


class MusicStudioApp(QMainWindow):
    """Primary application window for AI Music Studio."""

    def __init__(self, manager: PluginManager, config: dict):
        super().__init__()
        self.manager = manager
        self.config = config
        self.thread = None
        self.worker = None
        self.settings_widgets: dict[str, SettingWidget] = {}
        self._backend_metadata: dict = {}

        # Fetch metadata from all discovered backends (no model-specific info in GUI)
        self._backend_metadata = self.manager.get_backend_metadata()

        self.setWindowTitle("AI Music Studio")
        self.resize(900, 650)

        central = QWidget()
        self.setCentralWidget(central)

        self.splitter = QSplitter(Qt.Horizontal)
        root = QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self.splitter)

        # Left — controls with scroll area
        self.control_scroll = QScrollArea()
        self.control_scroll.setWidgetResizable(True)
        self.control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.control_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)
        self.control_layout.setSpacing(6)
        self.control_layout.setContentsMargins(4, 4, 4, 4)
        self.control_scroll.setWidget(self.control_panel)
        self.splitter.addWidget(self.control_scroll)

        # Right — console log
        self.log_panel = QWidget()
        self.log_layout = QVBoxLayout(self.log_panel)
        self.log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_layout.setSpacing(4)
        self.splitter.addWidget(self.log_panel)
        self.splitter.setSizes([350, 550])

        self._build_ui()
        self._setup_logging()
        
        # Setup Media Player
        self.last_saved_path = None
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._update_playback_state)

        QApplication.processEvents()
        # Ensure an active plugin is configured before loading
        if not self.config.get('plugins', {}).get('active_plugin'):
            backends = self.manager.discover_available_backends()
            if backends:
                self.config['plugins']['active_plugin'] = backends[0]
                self.backend_combo.blockSignals(True)
                self.backend_combo.setCurrentIndex(0)
                self.backend_combo.blockSignals(False)
        self.load_backend()

    # ── UI Construction ────────────────────────────────────────────

    def _build_ui(self):
        # App title - simplified
        title = QLabel("AI Music Studio")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet("color: #666; padding: 2px;")
        self.control_layout.addWidget(title)
        
        self._build_backend_selector()
        self._build_input_section()
        self._build_settings_section()
        self._build_controls_section()
        self._build_playback_section()
        self.control_layout.addStretch()
        self._build_log_section()

    def _build_backend_selector(self):
        # Simplified to just a dropdown without group box
        self.backend_combo = QComboBox()
        self._available_backends = self.manager.discover_available_backends()
        
        for backend_id in self._available_backends:
            info = self._backend_metadata.get(backend_id, {})
            icon = info.get('icon', '📦')
            name = info.get('name', backend_id.title())
            display_text = f"{icon} {name}"
            self.backend_combo.addItem(display_text, backend_id)
        
        self.backend_combo.setStyleSheet("""
            QComboBox {
                background-color: #222;
                border: 1px solid #333;
                border-radius: 2px;
                padding: 6px 10px;
                color: #ccc;
                min-height: 22px;
                font-size: 12px;
            }
            QComboBox:hover { border-color: #555; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox::down-arrow {
                image: none; border: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #666;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #222;
                border: 1px solid #333;
                selection-background-color: #444;
                color: #ccc; padding: 4px; outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 8px;
                border-bottom: 1px solid #333;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover { background-color: #333; }
            QComboBox QAbstractItemView::item:selected { background-color: #444; }
        """)

        current_plugin = self.config.get('plugins', {}).get('active_plugin', '')
        for i in range(self.backend_combo.count()):
            if self.backend_combo.itemData(i) == current_plugin:
                self.backend_combo.setCurrentIndex(i)
                break
        
        self.backend_combo.currentIndexChanged.connect(self._on_backend_selection_changed)
        self.control_layout.addWidget(self.backend_combo)

        # Simplified status label
        self.backend_status_label = QLabel("")
        self.backend_status_label.setStyleSheet("font-size: 10px; color: #555; padding: 2px;")
        self.control_layout.addWidget(self.backend_status_label)

    def _on_backend_selection_changed(self, index: int):
        if index < 0:
            return
            
        backend_name = self.backend_combo.itemData(index)
        if not backend_name:
            return

        if self.thread and self.thread.isRunning():
            QMessageBox.warning(
                self, "Cannot Switch",
                "A generation is currently running.\nPlease stop it before switching backends."
            )
            current_plugin = self.config.get('plugins', {}).get('active_plugin', '')
            self.backend_combo.blockSignals(True)
            for i in range(self.backend_combo.count()):
                if self.backend_combo.itemData(i) == current_plugin:
                    self.backend_combo.setCurrentIndex(i)
                    break
            self.backend_combo.blockSignals(False)
            return

        if self.manager.active_backend:
            self.manager.active_backend.unload()

        self.config['plugins']['active_plugin'] = backend_name
        save_config(self.config)
        self.load_backend()

    # ── Input Section ──────────────────────────────────────────────

    def _build_input_section(self):
        self.prompt_group = QFrame()
        self.prompt_group_layout = QVBoxLayout(self.prompt_group)
        self.prompt_group_layout.setSpacing(4)
        self.prompt_group_layout.setContentsMargins(0, 0, 0, 0)

        self.prompt_desc_label = QLabel()
        self.prompt_desc_label.setWordWrap(True)
        self.prompt_desc_label.setStyleSheet("color: #555; font-size: 10px;")
        self.prompt_group_layout.addWidget(self.prompt_desc_label)

        self.prompt_input = QTextEdit()
        self.prompt_input.setMinimumHeight(80)
        self.prompt_input.setMaximumHeight(150)
        self.prompt_group_layout.addWidget(self.prompt_input)

        row = QHBoxLayout()
        row.addWidget(QLabel("Duration:"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 300)
        self.duration_spin.setValue(30)
        self.duration_spin.setSuffix("s")
        self.duration_spin.setStyleSheet(STYLES['spinbox'])
        self.duration_spin.setMaximumWidth(80)
        row.addWidget(self.duration_spin)
        row.addStretch()
        self.prompt_group_layout.addLayout(row)

        self.control_layout.insertWidget(1, self.prompt_group)

    def _configure_prompt_section(self, prompt_schema: Optional[dict]):
        if not prompt_schema or not prompt_schema.get('required', True):
            self.prompt_group.hide()
            return

        self.prompt_group.show()

        description = prompt_schema.get('description', '')
        if description:
            self.prompt_desc_label.setText(description)
            self.prompt_desc_label.show()
        else:
            self.prompt_desc_label.hide()

        placeholder = prompt_schema.get('placeholder', '')
        self.prompt_input.setPlaceholderText(placeholder if placeholder else "")
        self.prompt_input.clear()

    def _build_settings_section(self):
        self.settings_group = QFrame()
        self.settings_outer_layout = QVBoxLayout(self.settings_group)
        self.settings_outer_layout.setSpacing(2)
        self.settings_outer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setMaximumHeight(250)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_layout.setSpacing(4)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        
        self.settings_scroll.setWidget(self.settings_container)
        self.settings_outer_layout.addWidget(self.settings_scroll)
        
        self.control_layout.addWidget(self.settings_group)

    def _build_controls_section(self):
        # Simplified controls without group box
        layout = QVBoxLayout()
        layout.setSpacing(4)

        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setStyleSheet(STYLES['button_primary'])
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self.start_generation)
        layout.addWidget(self.btn_generate)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(STYLES['button_danger'])
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_generation)
        layout.addWidget(self.btn_stop)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLES['progress_bar'])
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        row = QHBoxLayout()
        row.setSpacing(4)
        
        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setStyleSheet(STYLES['button_secondary'])
        self.btn_reload.setCursor(Qt.PointingHandCursor)
        self.btn_reload.clicked.connect(self.reload_backend)
        row.addWidget(self.btn_reload)
        
        self.btn_settings = QPushButton("Paths")
        self.btn_settings.setStyleSheet(STYLES['button_secondary'])
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.open_settings)
        row.addWidget(self.btn_settings)
        layout.addLayout(row)

        self.control_layout.addLayout(layout)

    def _build_playback_section(self):
        # Simplified playback without group box
        layout = QVBoxLayout()
        layout.setSpacing(4)

        self.lbl_now_playing = QLabel("No audio")
        self.lbl_now_playing.setStyleSheet("color: #555; font-size: 10px; padding: 2px;")
        self.lbl_now_playing.setWordWrap(True)
        layout.addWidget(self.lbl_now_playing)

        row = QHBoxLayout()
        row.setSpacing(4)
        
        self.btn_play = QPushButton("Play")
        self.btn_play.setEnabled(False)
        self.btn_play.setMinimumHeight(28)
        self.btn_play.setStyleSheet(STYLES['button_primary'])
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.clicked.connect(self.play_audio)
        row.addWidget(self.btn_play)

        self.btn_stop_play = QPushButton("Stop")
        self.btn_stop_play.setEnabled(False)
        self.btn_stop_play.setMinimumHeight(28)
        self.btn_stop_play.setStyleSheet(STYLES['button_secondary'])
        self.btn_stop_play.setCursor(Qt.PointingHandCursor)
        self.btn_stop_play.clicked.connect(self.stop_audio)
        row.addWidget(self.btn_stop_play)

        layout.addLayout(row)
        self.control_layout.addLayout(layout)

    def _build_log_section(self):
        header = QLabel("Console")
        header.setFont(QFont("Segoe UI", 10))
        header.setStyleSheet("color: #555; padding: 2px;")
        self.log_layout.addWidget(header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #666;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #222;
                border-radius: 2px;
                padding: 6px;
            }
        """)
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
            empty_label = QLabel("No backend loaded")
            empty_label.setStyleSheet("color: #444; font-size: 10px; padding: 10px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.settings_layout.addWidget(empty_label)
            self._configure_prompt_section(None)
            return
        
        prompt_schema = self.manager.active_backend.__class__.get_prompt_schema()
        self._configure_prompt_section(prompt_schema)

        schema = self.manager.active_backend.__class__.get_settings_schema()
        backend_name = self.config.get('plugins', {}).get('active_plugin', '')
        saved_settings = self.config.get('backend_settings', {}).get(backend_name, {})
        
        build_settings_widgets(schema, self.settings_layout, self.settings_widgets, saved_settings)
        create_reset_button(self.settings_widgets, self.settings_layout)

    def save_backend_settings(self):
        if not self.settings_widgets:
            return
            
        backend_name = self.config.get('plugins', {}).get('active_plugin', '')
        if not backend_name:
            return
            
        if 'backend_settings' not in self.config:
            self.config['backend_settings'] = {}
        if backend_name not in self.config['backend_settings']:
            self.config['backend_settings'][backend_name] = {}
            
        for key, widget in self.settings_widgets.items():
            value = widget.get_value()
            if value is not None:
                self.config['backend_settings'][backend_name][key] = value
                
        save_config(self.config)

    # ── Backend lifecycle ─────────────────────────────────────────

    def load_backend(self):
        plugin_name = self.config['plugins']['active_plugin']
        info = self._backend_metadata.get(plugin_name, {})
        friendly_name = info.get('name', plugin_name.title())
        
        try:
            self.manager.load_plugin(plugin_name, self.config)
            self.populate_settings()
            self.btn_generate.setEnabled(True)
            self.backend_status_label.setText(f"✓ {friendly_name} loaded")
            self.backend_status_label.setStyleSheet("font-size: 10px; color: #555; padding: 2px;")
        except Exception as e:
            logging.error(f"Failed to load: {e}")
            self.btn_generate.setEnabled(False)
            self.backend_status_label.setText(f"✗ {friendly_name} failed")
            self.backend_status_label.setStyleSheet("font-size: 10px; color: #663333; padding: 2px;")

    def reload_backend(self):
        if self.manager.active_backend:
            self.manager.active_backend.unload()
        self.load_backend()

    # ── Generation ────────────────────────────────────────────────

    def start_generation(self):
        if self.thread and self.thread.isRunning():
            return

        self.stop_audio()
        self.save_backend_settings()

        params = self._collect_params()
        prompt = self.prompt_input.toPlainText()

        prompt_schema = None
        if self.manager.active_backend:
            prompt_schema = self.manager.active_backend.__class__.get_prompt_schema()

        requires_prompt = prompt_schema.get('required', True) if prompt_schema else True
        if requires_prompt and not prompt.strip():
            QMessageBox.warning(
                self, "Empty Prompt",
                f"{prompt_schema.get('title', 'Prompt')} is required for this backend."
            )
            return

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
        self.btn_generate.setText("Generating...")
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)

    def _collect_params(self):
        params = {}
        for key, widget in self.settings_widgets.items():
            value = widget.get_value()
            if value is not None:
                params[key] = value
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
        has_audio = self.last_saved_path is not None
        
        self.btn_play.setEnabled(not is_playing and has_audio)
        self.btn_stop_play.setEnabled(is_playing)
        
        if is_playing:
            filename = os.path.basename(self.last_saved_path)
            self.lbl_now_playing.setText(f"▶ {filename}")
            self.lbl_now_playing.setStyleSheet("color: #555; font-size: 10px; padding: 2px;")
        elif has_audio:
            self.lbl_now_playing.setText("Paused")
            self.lbl_now_playing.setStyleSheet("color: #444; font-size: 10px; padding: 2px;")
        else:
            self.lbl_now_playing.setText("No audio")
            self.lbl_now_playing.setStyleSheet("color: #333; font-size: 10px; padding: 2px;")

    # ── Slots ─────────────────────────────────────────────────────

    @Slot(str)
    def append_log(self, message):
        if "ERROR" in message or "error" in message.lower():
            color = "#663333"
        elif "WARNING" in message or "warning" in message.lower():
            color = "#665533"
        elif "SUCCESS" in message or "✔" in message or "✅" in message:
            color = "#336633"
        else:
            color = "#666"
        
        self.log_text.append(f'<span style="color: {color};">{message}</span>')

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
            self.append_log(f"✓ Saved to: {path}")
            self.play_audio()
        except Exception as e:
            logging.error(f"Save error: {e}")

    @Slot(str)
    def on_error(self, err_msg):
        QMessageBox.critical(self, "Error", f"Generation failed:\n\n{err_msg}")

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
        self.btn_generate.setText("Generate")
        self.btn_stop.setEnabled(False)

    def closeEvent(self, event):
        self.save_backend_settings()
        self.stop_audio()
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
        event.accept()


def launch_gui(manager: PluginManager, config: dict):
    """Create the QApplication and show the main window."""
    app = QApplication(sys.argv)
    apply_global_styles(app)
    window = MusicStudioApp(manager, config)
    window.show()
    sys.exit(app.exec())