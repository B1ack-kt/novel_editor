"""
主窗口 - AI协同小说编辑器
整合所有子模块：项目面板、编辑器、Agent面板、状态栏
"""

import os
import time
import json
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QMessageBox, QFileDialog,
    QInputDialog, QDialog, QFormLayout, QLineEdit,
    QCheckBox, QDialogButtonBox, QTabWidget, QLabel,
    QStatusBar, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence, QFont, QIcon

from config.constants import (
    APP_NAME, APP_VERSION, BACKUP_INTERVALS,
    WARNING_TYPES, DEFAULT_WARNING_STYLE, WORD_COUNT_RULES
)
from config.settings import SettingsManager
from core.auth import AuthManager, AuthError
from core.storage import StorageManager
from core.crypto import derive_key, hash_password, verify_password
from core.project_manager import ProjectManager
from core.backup import BackupManager
from models.project import Project
from models.chapter import Chapter
from models.character import Character
from models.world import WorldRule
from utils.word_counter import WordCounter
from utils.export_utils import ExportUtils

from ui.project_panel import ProjectPanel
from ui.editor.text_editor import RichTextEditor
from ui.editor.markdown_editor import MarkdownEditorPanel
from ui.editor.editor_toolbar import EditorToolbar
from ui.editor.status_bar import StatusBar
from ui.agent.warning_panel import WarningPanel
from ui.agent.suggestion_bar import SuggestionBar
from ui.settings.model_manager import ModelManagerDialog
from ui.settings.warning_config import WarningConfigDialog
from ui.settings_lib.character_lib import CharacterDetailDialog
from ui.settings_lib.world_lib import WorldRuleDetailDialog
from ui.dialogs.export_dialog import ExportDialog
from ui.dialogs.backup_dialog import BackupDialog

from agent.model_client import ModelClient
from agent.context_builder import ContextBuilder


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(
        self,
        settings_manager: SettingsManager,
        auth_manager: AuthManager,
        storage_manager: StorageManager,
        project_manager: ProjectManager,
        backup_manager: BackupManager,
        master_key: bytes
    ):
        super().__init__()
        self._settings_mgr = settings_manager
        self._auth_mgr = auth_manager
        self._storage_mgr = storage_manager
        self._project_mgr = project_manager
        self._backup_mgr = backup_manager
        self._master_key = master_key

        # 当前状态
        self._current_editor_mode = "richtext"
        self._current_chapter: Optional[Chapter] = None
        self._model_client: Optional[ModelClient] = None
        self._context_builder: Optional[ContextBuilder] = None
        self._offline_mode = False

        self._setup_ui()
        self._setup_menu()
        self._setup_connections()
        self._load_settings()
        self._load_projects()

        # 备份定时器
        self._backup_timer = QTimer()
        self._backup_timer.timeout.connect(self._auto_backup)
        self._start_backup_timer()

    def _setup_ui(self):
        """设置主界面布局"""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # 中心组件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 工具栏 ===
        self._toolbar = EditorToolbar()
        main_layout.addWidget(self._toolbar)

        # === 主分割区 ===
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧 - 项目面板
        self._project_panel = ProjectPanel()
        self._main_splitter.addWidget(self._project_panel)

        # 中间 - 编辑器 + 建议栏
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        # 编辑器堆叠(富文本/Markdown)
        self._richtext_editor = RichTextEditor()
        self._markdown_editor = MarkdownEditorPanel()
        self._editor_stack = QTabWidget()
        self._editor_stack.tabBar().hide()  # 隐藏标签栏
        self._editor_stack.addTab(self._richtext_editor, "richtext")
        self._editor_stack.addTab(self._markdown_editor, "markdown")
        editor_layout.addWidget(self._editor_stack)

        # 建议栏(底部)
        self._suggestion_bar = SuggestionBar()
        editor_layout.addWidget(self._suggestion_bar)

        self._main_splitter.addWidget(editor_widget)

        # 右侧 - 预警面板
        self._warning_panel = WarningPanel()
        self._main_splitter.addWidget(self._warning_panel)

        # 设置比例 220:800:220
        self._main_splitter.setSizes([220, 960, 220])

        main_layout.addWidget(self._main_splitter)

        # === 底部状态栏 ===
        self._status_bar = StatusBar()
        main_layout.addWidget(self._status_bar)

        # 默认显示富文本编辑器
        self._show_editor("richtext")

    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # ===== 文件菜单 =====
        file_menu = menubar.addMenu("文件(&F)")

        new_project_action = QAction("新建项目(&N)", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_project_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_project_action)

        open_project_action = QAction("打开项目(&O)", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+O"))
        open_project_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_menu = QMenu("导出", self)
        for fmt in ["TXT", "DOCX", "PDF", "EPUB"]:
            action = export_menu.addAction(f"导出为{fmt}")
            action.triggered.connect(lambda checked, f=fmt: self._on_export(f))
        file_menu.addMenu(export_menu)

        file_menu.addSeparator()

        import_action = QAction("导入加密备份(.nev)", self)
        import_action.triggered.connect(self._on_import_nev)
        file_menu.addAction(import_action)

        export_nev_action = QAction("导出加密备份(.nev)", self)
        export_nev_action.triggered.connect(self._on_export_nev)
        file_menu.addAction(export_nev_action)

        file_menu.addSeparator()

        back_up_action = QAction("手动备份", self)
        back_up_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
        back_up_action.triggered.connect(self._on_manual_backup)
        file_menu.addAction(back_up_action)

        view_backup_action = QAction("查看备份版本", self)
        view_backup_action.triggered.connect(self._on_view_backups)
        file_menu.addAction(view_backup_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ===== 编辑菜单 =====
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        find_action = QAction("查找(&F)", self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self._on_find)
        edit_menu.addAction(find_action)

        replace_action = QAction("替换(&H)", self)
        replace_action.setShortcut(QKeySequence("Ctrl+H"))
        replace_action.triggered.connect(self._on_replace)
        edit_menu.addAction(replace_action)

        edit_menu.addSeparator()

        add_chapter_action = QAction("添加章节(&C)", self)
        add_chapter_action.setShortcut(QKeySequence("Ctrl+T"))
        add_chapter_action.triggered.connect(lambda: self._project_panel._on_add_chapter())
        edit_menu.addAction(add_chapter_action)

        # ===== Agent菜单 =====
        agent_menu = menubar.addMenu("Agent(&A)")

        agent_trigger_action = QAction("手动召唤Agent", self)
        agent_trigger_action.setShortcut(QKeySequence("Ctrl+A"))
        agent_trigger_action.triggered.connect(self._on_agent_trigger)
        agent_menu.addAction(agent_trigger_action)

        agent_menu.addSeparator()

        for action_id, action_name in [
            ("plot_generate", "情节生成"),
            ("polish", "文本润色"),
            ("check_settings", "设定校验"),
            ("outline", "生成大纲"),
            ("fill_details", "填充细节"),
        ]:
            action = QAction(action_name, self)
            action.triggered.connect(lambda checked, a=action_id: self._on_agent_action(a))
            agent_menu.addAction(action)

        # ===== 设置菜单 =====
        settings_menu = menubar.addMenu("设置(&S)")

        model_action = QAction("模型管理", self)
        model_action.triggered.connect(self._on_manage_models)
        settings_menu.addAction(model_action)

        warning_config_action = QAction("预警配置", self)
        warning_config_action.triggered.connect(self._on_warning_config)
        settings_menu.addAction(warning_config_action)

        settings_menu.addSeparator()

        settings_action = QAction("应用设置", self)
        settings_action.triggered.connect(self._on_app_settings)
        settings_menu.addAction(settings_action)

        change_pwd_action = QAction("修改密码", self)
        change_pwd_action.triggered.connect(self._on_change_password)
        settings_menu.addAction(change_pwd_action)

        # ===== 帮助菜单 =====
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_connections(self):
        """连接信号槽"""
        # 工具栏
        self._toolbar.mode_changed.connect(self._on_mode_changed)
        self._toolbar.model_switched.connect(self._on_model_switched)
        self._toolbar.agent_triggered.connect(self._on_agent_action)
        self._toolbar.font_changed.connect(self._richtext_editor.set_font_family)
        self._toolbar.font_size_changed.connect(self._richtext_editor.set_font_size)
        self._toolbar.color_changed.connect(self._richtext_editor.set_text_color)
        self._toolbar.indent_changed.connect(self._richtext_editor.set_first_line_indent)
        self._toolbar.spacing_changed.connect(self._richtext_editor.set_paragraph_spacing)

        # 项目面板
        self._project_panel.project_selected.connect(self._on_project_selected)
        self._project_panel.chapter_selected.connect(self._on_chapter_selected)
        self._project_panel.chapter_added.connect(self._on_chapter_added)
        self._project_panel.chapter_deleted.connect(self._on_chapter_deleted)
        self._project_panel.project_created.connect(self._on_new_project)
        self._project_panel.project_deleted.connect(self._on_project_deleted)
        self._project_panel.character_added.connect(self._on_character_added)
        self._project_panel.world_rule_added.connect(self._on_world_rule_added)
        self._project_panel.export_requested.connect(self._on_export)
        self._project_panel.backup_export_requested.connect(self._on_export_nev)
        self._project_panel.copyright_requested.connect(self._on_copyright)

        # 编辑器 - 内容变化
        self._richtext_editor.content_changed.connect(self._on_content_changed)
        self._markdown_editor.content_changed.connect(self._on_content_changed)

        # 状态栏
        self._status_bar.word_count_rule_changed.connect(self._on_word_count_rule_changed)
        self._status_bar.offline_mode_toggled.connect(self._on_offline_toggled)

        # 建议栏
        self._suggestion_bar.suggestion_accepted.connect(self._on_suggestion_accepted)

    def _show_editor(self, mode: str):
        """切换编辑器显示"""
        if mode == "richtext":
            self._editor_stack.setCurrentIndex(0)
            self._current_editor_mode = "richtext"
        else:
            self._editor_stack.setCurrentIndex(1)
            self._current_editor_mode = "markdown"

    # ========== 文件操作 ==========

    def _on_new_project(self):
        """新建项目"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新建小说项目")
        dialog.setMinimumWidth(450)
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText("项目名称")
        layout.addRow("项目名称:", name_input)

        path_input = QLineEdit()
        path_input.setText(self._settings_mgr.get_setting("default_storage_path", ""))
        path_input.setPlaceholderText("存储路径（默认本地路径）")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(lambda: self._browse_path(path_input))
        path_row = QHBoxLayout()
        path_row.addWidget(path_input)
        path_row.addWidget(browse_btn)
        layout.addRow("存储路径:", path_row)

        encrypt_check = QCheckBox("启用项目独立加密")
        layout.addRow("", encrypt_check)

        pwd_input = QLineEdit()
        pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_input.setPlaceholderText("项目独立密码（启用加密时必填）")
        layout.addRow("项目密码:", pwd_input)

        pwd_confirm = QLineEdit()
        pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_confirm.setPlaceholderText("确认密码")
        layout.addRow("确认密码:", pwd_confirm)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        name = name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入项目名称")
            return

        if encrypt_check.isChecked():
            if pwd_input.text() != pwd_confirm.text():
                QMessageBox.warning(self, "提示", "两次密码不一致")
                return
            if len(pwd_input.text()) < 6:
                QMessageBox.warning(self, "提示", "项目密码长度不能少于6位")
                return

        try:
            project = self._project_mgr.create_project(
                name=name,
                storage_path=path_input.text(),
                password=pwd_input.text() if encrypt_check.isChecked() else "",
                is_encrypted=encrypt_check.isChecked()
            )

            self._project_panel.add_project_item(project.id, project.name)
            self._project_panel.set_current_project(project.id)
            self._project_mgr.set_current_project(project)

            # 创建默认第一章
            first_chapter = self._project_mgr.create_chapter(project.id, "第一章")
            self._project_panel.add_chapter_item(
                project.id, first_chapter.id, first_chapter.title
            )

            self._update_status(f"项目 '{name}' 创建成功")

        except Exception as e:
            QMessageBox.critical(self, "创建失败", str(e))

    def _on_open_project(self):
        """打开项目（选择.nev文件或已有项目）"""
        # TODO: 实现项目列表选择对话框
        pass

    def _on_save(self):
        """保存当前章节"""
        if not self._current_chapter:
            self._update_status("没有打开的章节")
            return

        if self._current_editor_mode == "richtext":
            content = self._richtext_editor.get_plain_text()
        else:
            content = self._markdown_editor.get_plain_text()

        self._current_chapter.content = content
        self._current_chapter.word_count = WordCounter.count_words(
            content, self._status_bar.get_current_rule()
        )
        self._project_mgr.update_chapter(self._current_chapter)
        self._update_word_count()
        self._update_status("已保存")

    def _on_export(self, format_type: str):
        """导出文档"""
        project = self._project_mgr.get_current_project()
        if not project:
            QMessageBox.information(self, "提示", "请先打开一个项目")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, f"导出为{format_type}",
            os.path.expanduser(f"~/Desktop/{project.name}"),
            f"{format_type} Files (*.{format_type.lower()})"
        )
        if not filepath:
            return

        try:
            chapters = self._project_mgr.get_chapters(project.id)
            ExportUtils.export(
                format_type.upper(), chapters, filepath,
                title=project.name
            )
            self._update_status(f"导出成功: {filepath}")
            QMessageBox.information(self, "导出成功", f"已导出至:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_export_nev(self):
        """导出加密备份"""
        project = self._project_mgr.get_current_project()
        if not project:
            QMessageBox.information(self, "提示", "请先打开一个项目")
            return

        # 先自动备份当前数据
        self._on_manual_backup()

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出加密备份",
            os.path.expanduser(f"~/Desktop/{project.name}"),
            "加密备份文件 (*.nev)"
        )
        if not filepath:
            return

        # 输入分享密码
        share_pwd, ok = QInputDialog.getText(
            self, "分享密码", "请设置分享密码:",
            QLineEdit.EchoMode.Password
        )
        if not ok or not share_pwd:
            return

        project_pwd = ""
        if project.is_encrypted:
            project_pwd, ok2 = QInputDialog.getText(
                self, "项目密码", "请输入项目独立密码:",
                QLineEdit.EchoMode.Password
            )
            if not ok2:
                return

        try:
            self._backup_mgr.export_encrypted_backup(
                project.id, filepath, share_pwd, project_pwd
            )
            self._update_status("加密备份导出成功")
            QMessageBox.information(self, "导出成功", f"加密备份已导出至:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_import_nev(self):
        """导入加密备份"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入加密备份", "",
            "加密备份文件 (*.nev)"
        )
        if not filepath:
            return

        share_pwd, ok = QInputDialog.getText(
            self, "分享密码", "请输入分享密码:",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return

        project_pwd = ""
        # 询问是否有项目密码
        reply = QMessageBox.question(
            self, "项目密码",
            "此备份是否包含项目独立密码？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            project_pwd, ok2 = QInputDialog.getText(
                self, "项目密码", "请输入项目独立密码:",
                QLineEdit.EchoMode.Password
            )
            if not ok2:
                return

        try:
            self._backup_mgr.import_encrypted_backup(
                filepath, share_pwd, project_pwd
            )
            self._update_status("加密备份导入成功")
            QMessageBox.information(self, "导入成功", "项目数据已恢复")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    # ========== 编辑操作 ==========

    def _on_undo(self):
        if self._current_editor_mode == "richtext":
            self._richtext_editor.undo()

    def _on_redo(self):
        if self._current_editor_mode == "richtext":
            self._richtext_editor.redo()

    def _on_find(self):
        if self._current_editor_mode == "richtext":
            self._richtext_editor._show_find_dialog()

    def _on_replace(self):
        if self._current_editor_mode == "richtext":
            self._richtext_editor._show_replace_dialog()

    def _on_mode_changed(self, mode: str):
        """编辑模式切换"""
        # 先保存当前内容
        if self._current_chapter:
            old_content = (
                self._richtext_editor.get_plain_text()
                if self._current_editor_mode == "richtext"
                else self._markdown_editor.get_plain_text()
            )
            self._current_chapter.content = old_content

        self._show_editor(mode)

        # 切换内容
        if self._current_chapter:
            if mode == "richtext":
                self._richtext_editor.set_content(self._current_chapter.content)
            else:
                self._markdown_editor.set_content(self._current_chapter.content)

        self._toolbar.set_visual_only(mode)

    def _on_model_switched(self, model_id: str):
        """AI模型切换"""
        if model_id and self._context_builder:
            self._context_builder.set_current_model(model_id)
            self._update_status(f"已切换至模型: {model_id}")
            # 自动同步上下文
            if self._current_chapter and self._model_client:
                self._sync_context()

    def _on_agent_action(self, action_id: str):
        """Agent操作触发"""
        if self._offline_mode:
            self._update_status("离线模式下Agent不可用")
            return

        if not self._model_client:
            self._update_status("未配置AI模型，请先到设置中添加")
            return

        action_names = {
            "plot_generate": "情节生成",
            "polish": "文本润色",
            "check_settings": "设定校验",
            "outline": "生成大纲",
            "fill_details": "填充细节",
        }
        action_name = action_names.get(action_id, action_id)
        self._update_status(f"Agent: 正在执行{action_name}...")

        # 异步调用AI模型
        self._context_builder.set_current_action(action_id)
        context = self._context_builder.build_context()

        # 使用线程异步调用
        self._agent_thread = QThread()
        # TODO: 实现Agent工作线程

    def _on_content_changed(self, text: str):
        """编辑器内容变化"""
        if self._current_chapter:
            WordCounter.count_words(
                text, self._status_bar.get_current_rule()
            )

    def _on_word_count_rule_changed(self, rule: str):
        """字数统计规则切换"""
        self._update_word_count()

    def _on_offline_toggled(self, offline: bool):
        """离线模式切换"""
        self._offline_mode = offline
        self._toolbar.set_agent_enabled(not offline)
        if offline:
            self._update_status("已切换至离线模式（仅本地编辑）")
            self._suggestion_bar.hide()
            self._warning_panel.hide()
        else:
            self._update_status("已恢复在线模式")
            self._suggestion_bar.show()
            self._warning_panel.show()

    # ========== 项目管理 ==========

    def _on_project_selected(self, project_id: str):
        """选择项目"""
        try:
            project = self._project_mgr.open_project(project_id)
            self._project_mgr.set_current_project(project)

            # 刷新章节列表
            chapters = self._project_mgr.get_chapters(project_id)
            for ch in chapters:
                self._project_panel.add_chapter_item(
                    project_id, ch.id, ch.title, ch.word_count
                )

            # 刷新设定库
            self._project_panel.refresh_character_list(
                self._project_mgr.get_characters(project_id)
            )
            self._project_panel.refresh_world_tree(
                self._project_mgr.get_world_rules(project_id)
            )

            self._update_status(f"已打开项目: {project.name}")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", str(e))

    def _on_chapter_selected(self, project_id: str, chapter_id: str):
        """选择章节"""
        chapter = self._project_mgr.get_chapter(project_id, chapter_id)
        if chapter:
            self._on_save()  # 先保存当前章节
            self._current_chapter = chapter

            if self._current_editor_mode == "richtext":
                self._richtext_editor.set_content(chapter.content)
            else:
                self._markdown_editor.set_content(chapter.content)

            self._update_word_count()
            self._update_status(f"正在编辑: {chapter.title}")

    def _on_chapter_added(self, project_id: str):
        """添加章节"""
        title, ok = QInputDialog.getText(self, "新建章节", "章节标题:")
        if ok and title:
            chapter = self._project_mgr.create_chapter(project_id, title)
            self._project_panel.add_chapter_item(
                project_id, chapter.id, title
            )

    def _on_chapter_deleted(self, project_id: str, chapter_id: str):
        """删除章节"""
        self._project_mgr.delete_chapter(project_id, chapter_id)
        self._project_panel.remove_chapter_item(project_id, chapter_id)
        if self._current_chapter and self._current_chapter.id == chapter_id:
            self._current_chapter = None
            if self._current_editor_mode == "richtext":
                self._richtext_editor.clear()
            else:
                self._markdown_editor.set_content("")

    def _on_project_deleted(self, project_id: str):
        """删除项目"""
        self._project_mgr.delete_project(project_id)
        self._project_panel.clear_all()
        self._current_chapter = None

    # ========== 设定管理 ==========

    def _on_character_added(self, project_id: str):
        """添加人设"""
        name, ok = QInputDialog.getText(self, "添加人设", "角色名称:")
        if ok and name:
            char = self._project_mgr.add_character(project_id, name)
            self._project_panel.refresh_character_list(
                self._project_mgr.get_characters(project_id)
            )
            self._update_status(f"已添加人设: {name}")

    def _on_world_rule_added(self, project_id: str, category: str, name: str):
        """添加世界观规则"""
        if name:
            rule = self._project_mgr.add_world_rule(project_id, category, name)
            self._project_panel.refresh_world_tree(
                self._project_mgr.get_world_rules(project_id)
            )
            self._update_status(f"已添加世界观规则: {name}")

    # ========== 设置 ==========

    def _on_manage_models(self):
        """打开模型管理"""
        dialog = ModelManagerDialog(self._storage_mgr, self._master_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新工具栏模型列表
            self._refresh_models()

    def _on_warning_config(self):
        """预警配置"""
        dialog = WarningConfigDialog(self._settings_mgr, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._settings_mgr.settings = dialog.get_settings()

    def _on_app_settings(self):
        """应用设置"""
        QMessageBox.information(self, "提示", "应用设置功能即将实现")

    def _on_change_password(self):
        """修改密码"""
        old_pwd, ok1 = QInputDialog.getText(
            self, "修改密码", "请输入旧密码:",
            QLineEdit.EchoMode.Password
        )
        if not ok1:
            return

        new_pwd, ok2 = QInputDialog.getText(
            self, "修改密码", "请输入新密码:",
            QLineEdit.EchoMode.Password
        )
        if not ok2:
            return

        try:
            new_key = self._auth_mgr.change_password(old_pwd, new_pwd)
            self._master_key = new_key
            self._storage_mgr.set_master_key(new_key)
            self._backup_mgr.set_master_key(new_key)
            # TODO: 用新密钥重新加密所有数据
            QMessageBox.information(self, "成功", "密码修改成功")
        except AuthError as e:
            QMessageBox.warning(self, "修改失败", str(e))

    # ========== 备份 ==========

    def _start_backup_timer(self):
        """启动自动备份定时器"""
        interval = self._settings_mgr.get_setting("backup_interval_minutes", 10)
        self._backup_timer.start(interval * 60 * 1000)

    def _auto_backup(self):
        """自动备份"""
        self._on_save()
        project = self._project_mgr.get_current_project()
        if not project:
            return
        try:
            self._backup_mgr.create_backup(
                project.id,
                self._project_mgr.get_export_data(project.id)["project"],
                [c.to_dict() for c in self._project_mgr.get_chapters(project.id)],
                {},
                "自动备份"
            )
            self._status_bar.update_backup_status(
                time.strftime('%H:%M:%S'), False
            )
        except Exception:
            pass

    def _on_manual_backup(self):
        """手动备份"""
        self._on_save()
        project = self._project_mgr.get_current_project()
        if not project:
            QMessageBox.information(self, "提示", "请先打开一个项目")
            return

        try:
            export_data = self._project_mgr.get_export_data(project.id)
            self._backup_mgr.create_backup(
                project.id,
                export_data["project"],
                export_data["chapters"],
                export_data["settings_lib"],
                "手动备份"
            )
            self._update_status("手动备份完成")
        except Exception as e:
            QMessageBox.critical(self, "备份失败", str(e))

    def _on_view_backups(self):
        """查看备份版本"""
        project = self._project_mgr.get_current_project()
        if not project:
            QMessageBox.information(self, "提示", "请先打开一个项目")
            return

        dialog = BackupDialog(
            self._backup_mgr, project.id, self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 执行回滚
            version = dialog.get_selected_version()
            if version:
                try:
                    data = self._backup_mgr.restore_backup(project.id, version)
                    QMessageBox.information(self, "回滚成功", f"已回滚至版本 v{version}")
                except Exception as e:
                    QMessageBox.critical(self, "回滚失败", str(e))

    # ========== 版权 ==========

    def _on_copyright(self):
        """生成版权追溯文档"""
        project = self._project_mgr.get_current_project()
        if not project:
            return

        chapters = self._project_mgr.get_chapters(project.id)
        # 统计内容类型
        stats = {"original": 0, "ai_generated": 0, "ai_assisted": 0}
        for ch in chapters:
            for mark in ch.content_marks:
                if mark.content_type in stats:
                    stats[mark.content_type] += 1

        doc = f"创作追溯文档 - {project.name}\n"
        doc += "=" * 50 + "\n\n"
        doc += f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        doc += f"章节总数: {len(chapters)}\n"
        doc += f"总字数: {WordCounter.count_total_words(chapters)}字\n\n"
        doc += "内容类型统计:\n"
        doc += f"  纯原创: {stats['original']} 段\n"
        doc += f"  AI生成: {stats['ai_generated']} 段\n"
        doc += f"  AI辅助修改: {stats['ai_assisted']} 段\n"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存版权追溯文档",
            os.path.expanduser(f"~/Desktop/{project.name}_版权追溯"),
            "文本文件 (*.txt)"
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(doc)
            self._update_status("版权追溯文档已生成")

    # ========== 建议处理 ==========

    def _on_suggestion_accepted(self, suggestion_text: str):
        """接受Agent建议"""
        if self._current_editor_mode == "richtext":
            self._richtext_editor.insert_at_cursor(suggestion_text)
        else:
            self._markdown_editor.insert_at_cursor(suggestion_text)
        self._update_status("已插入Agent建议")

    # ========== 工具方法 ==========

    def _browse_path(self, line_edit: QLineEdit):
        """浏览文件夹"""
        path = QFileDialog.getExistingDirectory(self, "选择存储路径")
        if path:
            line_edit.setText(path)

    def _update_word_count(self):
        """更新字数统计"""
        if not self._current_chapter:
            return

        if self._current_editor_mode == "richtext":
            content = self._richtext_editor.get_plain_text()
            selected = self._richtext_editor.get_selected_text()
        else:
            content = self._markdown_editor.get_plain_text()
            selected = self._markdown_editor.get_selected_text()

        rule = self._status_bar.get_current_rule()
        chapter_count = WordCounter.count_chapter_words(content, rule)
        selected_count = WordCounter.count_selected_words(selected, rule) if selected else 0

        project = self._project_mgr.get_current_project()
        total_count = 0
        if project:
            total_count = WordCounter.count_total_words(
                self._project_mgr.get_chapters(project.id), rule
            )

        self._status_bar.update_word_count(chapter_count, total_count, selected_count)

    def _update_status(self, message: str):
        """更新状态栏消息"""
        self.statusBar().showMessage(message, 5000)

    def _refresh_models(self):
        """刷新工具栏模型列表"""
        # 从存储加载模型配置
        models = []  # TODO: 加载模型配置
        self._toolbar.update_models(models)

    def _sync_context(self):
        """同步创作上下文到AI模型"""
        if not self._context_builder or not self._model_client:
            return
        # TODO: 实现上下文同步
        pass

    def _load_settings(self):
        """加载应用设置"""
        settings = self._settings_mgr.settings
        self._toolbar.set_mode(settings.editor_mode)
        self._status_bar.set_offline_mode(settings.offline_mode)

    def _load_projects(self):
        """加载已有项目列表"""
        self._project_mgr.load_all_projects()
        for project in self._project_mgr.list_projects():
            self._project_panel.add_project_item(project.id, project.name)

    def _on_about(self):
        """关于对话框"""
        QMessageBox.about(
            self, "关于",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "一款以Agent深度协同+本地化隐私保护为核心的\n"
            "自用小说编辑器。\n\n"
            "100%本地存储 · AES-256加密 · 支持多AI模型\n"
            "纯免费 · 无云端上传 · 隐私安全\n\n"
            "技术栈: Python + PyQt6"
        )

    def _on_agent_trigger(self):
        """手动召唤Agent"""
        self._toolbar._show_agent_menu()

    def closeEvent(self, event):
        """关闭窗口前保存"""
        self._on_save()
        event.accept()
