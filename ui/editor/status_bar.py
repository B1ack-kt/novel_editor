"""
编辑器底部状态栏
显示：章节字数、全书总字数、备份状态、API调用状态
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QMenu, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from utils.word_counter import WordCounter
from config.constants import WORD_COUNT_RULES


class StatusBar(QWidget):
    """编辑器底部状态栏"""

    # 信号
    word_count_rule_changed = pyqtSignal(str)    # 字数统计规则切换
    backup_now_clicked = pyqtSignal()            # 手动备份
    offline_mode_toggled = pyqtSignal(bool)      # 离线模式切换

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_rule = "include_all"
        self._backup_timer = QTimer()
        self._backup_timer.timeout.connect(self._update_backup_time)

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)

        # === 字数统计（左侧） ===
        self._word_count_label = QLabel("0 字")
        self._word_count_label.setFont(QFont("Microsoft YaHei", 10))
        self._word_count_label.setToolTip("点击切换统计规则")
        self._word_count_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._word_count_label.mousePressEvent = self._on_word_count_click
        layout.addWidget(self._word_count_label)

        layout.addStretch()

        # === 备份状态（中间） ===
        self._backup_label = QLabel("上次备份: 暂无")
        self._backup_label.setFont(QFont("Microsoft YaHei", 9))
        self._backup_label.setStyleSheet("color: #888;")
        layout.addWidget(self._backup_label)

        layout.addSpacing(15)

        # === API状态（右侧） ===
        self._api_status_label = QLabel("API: 未连接")
        self._api_status_label.setFont(QFont("Microsoft YaHei", 9))
        self._api_status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._api_status_label)

        layout.addSpacing(10)

        # === 离线模式指示 ===
        self._offline_btn = QPushButton("在线")
        self._offline_btn.setCheckable(True)
        self._offline_btn.setFixedWidth(50)
        self._offline_btn.setToolTip("切换离线模式")
        self._offline_btn.toggled.connect(self._on_offline_toggled)
        self._offline_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 2px 8px;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #F44336;
            }
        """)
        layout.addWidget(self._offline_btn)

    def _on_word_count_click(self, event):
        """点击字数标签切换统计规则"""
        menu = QMenu(self)
        for rule_key, rule_name in WORD_COUNT_RULES.items():
            action = menu.addAction(rule_name)
            action.setCheckable(True)
            action.setChecked(rule_key == self._current_rule)
            action.triggered.connect(
                lambda checked, r=rule_key: self._switch_rule(r)
            )
        menu.exec(self._word_count_label.mapToGlobal(
            self._word_count_label.rect().bottomLeft()
        ))

    def _switch_rule(self, rule: str):
        """切换统计规则"""
        self._current_rule = rule
        self.word_count_rule_changed.emit(rule)

    def _on_offline_toggled(self, checked: bool):
        """离线模式切换"""
        if checked:
            self._offline_btn.setText("离线")
        else:
            self._offline_btn.setText("在线")
        self.offline_mode_toggled.emit(checked)

    def _update_backup_time(self):
        """更新备份时间显示"""
        import time
        self._backup_label.setText(
            f"上次备份: {time.strftime('%H:%M:%S')}"
        )

    # ========== 公共接口 ==========

    def update_word_count(self, chapter_count: int, total_count: int, selected_count: int = 0):
        """更新字数显示"""
        rule_display = WordCounter.get_rule_display(self._current_rule)
        parts = [f"本章: {WordCounter.format_count(chapter_count)}"]
        if selected_count > 0:
            parts.append(f"选中: {WordCounter.format_count(selected_count)}")
        parts.append(f"全书: {WordCounter.format_count(total_count)}")
        parts.append(f"[{rule_display}]")
        self._word_count_label.setText(" | ".join(parts))

    def update_backup_status(self, last_backup_time: str = "", is_backing_up: bool = False):
        """更新备份状态"""
        if is_backing_up:
            self._backup_label.setText("正在备份...")
            self._backup_label.setStyleSheet("color: #FF9800;")
        elif last_backup_time:
            self._backup_label.setText(f"上次备份: {last_backup_time}")
            self._backup_label.setStyleSheet("color: #888;")
            self._backup_timer.start(60000)  # 每分钟更新
        else:
            self._backup_label.setText("上次备份: 暂无")
            self._backup_label.setStyleSheet("color: #888;")

    def update_api_status(self, status: str, model_name: str = "", remaining: str = ""):
        """更新API调用状态
        Args:
            status: "success" / "error" / "calling" / "idle"
            model_name: 当前模型名
            remaining: 剩余额度信息
        """
        if status == "calling":
            self._api_status_label.setText(f"API: 调用中... ({model_name})")
            self._api_status_label.setStyleSheet("color: #FF9800;")
        elif status == "success":
            self._api_status_label.setText(f"API: 成功 ({model_name}) {remaining}")
            self._api_status_label.setStyleSheet("color: #4CAF50;")
        elif status == "error":
            self._api_status_label.setText(f"API: 失败 ({model_name})")
            self._api_status_label.setStyleSheet("color: #F44336;")
        else:
            self._api_status_label.setText(f"API: {model_name or '未连接'}")
            self._api_status_label.setStyleSheet("color: #888;")

    def set_offline_mode(self, offline: bool):
        """设置离线模式"""
        self._offline_btn.setChecked(offline)

    def get_current_rule(self) -> str:
        """获取当前字数统计规则"""
        return self._current_rule
