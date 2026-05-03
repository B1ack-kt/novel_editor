"""
富文本编辑器 - 基于QTextEdit扩展
支持：段落格式(缩进/行距)、字体调整、批注、撤销/重做、查找替换
双模式：富文本/Markdown一键切换，内容实时同步
"""

from PyQt6.QtWidgets import (
    QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QToolBar, QFontComboBox, QSpinBox,
    QLabel, QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import (
    QFont, QTextCursor, QTextCharFormat, QColor,
    QTextBlockFormat, QTextDocument, QAction,
    QKeySequence, QTextListFormat, QTextList
)


class RichTextEditor(QTextEdit):
    """富文本编辑器 - 小说正文编辑核心"""

    content_changed = pyqtSignal(str)  # 内容变化时发射纯文本
    selection_changed_signal = pyqtSignal(int, int)  # 选中文本变化 position, length
    cursor_position_changed = pyqtSignal(int)  # 光标位置变化

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_editor()
        self._setup_shortcuts()
        self._connect_signals()

    def _setup_editor(self):
        """初始化编辑器设置"""
        # 默认字体
        font = QFont("Microsoft YaHei", 14)
        self.setFont(font)
        self.setAcceptRichText(True)

        # 边距设置
        self.setStyleSheet("""
            QTextEdit {
                padding: 20px 30px;
                line-height: 1.8;
                background-color: #FAFAFA;
                border: none;
                selection-background-color: #B0D4F1;
            }
        """)

        # 文档设置
        doc = self.document()
        doc.setDefaultFont(font)

        # 允许撤销/重做
        self.setUndoRedoEnabled(True)

    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+B 加粗
        self._bold_action = QAction("加粗", self)
        self._bold_action.setShortcut(QKeySequence("Ctrl+B"))
        self._bold_action.triggered.connect(self._toggle_bold)
        self.addAction(self._bold_action)

        # Ctrl+I 斜体
        self._italic_action = QAction("斜体", self)
        self._italic_action.setShortcut(QKeySequence("Ctrl+I"))
        self._italic_action.triggered.connect(self._toggle_italic)
        self.addAction(self._italic_action)

        # Ctrl+U 下划线
        self._underline_action = QAction("下划线", self)
        self._underline_action.setShortcut(QKeySequence("Ctrl+U"))
        self._underline_action.triggered.connect(self._toggle_underline)
        self.addAction(self._underline_action)

        # Ctrl+F 查找
        self._find_action = QAction("查找", self)
        self._find_action.setShortcut(QKeySequence("Ctrl+F"))
        self._find_action.triggered.connect(self._show_find_dialog)
        self.addAction(self._find_action)

        # Ctrl+H 替换
        self._replace_action = QAction("替换", self)
        self._replace_action.setShortcut(QKeySequence("Ctrl+H"))
        self._replace_action.triggered.connect(self._show_replace_dialog)
        self.addAction(self._replace_action)

    def _connect_signals(self):
        """连接信号"""
        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.selectionChanged.connect(self._on_selection_changed)

    def _on_text_changed(self):
        """文本变化处理"""
        self.content_changed.emit(self.toPlainText())

    def _on_cursor_changed(self):
        """光标位置变化"""
        self.cursor_position_changed.emit(self.textCursor().position())

    def _on_selection_changed(self):
        """选中文本变化"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            self.selection_changed_signal.emit(start, end - start)
        else:
            self.selection_changed_signal.emit(-1, 0)

    # ========== 格式操作 ==========

    def _toggle_bold(self):
        """切换加粗"""
        fmt = QTextCharFormat()
        cursor = self.textCursor()
        current_weight = cursor.charFormat().fontWeight()
        fmt.setFontWeight(
            QFont.Weight.Normal if current_weight == QFont.Weight.Bold
            else QFont.Weight.Bold
        )
        cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)

    def _toggle_italic(self):
        """切换斜体"""
        fmt = QTextCharFormat()
        cursor = self.textCursor()
        fmt.setFontItalic(not cursor.charFormat().fontItalic())
        cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)

    def _toggle_underline(self):
        """切换下划线"""
        fmt = QTextCharFormat()
        cursor = self.textCursor()
        fmt.setFontUnderline(not cursor.charFormat().fontUnderline())
        cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)

    def set_font_family(self, font_name: str):
        """设置字体"""
        fmt = QTextCharFormat()
        fmt.setFontFamily(font_name)
        self.mergeCurrentCharFormat(fmt)

    def set_font_size(self, size: int):
        """设置字号"""
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.mergeCurrentCharFormat(fmt)

    def set_text_color(self, color: QColor):
        """设置文字颜色"""
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self.mergeCurrentCharFormat(fmt)

    def set_paragraph_spacing(self, spacing: float):
        """设置段落间距"""
        fmt = QTextBlockFormat()
        fmt.setLineHeight(spacing * 100, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        self.textCursor().mergeBlockFormat(fmt)

    def set_first_line_indent(self, indent: int):
        """设置首行缩进(字符数)"""
        fmt = QTextBlockFormat()
        font_size = self.font().pointSize()
        fmt.setTextIndent(indent * font_size)
        self.textCursor().mergeBlockFormat(fmt)

    def insert_bullet_list(self):
        """插入无序列表"""
        cursor = self.textCursor()
        cursor.insertList(QTextListFormat.Style.ListDisc)

    def insert_ordered_list(self):
        """插入有序列表"""
        cursor = self.textCursor()
        cursor.insertList(QTextListFormat.Style.ListDecimal)

    def insert_horizontal_line(self):
        """插入分割线"""
        cursor = self.textCursor()
        cursor.insertHtml("<hr>")

    # ========== 查找替换 ==========

    def _show_find_dialog(self):
        """显示查找对话框"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "查找", "输入查找内容:")
        if ok and text:
            self.find_text(text)

    def find_text(self, text: str):
        """查找文本"""
        found = self.find(text)
        if not found:
            # 从开头开始查找
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.setTextCursor(cursor)
            found = self.find(text)
        return found

    def _show_replace_dialog(self):
        """显示替换对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("查找替换")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("查找:"))
        find_input = QLineEdit()
        find_layout.addWidget(find_input)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("替换为:"))
        replace_input = QLineEdit()
        replace_layout.addWidget(replace_input)
        layout.addLayout(replace_layout)

        btn_find = QPushButton("查找下一个")
        btn_replace = QPushButton("替换")
        btn_replace_all = QPushButton("全部替换")

        btn_find.clicked.connect(lambda: self.find_text(find_input.text()))
        btn_replace.clicked.connect(lambda: self._replace_one(find_input.text(), replace_input.text()))
        btn_replace_all.clicked.connect(lambda: self._replace_all(find_input.text(), replace_input.text()))

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_find)
        btn_layout.addWidget(btn_replace)
        btn_layout.addWidget(btn_replace_all)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _replace_one(self, find_text: str, replace_text: str):
        """替换当前选中文本"""
        cursor = self.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == find_text:
            cursor.insertText(replace_text)
        # 查找下一个
        self.find_text(find_text)

    def _replace_all(self, find_text: str, replace_text: str):
        """全部替换"""
        cursor = QTextCursor(self.document().begin())
        self.setTextCursor(cursor)
        count = 0
        while self.find(find_text):
            cursor = self.textCursor()
            cursor.insertText(replace_text)
            count += 1
        QMessageBox.information(self, "替换完成", f"共替换 {count} 处")

    # ========== 内容类型标记 ==========

    def mark_content_type(self, start: int, end: int, content_type: str, color: QColor = None):
        """标记内容类型（AI生成/原创/修改）"""
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        fmt = QTextCharFormat()
        if content_type == "ai_generated":
            fmt.setBackground(QColor(200, 230, 255, 80))
        elif content_type == "ai_assisted":
            fmt.setBackground(QColor(255, 230, 200, 80))
        elif content_type == "original":
            fmt.setBackground(QColor(200, 255, 200, 60))

        cursor.mergeCharFormat(fmt)

    def highlight_warning(self, start: int, end: int, style_config: dict):
        """
        高亮预警文本

        Args:
            start: 起始位置
            end: 结束位置
            style_config: {marker_type, color, opacity}
        """
        cursor = QTextCursor(self.document())
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

    def clear_highlight(self, start: int, end: int):
        """清除高亮标记"""
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        fmt = QTextCharFormat()
        fmt.setBackground(Qt.GlobalColor.transparent)
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
        cursor.mergeCharFormat(fmt)

    # ========== 内容获取/设置 ==========

    def get_plain_text(self) -> str:
        """获取纯文本内容"""
        return self.toPlainText()

    def get_html(self) -> str:
        """获取HTML内容"""
        return self.toHtml()

    def set_content(self, text: str):
        """设置内容"""
        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)

    def set_content_html(self, html: str):
        """设置HTML内容"""
        self.blockSignals(True)
        self.setHtml(html)
        self.blockSignals(False)

    def get_selected_text(self) -> str:
        """获取选中的文本"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return cursor.selectedText()
        return ""

    def insert_at_cursor(self, text: str):
        """在光标处插入文本"""
        cursor = self.textCursor()
        cursor.insertText(text)

    def insert_block_at_cursor(self, text: str):
        """在光标处新起一行插入文本"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText("\n" + text)

    def add_annotation(self, text: str, annotation: str):
        """添加批注（用注释形式模拟）"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        fmt.setToolTip(annotation)
        fmt.setBackground(QColor(255, 255, 200))
        cursor.insertText(f"【{text}】", fmt)
