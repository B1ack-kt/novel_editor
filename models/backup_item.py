"""
BackupItem数据模型 - 备份项数据结构
"""

import uuid
import time
from dataclasses import dataclass, field


@dataclass
class BackupItem:
    """备份项数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    file_path: str = ""               # 备份文件绝对路径
    version: int = 1                  # 版本号
    file_size: int = 0                # 文件大小(字节)
    description: str = ""             # 备份说明
    is_encrypted: bool = True         # 是否加密
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "version": self.version,
            "file_size": self.file_size,
            "description": self.description,
            "is_encrypted": self.is_encrypted,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupItem":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            file_path=data.get("file_path", ""),
            version=data.get("version", 1),
            file_size=data.get("file_size", 0),
            description=data.get("description", ""),
            is_encrypted=data.get("is_encrypted", True),
            created_at=data.get("created_at", time.time())
        )
