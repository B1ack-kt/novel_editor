"""
项目面板 - 左侧导航面板
包含：项目列表、章节列表（拖拽排序）、设定库入口
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QLabel, QMenu,
    QInputDialog, QMessageBox, QSplitter, QTabWidget,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QAction

from config.constants import CHARACTER_DEFAULT_FIELDS, WORLD_CATEGORIES


class ProjectPanel(QWidget):
    """左侧项目与章节面板"""

    # 信号
    project_selected = pyqtSignal(str)          # 选择项目 (project_id)
    chapter_selected = pyqtSignal(str, str)     # 选择章节 (project_id, chapter_id)
    chapter_added = pyqtSignal(str)             # 新增章节 (project_id)
    chapter_deleted = pyqtSignal(str, str)      # 删除章节 (project_id, chapter_id)
    chapter_reordered = pyqtSignal(str, list)   # 重新排序 (project_id, chapter_ids)
    project_created = pyqtSignal()              # 请求创建项目
    project_deleted = pyqtSignal(str)           # 删除项目 (project_id)
    character_added = pyqtSignal(str)           # 新增人设 (project_id)
    world_rule_added = pyqtSignal(str, str, str)# 新增世界观 (project_id, category, name)
    export_requested = pyqtSignal(str)          # 导出请求 (project_id)
    backup_export_requested = pyqtSignal(str)   # 加密备份导出 (project_id)
    backup_import_requested = pyqtSignal()      # 加密备份导入
    copyright_requested = pyqtSignal(str)       # 版权追溯 (project_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_project_id = ""
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部标签
        header = QWidget()
        header.setStyleSheet("background-color: #4A90D9; padding: 8px;")
        header_layout = QHBoxLayout(header)
        title_label = QLabel("项目管理")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)

        self._new_project_btn = QPushButton("+")
        self._new_project_btn.setFixedSize(28, 28)
        self._new_project_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.2);
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.3);
            }
        """)
        self._new_project_btn.clicked.connect(self._on_new_project)
        header_layout.addWidget(self._new_project_btn)

        layout.addWidget(header)

        # 标签页：项目章节 / 设定库
        self._tab_widget = QTabWidget()

        # === 标签页1: 项目与章节 ===
        self._project_tree = QTreeWidget()
        self._project_tree.setHeaderLabels(["项目 / 章节", "字数"])
        self._project_tree.setColumnWidth(0, 200)
        self._project_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._project_tree.customContextMenuRequested.connect(self._on_context_menu)
        self._project_tree.itemClicked.connect(self._on_item_clicked)
        self._project_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._project_tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px 4px;
            }
            QTreeWidget::item:selected {
                background-color: #D0E4F7;
                color: #333;
            }
        """)
        self._tab_widget.addTab(self._project_tree, "章节")

        # === 标签页2: 设定库 ===
        self._create_settings_tab()

        self._tab_widget.addTab(self._settings_tab, "设定")

        layout.addWidget(self._tab_widget)

        # 底部操作栏
        footer = QWidget()
        footer.setStyleSheet("background-color: #F0F0F0; padding: 4px;")
        footer_layout = QHBoxLayout(footer)

        self._add_chapter_btn = QPushButton("+章")
        self._add_chapter_btn.setToolTip("添加新章节")
        self._add_chapter_btn.clicked.connect(lambda: self._on_add_chapter())
        footer_layout.addWidget(self._add_chapter_btn)

        self._add_char_btn = QPushButton("+人设")
        self._add_char_btn.setToolTip("添加人设")
        self._add_char_btn.clicked.connect(self._on_add_character)
        footer_layout.addWidget(self._add_char_btn)

        self._add_world_btn = QPushButton("+世界观")
        self._add_world_btn.setToolTip("添加世界观规则")
        self._add_world_btn.clicked.connect(self._on_add_world_rule)
        footer_layout.addWidget(self._add_world_btn)

        for btn in [self._add_chapter_btn, self._add_char_btn, self._add_world_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #D0D0D0;
                }
            """)

        layout.addWidget(footer)

    def _create_settings_tab(self):
        """创建设定库标签页"""
        self._settings_tab = QSplitter(Qt.Orientation.Vertical)

        # 人设列表
        char_widget = QWidget()
        char_layout = QVBoxLayout(char_widget)
        char_layout.setContentsMargins(4, 4, 4, 4)
        char_layout.addWidget(QLabel("人设库"))
        self._character_list = QListWidget()
        self._character_list.setStyleSheet("border: 1px solid #DDD; border-radius: 4px;")
        self._character_list.itemDoubleClicked.connect(self._on_character_double_clicked)
        char_layout.addWidget(self._character_list)
        self._settings_tab.addWidget(char_widget)

        # 世界观列表
        world_widget = QWidget()
        world_layout = QVBoxLayout(world_widget)
        world_layout.setContentsMargins(4, 4, 4, 4)
        world_layout.addWidget(QLabel("世界观库"))
        self._world_tree = QTreeWidget()
        self._world_tree.setHeaderHidden(True)
        self._world_tree.setStyleSheet("border: 1px solid #DDD; border-radius: 4px;")
        world_layout.addWidget(self._world_tree)
        self._settings_tab.addWidget(world_widget)

        self._settings_tab.setSizes([200, 200])

    # ========== 项目树操作 ==========

    def add_project_item(self, project_id: str, project_name: str):
        """添加项目节点"""
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, project_id)
        item.setText(0, project_name)
        item.setFlags(
            item.flags() | Qt.ItemFlag.ItemIsDragEnabled
        )
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        self._project_tree.addTopLevelItem(item)
        item.setExpanded(True)
        return item

    def add_chapter_item(self, project_id: str, chapter_id: str,
                         title: str, word_count: int = 0):
        """在指定项目下添加章节"""
        project_item = self._find_project_item(project_id)
        if not project_item:
            return

        chapter_item = QTreeWidgetItem(project_item)
        chapter_item.setData(0, Qt.ItemDataRole.UserRole, chapter_id)
        chapter_item.setText(0, title)
        chapter_item.setText(1, f"{word_count}字")
        chapter_item.setFlags(
            chapter_item.flags() | Qt.ItemFlag.ItemIsDragEnabled
        )
        return chapter_item

    def update_chapter_title(self, project_id: str, chapter_id: str,
                             title: str, word_count: int = 0):
        """更新章节标题与字数"""
        chapter_item = self._find_chapter_item(project_id, chapter_id)
        if chapter_item:
            chapter_item.setText(0, f"{title}（{word_count}字）" if word_count else title)

    def remove_chapter_item(self, project_id: str, chapter_id: str):
        """移除章节节点"""
        chapter_item = self._find_chapter_item(project_id, chapter_id)
        if chapter_item:
            parent = chapter_item.parent()
            if parent:
                parent.removeChild(chapter_item)

    def clear_all(self):
        """清空所有项目"""
        self._project_tree.clear()
        self._character_list.clear()
        self._world_tree.clear()

    def _find_project_item(self, project_id: str):
        """查找项目节点"""
        for i in range(self._project_tree.topLevelItemCount()):
            item = self._project_tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == project_id:
                return item
        return None

    def _find_chapter_item(self, project_id: str, chapter_id: str):
        """查找章节节点"""
        project_item = self._find_project_item(project_id)
        if not project_item:
            return None
        for i in range(project_item.childCount()):
            child = project_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == chapter_id:
                return child
        return None

    # ========== 事件处理 ==========

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击节点"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        parent = item.parent()

        if parent is None:
            # 项目节点
            self._current_project_id = data
            self.project_selected.emit(data)
        else:
            # 章节节点
            project_id = parent.data(0, Qt.ItemDataRole.UserRole)
            self.chapter_selected.emit(project_id, data)

    def _on_context_menu(self, pos):
        """右键菜单"""
        item = self._project_tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        data = item.data(0, Qt.ItemDataRole.UserRole)
        parent = item.parent()

        if parent is None:
            # 项目右键菜单
            rename_action = menu.addAction("重命名项目")
            rename_action.triggered.connect(lambda: self._on_rename_project(data))

            delete_action = menu.addAction("删除项目")
            delete_action.triggered.connect(lambda: self._on_delete_project(data))

            menu.addSeparator()

            export_menu = QMenu("导出", self)
            export_menu.addAction("TXT").triggered.connect(
                lambda: self.export_requested.emit(data)
            )
            export_menu.addAction("DOCX").triggered.connect(
                lambda: self.export_requested.emit(data)
            )
            export_menu.addAction("加密备份(.nev)").triggered.connect(
                lambda: self.backup_export_requested.emit(data)
            )
            menu.addMenu(export_menu)

            menu.addAction("生成版权追溯文档").triggered.connect(
                lambda: self.copyright_requested.emit(data)
            )
        else:
            # 章节右键菜单
            rename_action = menu.addAction("重命名章节")
            rename_action.triggered.connect(
                lambda: self._on_rename_chapter(parent.data(0, Qt.ItemDataRole.UserRole), data)
            )
            delete_action = menu.addAction("删除章节")
            delete_action.triggered.connect(
                lambda: self._on_delete_chapter(parent.data(0, Qt.ItemDataRole.UserRole), data)
            )

        menu.exec(self._project_tree.mapToGlobal(pos))

    def _on_new_project(self):
        """新建项目"""
        self.project_created.emit()

    def _on_add_chapter(self):
        """新增章节"""
        if self._current_project_id:
            self.chapter_added.emit(self._current_project_id)
        else:
            QMessageBox.information(self, "提示", "请先选择一个项目")

    def _on_rename_project(self, project_id: str):
        """重命名项目"""
        name, ok = QInputDialog.getText(self, "重命名", "新项目名称:")
        if ok and name:
            # 由主窗口处理
            self._find_project_item(project_id).setText(0, name)

    def _on_delete_project(self, project_id: str):
        """删除项目"""
        reply = QMessageBox.question(
            self, "确认删除",
            "删除项目将同时删除所有章节和设定数据，此操作不可恢复。\n确认删除？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project_deleted.emit(project_id)

    def _on_rename_chapter(self, project_id: str, chapter_id: str):
        """重命名章节"""
        name, ok = QInputDialog.getText(self, "重命名", "新章节标题:")
        if ok and name:
            item = self._find_chapter_item(project_id, chapter_id)
            if item:
                item.setText(0, name)

    def _on_delete_chapter(self, project_id: str, chapter_id: str):
        """删除章节"""
        reply = QMessageBox.question(
            self, "确认删除", "确认删除此章节？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.chapter_deleted.emit(project_id, chapter_id)

    def _on_add_character(self):
        """添加人设"""
        if self._current_project_id:
            self.character_added.emit(self._current_project_id)
        else:
            QMessageBox.information(self, "提示", "请先选择一个项目")

    def _on_add_world_rule(self):
        """添加世界观规则"""
        if not self._current_project_id:
            QMessageBox.information(self, "提示", "请先选择一个项目")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("添加世界观规则")
        layout = QFormLayout(dialog)

        category_combo = QComboBox()
        category_combo.addItems(WORLD_CATEGORIES)
        layout.addRow("分类:", category_combo)

        name_input = QLineEdit()
        layout.addRow("名称:", name_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.world_rule_added.emit(
                self._current_project_id,
                category_combo.currentText(),
                name_input.text()
            )

    def _on_character_double_clicked(self, item: QListWidgetItem):
        """双击人设查看详情"""
        # TODO: 打开人设详情对话框
        pass

    # ========== 公共刷新接口 ==========

    def refresh_character_list(self, characters: list):
        """刷新设定库人设列表
        Args:
            characters: Character对象列表
        """
        self._character_list.clear()
        for char in characters:
            item = QListWidgetItem(f"{char.name}")
            item.setData(Qt.ItemDataRole.UserRole, char.id)
            self._character_list.addItem(item)

    def refresh_world_tree(self, world_rules: list):
        """刷新世界观树"""
        self._world_tree.clear()
        # 按分类分组
        categories = {}
        for rule in world_rules:
            categories.setdefault(rule.category, {})[rule.id] = rule

        for category, rules in categories.items():
            cat_item = QTreeWidgetItem([category])
            # 先添加顶级规则
            for rid, rule in rules.items():
                if not rule.parent_id:
                    child = QTreeWidgetItem(cat_item, [rule.name])
                    child.setData(0, Qt.ItemDataRole.UserRole, rule.id)
                    self._add_world_children(child, rules, rule.children)
            self._world_tree.addTopLevelItem(cat_item)

    def _add_world_children(self, parent_item, rules: dict, children: list):
        """递归添加世界观子规则"""
        for child_id in children:
            if child_id in rules:
                rule = rules[child_id]
                child = QTreeWidgetItem(parent_item, [rule.name])
                child.setData(0, Qt.ItemDataRole.UserRole, rule.id)
                self._add_world_children(child, rules, rule.children)

    def set_current_project(self, project_id: str):
        """设置当前项目ID"""
        self._current_project_id = project_id
