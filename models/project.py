"""
Project数据模型 - 小说项目核心数据结构
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Project:
    """小说项目数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "未命名项目"
    storage_path: str = ""                    # 项目根目录绝对路径
    is_encrypted: bool = False                # 是否启用独立密码
    password_hash: str = ""                   # 项目独立密码哈希(salt+hash)
    password_salt: str = ""                   # 密码盐值
    chapters: list = field(default_factory=list)       # 章节ID列表
    character_ids: list = field(default_factory=list)  # 人设ID列表
    world_rule_ids: list = field(default_factory=list) # 世界观规则ID列表
    settings: dict = field(default_factory=dict)       # 项目级设置
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "storage_path": self.storage_path,
            "is_encrypted": self.is_encrypted,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "chapters": self.chapters,
            "character_ids": self.character_ids,
            "world_rule_ids": self.world_rule_ids,
            "settings": self.settings,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """从字典反序列化"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "未命名项目"),
            storage_path=data.get("storage_path", ""),
            is_encrypted=data.get("is_encrypted", False),
            password_hash=data.get("password_hash", ""),
            password_salt=data.get("password_salt", ""),
            chapters=data.get("chapters", []),
            character_ids=data.get("character_ids", []),
            world_rule_ids=data.get("world_rule_ids", []),
            settings=data.get("settings", {}),
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time())
        )

    def touch(self):
        """更新修改时间"""
        self.modified_at = time.time()
