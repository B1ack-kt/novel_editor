"""
主动建议引擎 - Agent主动创作建议
触发场景：卡壳预警(5分钟无输入)、章节结尾(写完后5秒)、细节补充(未引用设定)
"""

import time
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass, field


@dataclass
class Suggestion:
    """创作建议"""
    id: str = ""
    category: str = ""      # 情节分支 / 细节补充 / 文笔优化
    text: str = ""
    action_type: str = ""   # insert / replace / reference
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)


class SuggestionEngine:
    """
    主动建议引擎
    监控创作状态，在触发条件满足时生成建议
    """

    def __init__(self):
        self._last_input_time: float = time.time()
        self._current_content: str = ""
        self._selected_text: str = ""
        self._chapters: List = []
        self._characters: List = []
        self._world_rules: List = []
        self._current_chapter_index: int = -1

        # 配置
        self._stuck_threshold: float = 300      # 卡壳阈值：5分钟
        self._chapter_end_delay: float = 5       # 章节结尾延迟：5秒
        self._enable_suggestions: bool = True
        self._enabled_categories: List[str] = ["情节分支", "细节补充", "文笔优化"]

        # 回调
        self._on_suggestion: Optional[Callable] = None
        self._on_suggestions_ready: Optional[Callable] = None

        # 监控定时器
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False

    def set_data(self, chapters: List, characters: List, world_rules: List):
        """设置创作数据"""
        self._chapters = chapters
        self._characters = characters
        self._world_rules = world_rules

    def set_enabled_categories(self, categories: List[str]):
        """设置启用的建议分类"""
        self._enabled_categories = categories

    def enable(self, enabled: bool):
        """启用/禁用建议"""
        self._enable_suggestions = enabled

    def set_on_suggestion(self, callback: Callable):
        """设置建议就绪回调"""
        self._on_suggestion = callback

    def start_monitoring(self):
        """开始监控创作状态"""
        if self._running:
            return
        self._running = True
        self._last_input_time = time.time()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """停止监控"""
        self._running = False

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 检测卡壳
                idle_time = time.time() - self._last_input_time
                if idle_time >= self._stuck_threshold:
                    suggestions = self._generate_stuck_suggestions()
                    if suggestions and self._on_suggestion:
                        for s in suggestions:
                            self._on_suggestion(s)
                    self._last_input_time = time.time()  # 避免重复触发

                # 检测章节结尾
                if self._current_chapter_index >= 0 and self._check_chapter_end():
                    time.sleep(self._chapter_end_delay)
                    if self._running:
                        suggestions = self._generate_chapter_end_suggestions()
                        if suggestions and self._on_suggestion:
                            for s in suggestions:
                                self._on_suggestion(s)

            except Exception:
                pass

            time.sleep(5)  # 每5秒检测一次

    def on_user_input(self, content: str, selected_text: str = ""):
        """
        用户输入回调

        Args:
            content: 当前内容
            selected_text: 选中内容
        """
        self._last_input_time = time.time()
        self._current_content = content
        self._selected_text = selected_text

    def on_chapter_complete(self, chapter_index: int):
        """章节完成回调"""
        self._current_chapter_index = chapter_index

    def _check_chapter_end(self) -> bool:
        """检查是否刚完成一个章节"""
        # 简化判断：内容以章节结尾标记结束
        end_markers = ["第", "章", "未完待续", "（本章完）", "(本章完)",
                       "---", "***", "END", "# 第"]
        content_end = self._current_content[-200:] if len(self._current_content) > 200 else self._current_content

        # 如果最后200字中有章节标记且刚刚有输入
        has_marker = any(marker in content_end for marker in end_markers)
        recent_input = (time.time() - self._last_input_time) < 10

        return has_marker and recent_input

    def _generate_stuck_suggestions(self) -> List[Suggestion]:
        """
        生成卡壳建议
        当用户5分钟无输入时触发
        """
        if "情节分支" not in self._enabled_categories:
            return []

        suggestions = []
        current = self._current_content

        if len(current) < 100:
            return suggestions

        # 基于当前内容的最后一段生成提示
        last_para = current.split('\n')[-1] if current else ""

        suggestions.append(Suggestion(
            id=f"stuck_{int(time.time())}_1",
            category="情节分支",
            text=f"你已停留5分钟。基于当前场景，可以尝试：\n1. 引入一个新角色打破僵局\n2. 让场景发生意外转折\n3. 切换到另一条故事线\n\n当前结尾：{last_para[:100]}...",
            action_type="reference",
            confidence=0.7
        ))

        return suggestions

    def _generate_chapter_end_suggestions(self) -> List[Suggestion]:
        """生成章节结尾建议"""
        suggestions = []

        # 细节补充建议
        if "细节补充" in self._enabled_categories:
            # 检查是否有未引用的设定
            all_content = " ".join([getattr(c, 'content', '') for c in self._chapters])
            for char in self._characters:
                name = getattr(char, 'name', '')
                if name and name not in all_content:
                    suggestions.append(Suggestion(
                        id=f"detail_{int(time.time())}",
                        category="细节补充",
                        text=f"已创建人设「{name}」尚未在正文中出现。是否在本章结尾引入此角色？",
                        action_type="reference",
                        confidence=0.6
                    ))

        # 章节结尾续写建议
        if "情节分支" in self._enabled_categories:
            current_end = self._current_content[-300:] if len(self._current_content) > 300 else self._current_content
            suggestions.append(Suggestion(
                id=f"plot_{int(time.time())}",
                category="情节分支",
                text="章节已完成！下一章可以：\n1. 从另一个角色的视角展开同一事件\n2. 时间跳跃到关键事件发生的时刻\n3. 揭示此章节中隐藏的伏笔",
                action_type="reference",
                confidence=0.8
            ))

        return suggestions

    def generate_detail_suggestions(self, scene_content: str) -> List[Suggestion]:
        """
        生成细节补充建议
        检查当前场景是否可以补充已设定的角色特征
        """
        suggestions = []

        for char in self._characters:
            name = getattr(char, 'name', '')
            if not name or name not in scene_content:
                continue

            # 检查角色的自定义字段是否有可用于场景的特征
            custom_fields = getattr(char, 'custom_fields', [])
            for field in custom_fields:
                if hasattr(field, 'key'):
                    key = field.key
                    value = field.value
                    if key in ("外貌", "特殊技能") and value and value not in scene_content:
                        suggestions.append(Suggestion(
                            id=f"detail_{char.id}_{key}",
                            category="细节补充",
                            text=f"建议在「{name}」出现的场景中体现{key}特征：「{value[:50]}」",
                            action_type="insert",
                            confidence=0.65
                        ))

        return suggestions

    def generate_style_suggestions(self, selected_text: str) -> List[Suggestion]:
        """
        文笔优化建议
        """
        suggestions = []

        if not selected_text or len(selected_text) < 30:
            return suggestions

        # 简单的文笔检测
        # 检查是否过度使用"的"
        count_de = selected_text.count('的')
        if count_de > len(selected_text) // 20:  # 平均每20字一个"的"
            suggestions.append(Suggestion(
                id=f"style_de_{int(time.time())}",
                category="文笔优化",
                text="此段落中「的」字使用较多，可适当精简使文笔更流畅",
                action_type="reference",
                confidence=0.5
            ))

        # 检查是否连续多句以同一开头
        sentences = [s.strip()[:5] for s in selected_text.replace('！', '。').replace('？', '。').split('。') if s.strip()]
        if len(sentences) > 3:
            first_words = Counter(sentences)
            most_common_count = first_words.most_common(1)[0][1]
            if most_common_count >= 3:
                suggestions.append(Suggestion(
                    id=f"style_start_{int(time.time())}",
                    category="文笔优化",
                    text="多句连续以相同的词语开头，建议调整句式结构增加变化",
                    action_type="reference",
                    confidence=0.55
                ))

        return suggestions
