"""
Character数据模型 - 人设/角色数据结构
支持自定义字段与字段联动
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CharacterField:
    """自定义字段"""
    key: str                # 字段名
    value: str = ""         # 字段值
    field_type: str = "text"  # text / image / dropdown / richtext
    options: list = field(default_factory=list)  # dropdown类型时的选项列表

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "field_type": self.field_type,
            "options": self.options
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterField":
        return cls(
            key=data.get("key", ""),
            value=data.get("value", ""),
            field_type=data.get("field_type", "text"),
            options=data.get("options", [])
        )


@dataclass
class CharacterLink:
    """角色关联关系（字段联动）"""
    linked_character_id: str      # 关联的角色ID
    relation_desc: str = ""       # 关系描述(如"恋人""师徒""敌对")
    is_bidirectional: bool = True # 是否双向关系

    def to_dict(self) -> dict:
        return {
            "linked_character_id": self.linked_character_id,
            "relation_desc": self.relation_desc,
            "is_bidirectional": self.is_bidirectional
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterLink":
        return cls(
            linked_character_id=data.get("linked_character_id", ""),
            relation_desc=data.get("relation_desc", ""),
            is_bidirectional=data.get("is_bidirectional", True)
        )


@dataclass
class Character:
    """人设数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    name: str = ""
    custom_fields: list = field(default_factory=list)    # CharacterField列表
    image_path: str = ""                                  # 人设图片(本地路径)
    notes: str = ""                                       # 备注
    linked_characters: list = field(default_factory=list) # CharacterLink列表
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def get_field(self, key: str) -> Optional[CharacterField]:
        """获取指定字段"""
        for f in self.custom_fields:
            if f.key == key:
                return f
        return None

    def set_field(self, key: str, value: str, field_type: str = "text"):
        """设置字段值，存在则更新，不存在则新增"""
        existing = self.get_field(key)
        if existing:
            existing.value = value
        else:
            self.custom_fields.append(CharacterField(key=key, value=value, field_type=field_type))
        self.touch()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "custom_fields": [f.to_dict() for f in self.custom_fields],
            "image_path": self.image_path,
            "notes": self.notes,
            "linked_characters": [l.to_dict() for l in self.linked_characters],
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        fields = [CharacterField.from_dict(f) for f in data.get("custom_fields", [])]
        links = [CharacterLink.from_dict(l) for l in data.get("linked_characters", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            name=data.get("name", ""),
            custom_fields=fields,
            image_path=data.get("image_path", ""),
            notes=data.get("notes", ""),
            linked_characters=links,
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time())
        )

    def touch(self):
        self.modified_at = time.time()
