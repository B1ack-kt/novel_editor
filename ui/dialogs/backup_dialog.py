"""
备份版本管理对话框 - 查看历史备份并支持回滚
"""

import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QTextEdit,
    QMessageBox, QDialogButtonBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class BackupDialog(QDialog):
    """备份版本管理"""

    def __init__(self, backup_manager, project_id: str, parent=None):
        super().__init__(parent)
        self._backup_mgr = backup_manager
        self._project_id = project_id
        self._selected_version = None
        self._setup_ui()
        self._load_backups()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("备份版本管理")
        self.setMinimumSize(600, 450)

        layout = QVBoxLayout(self)

        info_label = QLabel(f"项目备份列表（最多保留10个版本）")
        info_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(info_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：版本列表
        self._backup_list = QListWidget()
        self._backup_list.currentRowChanged.connect(self._on_version_selected)
        self._backup_list.setStyleSheet("""
            QListWidget { border: 1px solid #DDD; border-radius: 4px; font-size: 13px; }
            QListWidget::item:selected { background-color: #D0E4F7; }
            QListWidget::item { padding: 8px; }
        """)
        splitter.addWidget(self._backup_list)

        # 右侧：版本详情
        detail_widget = QVBoxLayout()
        self._detail_label = QLabel("选择左侧版本查看详情")
        self._detail_label.setWordWrap(True)
        self._detail_label.setStyleSheet("padding: 10px; color: #555;")
        detail_widget.addWidget(self._detail_label)
        detail_widget.addStretch()

        detail_container = QVBoxLayout()
        detail_container.addLayout(detail_widget)
        detail_container_widget = QVBoxLayout()
        detail_container_widget.addLayout(detail_widget)

        splitter.addWidget(QLabel(""))  # placeholder
        # 使用简单的右侧面板
        layout.addWidget(splitter)

        # 简化：直接用详情标签
        detail_frame = QVBoxLayout()
        detail_frame.addWidget(self._detail_label)
        layout.addLayout(detail_frame)

        # 按钮
        btn_layout = QHBoxLayout()

        self._restore_btn = QPushButton("回滚到此版本")
        self._restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800; color: white; border: none;
                padding: 8px 20px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        self._restore_btn.clicked.connect(self._on_restore)
        self._restore_btn.setEnabled(False)
        btn_layout.addWidget(self._restore_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _load_backups(self):
        """加载备份列表"""
        backups = self._backup_mgr.get_backup_list(self._project_id)
        backups.sort(key=lambda x: x.version, reverse=True)

        self._backup_list.clear()
        for backup in backups:
            time_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                     time.localtime(backup.created_at))
            size_kb = backup.file_size / 1024
            item_text = f"v{backup.version:03d}  {time_str}  ({size_kb:.1f}KB)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, backup.version)
            self._backup_list.addItem(item)

    def _on_version_selected(self, index: int):
        """选中版本"""
        if index < 0:
            return
        item = self._backup_list.item(index)
        version = item.data(Qt.ItemDataRole.UserRole)

        backups = self._backup_mgr.get_backup_list(self._project_id)
        for b in backups:
            if b.version == version:
                time_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                         time.localtime(b.created_at))
                size_kb = b.file_size / 1024
                detail = (
                    f"版本: v{version:03d}\n"
                    f"时间: {time_str}\n"
                    f"大小: {size_kb:.1f}KB\n"
                    f"说明: {b.description}\n"
                    f"加密: {'是' if b.is_encrypted else '否'}"
                )
                self._detail_label.setText(detail)
                self._selected_version = version
                self._restore_btn.setEnabled(True)
                break

    def _on_restore(self):
        """执行回滚"""
        if not self._selected_version:
            return

        reply = QMessageBox.question(
            self, "确认回滚",
            f"确认回滚至 v{self._selected_version:03d}？\n"
            "当前未保存的修改将丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def get_selected_version(self) -> int:
        """获取选中的版本号"""
        return self._selected_version
