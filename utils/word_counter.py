"""
字数统计工具 - 章节/全书/选中段落字数统计
支持两种统计规则：包含标点空格 / 仅文字
"""

import re
from typing import Tuple


class WordCounter:
    """字数统计工具"""

    @staticmethod
    def count_words(text: str, rule: str = "include_all") -> int:
        """
        统计文本字数

        Args:
            text: 输入文本
            rule: "include_all" 包含标点/空格, "text_only" 仅文字

        Returns:
            字数
        """
        if not text:
            return 0

        if rule == "text_only":
            # 仅统计中文字符+英文字母
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_words = len(re.findall(r'[a-zA-Z]+', text))
            return chinese_chars + english_words
        else:
            # 包含所有字符(不计换行)
            cleaned = text.replace('\n', '').replace('\r', '').replace(' ', '')
            # 统计中文字符
            chinese = len(re.findall(r'[\u4e00-\u9fff]', cleaned))
            # 统计英文单词
            english = len(re.findall(r'[a-zA-Z]+', cleaned))
            # 统计数字序列
            digits = len(re.findall(r'\d+', cleaned))
            # 标点符号
            punctuation = len(re.findall(r'[，。！？；：""''（）【】《》\-,.!?;:()\[\]\'\"…—]', cleaned))
            return chinese + english + digits + punctuation

    @staticmethod
    def count_chapter_words(text: str, rule: str = "include_all") -> int:
        """
        统计章节字数（与count_words相同，预留独立扩展点）
        """
        return WordCounter.count_words(text, rule)

    @staticmethod
    def count_selected_words(text: str, rule: str = "include_all") -> int:
        """
        统计选中文本字数
        """
        return WordCounter.count_words(text, rule)

    @staticmethod
    def count_total_words(chapters: list, rule: str = "include_all") -> int:
        """
        统计全书总字数

        Args:
            chapters: Chapter列表
            rule: 统计规则

        Returns:
            全书总字数
        """
        total = 0
        for chapter in chapters:
            total += WordCounter.count_words(chapter.content, rule)
        return total

    @staticmethod
    def format_count(count: int) -> str:
        """格式化字数显示"""
        if count >= 10000:
            return f"{count/10000:.1f}万字"
        elif count >= 1000:
            return f"{count}字"
        else:
            return f"{count}字"

    @staticmethod
    def get_rule_display(rule: str) -> str:
        """获取统计规则显示名称"""
        rules = {
            "include_all": "包含标点/空格",
            "text_only": "仅文字"
        }
        return rules.get(rule, rule)
