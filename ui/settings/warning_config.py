"""
预警配置对话框 - 自定义预警样式
支持：标记类型(标红/下划线/波浪线)、颜色、透明度、单独关闭某类预警
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPushButton, QLabel, QSlider, QCheckBox,
    QGroupBox, QDialogButtonBox, QWidget, QColorDialog,
    QFrame, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette

from config.constants import WARNING_TYPES, DEFAULT_WARNING_STYLE
from config.settings import SettingsManager


class WarningPreviewWidget(QFrame):
    """预警样式预览"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(60)
        self.setStyleSheet("background-color: white; border: 1px solid #DDD; border-radius: 4px;")

        layout = QVBoxLayout(self)
        self._preview_label = QLabel("示例预警文本：角色的行为与设定存在冲突")
        self._preview_label.setFont(QFont("Microsoft YaHei", 13))
        layout.addWidget(self._preview_label)

    def update_style(self, marker_type: str, color: str, opacity: float):
        """更新预览样式"""
        if marker_type == "underline":
            self._preview_label.setStyleSheet(
                f"text-decoration: underline; text-decoration-color: {color}; "
                f"font-size: 14px; padding: 10px;"
            )
        elif marker_type == "wavy":
            self._preview_label.setStyleSheet(
                f"text-decoration: underline; text-decoration-style: wavy; "
                f"text-decoration-color: {color}; font-size: 14px; padding: 10px;"
                # QSS doesn't fully support wavy, use color approximation
            )
        elif marker_type == "highlight":
            from PyQt6.QtGui import QColor as Qc
            c = Qc(color)
            c.setAlphaF(opacity)
            self._preview_label.setStyleSheet(
                f"background-color: rgba({c.red()},{c.green()},{c.blue()},{c.alphaF()}); "
                f"font-size: 14px; padding: 10px;"
            )


class WarningConfigDialog(QDialog):
    """预警配置对话框"""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self._settings_mgr = settings_manager
        self._settings = settings_manager.settings
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("预警配置 - 样式自定义")
        self.setMinimumSize(550, 500)
        self.setStyleSheet("""
            QDialog { background-color: #FAFAFA; }
            QGroupBox { font-weight: bold; border: 1px solid #DDD; border-radius: 6px;
                        margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

        layout = QVBoxLayout(self)

        # === 预警主动程度 ===
        level_group = QGroupBox("主动程度")
        level_layout = QHBoxLayout(level_group)
        self._level_combo = QComboBox()
        self._level_combo.addItems(["高 - 全场景预警+建议", "中 - 仅预警+章节结尾建议", "低 - 仅手动召唤Agent"])
        level_layout.addWidget(QLabel("预警级别:"))
        level_layout.addWidget(self._level_combo)
        layout.addWidget(level_group)

        # === 预警类型开关 ===
        types_group = QGroupBox("预警类型开关")
        types_layout = QVBoxLayout(types_group)
        self._type_checkboxes = {}
        for wtype, wname in WARNING_TYPES.items():
            cb = QCheckBox(wname)
            cb.setChecked(True)
            types_layout.addWidget(cb)
            self._type_checkboxes[wtype] = cb
        layout.addWidget(types_group)

        # === 样式自定义 ===
        style_group = QGroupBox("样式自定义")
        style_layout = QVBoxLayout(style_group)

        # 标记类型
        marker_layout = QHBoxLayout()
        marker_layout.addWidget(QLabel("标记类型:"))
        self._marker_combo = QComboBox()
        self._marker_combo.addItems(["下划线", "波浪线", "高亮"])
        self._marker_combo.setItemData(0, "underline")
        self._marker_combo.setItemData(1, "wavy")
        self._marker_combo.setItemData(2, "highlight")
        self._marker_combo.currentIndexChanged.connect(self._update_preview)
        marker_layout.addWidget(self._marker_combo)
        marker_layout.addStretch()
        style_layout.addLayout(marker_layout)

        # 颜色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("标记颜色:"))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(30, 30)
        self._color_btn.setStyleSheet("background-color: #FF0000; border: 1px solid #999; border-radius: 4px;")
        self._color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(self._color_btn)
        self._color_label = QLabel("#FF0000")
        color_layout.addWidget(self._color_label)
        color_layout.addStretch()
        style_layout.addLayout(color_layout)

        # 透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(50)
        self._opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._opacity_slider.valueChanged.connect(self._update_preview)
        opacity_layout.addWidget(self._opacity_slider)
        self._opacity_label = QLabel("50%")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        opacity_layout.addWidget(self._opacity_label)
        style_layout.addLayout(opacity_layout)

        # 预览
        style_layout.addWidget(QLabel("实时预览:"))
        self._preview = WarningPreviewWidget()
        style_layout.addWidget(self._preview)

        layout.addWidget(style_group)

        # === 按钮 ===
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )
        layout.addWidget(buttons)

        self._current_color = "#FF0000"

    def _pick_color(self):
        """选择颜色"""
        color = QColorDialog.getColor(QColor(self._current_color), self)
        if color.isValid():
            self._current_color = color.name()
            self._color_btn.setStyleSheet(
                f"background-color: {self._current_color}; border: 1px solid #999; border-radius: 4px;"
            )
            self._color_label.setText(self._current_color)
            self._update_preview()

    def _update_preview(self):
        """更新预览"""
        marker = self._marker_combo.currentData()
        opacity = self._opacity_slider.value() / 100.0
        self._preview.update_style(marker, self._current_color, opacity)

    def _load_current_settings(self):
        """加载当前设置"""
        ws = self._settings.warning_style
        # 标记类型
        marker_map = {"underline": 0, "wavy": 1, "highlight": 2}
        self._marker_combo.setCurrentIndex(marker_map.get(ws.get("marker_type", "underline"), 0))

        # 颜色
        self._current_color = ws.get("color", "#FF0000")
        self._color_btn.setStyleSheet(
            f"background-color: {self._current_color}; border: 1px solid #999; border-radius: 4px;"
        )
        self._color_label.setText(self._current_color)

        # 透明度
        opacity = int(ws.get("opacity", 0.5) * 100)
        self._opacity_slider.setValue(opacity)
        self._opacity_label.setText(f"{opacity}%")

        # 预警类型
        enabled_types = self._settings.enabled_warning_types
        for wtype, cb in self._type_checkboxes.items():
            cb.setChecked(wtype in enabled_types)

        # 主动程度
        level_map = {"high": 0, "medium": 1, "low": 2}
        self._level_combo.setCurrentIndex(
            level_map.get(self._settings.warning_aggressiveness, 0)
        )

        self._update_preview()

    def _restore_defaults(self):
        """恢复默认设置"""
        ds = DEFAULT_WARNING_STYLE
        marker_map = {"underline": 0, "wavy": 1, "highlight": 2}
        self._marker_combo.setCurrentIndex(marker_map.get(ds["marker_type"], 0))
        self._current_color = ds["color"]
        self._color_btn.setStyleSheet(
            f"background-color: {self._current_color}; border: 1px solid #999; border-radius: 4px;"
        )
        self._color_label.setText(self._current_color)
        self._opacity_slider.setValue(int(ds["opacity"] * 100))
        for cb in self._type_checkboxes.values():
            cb.setChecked(True)
        self._level_combo.setCurrentIndex(0)
        self._update_preview()

    def _on_accept(self):
        """保存设置"""
        ws = {
            "marker_type": self._marker_combo.currentData(),
            "color": self._current_color,
            "opacity": self._opacity_slider.value() / 100.0
        }
        enabled_types = [
            wtype for wtype, cb in self._type_checkboxes.items() if cb.isChecked()
        ]
        level_map = {0: "high", 1: "medium", 2: "low"}

        self._settings_mgr.update_settings(
            warning_style=ws,
            enabled_warning_types=enabled_types,
            warning_aggressiveness=level_map[self._level_combo.currentIndex()]
        )
        self.accept()

    def get_settings(self):
        """获取当前设置（供外部使用）"""
        return self._settings_mgr.settings
