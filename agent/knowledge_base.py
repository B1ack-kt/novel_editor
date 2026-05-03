"""
创作知识库 - Agent的知识记忆系统
自动抓取并记忆：章节正文、人设库、世界观库、大纲、用户修改记录
知识库仅本地存储，实时更新，支持手动编辑/删除
"""

import json
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str = ""
    category: str = ""          # chapter / character / world / outline / change_log
    content: str = ""           # 知识内容
    source: str = ""            # 来源标识
    tags: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_manual: bool = False     # 是否手动创建


class KnowledgeBase:
    """
    创作知识库
    本地存储，实时同步项目数据
    """

    def __init__(self):
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._project_id: str = ""
        self._index: Dict[str, List[str]] = {}  # category -> [entry_ids]

    def set_project(self, project_id: str):
        """设置当前项目"""
        self._project_id = project_id
        self._entries.clear()
        self._index.clear()

    def sync_chapter(self, chapter_id: str, title: str, content: str):
        """
        同步章节内容到知识库
        关键信息自动提取：人名、地名、关键事件
        """
        entry_id = f"chapter_{chapter_id}"

        # 提取关键信息
        key_info = self._extract_key_info(content)

        entry = KnowledgeEntry(
            id=entry_id,
            category="chapter",
            content=json.dumps({
                "title": title,
                "content_summary": content[:2000],  # 存储摘要用于上下文
                "key_info": key_info,
                "length": len(content)
            }, ensure_ascii=False),
            source=f"章节: {title}",
            tags=["chapter", chapter_id]
        )

        self._entries[entry_id] = entry
        self._index.setdefault("chapter", []).append(entry_id)

    def sync_character(self, character_id: str, name: str, fields: list):
        """同步人设到知识库"""
        entry_id = f"character_{character_id}"
        fields_dict = {f.get("key", ""): f.get("value", "") for f in fields}

        entry = KnowledgeEntry(
            id=entry_id,
            category="character",
            content=json.dumps({"name": name, "fields": fields_dict}, ensure_ascii=False),
            source=f"人设: {name}",
            tags=["character", character_id, name]
        )

        self._entries[entry_id] = entry
        self._index.setdefault("character", []).append(entry_id)

    def sync_world_rule(self, rule_id: str, category: str, name: str, content: str):
        """同步世界观规则到知识库"""
        entry_id = f"world_{rule_id}"

        entry = KnowledgeEntry(
            id=entry_id,
            category="world",
            content=json.dumps({
                "category": category, "name": name, "content": content
            }, ensure_ascii=False),
            source=f"世界观: {name}",
            tags=["world", category, rule_id]
        )

        self._entries[entry_id] = entry
        self._index.setdefault("world", []).append(entry_id)

    def sync_outline(self, outline_content: str):
        """同步大纲"""
        entry_id = "outline_main"

        entry = KnowledgeEntry(
            id=entry_id,
            category="outline",
            content=outline_content,
            source="小说大纲",
            tags=["outline"]
        )

        self._entries[entry_id] = entry
        self._index.setdefault("outline", []).append(entry_id)

    def record_change(self, description: str, old_content: str = "",
                      new_content: str = ""):
        """记录修改日志"""
        entry_id = f"change_{int(time.time() * 1000)}"

        entry = KnowledgeEntry(
            id=entry_id,
            category="change_log",
            content=json.dumps({
                "description": description,
                "old_snippet": old_content[:200],
                "new_snippet": new_content[:200]
            }, ensure_ascii=False),
            source="修改记录",
            tags=["change_log"]
        )

        self._entries[entry_id] = entry
        self._index.setdefault("change_log", []).append(entry_id)

        # 限制修改日志数量
        logs = self._index.get("change_log", [])
        if len(logs) > 100:
            to_remove = logs[:-100]
            for rid in to_remove:
                self._entries.pop(rid, None)
                logs.remove(rid)

    def add_manual_entry(self, category: str, content: str, source: str,
                         tags: list = None) -> str:
        """手动添加知识条目"""
        entry_id = f"manual_{int(time.time() * 1000)}"

        entry = KnowledgeEntry(
            id=entry_id,
            category=category,
            content=content,
            source=source,
            tags=tags or [],
            is_manual=True
        )

        self._entries[entry_id] = entry
        self._index.setdefault(category, []).append(entry_id)
        return entry_id

    def update_entry(self, entry_id: str, content: str):
        """更新知识条目"""
        if entry_id in self._entries:
            self._entries[entry_id].content = content
            self._entries[entry_id].updated_at = time.time()

    def delete_entry(self, entry_id: str):
        """删除知识条目"""
        entry = self._entries.pop(entry_id, None)
        if entry:
            cat_list = self._index.get(entry.category, [])
            if entry_id in cat_list:
                cat_list.remove(entry_id)

    def get_entries(self, category: str = "") -> List[KnowledgeEntry]:
        """获取知识条目"""
        if category:
            ids = self._index.get(category, [])
            return [self._entries[eid] for eid in ids if eid in self._entries]
        return list(self._entries.values())

    def search(self, query: str) -> List[KnowledgeEntry]:
        """搜索知识库"""
        results = []
        query_lower = query.lower()
        for entry in self._entries.values():
            if query_lower in entry.content.lower() or \
               query_lower in entry.source.lower() or \
               any(query_lower in tag.lower() for tag in entry.tags):
                results.append(entry)
        return results

    def get_context_summary(self, max_chars: int = 10000) -> str:
        """
        生成知识库摘要，用于AI模型上下文

        Returns:
            JSON格式的知识库摘要
        """
        summary = {
            "characters": [],
            "world_rules": [],
            "outline": "",
            "recent_changes": []
        }

        # 人设摘要
        for char_id in self._index.get("character", []):
            entry = self._entries.get(char_id)
            if entry:
                try:
                    data = json.loads(entry.content)
                    summary["characters"].append({
                        "name": data.get("name", ""),
                        "fields": data.get("fields", {})
                    })
                except json.JSONDecodeError:
                    pass

        # 世界观摘要
        for world_id in self._index.get("world", []):
            entry = self._entries.get(world_id)
            if entry:
                try:
                    data = json.loads(entry.content)
                    summary["world_rules"].append({
                        "category": data.get("category", ""),
                        "name": data.get("name", ""),
                        "content": data.get("content", "")[:300]
                    })
                except json.JSONDecodeError:
                    pass

        # 大纲
        outline_ids = self._index.get("outline", [])
        if outline_ids:
            summary["outline"] = self._entries.get(outline_ids[0],
                                                   KnowledgeEntry()).content[:2000]

        # 最近修改
        change_ids = self._index.get("change_log", [])[-5:]
        for cid in change_ids:
            entry = self._entries.get(cid)
            if entry:
                summary["recent_changes"].append(entry.content)

        summary_str = json.dumps(summary, ensure_ascii=False)
        if len(summary_str) > max_chars:
            # 缩减世界规则内容
            for wr in summary["world_rules"]:
                wr["content"] = wr["content"][:100]
            summary_str = json.dumps(summary, ensure_ascii=False)

        return summary_str[:max_chars]

    def _extract_key_info(self, content: str) -> dict:
        """
        从文本中提取关键信息
        使用启发式方法提取人名、地名、关键事件

        Note: 此为基础实现，更精确的实体识别需依赖AI模型或NLP库
        """
        info = {
            "potential_names": [],
            "potential_places": [],
            "key_events": []
        }

        # 简单提取：中英文名、特殊标记等
        import re

        # 中文名(2-4字，跟在"说""道""喊"等前后)
        name_patterns = [
            r'(?:^|\n|。|，|！|？)([\u4e00-\u9fff]{2,4})(?:说|道|喊|问|答|想|笑|哭)',
            r'(?:说|道|喊|问|答)(?:了|着)?[：:]?[\u4e00-\u9fff]{2,4}'
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            info["potential_names"].extend(matches[:5])  # 最多5个

        # 地点模式
        place_patterns = [
            r'(?:在|到|去|从)([\u4e00-\u9fff]{2,6})(?:的|，|。|！)',
            r'([\u4e00-\u9fff]{2,4})(?:城|国|镇|村|山|海|林|谷|殿|寺|庙)'
        ]
        for pattern in place_patterns:
            matches = re.findall(pattern, content)
            info["potential_places"].extend(matches[:5])

        # 关键事件：章节开始/结尾的重大变化
        # 简化为提取前几句的开头
        first_sentences = re.split(r'[。！？]', content)[:3]
        info["key_events"] = [s[:50] for s in first_sentences if len(s) > 10]

        return info

    def to_dict(self) -> dict:
        """序列化"""
        return {
            "project_id": self._project_id,
            "entries": {k: {
                "id": e.id, "category": e.category, "content": e.content,
                "source": e.source, "tags": e.tags,
                "created_at": e.created_at, "updated_at": e.updated_at,
                "is_manual": e.is_manual
            } for k, e in self._entries.items()},
            "index": self._index
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeBase":
        """反序列化"""
        kb = cls()
        kb._project_id = data.get("project_id", "")
        kb._entries = {}
        for k, v in data.get("entries", {}).items():
            entry = KnowledgeEntry(
                id=v["id"], category=v["category"], content=v["content"],
                source=v["source"], tags=v.get("tags", []),
                created_at=v.get("created_at", 0), updated_at=v.get("updated_at", 0),
                is_manual=v.get("is_manual", False)
            )
            kb._entries[k] = entry
        kb._index = data.get("index", {})
        return kb
