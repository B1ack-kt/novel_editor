"""
模型管理对话框 - 管理AI模型预设/自定义
支持：添加预设模型、自定义模型、API密钥管理、测试连接
"""

import json
from typing import List, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit,
    QComboBox, QTextEdit, QLabel, QTabWidget, QWidget,
    QDialogButtonBox, QMessageBox, QInputDialog, QCheckBox,
    QSpinBox, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config.constants import PRESET_MODELS, API_TIMEOUT_DEFAULT
from core.crypto import encrypt_json, decrypt_json


class ModelConfig:
    """模型配置数据类"""
    def __init__(self, id: str = "", name: str = "", api_url: str = "",
                 api_key: str = "", model_type: str = "", parameters: dict = None,
                 category: str = "", is_default: bool = False):
        self.id = id or name
        self.name = name
        self.api_url = api_url
        self.api_key = api_key
        self.model_type = model_type
        self.parameters = parameters or {}
        self.category = category
        self.is_default = is_default

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "api_url": self.api_url, "api_key": self.api_key,
            "model_type": self.model_type, "parameters": self.parameters,
            "category": self.category, "is_default": self.is_default
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelConfig":
        return cls(**{k: data.get(k, "") if k != "parameters" else data.get(k, {})
                      for k in ["id", "name", "api_url", "api_key", "model_type",
                                 "parameters", "category", "is_default"]})


class ModelManagerDialog(QDialog):
    """模型管理对话框"""

    def __init__(self, storage_manager, master_key: bytes, parent=None):
        super().__init__(parent)
        self._storage = storage_manager
        self._master_key = master_key
        self._models: List[ModelConfig] = []
        self._load_models()
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("模型管理")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #FAFAFA; }
            QListWidget { border: 1px solid #DDD; border-radius: 4px; font-size: 13px; }
            QListWidget::item:selected { background-color: #D0E4F7; }
            QLineEdit, QComboBox, QTextEdit, QSpinBox {
                border: 1px solid #DDD; border-radius: 4px; padding: 6px; font-size: 13px;
            }
            QPushButton {
                border: 1px solid #CCC; padding: 6px 16px; border-radius: 4px;
                background-color: #F5F5F5; font-size: 13px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        """)

        layout = QVBoxLayout(self)

        # === 模型列表 + 添加区域 ===
        top_layout = QHBoxLayout()

        # 左侧模型列表
        list_group = QGroupBox("已配置模型")
        list_layout = QVBoxLayout(list_group)
        self._model_list = QListWidget()
        self._model_list.currentRowChanged.connect(self._on_model_selected)
        list_layout.addWidget(self._model_list)
        top_layout.addWidget(list_group, 3)

        # 右侧配置表单
        form_group = QGroupBox("模型配置")
        form_layout = QFormLayout(form_group)

        # 预设/自定义切换
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("-- 自定义 --")
        for name in PRESET_MODELS.keys():
            self._preset_combo.addItem(name)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        form_layout.addRow("预设模型:", self._preset_combo)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("模型显示名称")
        form_layout.addRow("名称:", self._name_input)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("API接口地址")
        form_layout.addRow("API地址:", self._url_input)

        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("输入API密钥")
        form_layout.addRow("API密钥:", self._key_input)

        self._show_key_check = QCheckBox("显示密钥")
        self._show_key_check.toggled.connect(
            lambda checked: self._key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        form_layout.addRow("", self._show_key_check)

        self._category_input = QComboBox()
        self._category_input.setEditable(True)
        self._category_input.addItems(["默认", "情节生成", "润色", "校验", "大纲", "细节"])
        form_layout.addRow("分类:", self._category_input)

        # 参数配置
        param_group = QGroupBox("请求参数")
        param_layout = QFormLayout(param_group)

        self._temp_spin = QSpinBox()
        self._temp_spin.setRange(0, 200)
        self._temp_spin.setValue(70)
        self._temp_spin.setSuffix("%")
        self._temp_spin.setToolTip("temperature * 100")
        param_layout.addRow("Temperature:", self._temp_spin)

        self._max_tokens = QSpinBox()
        self._max_tokens.setRange(100, 32768)
        self._max_tokens.setValue(4096)
        param_layout.addRow("Max Tokens:", self._max_tokens)

        form_layout.addRow(param_group)

        top_layout.addWidget(form_group, 4)
        layout.addLayout(top_layout)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()

        self._add_btn = QPushButton("添加模型")
        self._add_btn.setStyleSheet("background-color: #4CAF50; color: white; border: none;")
        self._add_btn.clicked.connect(self._on_add_model)
        btn_layout.addWidget(self._add_btn)

        self._test_btn = QPushButton("测试连接")
        self._test_btn.setStyleSheet("background-color: #FF9800; color: white; border: none;")
        self._test_btn.clicked.connect(self._on_test_connection)
        btn_layout.addWidget(self._test_btn)

        self._delete_btn = QPushButton("删除模型")
        self._delete_btn.setStyleSheet("background-color: #F44336; color: white; border: none;")
        self._delete_btn.clicked.connect(self._on_delete_model)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        self._export_keys_btn = QPushButton("导出密钥")
        self._export_keys_btn.clicked.connect(self._on_export_keys)
        btn_layout.addWidget(self._export_keys_btn)

        self._import_keys_btn = QPushButton("导入密钥")
        self._import_keys_btn.clicked.connect(self._on_import_keys)
        btn_layout.addWidget(self._import_keys_btn)

        layout.addLayout(btn_layout)

        # 对话框按钮
        dlg_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        dlg_buttons.accepted.connect(self._on_accept)
        dlg_buttons.rejected.connect(self.reject)
        layout.addWidget(dlg_buttons)

        # 刷新列表
        self._refresh_list()

    def _on_preset_changed(self, preset_name: str):
        """预选模型切换"""
        if preset_name in PRESET_MODELS:
            preset = PRESET_MODELS[preset_name]
            self._name_input.setText(preset_name)
            self._url_input.setText(preset.get("api_url", ""))
            # 预设参数
            params = preset.get("parameters", {})
            temp = params.get("temperature", 0.7)
            self._temp_spin.setValue(int(temp * 100))
            self._max_tokens.setValue(params.get("max_tokens", 4096))
        elif preset_name == "-- 自定义 --":
            self._name_input.clear()
            self._url_input.clear()

    def _on_model_selected(self, index: int):
        """选中模型列表中的模型"""
        if index < 0 or index >= len(self._models):
            return
        model = self._models[index]
        self._name_input.setText(model.name)
        self._url_input.setText(model.api_url)
        self._key_input.setText(model.api_key)
        self._category_input.setCurrentText(model.category)
        self._temp_spin.setValue(int(model.parameters.get("temperature", 0.7) * 100))
        self._max_tokens.setValue(model.parameters.get("max_tokens", 4096))

    def _on_add_model(self):
        """添加模型"""
        name = self._name_input.text().strip()
        url = self._url_input.text().strip()
        key = self._key_input.text().strip()

        if not name:
            QMessageBox.warning(self, "提示", "请输入模型名称")
            return

        # 检查重复
        for m in self._models:
            if m.name == name:
                QMessageBox.warning(self, "提示", "已存在同名模型")
                return

        model = ModelConfig(
            name=name,
            api_url=url,
            api_key=key,
            model_type=self._preset_combo.currentText(),
            parameters={
                "temperature": self._temp_spin.value() / 100.0,
                "max_tokens": self._max_tokens.value()
            },
            category=self._category_input.currentText()
        )
        self._models.append(model)
        self._refresh_list()
        self._model_list.setCurrentRow(len(self._models) - 1)

    def _on_delete_model(self):
        """删除模型"""
        index = self._model_list.currentRow()
        if index < 0:
            return
        reply = QMessageBox.question(self, "确认", f"确认删除模型 '{self._models[index].name}'？")
        if reply == QMessageBox.StandardButton.Yes:
            self._models.pop(index)
            self._refresh_list()

    def _on_test_connection(self):
        """测试API连接"""
        url = self._url_input.text().strip()
        key = self._key_input.text().strip()

        if not url:
            QMessageBox.warning(self, "提示", "请输入API地址")
            return

        self._test_btn.setEnabled(False)
        self._test_btn.setText("测试中...")

        try:
            # 发送简单测试请求
            if not HAS_HTTPX:
                QMessageBox.warning(self, "提示", "httpx未安装，无法发送网络请求。\n请运行: pip install httpx")
                self._test_btn.setEnabled(True)
                self._test_btn.setText("测试连接")
                return

            import threading

            def test():
                try:
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                    # 简单GET测试
                    base_url = url.split("/chat")[0] if "/chat" in url else url.split("/completions")[0]
                    resp = httpx.get(base_url, headers=headers, timeout=10.0)
                    QMessageBox.information(self, "测试结果", f"连接成功!\n状态码: {resp.status_code}")
                except Exception as e:
                    QMessageBox.warning(self, "测试结果", f"连接失败: {str(e)}")
                finally:
                    self._test_btn.setEnabled(True)
                    self._test_btn.setText("测试连接")

            threading.Thread(target=test, daemon=True).start()
        except Exception as e:
            self._test_btn.setEnabled(True)
            self._test_btn.setText("测试连接")
            QMessageBox.warning(self, "测试失败", str(e))

    def _on_export_keys(self):
        """导出密钥(加密)"""
        if not self._models:
            QMessageBox.information(self, "提示", "没有可导出的模型")
            return

        # 验证登录密码
        pwd, ok = QInputDialog.getText(
            self, "验证", "请输入登录密码以导出密钥:",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出密钥", "", "密钥文件 (*.key)"
        )
        if not filepath:
            return

        try:
            data = {"models": [m.to_dict() for m in self._models]}
            encrypted = encrypt_json(data, self._master_key)
            with open(filepath, 'wb') as f:
                f.write(encrypted)
            QMessageBox.information(self, "导出成功", "密钥文件已加密保存")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_import_keys(self):
        """导入密钥(解密)"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入密钥", "", "密钥文件 (*.key)"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'rb') as f:
                encrypted = f.read()
            data = decrypt_json(encrypted, self._master_key)
            imported = [ModelConfig.from_dict(m) for m in data.get("models", [])]
            for model in imported:
                if not any(m.name == model.name for m in self._models):
                    self._models.append(model)
            self._refresh_list()
            QMessageBox.information(self, "导入成功", f"导入了 {len(imported)} 个模型")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"密钥文件无效或密码不匹配: {e}")

    def _refresh_list(self):
        """刷新模型列表"""
        self._model_list.clear()
        for model in self._models:
            item = QListWidgetItem(f"{model.name} [{model.category or '默认'}]")
            self._model_list.addItem(item)

    def _load_models(self):
        """从加密存储加载模型配置"""
        try:
            if self._storage.file_exists("api_keys.enc"):
                data = self._storage.read_encrypted("api_keys.enc", self._master_key)
                self._models = [ModelConfig.from_dict(m) for m in data.get("models", [])]
        except Exception:
            self._models = []

    def _save_models(self):
        """保存模型配置到加密存储"""
        data = {"models": [m.to_dict() for m in self._models]}
        self._storage.write_encrypted("api_keys.enc", data)

    def _on_accept(self):
        """确认保存"""
        self._save_models()
        self.accept()

    def get_models(self) -> List[ModelConfig]:
        """获取模型列表"""
        return self._models
