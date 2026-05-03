"""
WorldRule数据模型 - 世界观规则数据结构
支持多层级子项与分类间联动
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorldRuleLink:
    """世界观规则关联联动"""
    linked_rule_id: str          # 关联的规则ID
    link_desc: str = ""          # 关联描述
    is_bidirectional: bool = True

    def to_dict(self) -> dict:
        return {
            "linked_rule_id": self.linked_rule_id,
            "link_desc": self.link_desc,
            "is_bidirectional": self.is_bidirectional
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldRuleLink":
        return cls(
            linked_rule_id=data.get("linked_rule_id", ""),
            link_desc=data.get("link_desc", ""),
            is_bidirectional=data.get("is_bidirectional", True)
        )


@dataclass
class WorldRule:
    """世界观规则数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    category: str = ""             # 主分类: 魔法体系/社会制度/地理设定/时间线
    name: str = ""
    content: str = ""              # 规则内容
    parent_id: str = ""            # 父规则ID(空=顶级规则),支持多层嵌套
    children: list = field(default_factory=list)    # 子规则ID列表
    linked_rules: list = field(default_factory=list) # WorldRuleLink列表
    order: int = 0                 # 排序
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "category": self.category,
            "name": self.name,
            "content": self.content,
            "parent_id": self.parent_id,
            "children": self.children,
            "linked_rules": [l.to_dict() for l in self.linked_rules],
            "order": self.order,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldRule":
        links = [WorldRuleLink.from_dict(l) for l in data.get("linked_rules", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            category=data.get("category", ""),
            name=data.get("name", ""),
            content=data.get("content", ""),
            parent_id=data.get("parent_id", ""),
            children=data.get("children", []),
            linked_rules=links,
            order=data.get("order", 0),
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time())
        )

    def touch(self):
        self.modified_at = time.time()
