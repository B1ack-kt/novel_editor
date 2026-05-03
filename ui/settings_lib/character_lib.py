"""
人设库详情对话框 - 人设的编辑/字段管理
支持：预设字段、自定义字段、图片上传、角色关联
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QTabWidget, QWidget,
    QFileDialog, QDialogButtonBox, QMessageBox, QScrollArea,
    QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

from config.constants import CHARACTER_DEFAULT_FIELDS, FIELD_TYPES


class CharacterDetailDialog(QDialog):
    """人设详情对话框"""

    character_saved = pyqtSignal(dict)  # 保存的人设数据

    def __init__(self, character=None, all_characters=None, parent=None):
        """
        Args:
            character: Character对象(编辑模式)或None(新建模式)
            all_characters: 所有角色列表(用于字段联动)
        """
        super().__init__(parent)
        self._character = character
        self._all_characters = all_characters or []
        self._custom_fields_widgets = []  # (key_input, value_input, type_combo) tuples
        self._setup_ui()

        if character:
            self._load_character_data()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("人设详情")
        self.setMinimumSize(550, 600)
        self.setStyleSheet("""
            QDialog { background-color: #FAFAFA; }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #DDD; border-radius: 4px; padding: 6px; font-size: 13px;
            }
            QGroupBox { font-weight: bold; border: 1px solid #DDD; border-radius: 6px;
                        margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

        layout = QVBoxLayout(self)

        # 基本字段
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("角色名称")
        basic_layout.addRow("姓名:", self._name_input)
        layout.addWidget(basic_group)

        # 预设字段
        preset_group = QGroupBox("预设字段")
        preset_layout = QFormLayout(preset_group)

        self._preset_widgets = {}
        for field_name in CHARACTER_DEFAULT_FIELDS:
            if field_name == "姓名":
                continue
            widget = QTextEdit()
            widget.setMaximumHeight(80)
            widget.setPlaceholderText(f"请输入{field_name}")
            preset_layout.addRow(f"{field_name}:", widget)
            self._preset_widgets[field_name] = widget

        layout.addWidget(preset_group)

        # 自定义字段
        custom_group = QGroupBox("自定义字段")
        self._custom_layout = QVBoxLayout(custom_group)

        add_btn = QPushButton("+ 添加自定义字段")
        add_btn.clicked.connect(self._add_custom_field)
        self._custom_layout.addWidget(add_btn)

        layout.addWidget(custom_group)

        # 角色关联（字段联动）
        link_group = QGroupBox("角色关联")
        link_layout = QVBoxLayout(link_group)

        self._link_list = QListWidget()
        self._link_list.setMaximumHeight(120)
        link_layout.addWidget(QLabel("关联的角色及关系:"))
        link_layout.addWidget(self._link_list)

        add_link_btn = QPushButton("+ 添加关联")
        add_link_btn.clicked.connect(self._add_character_link)
        link_layout.addWidget(add_link_btn)

        layout.addWidget(link_group)

        # 图片
        img_group = QGroupBox("人设图片")
        img_layout = QHBoxLayout(img_group)

        self._img_label = QLabel("无图片")
        self._img_label.setFixedSize(120, 120)
        self._img_label.setStyleSheet("border: 1px dashed #CCC; background-color: #F5F5F5;")
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_layout.addWidget(self._img_label)

        img_btn_layout = QVBoxLayout()
        upload_btn = QPushButton("上传图片")
        upload_btn.clicked.connect(self._on_upload_image)
        img_btn_layout.addWidget(upload_btn)

        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(lambda: self._img_label.setText("无图片"))
        img_btn_layout.addWidget(clear_btn)
        img_btn_layout.addStretch()
        img_layout.addLayout(img_btn_layout)

        layout.addWidget(img_group)

        # 备注
        note_group = QGroupBox("备注")
        note_layout = QVBoxLayout(note_group)
        self._notes_input = QTextEdit()
        self._notes_input.setMaximumHeight(80)
        self._notes_input.setPlaceholderText("其他备注信息...")
        note_layout.addWidget(self._notes_input)
        layout.addWidget(note_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_custom_field(self):
        """添加自定义字段行"""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        key_input = QLineEdit()
        key_input.setPlaceholderText("字段名")
        row_layout.addWidget(key_input)

        value_input = QLineEdit()
        value_input.setPlaceholderText("字段值")
        row_layout.addWidget(value_input)

        type_combo = QComboBox()
        type_combo.addItems(FIELD_TYPES)
        row_layout.addWidget(type_combo)

        remove_btn = QPushButton("X")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_custom_field(row_widget))
        row_layout.addWidget(remove_btn)

        # 插入到添加按钮之前
        insert_pos = self._custom_layout.count() - 1
        self._custom_layout.insertWidget(insert_pos, row_widget)
        self._custom_fields_widgets.append((key_input, value_input, type_combo))

    def _remove_custom_field(self, row_widget):
        """移除自定义字段"""
        for i, (k, v, t) in enumerate(self._custom_fields_widgets):
            if k.parent() == row_widget:
                self._custom_fields_widgets.pop(i)
                break
        self._custom_layout.removeWidget(row_widget)
        row_widget.deleteLater()

    def _add_character_link(self):
        """添加角色关联"""
        if not self._all_characters:
            QMessageBox.information(self, "提示", "暂无可关联的角色")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("添加角色关联")
        layout = QFormLayout(dialog)

        char_combo = QComboBox()
        for c in self._all_characters:
            if c.id != (self._character.id if self._character else ""):
                char_combo.addItem(c.name, c.id)
        layout.addRow("关联角色:", char_combo)

        relation_input = QLineEdit()
        relation_input.setPlaceholderText("如: 恋人、师徒、敌对...")
        layout.addRow("关系:", relation_input)

        bidirectional_check = QCheckBox("双向关系")
        bidirectional_check.setChecked(True)
        layout.addRow("", bidirectional_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = f"{char_combo.currentText()} → {relation_input.text()}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, char_combo.currentData())
            self._link_list.addItem(item)

    def _on_upload_image(self):
        """上传人设图片"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择人设图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if filepath:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._img_label.setPixmap(scaled)
                self._img_label.setProperty("path", filepath)

    def _load_character_data(self):
        """加载已有角色数据"""
        if not self._character:
            return
        self._name_input.setText(self._character.name)

        # 预设字段
        for field in self._character.custom_fields:
            if field.key in self._preset_widgets:
                self._preset_widgets[field.key].setPlainText(field.value)
            else:
                # 自定义字段
                self._add_custom_field_row(field.key, field.value, field.field_type)

        # 角色关联
        for link in self._character.linked_characters:
            text = f"{link.linked_character_id} → {link.relation_desc}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, link.linked_character_id)
            self._link_list.addItem(item)

        self._notes_input.setPlainText(self._character.notes)

    def _add_custom_field_row(self, key: str, value: str, field_type: str):
        """添加已有自定义字段行"""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        key_input = QLineEdit(key)
        row_layout.addWidget(key_input)

        value_input = QLineEdit(value)
        row_layout.addWidget(value_input)

        type_combo = QComboBox()
        type_combo.addItems(FIELD_TYPES)
        type_combo.setCurrentText(field_type)
        row_layout.addWidget(type_combo)

        remove_btn = QPushButton("X")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_custom_field(row_widget))
        row_layout.addWidget(remove_btn)

        insert_pos = self._custom_layout.count() - 1
        self._custom_layout.insertWidget(insert_pos, row_widget)
        self._custom_fields_widgets.append((key_input, value_input, type_combo))

    def _on_save(self):
        """保存人设数据"""
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入角色名称")
            return

        # 收集数据
        data = {"name": name, "custom_fields": [], "linked_characters": [], "notes": ""}

        # 预设字段
        for field_name, widget in self._preset_widgets.items():
            value = widget.toPlainText().strip()
            if value:
                data["custom_fields"].append({
                    "key": field_name, "value": value, "field_type": "text"
                })

        # 自定义字段
        for key_input, value_input, type_combo in self._custom_fields_widgets:
            key = key_input.text().strip()
            value = value_input.text().strip()
            if key:
                data["custom_fields"].append({
                    "key": key, "value": value,
                    "field_type": type_combo.currentText()
                })

        # 角色关联
        for i in range(self._link_list.count()):
            item = self._link_list.item(i)
            data["linked_characters"].append({
                "linked_character_id": item.data(Qt.ItemDataRole.UserRole),
                "relation_desc": item.text()
            })

        data["notes"] = self._notes_input.toPlainText()
        data["image_path"] = self._img_label.property("path") or ""

        self.character_saved.emit(data)
        self.accept()
