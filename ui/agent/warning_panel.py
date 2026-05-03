"""
预警面板 - 编辑区右侧预警图标与详情展示
支持：预警类型图标、点击展开详情、忽略/白名单操作
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QFrame, QListWidget,
    QListWidgetItem, QMenu, QSizePolicy,
    QToolButton, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

from config.constants import WARNING_TYPES


class WarningItemWidget(QFrame):
    """单个预警条目"""

    ignore_clicked = pyqtSignal(str)       # warning_id
    whitelist_clicked = pyqtSignal(str)    # warning_id
    suggestion_clicked = pyqtSignal(str, int)  # warning_id, suggestion_index

    def __init__(self, warning_data: dict, parent=None):
        super().__init__(parent)
        self._warning_id = warning_data.get("id", "")
        self._suggestions = warning_data.get("suggestions", [])
        self._setup_ui(warning_data)

    def _setup_ui(self, data: dict):
        """设置UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            WarningItemWidget {
                background-color: #FFF8E1;
                border: 1px solid #FFE082;
                border-radius: 6px;
                padding: 8px;
                margin: 3px 0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # 类型标签
        wtype = data.get("warning_type", "")
        type_display = WARNING_TYPES.get(wtype, wtype)
        severity = data.get("severity", "medium")

        header = QHBoxLayout()
        severity_icon = {"high": "!", "medium": "", "low": "i"}.get(severity, "")
        severity_color = {"high": "#F44336", "medium": "#FF9800", "low": "#2196F3"}.get(severity, "#888")

        type_label = QLabel(f"{severity_icon} {type_display}")
        type_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        type_label.setStyleSheet(f"color: {severity_color};")
        header.addWidget(type_label)
        header.addStretch()

        # 操作按钮
        ignore_btn = QToolButton()
        ignore_btn.setText("忽略")
        ignore_btn.setToolTip("忽略此预警")
        ignore_btn.clicked.connect(lambda: self.ignore_clicked.emit(self._warning_id))
        header.addWidget(ignore_btn)

        whitelist_btn = QToolButton()
        whitelist_btn.setText("白名单")
        whitelist_btn.setToolTip("添加到白名单")
        whitelist_btn.clicked.connect(lambda: self.whitelist_clicked.emit(self._warning_id))
        header.addWidget(whitelist_btn)

        for btn in [ignore_btn, whitelist_btn]:
            btn.setStyleSheet("""
                QToolButton {
                    border: 1px solid #DDD;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QToolButton:hover {
                    background-color: #EEE;
                }
            """)

        layout.addLayout(header)

        # 冲突描述
        desc = data.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; font-size: 12px;")
            layout.addWidget(desc_label)

        # 建议列表
        if self._suggestions:
            sugg_label = QLabel("调整建议:")
            sugg_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
            layout.addWidget(sugg_label)

            for i, sugg in enumerate(self._suggestions):
                sugg_text = sugg.get("text", str(sugg))
                btn = QPushButton(f"  {i+1}. {sugg_text}")
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        border: none;
                        background: transparent;
                        color: #1565C0;
                        font-size: 11px;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        background-color: #E3F2FD;
                        border-radius: 3px;
                    }
                """)
                btn.clicked.connect(
                    lambda checked, idx=i: self.suggestion_clicked.emit(self._warning_id, idx)
                )
                layout.addWidget(btn)


class WarningPanel(QWidget):
    """预警面板 - 右侧边栏"""

    warning_ignored = pyqtSignal(str)
    warning_whitelisted = pyqtSignal(str)
    suggestion_applied = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._warnings: list = []
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题
        title_layout = QHBoxLayout()
        title = QLabel("创作预警")
        title.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #333;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        # 批量操作
        batch_btn = QToolButton()
        batch_btn.setText("批量")
        batch_btn.setToolTip("批量处理预警")
        batch_btn.clicked.connect(self._on_batch_action)
        title_layout.addWidget(batch_btn)

        layout.addLayout(title_layout)

        # 统计
        self._count_label = QLabel("共 0 条预警")
        self._count_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._count_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self._warning_container = QWidget()
        self._warning_layout = QVBoxLayout(self._warning_container)
        self._warning_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._warning_layout.addStretch()
        scroll.setWidget(self._warning_container)

        layout.addWidget(scroll)

        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

    def set_warnings(self, warnings: list):
        """设置预警列表

        Args:
            warnings: Warning对象列表(或字典列表)
        """
        self._warnings = warnings

        # 清除旧widget
        while self._warning_layout.count() > 1:
            item = self._warning_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for w in warnings:
            wdata = w.to_dict() if hasattr(w, 'to_dict') else w
            item_widget = WarningItemWidget(wdata)
            item_widget.ignore_clicked.connect(self.warning_ignored)
            item_widget.whitelist_clicked.connect(self.warning_whitelisted)
            item_widget.suggestion_clicked.connect(self.suggestion_applied)
            self._warning_layout.insertWidget(self._warning_layout.count() - 1, item_widget)

        self._count_label.setText(f"共 {len(warnings)} 条预警")

    def clear_warnings(self):
        """清空预警"""
        self.set_warnings([])

    def add_warning(self, warning):
        """添加单条预警"""
        self._warnings.append(warning)
        self.set_warnings(self._warnings)

    def _on_batch_action(self):
        """批量操作"""
        menu = QMenu(self)
        menu.addAction("全部忽略").triggered.connect(self._ignore_all)
        menu.addAction("全部加入白名单").triggered.connect(self._whitelist_all)
        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))

    def _ignore_all(self):
        """全部忽略"""
        for w in self._warnings:
            wid = w.id if hasattr(w, 'id') else w.get("id", "")
            self.warning_ignored.emit(wid)
        self.clear_warnings()

    def _whitelist_all(self):
        """全部加入白名单"""
        for w in self._warnings:
            wid = w.id if hasattr(w, 'id') else w.get("id", "")
            self.warning_whitelisted.emit(wid)
        self.clear_warnings()
