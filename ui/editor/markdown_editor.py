"""
Markdown编辑器 - 支持Markdown编辑与实时预览
提供：标题、加粗、斜体、引用、列表、分割线、链接、图片等语法
双模式：富文本/Markdown一键切换，内容实时同步
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QTextBrowser, QPushButton, QToolBar,
    QLabel, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QRegularExpression
from PyQt6.QtGui import (
    QFont, QTextCursor, QTextCharFormat, QColor,
    QAction, QKeySequence, QDesktopServices
)

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


class MarkdownEditorPanel(QWidget):
    """
    Markdown编辑器面板
    左侧编辑区 + 右侧实时预览 + 工具栏
    """

    content_changed = pyqtSignal(str)  # 内容变化(纯文本)
    selection_changed = pyqtSignal(int, int)  # 选中位置变化

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_toolbar_actions()
        self._connect_signals()

    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        self._setup_toolbar()
        layout.addWidget(self._toolbar)

        # 分割编辑区和预览区
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧 - 编辑区
        self._editor = QTextEdit()
        self._editor.setFont(QFont("Consolas", 13))
        self._editor.setStyleSheet("""
            QTextEdit {
                padding: 15px;
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                selection-background-color: #264F78;
            }
        """)
        self._editor.setPlaceholderText("在此输入Markdown内容...\n\n# 一级标题\n## 二级标题\n**加粗文字** *斜体文字*\n\n> 引用文字\n\n- 列表项\n\n---分割线---")
        self._splitter.addWidget(self._editor)

        # 右侧 - 预览区
        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(True)
        self._preview.setStyleSheet("""
            QTextBrowser {
                padding: 15px;
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
            }
        """)
        self._splitter.addWidget(self._preview)

        # 默认比例 60:40
        self._splitter.setSizes([600, 400])

        layout.addWidget(self._splitter)

        # 预览模式切换
        mode_layout = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["分屏预览", "纯编辑", "纯预览"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addStretch()
        mode_layout.addWidget(QLabel("模式:"))
        mode_layout.addWidget(self._mode_combo)
        layout.addLayout(mode_layout)

    def _setup_toolbar(self):
        """设置Markdown工具栏"""
        self._toolbar = QToolBar()

        # 标题按钮
        self._btn_h1 = QPushButton("H1")
        self._btn_h1.setToolTip("一级标题 (Ctrl+1)")
        self._btn_h1.clicked.connect(lambda: self._insert_header(1))
        self._toolbar.addWidget(self._btn_h1)

        self._btn_h2 = QPushButton("H2")
        self._btn_h2.setToolTip("二级标题 (Ctrl+2)")
        self._btn_h2.clicked.connect(lambda: self._insert_header(2))
        self._toolbar.addWidget(self._btn_h2)

        self._btn_h3 = QPushButton("H3")
        self._btn_h3.setToolTip("三级标题 (Ctrl+3)")
        self._btn_h3.clicked.connect(lambda: self._insert_header(3))
        self._toolbar.addWidget(self._btn_h3)

        self._toolbar.addSeparator()

        # 格式按钮
        self._btn_bold = QPushButton("B")
        self._btn_bold.setStyleSheet("font-weight: bold;")
        self._btn_bold.setToolTip("加粗 (Ctrl+B)")
        self._btn_bold.clicked.connect(lambda: self._wrap_selection("**", "**"))
        self._toolbar.addWidget(self._btn_bold)

        self._btn_italic = QPushButton("I")
        self._btn_italic.setStyleSheet("font-style: italic;")
        self._btn_italic.setToolTip("斜体 (Ctrl+I)")
        self._btn_italic.clicked.connect(lambda: self._wrap_selection("*", "*"))
        self._toolbar.addWidget(self._btn_italic)

        self._btn_strikethrough = QPushButton("S")
        self._btn_strikethrough.setToolTip("删除线")
        self._btn_strikethrough.clicked.connect(lambda: self._wrap_selection("~~", "~~"))
        self._toolbar.addWidget(self._btn_strikethrough)

        self._toolbar.addSeparator()

        # 插入元素按钮
        self._btn_quote = QPushButton('"')
        self._btn_quote.setToolTip("引用")
        self._btn_quote.clicked.connect(self._insert_quote)
        self._toolbar.addWidget(self._btn_quote)

        self._btn_ul = QPushButton("•")
        self._btn_ul.setToolTip("无序列表")
        self._btn_ul.clicked.connect(self._insert_unordered_list)
        self._toolbar.addWidget(self._btn_ul)

        self._btn_ol = QPushButton("1.")
        self._btn_ol.setToolTip("有序列表")
        self._btn_ol.clicked.connect(self._insert_ordered_list)
        self._toolbar.addWidget(self._btn_ol)

        self._btn_hr = QPushButton("—")
        self._btn_hr.setToolTip("分割线")
        self._btn_hr.clicked.connect(self._insert_horizontal_rule)
        self._toolbar.addWidget(self._btn_hr)

        self._toolbar.addSeparator()

        # 链接/图片按钮
        self._btn_link = QPushButton("链接")
        self._btn_link.setToolTip("插入链接 (Ctrl+L)")
        self._btn_link.clicked.connect(self._insert_link)
        self._toolbar.addWidget(self._btn_link)

        self._btn_image = QPushButton("图片")
        self._btn_image.setToolTip("插入图片 (Ctrl+P)")
        self._btn_image.clicked.connect(self._insert_image)
        self._toolbar.addWidget(self._btn_image)

    def _setup_toolbar_actions(self):
        """设置快捷键"""
        # Ctrl+B
        bold_action = QAction(self)
        bold_action.setShortcut(QKeySequence("Ctrl+B"))
        bold_action.triggered.connect(lambda: self._wrap_selection("**", "**"))
        self.addAction(bold_action)

        # Ctrl+I
        italic_action = QAction(self)
        italic_action.setShortcut(QKeySequence("Ctrl+I"))
        italic_action.triggered.connect(lambda: self._wrap_selection("*", "*"))
        self.addAction(italic_action)

        # Ctrl+L
        link_action = QAction(self)
        link_action.setShortcut(QKeySequence("Ctrl+L"))
        link_action.triggered.connect(self._insert_link)
        self.addAction(link_action)

    def _connect_signals(self):
        """连接信号"""
        self._editor.textChanged.connect(self._on_editor_text_changed)
        self._editor.selectionChanged.connect(self._on_selection_changed)

    def _on_editor_text_changed(self):
        """编辑区文本变化，实时更新预览"""
        text = self._editor.toPlainText()
        self.content_changed.emit(text)

        if HAS_MARKDOWN:
            try:
                html = markdown.markdown(
                    text,
                    extensions=['extra', 'codehilite', 'tables', 'fenced_code']
                )
                self._preview.setHtml(html)
            except Exception:
                self._preview.setPlainText(text)
        else:
            self._preview.setPlainText(text)

    def _on_selection_changed(self):
        """选中文本变化"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            self.selection_changed.emit(start, end - start)

    def _on_mode_changed(self, index: int):
        """切换预览模式"""
        if index == 0:  # 分屏预览
            self._editor.show()
            self._preview.show()
        elif index == 1:  # 纯编辑
            self._editor.show()
            self._preview.hide()
        elif index == 2:  # 纯预览
            self._editor.hide()
            self._preview.show()

    # ========== Markdown插入操作 ==========

    def _insert_header(self, level: int):
        """插入标题"""
        prefix = "#" * level + " "
        self._insert_at_line_start(prefix)

    def _wrap_selection(self, prefix: str, suffix: str):
        """用前缀/后缀包裹选中文本"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(f"{prefix}{selected}{suffix}")
        else:
            cursor.insertText(f"{prefix}文字{suffix}")
            # 选中"文字"方便替换
            pos = cursor.position()
            cursor.setPosition(pos - len(suffix) - 2)
            cursor.setPosition(pos - len(suffix), QTextCursor.MoveMode.KeepAnchor)
            self._editor.setTextCursor(cursor)

    def _insert_at_line_start(self, text: str):
        """在当前行开头插入文本"""
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText(text)

    def _insert_quote(self):
        """插入引用"""
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText("> ")

    def _insert_unordered_list(self):
        """插入无序列表"""
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText("- ")

    def _insert_ordered_list(self):
        """插入有序列表"""
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText("1. ")

    def _insert_horizontal_rule(self):
        """插入分割线"""
        cursor = self._editor.textCursor()
        cursor.insertText("\n\n---\n\n")

    def _insert_link(self):
        """插入链接"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"[{text}](url)")
            # 选中url方便替换
            pos = cursor.position()
            cursor.setPosition(pos - 4)
            cursor.setPosition(pos - 1, QTextCursor.MoveMode.KeepAnchor)
            self._editor.setTextCursor(cursor)
        else:
            cursor.insertText("[链接文字](url)")

    def _insert_image(self):
        """插入图片"""
        cursor = self._editor.textCursor()
        cursor.insertText("![图片描述](图片路径)")

    # ========== 内容获取/设置 ==========

    def set_content(self, text: str):
        """设置编辑器内容"""
        self._editor.blockSignals(True)
        self._editor.setPlainText(text)
        self._editor.blockSignals(False)
        self._on_editor_text_changed()

    def get_plain_text(self) -> str:
        """获取纯文本内容"""
        return self._editor.toPlainText()

    def get_html(self) -> str:
        """获取渲染后的HTML"""
        if HAS_MARKDOWN:
            text = self._editor.toPlainText()
            return markdown.markdown(
                text,
                extensions=['extra', 'codehilite', 'tables', 'fenced_code']
            )
        return self._editor.toPlainText()

    def insert_at_cursor(self, text: str):
        """在光标处插入文本"""
        cursor = self._editor.textCursor()
        cursor.insertText(text)

    def get_selected_text(self) -> str:
        """获取选中的文本"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            return cursor.selectedText()
        return ""

    def get_editor(self) -> QTextEdit:
        """获取底层编辑器(供外部访问)"""
        return self._editor

    def highlight_warning(self, start: int, end: int, style_config: dict):
        """高亮预警文本(Markdown编辑器中也适用)"""
        cursor = self._editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        fmt = QTextCharFormat()
        color = QColor(style_config.get("color", "#FF0000"))
        color.setAlphaF(style_config.get("opacity", 0.5))

        marker = style_config.get("marker_type", "underline")
        if marker == "underline":
            fmt.setUnderlineColor(color)
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        elif marker == "wavy":
            fmt.setUnderlineColor(color)
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        elif marker == "highlight":
            fmt.setBackground(color)

        cursor.mergeCharFormat(fmt)
