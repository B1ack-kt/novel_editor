"""
建议栏 - 编辑区底部可折叠的建议面板
Agent主动建议显示区域，支持折叠/展开
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QToolButton,
    QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor


class SuggestionItem(QFrame):
    """单条建议"""

    accept_clicked = pyqtSignal(str)       # 建议文本
    more_clicked = pyqtSignal(str)         # 建议ID

    def __init__(self, category: str, text: str, suggestion_id: str = "", parent=None):
        super().__init__(parent)
        self._text = text
        self._suggestion_id = suggestion_id
        self._setup_ui(category)

    def _setup_ui(self, category: str):
        """设置UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            SuggestionItem {
                background-color: #F3F8FF;
                border: 1px solid #BBDEFB;
                border-radius: 6px;
                padding: 6px;
                margin: 2px 0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # 分类标签
        cat_label = QLabel(f"[{category}]")
        cat_label.setStyleSheet("color: #1565C0; font-size: 10px; font-weight: bold;")
        layout.addWidget(cat_label)

        # 建议文本
        text_label = QLabel(self._text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("color: #333; font-size: 12px;")
        layout.addWidget(text_label)

        # 操作按钮
        btn_layout = QHBoxLayout()

        accept_btn = QPushButton("插入文本")
        accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
        """)
        accept_btn.clicked.connect(lambda: self.accept_clicked.emit(self._text))
        btn_layout.addWidget(accept_btn)

        more_btn = QPushButton("更多版本")
        more_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1565C0;
                border: 1px solid #BBDEFB;
                padding: 4px 12px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #E3F2FD;
            }
        """)
        more_btn.clicked.connect(lambda: self.more_clicked.emit(self._suggestion_id))
        btn_layout.addWidget(more_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class SuggestionBar(QWidget):
    """底部建议栏 - 可折叠"""

    suggestion_accepted = pyqtSignal(str)       # 建议文本
    collapsed = pyqtSignal(bool)               # 折叠状态变化

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_collapsed = False
        self._new_suggestions = False
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setMaximumHeight(300)  # 不超过编辑区1/3

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # 标题栏(可点击折叠)
        title_bar = QHBoxLayout()

        self._title_label = QLabel("Agent建议")
        self._title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #333;")
        title_bar.addWidget(self._title_label)

        # 小红点(有新建议时亮起)
        self._new_dot = QLabel("●")
        self._new_dot.setStyleSheet("color: #F44336; font-size: 14px;")
        self._new_dot.hide()
        title_bar.addWidget(self._new_dot)

        title_bar.addStretch()

        # 折叠按钮
        self._collapse_btn = QToolButton()
        self._collapse_btn.setText("—")
        self._collapse_btn.setToolTip("收起建议栏")
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        self._collapse_btn.setStyleSheet("""
            QToolButton {
                border: none;
                font-size: 16px;
                font-weight: bold;
                color: #888;
            }
            QToolButton:hover {
                color: #333;
            }
        """)
        title_bar.addWidget(self._collapse_btn)

        layout.addLayout(title_bar)

        # 建议列表滚动区
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._suggestion_container = QWidget()
        self._suggestion_layout = QVBoxLayout(self._suggestion_container)
        self._suggestion_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._suggestion_layout.addStretch()
        self._scroll.setWidget(self._suggestion_container)

        layout.addWidget(self._scroll)

    def set_suggestions(self, suggestions: list):
        """
        设置建议列表

        Args:
            suggestions: [{"category": "情节分支", "text": "...", "id": "..."}, ...]
        """
        # 清除旧建议
        while self._suggestion_layout.count() > 1:
            item = self._suggestion_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for sugg in suggestions:
            item_widget = SuggestionItem(
                category=sugg.get("category", ""),
                text=sugg.get("text", ""),
                suggestion_id=sugg.get("id", "")
            )
            item_widget.accept_clicked.connect(self.suggestion_accepted)
            self._suggestion_layout.insertWidget(
                self._suggestion_layout.count() - 1, item_widget
            )

        # 显示新建议红点
        if suggestions:
            self._new_suggestions = True
            if self._is_collapsed:
                self._new_dot.show()

    def _toggle_collapse(self):
        """切换折叠/展开"""
        self._is_collapsed = not self._is_collapsed

        if self._is_collapsed:
            self._scroll.hide()
            self._collapse_btn.setText("+")
            self._collapse_btn.setToolTip("展开建议栏")
            self.setMaximumHeight(35)
        else:
            self._scroll.show()
            self._collapse_btn.setText("—")
            self._collapse_btn.setToolTip("收起建议栏")
            self.setMaximumHeight(300)
            self._new_dot.hide()
            self._new_suggestions = False

        self.collapsed.emit(self._is_collapsed)

    def clear(self):
        """清空建议"""
        self.set_suggestions([])

    def is_collapsed(self) -> bool:
        return self._is_collapsed
