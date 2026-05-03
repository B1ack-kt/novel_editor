"""
Warning数据模型 - 预警数据结构
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WarningSuggestion:
    """预警建议"""
    text: str                     # 建议内容
    action_type: str = "fix"      # fix / alternative / reference
    score: float = 0.0            # 建议置信度

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "action_type": self.action_type,
            "score": self.score
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WarningSuggestion":
        return cls(
            text=data.get("text", ""),
            action_type=data.get("action_type", "fix"),
            score=data.get("score", 0.0)
        )


@dataclass
class Warning:
    """创作预警数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    chapter_id: str = ""
    warning_type: str = ""         # character_conflict / world_conflict / plot_hole / repetition / unreferenced_setting
    severity: str = "medium"       # low / medium / high
    start_pos: int = 0             # 预警文本起始位置
    end_pos: int = 0               # 预警文本结束位置
    description: str = ""          # 冲突原因描述
    suggestions: list = field(default_factory=list)  # WarningSuggestion列表
    ignored: bool = False          # 是否已忽略
    whitelisted: bool = False      # 是否已加入白名单
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "warning_type": self.warning_type,
            "severity": self.severity,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "description": self.description,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "ignored": self.ignored,
            "whitelisted": self.whitelisted,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Warning":
        suggestions = [WarningSuggestion.from_dict(s) for s in data.get("suggestions", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            chapter_id=data.get("chapter_id", ""),
            warning_type=data.get("warning_type", ""),
            severity=data.get("severity", "medium"),
            start_pos=data.get("start_pos", 0),
            end_pos=data.get("end_pos", 0),
            description=data.get("description", ""),
            suggestions=suggestions,
            ignored=data.get("ignored", False),
            whitelisted=data.get("whitelisted", False),
            created_at=data.get("created_at", time.time())
        )


@dataclass
class WhitelistEntry:
    """预警白名单条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    warning_type: str = ""         # 预警类型
    pattern: str = ""              # 匹配模式
    scope: str = "global"          # chapter / global
    chapter_id: str = ""           # scope=chapter时的章节ID
    reason: str = ""               # 加入白名单原因
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "warning_type": self.warning_type,
            "pattern": self.pattern,
            "scope": self.scope,
            "chapter_id": self.chapter_id,
            "reason": self.reason,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WhitelistEntry":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            project_id=data.get("project_id", ""),
            warning_type=data.get("warning_type", ""),
            pattern=data.get("pattern", ""),
            scope=data.get("scope", "global"),
            chapter_id=data.get("chapter_id", ""),
            reason=data.get("reason", ""),
            created_at=data.get("created_at", time.time())
        )
