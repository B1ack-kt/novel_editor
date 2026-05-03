"""
Agent菜单 - 手动召唤Agent的弹出式功能菜单
快捷键Ctrl+A，右键菜单，工具栏按钮均可触发
"""

from PyQt6.QtWidgets import (
    QMenu, QAction, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


AGENT_ACTIONS = [
    {
        "id": "plot_generate",
        "name": "情节生成",
        "description": "根据当前上下文生成情节分支建议",
        "icon": ""
    },
    {
        "id": "polish",
        "name": "文本润色",
        "description": "优化选中文笔、修辞和表达",
        "icon": ""
    },
    {
        "id": "check_settings",
        "name": "设定校验",
        "description": "检查当前章节与设定库的一致性",
        "icon": ""
    },
    {
        "id": "outline",
        "name": "生成大纲",
        "description": "为当前项目生成章节大纲",
        "icon": ""
    },
    {
        "id": "fill_details",
        "name": "填充细节",
        "description": "根据设定库补充场景/人物细节描写",
        "icon": ""
    },
    {
        "id": "expand_paragraph",
        "name": "段落扩写",
        "description": "将选中段落扩展为更丰富的内容",
        "icon": ""
    },
    {
        "id": "summarize",
        "name": "内容总结",
        "description": "总结当前章节内容",
        "icon": ""
    },
    {
        "id": "dialogue_generate",
        "name": "对话生成",
        "description": "为当前场景生成角色对话",
        "icon": ""
    },
]


def create_agent_menu(parent=None) -> QMenu:
    """创建Agent功能菜单"""
    menu = QMenu("Agent辅助", parent)
    menu.setStyleSheet("""
        QMenu {
            background-color: white;
            border: 1px solid #DDD;
            border-radius: 8px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #E3F2FD;
        }
    """)

    for action_info in AGENT_ACTIONS:
        action = QAction(action_info["name"], menu)
        action.setToolTip(action_info["description"])
        action.setData(action_info["id"])
        menu.addAction(action)

    return menu


class AgentDialog(QDialog):
    """Agent功能弹窗（用于可视化选择）"""

    action_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agent 辅助功能")
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("选择Agent功能")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        for action_info in AGENT_ACTIONS:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 10px;
                }
                QFrame:hover {
                    border-color: #1565C0;
                    background-color: #F3F8FF;
                }
            """)
            frame_layout = QHBoxLayout(frame)

            info_layout = QVBoxLayout()
            name_label = QLabel(action_info["name"])
            name_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
            info_layout.addWidget(name_label)

            desc_label = QLabel(action_info["description"])
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)

            frame_layout.addLayout(info_layout)

            btn = QPushButton("执行")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90D9;
                    color: white;
                    border: none;
                    padding: 6px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #357ABD;
                }
            """)
            btn.clicked.connect(
                lambda checked, a=action_info["id"]: self._on_action(a)
            )
            frame_layout.addWidget(btn)

            layout.addWidget(frame)

    def _on_action(self, action_id: str):
        self.action_selected.emit(action_id)
        self.accept()
