"""
上下文构建器 - 为Agent构建创作知识库上下文
自动抓取并记忆：章节正文、人设库、世界观库、大纲、用户修改记录
知识库仅本地存储，实时更新
"""

import json
import time
from typing import Optional, Dict, List
from dataclasses import dataclass, field


@dataclass
class ContextSnapshot:
    """上下文快照"""
    project_id: str = ""
    chapter_id: str = ""
    current_content: str = ""         # 当前编辑内容
    selected_text: str = ""           # 选中文本
    characters: dict = field(default_factory=dict)   # {id: Character.to_dict()}
    world_rules: dict = field(default_factory=dict)  # {id: WorldRule.to_dict()}
    chapter_list: list = field(default_factory=list)  # [Chapter.to_dict()]
    recent_warnings: list = field(default_factory=list)
    recent_changes: list = field(default_factory=list)  # 最近修改记录
    current_action: str = ""          # 当前Agent操作类型
    current_model: str = ""           # 当前使用的模型ID
    timestamp: float = field(default_factory=time.time)


class ContextBuilder:
    """
    上下文构建器
    负责从项目中构建Agent理解的上下文
    """

    # 最大上下文字符数限制
    MAX_CONTEXT_CHARS = 32000

    def __init__(self):
        self._snapshot: Optional[ContextSnapshot] = None
        self._change_history: List[dict] = []     # 修改历史
        self._knowledge_cache: dict = {}           # 知识缓存
        self._max_history = 50                     # 最多保留50条修改记录

    def set_project_data(
        self,
        project_id: str,
        chapters: List,
        characters: List,
        world_rules: List
    ):
        """设置项目数据"""
        if not self._snapshot:
            self._snapshot = ContextSnapshot()

        self._snapshot.project_id = project_id
        self._snapshot.chapter_list = [
            ch.to_dict() if hasattr(ch, 'to_dict') else ch
            for ch in chapters
        ]
        self._snapshot.characters = {
            c.id if hasattr(c, 'id') else c.get('id', ''):
            c.to_dict() if hasattr(c, 'to_dict') else c
            for c in characters
        }
        self._snapshot.world_rules = {
            r.id if hasattr(r, 'id') else r.get('id', ''):
            r.to_dict() if hasattr(r, 'to_dict') else r
            for r in world_rules
        }

    def set_current_chapter(self, chapter_id: str, content: str):
        """设置当前编辑的章节"""
        if not self._snapshot:
            self._snapshot = ContextSnapshot()
        self._snapshot.chapter_id = chapter_id
        self._snapshot.current_content = content

    def set_selected_text(self, text: str):
        """设置选中的文本"""
        if self._snapshot:
            self._snapshot.selected_text = text

    def set_current_action(self, action_id: str):
        """设置当前Agent操作"""
        if self._snapshot:
            self._snapshot.current_action = action_id

    def set_current_model(self, model_id: str):
        """设置当前模型"""
        if self._snapshot:
            self._snapshot.current_model = model_id

    def record_change(self, change_type: str, description: str,
                      old_content: str = "", new_content: str = ""):
        """记录一次修改"""
        self._change_history.append({
            "type": change_type,
            "description": description,
            "old_content": old_content[:500],   # 截断长内容
            "new_content": new_content[:500],
            "timestamp": time.time()
        })
        # 限制历史记录数量
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history:]

        if self._snapshot:
            self._snapshot.recent_changes = self._change_history[-10:]

    def set_warnings(self, warnings: List):
        """设置当前预警"""
        if self._snapshot:
            self._snapshot.recent_warnings = [
                w.to_dict() if hasattr(w, 'to_dict') else w
                for w in warnings
            ]

    def build_context(self, max_chars: int = None) -> dict:
        """
        构建Agent所需上下文

        Returns:
            上下文字典，可直接传给ModelClient
        """
        if not self._snapshot:
            return {}

        max_chars = max_chars or self.MAX_CONTEXT_CHARS
        s = self._snapshot

        context = {
            "action": s.current_action,
            "model": s.current_model,
            "current_chapter": {
                "id": s.chapter_id,
                "content": s.current_content[:8000]  # 截断长章节
            },
            "selected_text": s.selected_text[:2000] if s.selected_text else "",
            "characters_summary": self._summarize_characters(s.characters),
            "world_rules_summary": self._summarize_world_rules(s.world_rules),
            "chapter_titles": [
                {"title": ch.get("title", ""), "order": ch.get("order", 0)}
                for ch in s.chapter_list
            ],
            "recent_changes": s.recent_changes[-5:] if s.recent_changes else [],
            "recent_warnings": [
                {"type": w.get("warning_type", ""), "desc": w.get("description", "")}
                for w in (s.recent_warnings or [])
            ]
        }

        # 检查总长度
        context_str = json.dumps(context, ensure_ascii=False)
        if len(context_str) > max_chars:
            # 缩减内容
            context["current_chapter"]["content"] = s.current_content[:3000]
            context.pop("selected_text", None)

        return context

    def _summarize_characters(self, characters: dict) -> List[dict]:
        """汇总人设信息（只提取关键字段）"""
        summary = []
        for cid, cdata in characters.items():
            name = cdata.get("name", cid)
            fields = {}
            for f in cdata.get("custom_fields", []):
                key = f.get("key", "")
                value = f.get("value", "")
                if key and value:
                    fields[key] = value
            summary.append({"name": name, "fields": fields})
        return summary

    def _summarize_world_rules(self, world_rules: dict) -> List[dict]:
        """汇总世界观信息"""
        summary = []
        for rid, rdata in world_rules.items():
            summary.append({
                "category": rdata.get("category", ""),
                "name": rdata.get("name", ""),
                "content": rdata.get("content", "")[:500]
            })
        return summary

    def get_system_prompt(self) -> str:
        """构建系统提示词（包含创作背景）"""
        if not self._snapshot:
            return "你是一位小说创作助手，帮助作者进行创作。"

        characters = self._summarize_characters(self._snapshot.characters)
        world = self._summarize_world_rules(self._snapshot.world_rules)

        prompt_parts = [
            "你是一位专业的小说创作顾问，正在帮助一位作家进行创作。",
            "你的建议应当：",
            "- 保持一致性和逻辑性",
            "- 尊重已有的设定和人设",
            "- 提供具体、可操作的创作建议",
            ""
        ]

        if characters:
            prompt_parts.append("## 当前已登记的人设：")
            for c in characters:
                prompt_parts.append(f"- {c['name']}: {json.dumps(c['fields'], ensure_ascii=False)}")

        if world:
            prompt_parts.append("\n## 当前世界观设定：")
            for w in world:
                prompt_parts.append(f"- [{w['category']}] {w['name']}: {w['content'][:200]}")

        return "\n".join(prompt_parts)

    def clear(self):
        """清空上下文"""
        self._snapshot = None
        self._change_history = []
