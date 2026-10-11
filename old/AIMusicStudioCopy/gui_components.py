"""Reusable dialog and dynamic-setting widget builders."""
from PySide6.QtWidgets import (QLabel, QLineEdit, QPushButton, QComboBox, QSlider, QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout)
from PySide6.QtCore import Qt
from config import save_config

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent); self.setWindowTitle("Global Settings"); self.setMinimumWidth(450); self.config = current_config
        layout = QVBoxLayout(self)
        
        # Cache Folder
        form = QHBoxLayout(); form.addWidget(QLabel("Model Cache Folder:"))
        self.path_edit = QLineEdit(self.config.get('system', {}).get('cache_dir', 'E:\\cacheAI'))
        browse_btn = QPushButton("Browse..."); browse_btn.clicked.connect(self._browse_folder)
        form.addWidget(self.path_edit); form.addWidget(browse_btn); layout.addLayout(form)
        
        # CKPT Folder
        ckpt_form = QHBoxLayout(); ckpt_form.addWidget(QLabel("HeartMuLa Ckpt Folder:"))
        self.ckpt_edit = QLineEdit(self.config.get('system', {}).get('ckpt_dir', 'E:\\cacheAI'))
        ckpt_browse_btn = QPushButton("Browse..."); ckpt_browse_btn.clicked.connect(self._browse_ckpt_folder)
        ckpt_form.addWidget(self.ckpt_edit); ckpt_form.addWidget(ckpt_browse_btn); layout.addLayout(ckpt_form)

        # HeartMuLa Repo Folder
        repo_form = QHBoxLayout(); repo_form.addWidget(QLabel("HeartMuLa Git Repo Folder:"))
        self.repo_edit = QLineEdit(self.config.get('system', {}).get('heartlib_repo_dir', ''))
        repo_browse_btn = QPushButton("Browse..."); repo_browse_btn.clicked.connect(self._browse_repo_folder)
        repo_form.addWidget(self.repo_edit); repo_form.addWidget(repo_browse_btn); layout.addLayout(repo_form)

        layout.addWidget(QLabel("Note: Changing folders requires an application restart."))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_settings); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        
    def _browse_folder(self): 
        folder = QFileDialog.getExistingDirectory(self, "Select Cache Directory")
        if folder: self.path_edit.setText(folder)
    def _browse_ckpt_folder(self): 
        folder = QFileDialog.getExistingDirectory(self, "Select HeartMuLa Ckpt Directory")
        if folder: self.ckpt_edit.setText(folder)
    def _browse_repo_folder(self): 
        folder = QFileDialog.getExistingDirectory(self, "Select HeartMuLa Git Repo Directory")
        if folder: self.repo_edit.setText(folder)
        
    def _save_settings(self):
        self.config['system']['cache_dir'] = self.path_edit.text()
        self.config['system']['ckpt_dir'] = self.ckpt_edit.text()
        self.config['system']['heartlib_repo_dir'] = self.repo_edit.text()
        try: save_config(self.config); QMessageBox.information(self, "Saved", "Settings saved. Please restart the app."); self.accept()
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not save config: {e}")

def build_settings_widgets(schema, layout, settings_widgets):
    for item in schema:
        layout.addWidget(QLabel(item['label']))
        if item['type'] == 'slider':
            slider = QSlider(Qt.Horizontal); slider.setMinimum(int(item['min'] * 10)); slider.setMaximum(int(item['max'] * 10)); slider.setValue(int(item['default'] * 10))
            val_label = QLabel(str(item['default'])); slider.valueChanged.connect(lambda v, lbl=val_label: lbl.setText(str(v / 10.0)))
            row = QHBoxLayout(); row.addWidget(slider); row.addWidget(val_label); layout.addLayout(row); settings_widgets[item['id']] = (slider, val_label)
        elif item['type'] == 'dropdown':
            combo = QComboBox(); combo.addItems(item['options']); combo.setCurrentText(item['default']); layout.addWidget(combo); settings_widgets[item['id']] = combo
        elif item['type'] == 'text':
            text_edit = QLineEdit(item.get('default', '')); layout.addWidget(text_edit); settings_widgets[item['id']] = text_edit

def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0); widget = item.widget()
        if widget: widget.deleteLater()