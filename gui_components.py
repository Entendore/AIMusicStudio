"""Minimalist dialog and dynamic-setting widget builders with simplified styling."""
from PySide6.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QComboBox, QSlider, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout,
    QFrame, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from config import save_config


# ── Minimalist Stylesheet Constants ────────────────────────────────

STYLES = {
    'group_box': """
        QGroupBox {
            font-weight: normal;
            font-size: 12px;
            border: 1px solid #333;
            border-radius: 4px;
            margin-top: 8px;
            padding: 8px 6px 6px 6px;
            background-color: #1a1a1a;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: #888;
        }
    """,
    'settings_card': """
        QFrame#settingsCard {
            background-color: #1a1a1a;
            border: none;
            border-radius: 2px;
            padding: 4px;
        }
    """,
    'slider': """
        QSlider::groove:horizontal {
            border: none;
            height: 4px;
            background: #333;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #555;
            border: none;
            width: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }
        QSlider::handle:horizontal:hover {
            background: #666;
        }
        QSlider::sub-page:horizontal {
            background: #444;
            border-radius: 2px;
        }
    """,
    'dropdown': """
        QComboBox {
            background-color: #222;
            border: 1px solid #333;
            border-radius: 2px;
            padding: 4px 8px;
            color: #ccc;
            min-height: 20px;
        }
        QComboBox:hover {
            border-color: #555;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            border: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #666;
            margin-right: 6px;
        }
        QComboBox QAbstractItemView {
            background-color: #222;
            border: 1px solid #333;
            selection-background-color: #444;
            color: #ccc;
            padding: 2px;
        }
    """,
    'spinbox': """
        QSpinBox, QDoubleSpinBox {
            background-color: #222;
            border: 1px solid #333;
            border-radius: 2px;
            padding: 2px 4px;
            color: #ccc;
            min-height: 20px;
        }
        QSpinBox:hover, QDoubleSpinBox:hover {
            border-color: #555;
        }
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            background-color: #333;
            border: none;
            width: 16px;
        }
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
            background-color: #444;
        }
    """,
    'button_primary': """
        QPushButton {
            background-color: #444;
            color: #fff;
            border: none;
            border-radius: 2px;
            padding: 6px 12px;
            font-weight: normal;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #555;
        }
        QPushButton:pressed {
            background-color: #333;
        }
        QPushButton:disabled {
            background-color: #222;
            color: #555;
        }
    """,
    'button_secondary': """
        QPushButton {
            background-color: #333;
            color: #999;
            border: 1px solid #444;
            border-radius: 2px;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #444;
            border-color: #555;
        }
        QPushButton:disabled {
            background-color: #222;
            color: #444;
        }
    """,
    'button_danger': """
        QPushButton {
            background-color: #663333;
            color: #fff;
            border: none;
            border-radius: 2px;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #774444;
        }
        QPushButton:disabled {
            background-color: #222;
            color: #555;
        }
    """,
    'line_edit': """
        QLineEdit {
            background-color: #222;
            border: 1px solid #333;
            border-radius: 2px;
            padding: 4px 6px;
            color: #ccc;
        }
        QLineEdit:focus {
            border-color: #555;
        }
    """,
    'progress_bar': """
        QProgressBar {
            border: 1px solid #333;
            border-radius: 2px;
            text-align: center;
            background-color: #1a1a1a;
            color: #ccc;
            height: 16px;
            font-size: 10px;
        }
        QProgressBar::chunk {
            background: #444;
            border-radius: 1px;
        }
    """,
    'tooltip': """
        QToolTip {
            background-color: #222;
            color: #ccc;
            border: 1px solid #444;
            border-radius: 2px;
            padding: 4px 6px;
            font-size: 10px;
        }
    """
}


def apply_global_styles(app):
    """Apply the minimalist dark theme stylesheet."""
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #111;
        }
        QWidget {
            color: #999;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 11px;
        }
        QLabel {
            color: #999;
        }
        QTextEdit {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 2px;
            padding: 6px;
            color: #ccc;
            selection-background-color: #444;
        }
        QTextEdit:focus {
            border-color: #555;
        }
        QSplitter::handle {
            background-color: #333;
            width: 2px;
        }
        QSplitter::handle:hover {
            background-color: #555;
        }
        QScrollBar:vertical {
            background-color: #111;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background-color: #333;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #555;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
    """ + STYLES['tooltip'])


# ── Minimalist Settings Dialog ─────────────────────────────────────

class SettingsDialog(QDialog):
    """Global settings dialog with minimal layout and styling."""

    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        self.config = current_config
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Cache Folder
        layout.addWidget(self._create_path_row(
            "Model Cache:",
            self.config.get('system', {}).get('cache_dir', 'E:\\cacheAI'),
            'cache',
            "Model caches"
        ))

        # CKPT Folder
        layout.addWidget(self._create_path_row(
            "Checkpoints:",
            self.config.get('system', {}).get('ckpt_dir', 'E:\\cacheAI'),
            'ckpt',
            "Model weights"
        ))

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #fff;
                border: none;
                border-radius: 2px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton#cancel {
                background-color: #333;
                color: #999;
            }
            QPushButton#cancel:hover { background-color: #444; }
        """)
        buttons.button(QDialogButtonBox.Cancel).setObjectName("cancel")
        buttons.accepted.connect(self._save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)

        self.setStyleSheet("background-color: #111;")

    def _create_path_row(self, label_text, default_value, attr_suffix, tooltip_text):
        frame = QFrame()
        frame.setObjectName("settingsCard")
        frame.setStyleSheet(STYLES['settings_card'])
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setMinimumWidth(90)
        label.setToolTip(tooltip_text)
        layout.addWidget(label)

        edit = QLineEdit(default_value)
        edit.setStyleSheet(STYLES['line_edit'])
        edit.setToolTip(tooltip_text)
        layout.addWidget(edit)
        
        btn = QPushButton("...")
        btn.setStyleSheet(STYLES['button_secondary'])
        btn.setMaximumWidth(30)
        btn.setMinimumWidth(30)
        
        if attr_suffix == 'cache':
            btn.clicked.connect(lambda: self._browse(edit))
        elif attr_suffix == 'ckpt':
            btn.clicked.connect(lambda: self._browse(edit, "Select Checkpoint Directory"))
        else:
            btn.clicked.connect(lambda: self._browse(edit, "Select Git Repo Directory"))

        layout.addWidget(btn)

        setattr(self, f'{attr_suffix}_edit', edit)
        return frame

    def _browse(self, line_edit, title="Select Directory"):
        folder = QFileDialog.getExistingDirectory(self, title)
        if folder:
            line_edit.setText(folder)

    def _save_settings(self):
        self.config['system']['cache_dir'] = self.cache_edit.text()
        self.config['system']['ckpt_dir'] = self.ckpt_edit.text()
        try:
            save_config(self.config)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save config:\n{e}")


# ── Minimalist Settings Widget Builders ────────────────────────────

class SettingWidget:
    """Container for a setting's UI elements and metadata."""
    def __init__(self, setting_id, widget, value_label=None, default=None, step=None):
        self.id = setting_id
        self.widget = widget
        self.value_label = value_label
        self.default = default
        self.step = step

    def get_value(self):
        if isinstance(self.widget, QSlider):
            # If step >= 1, we didn't multiply by 10, so return raw int
            if self.step and self.step >= 1:
                return self.widget.value()
            else:
                return self.widget.value() / 10.0
        elif isinstance(self.widget, QComboBox):
            return self.widget.currentText()
        elif isinstance(self.widget, QLineEdit):
            return self.widget.text()
        elif isinstance(self.widget, (QSpinBox, QDoubleSpinBox)):
            return self.widget.value()
        return None

    def set_value(self, value):
        if isinstance(self.widget, QSlider):
            if self.step and self.step >= 1:
                self.widget.setValue(int(value))
            else:
                self.widget.setValue(int(float(value) * 10))
            if self.value_label:
                self.value_label.setText(self._format_value(value))
        elif isinstance(self.widget, QComboBox):
            idx = self.widget.findText(str(value))
            if idx >= 0:
                self.widget.setCurrentIndex(idx)
        elif isinstance(self.widget, QLineEdit):
            self.widget.setText(str(value))
        elif isinstance(self.widget, (QSpinBox, QDoubleSpinBox)):
            self.widget.setValue(float(value))

    def _format_value(self, value):
        if self.step and self.step >= 1:
            return str(int(value))
        return f"{float(value):.1f}"

    def reset_to_default(self):
        if self.default is not None:
            self.set_value(self.default)


def build_settings_widgets(schema, layout, settings_widgets: dict, saved_values: dict = None):
    """Build UI widgets for a settings schema, grouped by category."""
    
    # Group schema items by category
    categories = {}
    uncategorized = []
    
    for item in schema:
        cat = item.get('category')
        if cat:
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        else:
            uncategorized.append(item)
    
    # Build categorized sections first
    for cat_name, items in categories.items():
        # Category header - simplified
        cat_header = QLabel(cat_name)
        cat_header.setStyleSheet(
            "color: #666; font-size: 10px; padding: 4px 0 2px 0;"
        )
        layout.addWidget(cat_header)
        
        # Build each setting in this category
        for item in items:
            _build_single_setting(item, layout, settings_widgets, saved_values)
    
    # Build uncategorized items (no header)
    for item in uncategorized:
        _build_single_setting(item, layout, settings_widgets, saved_values)


def _build_single_setting(item, layout, settings_widgets: dict, saved_values: dict):
    """Build a single setting widget and add it to the layout."""
    setting_id = item['id']
    label = item.get('label', setting_id)
    description = item.get('description', '')
    default = item.get('default')
    saved_value = saved_values.get(setting_id, default) if saved_values else default
    
    # Create setting card frame - simplified
    card = QFrame()
    card.setObjectName("settingsCard")
    card.setStyleSheet(STYLES['settings_card'])
    card_layout = QHBoxLayout(card)
    card_layout.setContentsMargins(6, 4, 6, 4)
    card_layout.setSpacing(6)

    # Label - simplified
    label_widget = QLabel(label)
    label_widget.setMinimumWidth(80)
    if description:
        label_widget.setToolTip(description)
    card_layout.addWidget(label_widget)

    # Build input widget
    if item['type'] == 'slider':
        widget, value_label = _build_slider(item, saved_value)
        card_layout.addWidget(widget)
        card_layout.addWidget(value_label)
        settings_widgets[setting_id] = SettingWidget(
            setting_id, widget, value_label, default, item.get('step')
        )

    elif item['type'] == 'dropdown':
        widget = _build_dropdown(item, saved_value)
        card_layout.addWidget(widget)
        settings_widgets[setting_id] = SettingWidget(
            setting_id, widget, default=default
        )

    elif item['type'] == 'text':
        widget = _build_text_input(item, saved_value)
        card_layout.addWidget(widget)
        settings_widgets[setting_id] = SettingWidget(
            setting_id, widget, default=default
        )

    elif item['type'] == 'spinbox':
        widget = _build_spinbox(item, saved_value)
        card_layout.addWidget(widget)
        settings_widgets[setting_id] = SettingWidget(
            setting_id, widget, default=default
        )

    layout.addWidget(card)


def _build_slider(item, saved_value):
    """Create a minimalist slider with proper step handling."""
    min_val = item.get('min', 0)
    max_val = item.get('max', 100)
    step = item.get('step', 0.1)
    default = item.get('default', min_val)
    value = saved_value if saved_value is not None else default

    # Determine if integer step
    is_int_step = step >= 1

    # Calculate slider scale factor
    if is_int_step:
        scale = 1
        slider_min = int(min_val)
        slider_max = int(max_val)
        slider_val = int(value)
    else:
        scale = 10
        slider_min = int(min_val * scale)
        slider_max = int(max_val * scale)
        slider_val = int(value * scale)

    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(slider_min)
    slider.setMaximum(slider_max)
    slider.setValue(slider_val)
    slider.setStyleSheet(STYLES['slider'])

    # Value label - simplified
    def format_val(v):
        if is_int_step:
            return f"{v}"
        return f"{v / scale:.1f}"

    value_label = QLabel(format_val(slider_val))
    value_label.setStyleSheet("""
        color: #666;
        font-family: 'Consolas', monospace;
        font-size: 10px;
        min-width: 35px;
    """)
    value_label.setAlignment(Qt.AlignCenter)

    def on_change(v):
        value_label.setText(format_val(v))

    slider.valueChanged.connect(on_change)

    return slider, value_label


def _build_dropdown(item, saved_value):
    """Create a minimalist dropdown with styling."""
    combo = QComboBox()
    combo.addItems(item.get('options', []))
    
    if saved_value is not None:
        idx = combo.findText(str(saved_value))
        if idx >= 0:
            combo.setCurrentIndex(idx)
    
    combo.setStyleSheet(STYLES['dropdown'])
    
    if item.get('description'):
        combo.setToolTip(item['description'])
    
    return combo


def _build_text_input(item, saved_value):
    """Create a minimalist text input with styling."""
    edit = QLineEdit(str(saved_value) if saved_value is not None else item.get('default', ''))
    edit.setStyleSheet(STYLES['line_edit'])
    edit.setPlaceholderText(item.get('placeholder', ''))
    
    if item.get('description'):
        edit.setToolTip(item['description'])
    
    return edit


def _build_spinbox(item, saved_value):
    """Create a spinbox for integer values."""
    min_val = item.get('min', 0)
    max_val = item.get('max', 1000)
    step = item.get('step', 1)
    default = item.get('default', min_val)
    value = saved_value if saved_value is not None else default

    if step >= 1:
        spinbox = QSpinBox()
        spinbox.setMinimum(int(min_val))
        spinbox.setMaximum(int(max_val))
        spinbox.setSingleStep(int(step))
        spinbox.setValue(int(value))
    else:
        spinbox = QDoubleSpinBox()
        spinbox.setMinimum(float(min_val))
        spinbox.setMaximum(float(max_val))
        spinbox.setSingleStep(float(step))
        spinbox.setDecimals(1)
        spinbox.setValue(float(value))

    spinbox.setStyleSheet(STYLES['spinbox'])
    return spinbox


def create_reset_button(settings_widgets: dict, parent_layout):
    """Create a reset-to-defaults button."""
    btn = QPushButton("Reset")
    btn.setStyleSheet(STYLES['button_secondary'])
    btn.setMaximumWidth(60)
    
    def reset_all():
        for widget in settings_widgets.values():
            widget.reset_to_default()
    
    btn.clicked.connect(reset_all)
    parent_layout.addWidget(btn, alignment=Qt.AlignRight)
    return btn


def clear_layout(layout):
    """Safely clear a layout and delete all child widgets."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        sub_layout = item.layout()
        if sub_layout:
            clear_layout(sub_layout)