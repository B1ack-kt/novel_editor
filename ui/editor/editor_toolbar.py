"""
编辑器顶部工具栏
提供：编辑模式切换、模型切换、Agent按钮、格式工具栏
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolBar,
    QPushButton, QComboBox, QLabel, QSpinBox,
    QFontComboBox, QColorDialog, QMenu, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QAction, QIcon, QFont


class EditorToolbar(QWidget):
    """编辑器顶部工具栏"""

    # 信号
    mode_changed = pyqtSignal(str)       # richtext / markdown
    model_switched = pyqtSignal(str)     # 模型ID
    agent_triggered = pyqtSignal(str)    # Agent功能名称
    font_changed = pyqtSignal(str)       # 字体名
    font_size_changed = pyqtSignal(int)  # 字号
    color_changed = pyqtSignal(QColor)   # 颜色
    indent_changed = pyqtSignal(int)     # 缩进
    spacing_changed = pyqtSignal(float)  # 行距

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # === 编辑模式切换 ===
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["富文本模式", "Markdown模式"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(QLabel("模式:"))
        layout.addWidget(self._mode_combo)

        layout.addSpacing(10)

        # === 字体选择 ===
        layout.addWidget(QLabel("字体:"))
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont("Microsoft YaHei"))
        self._font_combo.currentFontChanged.connect(
            lambda f: self.font_changed.emit(f.family())
        )
        layout.addWidget(self._font_combo)

        # === 字号 ===
        layout.addWidget(QLabel("字号:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(10, 24)
        self._font_size_spin.setValue(14)
        self._font_size_spin.valueChanged.connect(self.font_size_changed)
        layout.addWidget(self._font_size_spin)

        # === 文字颜色 ===
        self._color_btn = QPushButton("A")
        self._color_btn.setStyleSheet("font-weight: bold; color: #CC0000;")
        self._color_btn.setToolTip("文字颜色")
        self._color_btn.clicked.connect(self._pick_color)
        layout.addWidget(self._color_btn)

        layout.addSpacing(10)

        # === 段落格式 ===
        layout.addWidget(QLabel("缩进:"))
        self._indent_spin = QSpinBox()
        self._indent_spin.setRange(0, 8)
        self._indent_spin.setValue(2)
        self._indent_spin.setSuffix("字符")
        self._indent_spin.valueChanged.connect(self.indent_changed)
        layout.addWidget(self._indent_spin)

        layout.addWidget(QLabel("行距:"))
        self._spacing_combo = QComboBox()
        self._spacing_combo.addItems(["1.0", "1.5", "1.8", "2.0", "2.5"])
        self._spacing_combo.setCurrentText("1.8")
        self._spacing_combo.currentTextChanged.connect(
            lambda s: self.spacing_changed.emit(float(s))
        )
        layout.addWidget(self._spacing_combo)

        layout.addStretch()

        # === 模型切换 ===
        layout.addWidget(QLabel("模型:"))
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(150)
        self._model_combo.addItem("未配置模型")
        self._model_combo.currentIndexChanged.connect(
            lambda: self.model_switched.emit(self._model_combo.currentData())
        )
        layout.addWidget(self._model_combo)

        # === Agent按钮 ===
        self._agent_btn = QPushButton("Agent ▾")
        self._agent_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        self._agent_btn.clicked.connect(self._show_agent_menu)
        layout.addWidget(self._agent_btn)

    def _on_mode_changed(self, index: int):
        """编辑模式切换"""
        if index == 0:
            self.mode_changed.emit("richtext")
        else:
            self.mode_changed.emit("markdown")

    def _pick_color(self):
        """选择文字颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            self._color_btn.setStyleSheet(
                f"font-weight: bold; color: {color.name()};"
            )
            self.color_changed.emit(color)

    def _show_agent_menu(self):
        """显示Agent功能菜单"""
        menu = QMenu(self)
        actions = [
            ("情节生成", "plot_generate"),
            ("文本润色", "polish"),
            ("设定校验", "check_settings"),
            ("生成大纲", "outline"),
            ("填充细节", "fill_details"),
        ]
        for name, action_id in actions:
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, a=action_id: self.agent_triggered.emit(a))
        menu.exec(self._agent_btn.mapToGlobal(self._agent_btn.rect().bottomLeft()))

    # ========== 公共接口 ==========

    def update_models(self, models: list):
        """更新模型列表
        Args:
            models: [(model_id, model_name), ...]
        """
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for model_id, model_name in models:
            self._model_combo.addItem(model_name, model_id)
        if not models:
            self._model_combo.addItem("未配置模型")
        self._model_combo.blockSignals(False)

    def set_mode(self, mode: str):
        """设置编辑模式"""
        if mode == "richtext":
            self._mode_combo.setCurrentIndex(0)
        else:
            self._mode_combo.setCurrentIndex(1)

    def get_mode(self) -> str:
        """获取当前编辑模式"""
        return "richtext" if self._mode_combo.currentIndex() == 0 else "markdown"

    def get_current_model_id(self) -> str:
        """获取当前选中的模型ID"""
        return self._model_combo.currentData() or ""

    def set_agent_enabled(self, enabled: bool):
        """设置Agent按钮启用状态"""
        self._agent_btn.setEnabled(enabled)

    def set_visual_only(self, mode: str):
        """仅显示模式相关控件(精简模式)"""
        if mode == "richtext":
            self._font_combo.show()
            self._font_size_spin.show()
            self._color_btn.show()
            self._indent_spin.show()
            self._spacing_combo.show()
        else:
            self._font_combo.hide()
            self._font_size_spin.hide()
            self._color_btn.hide()
            self._indent_spin.hide()
            self._spacing_combo.hide()
