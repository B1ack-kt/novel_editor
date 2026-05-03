"""
全局配置管理器(单例) - 管理用户级别设置
所有配置加密存储在本地，不涉及云端
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from .constants import (
    BACKUP_INTERVAL_DEFAULT, DEFAULT_STORAGE_DIR,
    DEFAULT_WARNING_STYLE, WARNING_AGGRESSIVENESS,
    API_TIMEOUT_DEFAULT, API_CALL_RATE_LIMIT, API_LOG_RETENTION_DAYS,
    WORD_COUNT_RULES, FONT_SIZE_DEFAULT, CONTENT_TYPES
)


@dataclass
class AppSettings:
    """应用级别设置（单用户，自用场景）"""
    # 存储
    default_storage_path: str = ""                    # 默认项目存储根路径
    backup_interval_minutes: int = BACKUP_INTERVAL_DEFAULT
    show_backup_folder: bool = False                  # 是否显示隐藏的备份文件夹

    # 编辑器
    editor_mode: str = "richtext"                     # richtext / markdown
    font_size: int = FONT_SIZE_DEFAULT
    word_count_rule: str = "include_all"              # include_all / text_only

    # 预警
    warning_aggressiveness: str = "high"              # high / medium / low
    warning_style: dict = field(default_factory=lambda: dict(DEFAULT_WARNING_STYLE))
    enabled_warning_types: list = field(default_factory=lambda: [
        "character_conflict", "world_conflict", "plot_hole",
        "repetition", "unreferenced_setting"
    ])

    # 建议
    enable_suggestions: bool = True
    suggestion_categories: list = field(default_factory=lambda: ["情节分支", "细节补充", "文笔优化"])

    # API
    api_timeout: int = API_TIMEOUT_DEFAULT
    api_rate_limit: int = API_CALL_RATE_LIMIT
    api_log_retention_days: int = API_LOG_RETENTION_DAYS
    offline_mode: bool = False                        # 离线模式

    # 隐私
    encrypt_data: bool = True                         # 是否加密存储
    auto_clean_logs: bool = True

    def to_dict(self) -> dict:
        return {
            "default_storage_path": self.default_storage_path,
            "backup_interval_minutes": self.backup_interval_minutes,
            "show_backup_folder": self.show_backup_folder,
            "editor_mode": self.editor_mode,
            "font_size": self.font_size,
            "word_count_rule": self.word_count_rule,
            "warning_aggressiveness": self.warning_aggressiveness,
            "warning_style": self.warning_style,
            "enabled_warning_types": self.enabled_warning_types,
            "enable_suggestions": self.enable_suggestions,
            "suggestion_categories": self.suggestion_categories,
            "api_timeout": self.api_timeout,
            "api_rate_limit": self.api_rate_limit,
            "api_log_retention_days": self.api_log_retention_days,
            "offline_mode": self.offline_mode,
            "encrypt_data": self.encrypt_data,
            "auto_clean_logs": self.auto_clean_logs
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        return cls(
            default_storage_path=data.get("default_storage_path", ""),
            backup_interval_minutes=data.get("backup_interval_minutes", BACKUP_INTERVAL_DEFAULT),
            show_backup_folder=data.get("show_backup_folder", False),
            editor_mode=data.get("editor_mode", "richtext"),
            font_size=data.get("font_size", FONT_SIZE_DEFAULT),
            word_count_rule=data.get("word_count_rule", "include_all"),
            warning_aggressiveness=data.get("warning_aggressiveness", "high"),
            warning_style=data.get("warning_style", dict(DEFAULT_WARNING_STYLE)),
            enabled_warning_types=data.get("enabled_warning_types", [
                "character_conflict", "world_conflict", "plot_hole",
                "repetition", "unreferenced_setting"
            ]),
            enable_suggestions=data.get("enable_suggestions", True),
            suggestion_categories=data.get("suggestion_categories", ["情节分支", "细节补充", "文笔优化"]),
            api_timeout=data.get("api_timeout", API_TIMEOUT_DEFAULT),
            api_rate_limit=data.get("api_rate_limit", API_CALL_RATE_LIMIT),
            api_log_retention_days=data.get("api_log_retention_days", API_LOG_RETENTION_DAYS),
            offline_mode=data.get("offline_mode", False),
            encrypt_data=data.get("encrypt_data", True),
            auto_clean_logs=data.get("auto_clean_logs", True)
        )


class SettingsManager:
    """全局配置管理器（单例模式）"""
    _instance: Optional["SettingsManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.settings = AppSettings()
        self._settings_dir = ""
        self._settings_file = "app_config.enc"
        self._master_key: Optional[bytes] = None

    def set_master_key(self, key: bytes):
        """设置主加密密钥"""
        self._master_key = key

    def get_master_key(self) -> Optional[bytes]:
        """获取主加密密钥"""
        return self._master_key

    def set_storage_dir(self, path: str):
        """设置配置存储目录"""
        self._settings_dir = path
        os.makedirs(path, exist_ok=True)

    def get_setting(self, key: str, default=None):
        """获取单项设置"""
        return getattr(self.settings, key, default)

    def update_settings(self, **kwargs):
        """批量更新设置"""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)

    def to_json(self) -> str:
        """导出为JSON字符串（用于加密存储）"""
        return json.dumps(self.settings.to_dict(), ensure_ascii=False, indent=2)

    def load_from_json(self, json_str: str):
        """从JSON字符串加载（解密后）"""
        data = json.loads(json_str)
        self.settings = AppSettings.from_dict(data)
