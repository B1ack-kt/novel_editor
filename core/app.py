"""
应用主控制器 - 全局状态管理与模块协调
协调认证→存储→项目管理→编辑器→Agent全链路
"""

import os
import sys
import json
import time
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from config.settings import SettingsManager
from config.constants import APP_NAME, DEFAULT_STORAGE_DIR
from core.auth import AuthManager, AuthError
from core.storage import StorageManager
from core.crypto import encrypt_json, decrypt_json, CryptoError
from core.project_manager import ProjectManager
from core.backup import BackupManager
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


class Application:
    """
    应用主控制器
    管理整个应用的生命周期
    """

    def __init__(self):
        self._qt_app: Optional[QApplication] = None
        self._settings_mgr = SettingsManager()
        self._auth_mgr = AuthManager()
        self._storage_mgr: Optional[StorageManager] = None
        self._project_mgr: Optional[ProjectManager] = None
        self._backup_mgr: Optional[BackupManager] = None
        self._main_window: Optional[MainWindow] = None
        self._master_key: Optional[bytes] = None

        # 数据目录
        self._data_dir = ""

    def run(self):
        """启动应用"""
        self._qt_app = QApplication(sys.argv)
        self._qt_app.setApplicationName(APP_NAME)
        self._qt_app.setStyle("Fusion")

        # 设置全局样式
        self._qt_app.setStyleSheet("""
            * {
                font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            }
            QToolTip {
                background-color: #333;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
        """)

        # 1. 初始化数据目录
        self._init_data_dir()

        # 2. 加载认证数据
        self._load_auth_data()

        # 3. 显示登录对话框
        if not self._show_login():
            return  # 用户取消登录

        # 4. 初始化各管理器
        self._init_managers()

        # 5. 显示主窗口
        self._show_main_window()

        # 6. 进入事件循环
        sys.exit(self._qt_app.exec())

    def _init_data_dir(self):
        """初始化数据存储目录"""
        # 默认存储在用户目录下的 NovelEditor 文件夹
        home = os.path.expanduser("~")
        data_dir = os.path.join(home, DEFAULT_STORAGE_DIR)

        # 检查是否有已保存的自定义路径
        config_path = os.path.join(home, ".novel_editor_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    data_dir = config.get("data_dir", data_dir)
            except Exception:
                pass

        os.makedirs(data_dir, exist_ok=True)
        self._data_dir = data_dir

    def _load_auth_data(self):
        """尝试加载已有认证数据"""
        auth_file = os.path.join(self._data_dir, "auth.enc")

        if os.path.exists(auth_file):
            # 已有认证文件，但不在此处解密（登录时才解密）
            self._auth_mgr._auth_file = auth_file

    def _show_login(self) -> bool:
        """显示登录对话框

        Returns:
            True=登录成功, False=取消
        """
        auth_file = os.path.join(self._data_dir, "auth.enc")

        if os.path.exists(auth_file):
            # 已有密码
            try:
                with open(auth_file, 'rb') as f:
                    # 这里auth_data未加密存储(仅salt和hash，非明文密码)
                    raw = f.read()
                    data = json.loads(raw.decode('utf-8'))
                    self._auth_mgr.load_auth_data(data)
            except Exception:
                pass

        dialog = LoginDialog(self._auth_mgr)

        if dialog.exec() != LoginDialog.DialogCode.Accepted:
            return False

        self._master_key = self._auth_mgr.get_master_key()

        # 保存认证数据(如果首次设置)
        if self._auth_mgr.is_authenticated():
            auth_data = self._auth_mgr.get_auth_data()
            if auth_data:
                with open(auth_file, 'w', encoding='utf-8') as f:
                    json.dump(auth_data.to_dict(), f, ensure_ascii=False)

        return True

    def _init_managers(self):
        """初始化所有核心管理器"""
        # 存储管理器
        self._storage_mgr = StorageManager(self._master_key)
        self._storage_mgr.set_base_dir(self._data_dir)
        self._settings_mgr.set_master_key(self._master_key)

        # 加载应用设置
        settings_path = os.path.join(self._data_dir, "app_config.enc")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'rb') as f:
                    encrypted = f.read()
                data = decrypt_json(encrypted, self._master_key)
                self._settings_mgr.load_from_json(
                    json.dumps(data, ensure_ascii=False)
                )
            except Exception:
                pass

        # 项目管理器
        self._project_mgr = ProjectManager(
            self._storage_mgr, self._master_key
        )

        # 备份管理器
        self._backup_mgr = BackupManager(
            self._storage_mgr, self._master_key
        )

    def _show_main_window(self):
        """显示主窗口"""
        self._main_window = MainWindow(
            self._settings_mgr,
            self._auth_mgr,
            self._storage_mgr,
            self._project_mgr,
            self._backup_mgr,
            self._master_key
        )
        self._main_window.show()

        # 保存设置定时器（每5分钟自动保存）
        save_timer = QTimer()
        save_timer.timeout.connect(self._auto_save_settings)
        save_timer.start(5 * 60 * 1000)

    def _auto_save_settings(self):
        """自动保存应用设置(加密)"""
        try:
            if self._master_key and self._storage_mgr:
                settings_json = self._settings_mgr.to_json()
                encrypted = encrypt_json(
                    json.loads(settings_json), self._master_key
                )
                settings_path = os.path.join(self._data_dir, "app_config.enc")
                with open(settings_path, 'wb') as f:
                    f.write(encrypted)
        except Exception:
            pass

    @staticmethod
    def check_python_version():
        """检查Python版本"""
        if sys.version_info < (3, 10):
            print("需要 Python 3.10 及以上版本")
            print(f"当前版本: {sys.version}")
            sys.exit(1)

    @staticmethod
    def check_dependencies():
        """检查依赖"""
        missing = []
        try:
            from PyQt6.QtWidgets import QApplication
        except ImportError:
            missing.append("PyQt6")

        try:
            from Crypto.Cipher import AES
        except ImportError:
            missing.append("pycryptodome")

        try:
            import markdown
        except ImportError:
            missing.append("markdown")

        try:
            import httpx
        except ImportError:
            missing.append("httpx")

        if missing:
            print("缺少以下依赖:")
            for m in missing:
                print(f"  - {m}")
            print(f"\n请运行: pip install -r requirements.txt")
            sys.exit(1)
