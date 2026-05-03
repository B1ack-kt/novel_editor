"""
世界观库详情对话框 - 世界观规则的编辑/层级管理
支持：分类创建、多层级子项、分类间联动
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QComboBox,
    QTreeWidget, QTreeWidgetItem, QDialogButtonBox,
    QMessageBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal

from config.constants import WORLD_CATEGORIES


class WorldRuleDetailDialog(QDialog):
    """世界观规则详情对话框"""

    rule_saved = pyqtSignal(dict)

    def __init__(self, rule=None, all_rules=None, parent=None):
        super().__init__(parent)
        self._rule = rule
        self._all_rules = all_rules or []
        self._setup_ui()

        if rule:
            self._load_rule_data()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("世界观规则详情")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog { background-color: #FAFAFA; }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #DDD; border-radius: 4px; padding: 6px; font-size: 13px;
            }
            QGroupBox { font-weight: bold; border: 1px solid #DDD; border-radius: 6px;
                        margin-top: 10px; padding-top: 10px; }
        """)

        layout = QVBoxLayout(self)

        # 基本属性
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)

        self._category_combo = QComboBox()
        self._category_combo.addItems(WORLD_CATEGORIES)
        basic_layout.addRow("分类:", self._category_combo)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("规则名称")
        basic_layout.addRow("名称:", self._name_input)

        self._parent_combo = QComboBox()
        self._parent_combo.addItem("(无，创建为顶级规则)", "")
        for rule in self._all_rules:
            if not rule.parent_id:
                self._parent_combo.addItem(rule.name, rule.id)
        basic_layout.addRow("父规则:", self._parent_combo)

        layout.addWidget(basic_group)

        # 内容
        content_group = QGroupBox("规则内容")
        content_layout = QVBoxLayout(content_group)
        self._content_input = QTextEdit()
        self._content_input.setPlaceholderText("详细描述此世界观的规则、限制、说明等...")
        self._content_input.setMinimumHeight(150)
        content_layout.addWidget(self._content_input)
        layout.addWidget(content_group)

        # 关联规则联动
        link_group = QGroupBox("关联规则")
        link_layout = QVBoxLayout(link_group)

        self._link_tree = QTreeWidget()
        self._link_tree.setHeaderLabels(["关联规则", "描述"])
        self._link_tree.setMaximumHeight(150)
        link_layout.addWidget(self._link_tree)

        add_link_btn = QPushButton("+ 添加关联规则")
        add_link_btn.clicked.connect(self._add_rule_link)
        link_layout.addWidget(add_link_btn)

        layout.addWidget(link_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_rule_link(self):
        """添加规则关联"""
        if not self._all_rules:
            QMessageBox.information(self, "提示", "暂无可关联的规则")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("添加规则关联")
        layout = QFormLayout(dialog)

        rule_combo = QComboBox()
        for r in self._all_rules:
            if r.id != (self._rule.id if self._rule else ""):
                rule_combo.addItem(r.name, r.id)
        layout.addRow("关联规则:", rule_combo)

        desc_input = QLineEdit()
        desc_input.setPlaceholderText("关联描述（如：社会制度由地理决定）")
        layout.addRow("关联描述:", desc_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = QTreeWidgetItem([
                rule_combo.currentText(),
                desc_input.text()
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, rule_combo.currentData())
            self._link_tree.addTopLevelItem(item)

    def _load_rule_data(self):
        """加载已有规则数据"""
        if not self._rule:
            return
        self._category_combo.setCurrentText(self._rule.category)
        self._name_input.setText(self._rule.name)
        self._content_input.setPlainText(self._rule.content)

        # 父规则
        for i in range(self._parent_combo.count()):
            if self._parent_combo.itemData(i) == self._rule.parent_id:
                self._parent_combo.setCurrentIndex(i)
                break

        # 关联规则
        for link in self._rule.linked_rules:
            item = QTreeWidgetItem([link.linked_rule_id, link.link_desc])
            item.setData(0, Qt.ItemDataRole.UserRole, link.linked_rule_id)
            self._link_tree.addTopLevelItem(item)

    def _on_save(self):
        """保存规则数据"""
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入规则名称")
            return

        data = {
            "category": self._category_combo.currentText(),
            "name": name,
            "content": self._content_input.toPlainText(),
            "parent_id": self._parent_combo.currentData() or "",
            "linked_rules": []
        }

        for i in range(self._link_tree.topLevelItemCount()):
            item = self._link_tree.topLevelItem(i)
            data["linked_rules"].append({
                "linked_rule_id": item.data(0, Qt.ItemDataRole.UserRole),
                "link_desc": item.text(1)
            })

        self.rule_saved.emit(data)
        self.accept()
