"""
导出对话框 - 多格式导出选项配置
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QCheckBox, QLineEdit, QPushButton, QLabel,
    QHBoxLayout, QFileDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class ExportDialog(QDialog):
    """多格式导出对话框"""

    def __init__(self, project_name: str = "", parent=None):
        super().__init__(parent)
        self._project_name = project_name
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("导出小说")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # 格式选择
        form = QFormLayout()
        self._format_combo = QComboBox()
        self._format_combo.addItems(["TXT", "DOCX", "PDF", "EPUB"])
        form.addRow("导出格式:", self._format_combo)

        layout.addLayout(form)

        # 选项
        self._include_marks_check = QCheckBox("包含内容类型标记(原创/AI生成/AI辅助)")
        layout.addWidget(self._include_marks_check)

        self._keep_annotations_check = QCheckBox("保留批注")
        layout.addWidget(self._keep_annotations_check)

        # 章节标题格式
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("章节标题格式:"))
        self._title_format_input = QLineEdit("第{num}章 {title}")
        title_layout.addWidget(self._title_format_input)
        layout.addLayout(title_layout)

        layout.addWidget(QLabel("可用变量: {num}=章节序号, {title}=章节标题"))

        # 输出路径
        path_layout = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("导出路径")
        path_layout.addWidget(self._path_input)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        layout.addWidget(QLabel("输出路径:"))
        layout.addLayout(path_layout)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_path(self):
        """浏览路径"""
        format_ext = self._format_combo.currentText().lower()
        filepath, _ = QFileDialog.getSaveFileName(
            self, "选择导出路径",
            f"{self._project_name}.{format_ext}",
            f"{self._format_combo.currentText()} Files (*.{format_ext})"
        )
        if filepath:
            self._path_input.setText(filepath)

    def get_export_options(self) -> dict:
        """获取导出选项"""
        return {
            "format_type": self._format_combo.currentText(),
            "include_marks": self._include_marks_check.isChecked(),
            "keep_annotations": self._keep_annotations_check.isChecked(),
            "chapter_title_format": self._title_format_input.text(),
            "output_path": self._path_input.text()
        }
