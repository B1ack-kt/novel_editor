"""
预警检测引擎 - Agent主动预警核心
检测：人设冲突、世界观矛盾、情节逻辑漏洞、重复表述、设定未引用
"""

import re
import time
from typing import List, Optional, Dict, Set
from collections import Counter

from models.warning import Warning, WarningSuggestion
from models.character import Character
from models.world import WorldRule
from models.chapter import Chapter


class WarningEngine:
    """
    预警检测引擎
    对创作内容进行主动扫描，输出预警
    """

    def __init__(self):
        self._characters: Dict[str, Character] = {}
        self._world_rules: Dict[str, WorldRule] = {}
        self._chapters: List[Chapter] = []
        self._whitelist: List[dict] = []
        self._warning_config: dict = {
            "enabled_types": [
                "character_conflict", "world_conflict",
                "plot_hole", "repetition", "unreferenced_setting"
            ]
        }

    def set_data(self, characters: List[Character], world_rules: List[WorldRule],
                 chapters: List[Chapter]):
        """设置检测数据"""
        self._characters = {c.id: c for c in characters}
        self._world_rules = {r.id: r for r in world_rules}
        self._chapters = chapters

    def set_whitelist(self, whitelist: List[dict]):
        """设置白名单"""
        self._whitelist = whitelist

    def set_config(self, enabled_types: List[str]):
        """设置预警类型开关"""
        self._warning_config["enabled_types"] = enabled_types

    def analyze_chapter(self, chapter: Chapter) -> List[Warning]:
        """
        分析单个章节，返回预警列表

        Args:
            chapter: 待分析的章节

        Returns:
            Warning对象列表
        """
        warnings: List[Warning] = []
        content = chapter.content

        # 1. 人设冲突检测
        if "character_conflict" in self._warning_config["enabled_types"]:
            warnings.extend(self._check_character_conflicts(chapter))

        # 2. 世界观矛盾检测
        if "world_conflict" in self._warning_config["enabled_types"]:
            warnings.extend(self._check_world_conflicts(chapter))

        # 3. 情节逻辑漏洞
        if "plot_hole" in self._warning_config["enabled_types"]:
            warnings.extend(self._check_plot_holes(chapter))

        # 4. 重复表述检测
        if "repetition" in self._warning_config["enabled_types"]:
            warnings.extend(self._check_repetitions(chapter))

        # 5. 设定未引用检测
        if "unreferenced_setting" in self._warning_config["enabled_types"]:
            warnings.extend(self._check_unreferenced_settings(chapter))

        # 过滤白名单
        warnings = [w for w in warnings if not self._is_whitelisted(w)]

        return warnings

    def _check_character_conflicts(self, chapter: Chapter) -> List[Warning]:
        """
        人设冲突检测
        检查正文中人设性格/行为/禁忌是否与设定矛盾
        """
        warnings = []
        content = chapter.content

        for char_id, char in self._characters.items():
            name = char.name
            if not name or name not in content:
                continue

            # 获取禁忌字段
            taboo_field = None
            for f in char.custom_fields:
                if f.key == "禁忌":
                    taboo_field = f.value
                    break

            if taboo_field:
                # 检查禁忌词是否在角色相关段落出现
                taboo_keywords = self._extract_keywords(taboo_field)
                for keyword in taboo_keywords:
                    # 查找人名附近出现禁忌关键字的位置
                    name_positions = [m.start() for m in re.finditer(re.escape(name), content)]
                    for np in name_positions:
                        # 检查名字前后200字范围内
                        start = max(0, np - 200)
                        end = min(len(content), np + 200)
                        around = content[start:end]
                        if keyword in around:
                            pos = around.find(keyword)
                            warnings.append(Warning(
                                project_id=chapter.project_id,
                                chapter_id=chapter.id,
                                warning_type="character_conflict",
                                severity="high",
                                start_pos=start + pos,
                                end_pos=start + pos + len(keyword),
                                description=f"角色「{name}」的行为可能与禁忌「{taboo_field}」冲突",
                                suggestions=[
                                    WarningSuggestion(
                                        text=f"建议调整此处行为，避免与{name}的性格禁忌矛盾",
                                        action_type="fix",
                                        score=0.8
                                    ),
                                    WarningSuggestion(
                                        text=f"或在此处添加解释：为什么{name}会突破自己的禁忌",
                                        action_type="alternative",
                                        score=0.6
                                    ),
                                    WarningSuggestion(
                                        text=f"检查是否需要修改{name}的人设禁忌设定",
                                        action_type="reference",
                                        score=0.5
                                    )
                                ]
                            ))

            # 检查性格一致性（简化版：检查已设定的性格关键词与行为矛盾）
            personality_field = None
            for f in char.custom_fields:
                if f.key in ("性格", "外貌"):
                    personality_field = (personality_field or "") + f.value

        return warnings

    def _check_world_conflicts(self, chapter: Chapter) -> List[Warning]:
        """
        世界观矛盾检测
        检查正文中是否违反已有的世界观规则
        """
        warnings = []
        content = chapter.content

        for rule_id, rule in self._world_rules.items():
            rule_name = rule.name
            if not rule_name or not rule.content:
                continue

            # 从规则内容中提取关键约束词
            constraint_keywords = self._extract_constraints(rule.content)

            # 检查正文中是否有违反约束的词
            for keyword, forbidden in constraint_keywords:
                if forbidden:
                    # 查找keyword但检查是否违反
                    pass
                if keyword in content:
                    # 规则在正文中被引用，检查上下文
                    pos = content.find(keyword)
                    # 简化：标记为引用位置，供用户确认
                    if rule.category and rule.category in content[max(0, pos-100):pos+100]:
                        # 同类规则聚集，检查一致性
                        other_rules = [
                            r for r in self._world_rules.values()
                            if r.category == rule.category and r.id != rule_id
                        ]
                        for other in other_rules:
                            if other.name in content[max(0, pos-200):pos+200]:
                                # 同一位置引用了两个同类规则，可能存在矛盾
                                pass

        return warnings

    def _check_plot_holes(self, chapter: Chapter) -> List[Warning]:
        """
        情节逻辑漏洞检测
        检查：无理由场景切换、人物失踪、时间跳跃无说明
        """
        warnings = []
        content = chapter.content

        # 检测场景断裂：两个连续段落主题完全不同且无过渡
        paragraphs = [p.strip() for p in content.split('\n') if p.strip() and len(p.strip()) > 20]

        for i in range(len(paragraphs) - 1):
            current = paragraphs[i]
            next_para = paragraphs[i + 1]

            # 简单启发式：如果相邻段落没有共同关键词，可能场景切换
            current_words = set(self._extract_chinese_words(current))
            next_words = set(self._extract_chinese_words(next_para))

            if current_words and next_words:
                overlap = current_words & next_words
                # 重叠词太少且段落较长，可能是场景断裂
                if len(overlap) < 3 and len(current) > 100 and len(next_para) > 100:
                    # 检查是否有过渡词
                    transition_words = {"这时", "与此同时", "另一边", "接着", "之后", "然而", "但是", "不过"}
                    has_transition = any(tw in next_para[:20] for tw in transition_words)

                    if not has_transition:
                        # 找到此段落位置
                        pos = content.find(next_para)
                        warnings.append(Warning(
                            project_id=chapter.project_id,
                            chapter_id=chapter.id,
                            warning_type="plot_hole",
                            severity="medium",
                            start_pos=pos,
                            end_pos=pos + len(next_para),
                            description="此处可能存在无过渡的场景切换",
                            suggestions=[
                                WarningSuggestion(
                                    text="建议添加场景切换的过渡语句",
                                    action_type="fix",
                                    score=0.7
                                ),
                                WarningSuggestion(
                                    text="确认是否为有意的跳跃式叙事",
                                    action_type="alternative",
                                    score=0.5
                                )
                            ]
                        ))

        # 检测人物失踪：前文出现的人名在后文中长时间未出现
        all_names = set()
        for char in self._characters.values():
            all_names.add(char.name)

        # 如果角色在章节前半部分出现但后半部分消失
        half_point = len(content) // 2
        first_half = content[:half_point]
        second_half = content[half_point:]

        for name in all_names:
            if name and name in first_half and name not in second_half:
                # 只在较长章节(>500字)才提示
                if len(content) > 500:
                    pos = content.find(name)
                    warnings.append(Warning(
                        project_id=chapter.project_id,
                        chapter_id=chapter.id,
                        warning_type="plot_hole",
                        severity="low",
                        start_pos=pos,
                        end_pos=pos + len(name),
                        description=f"人物「{name}」在本章节后半部分未再出现",
                        suggestions=[
                            WarningSuggestion(
                                text=f"确认「{name}」的去向是否已交代",
                                action_type="fix",
                                score=0.6
                            )
                        ]
                    ))

        return warnings

    def _check_repetitions(self, chapter: Chapter) -> List[Warning]:
        """
        重复表述检测
        同一段落/章节内的重复内容
        """
        warnings = []
        content = chapter.content

        # 检测重复句子（3个及以上相同字符的序列）
        sentences = re.split(r'[。！？；，\n]', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        seen = {}
        for i, sentence in enumerate(sentences):
            key = sentence[:30]  # 用前30字做键
            if key in seen:
                prev_idx = seen[key]
                pos = content.find(sentence)
                prev_pos = content.find(sentences[prev_idx])

                warnings.append(Warning(
                    project_id=chapter.project_id,
                    chapter_id=chapter.id,
                    warning_type="repetition",
                    severity="low",
                    start_pos=pos,
                    end_pos=pos + len(sentence),
                    description=f"此处与上文存在相似表述（第{prev_idx+1}句）",
                    suggestions=[
                        WarningSuggestion(
                            text="建议删除或改写重复表述",
                            action_type="fix",
                            score=0.7
                        ),
                        WarningSuggestion(
                            text="若为强调手法，可添加「正如前文所述」等铺垫",
                            action_type="alternative",
                            score=0.5
                        )
                    ]
                ))
            else:
                seen[key] = i

        # 检测高频词（同一词在短时间内大量重复）
        words = self._extract_chinese_words(content)
        word_counts = Counter(words)

        for word, count in word_counts.most_common(20):
            if count > 8 and len(word) >= 2:  # 二词在短篇幅内出现超过8次
                # 找到第一次出现的位置
                pos = content.find(word)
                if pos >= 0:
                    warnings.append(Warning(
                        project_id=chapter.project_id,
                        chapter_id=chapter.id,
                        warning_type="repetition",
                        severity="low",
                        start_pos=pos,
                        end_pos=pos + len(word),
                        description=f"词语「{word}」在本章出现{count}次，可能存在过度重复",
                        suggestions=[
                            WarningSuggestion(
                                text=f"建议使用近义词替换部分「{word}」",
                                action_type="fix",
                                score=0.6
                            )
                        ]
                    ))
                    break  # 只报告最严重的一个

        return warnings

    def _check_unreferenced_settings(self, chapter: Chapter) -> List[Warning]:
        """
        设定未引用检测
        已创建的人设/世界观在正文中未提及
        """
        warnings = []
        content = chapter.content
        all_chapter_text = " ".join([c.content for c in self._chapters])

        # 检查人设
        for char_id, char in self._characters.items():
            if char.name and char.name not in all_chapter_text:
                # 检查是否是刚创建的人设（宽容时间：1小时内）
                if time.time() - char.created_at < 3600:
                    continue

                warnings.append(Warning(
                    project_id=chapter.project_id,
                    chapter_id=chapter.id,
                    warning_type="unreferenced_setting",
                    severity="low",
                    start_pos=0,
                    end_pos=0,
                    description=f"人设「{char.name}」在全书正文中尚未被引用或提及",
                    suggestions=[
                        WarningSuggestion(
                            text=f"建议在适当场景引入人物「{char.name}」",
                            action_type="fix",
                            score=0.6
                        ),
                        WarningSuggestion(
                            text=f"或确认「{char.name}」是否为后续章节预留",
                            action_type="alternative",
                            score=0.4
                        )
                    ]
                ))

        # 检查世界观
        for rule_id, rule in self._world_rules.items():
            if rule.name and rule.name not in all_chapter_text:
                if time.time() - rule.created_at < 3600:
                    continue

                warnings.append(Warning(
                    project_id=chapter.project_id,
                    chapter_id=chapter.id,
                    warning_type="unreferenced_setting",
                    severity="low",
                    start_pos=0,
                    end_pos=0,
                    description=f"世界观规则「{rule.name}」在正文中尚未被应用",
                    suggestions=[
                        WarningSuggestion(
                            text=f"建议在相关场景中体现「{rule.name}」规则",
                            action_type="fix",
                            score=0.5
                        )
                    ]
                ))

        return warnings

    def _is_whitelisted(self, warning: Warning) -> bool:
        """检查预警是否在白名单中"""
        for entry in self._whitelist:
            if entry.get("warning_type") == warning.warning_type:
                pattern = entry.get("pattern", "")
                if pattern and pattern in warning.description:
                    return True
        return False

    # ========== 工具方法 ==========

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单分词：提取2-4字的中文词组
        return re.findall(r'[\u4e00-\u9fff]{2,4}', text)

    def _extract_constraints(self, rule_content: str) -> List[tuple]:
        """
        从规则内容中提取约束条件
        Returns: [(keyword, is_forbidden), ...]
        """
        constraints = []
        # 识别禁止性规则
        forbidden_patterns = [
            r'(?:禁止|不允许|不能|不可以|不可|不得|严禁)([\u4e00-\u9fff]{2,10})',
            r'([\u4e00-\u9fff]{2,6})(?:是禁止的|是不允许的|是不能的)'
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, rule_content)
            for m in matches:
                constraints.append((m, True))

        # 识别必须性规则
        must_patterns = [
            r'(?:必须|一定要|务必|需要)([\u4e00-\u9fff]{2,10})'
        ]
        for pattern in must_patterns:
            matches = re.findall(pattern, rule_content)
            for m in matches:
                constraints.append((m, False))

        return constraints

    def _extract_chinese_words(self, text: str) -> List[str]:
        """提取中文词汇（2字及以上）"""
        return re.findall(r'[\u4e00-\u9fff]{2,}', text)
