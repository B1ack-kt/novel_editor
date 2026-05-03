"""
Chapter数据模型 - 章节数据结构
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentMark:
    """内容类型标记"""
    start_pos: int        # 标记起始位置
    end_pos: int          # 标记结束位置
    content_type: str     # original / ai_generated / ai_assisted
    model_name: str = ""  # 生成模型名称
    created_at: float = field(default_factory=time.time)
    modified_count: int = 0  # 修改次数

    def to_dict(self) -> dict:
        return {
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "content_type": self.content_type,
            "model_name": self.model_name,
            "created_at": self.created_at,
            "modified_count": self.modified_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContentMark":
        return cls(
            start_pos=data.get("start_pos", 0),
            end_pos=data.get("end_pos", 0),
            content_type=data.get("content_type", "original"),
            model_name=data.get("model_name", ""),
            created_at=data.get("created_at", time.time()),
            modified_count=data.get("modified_count", 0)
        )


@dataclass
class Chapter:
    """章节数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    title: str = "新章节"
    content: str = ""                         # 正文内容(纯文本/Markdown)
    content_type: str = "text"                # "rich_text" / "markdown"
    order: int = 0                            # 章节排序
    word_count: int = 0                       # 字数
    content_marks: list = field(default_factory=list)  # ContentMark列表
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "order": self.order,
            "word_count": self.word_count,
            "content_marks": [m.to_dict() for m in self.content_marks],
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chapter":
        marks = [ContentMark.from_dict(m) for m in data.get("content_marks", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            title=data.get("title", "新章节"),
            content=data.get("content", ""),
            content_type=data.get("content_type", "text"),
            order=data.get("order", 0),
            word_count=data.get("word_count", 0),
            content_marks=marks,
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time())
        )

    def touch(self):
        """更新修改时间"""
        self.modified_at = time.time()
