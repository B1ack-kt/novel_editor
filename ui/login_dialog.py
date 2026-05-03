"""
登录对话框 - 软件启动认证
支持：首次密码设置、密码登录、密码找回、密码修改
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QStackedWidget,
    QWidget, QMessageBox, QCheckBox, QComboBox,
    QFrame, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from core.auth import AuthManager, AuthError
from config.constants import MIN_PASSWORD_LENGTH, APP_NAME, APP_VERSION


class LoginDialog(QDialog):
    """
    登录/注册对话框
    """

    login_success = pyqtSignal(bytes)  # 发送master_key

    def __init__(self, auth_manager: AuthManager, parent=None):
        super().__init__(parent)
        self._auth = auth_manager
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - 登录")
        self.setFixedSize(480, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #DDD;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4A90D9;
            }
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel {
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 图标/标题
        title_label = QLabel(APP_NAME)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333; margin-top: 20px;")
        layout.addWidget(title_label)

        subtitle = QLabel("纯本地 · 隐私安全 · AI协同创作")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(subtitle)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(line)

        # 堆叠页面：首次设置 / 登录 / 找回密码
        self._stack = QStackedWidget()

        self._init_page = self._create_first_time_page()
        self._login_page = self._create_login_page()
        self._recovery_page = self._create_recovery_page()

        self._stack.addWidget(self._init_page)     # index 0
        self._stack.addWidget(self._login_page)    # index 1
        self._stack.addWidget(self._recovery_page) # index 2

        # 判断首次使用
        if self._auth.is_first_time():
            self._stack.setCurrentIndex(0)
        else:
            self._stack.setCurrentIndex(1)

        layout.addWidget(self._stack)

        # 底部提示
        self._hint_label = QLabel("")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("color: #F44336; font-size: 12px;")
        layout.addWidget(self._hint_label)

    def _create_first_time_page(self) -> QWidget:
        """首次密码设置页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        info_label = QLabel("首次使用，请设置登录密码以保护您的创作数据安全\n所有数据将在本地通过AES-256加密存储")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; padding: 10px;")
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(10)

        self._init_pwd = QLineEdit()
        self._init_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._init_pwd.setPlaceholderText(f"至少{MIN_PASSWORD_LENGTH}位字符")
        form.addRow("设置密码:", self._init_pwd)

        self._init_pwd_confirm = QLineEdit()
        self._init_pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._init_pwd_confirm.setPlaceholderText("再次输入密码")
        form.addRow("确认密码:", self._init_pwd_confirm)

        layout.addLayout(form)

        # 找回方式
        group = QGroupBox("密码找回方式（本地存储，不涉及云端）")
        group_layout = QVBoxLayout(group)

        self._init_email = QLineEdit()
        self._init_email.setPlaceholderText("预留邮箱（可选）")
        group_layout.addWidget(self._init_email)

        self._init_question = QComboBox()
        self._init_question.setEditable(True)
        self._init_question.addItems([
            "您最喜欢的书是什么？",
            "您的第一部小说的主角名字？",
            "您童年的梦想是什么？",
            "自定义问题..."
        ])
        group_layout.addWidget(self._init_question)

        self._init_answer = QLineEdit()
        self._init_answer.setPlaceholderText("安全答案")
        group_layout.addWidget(self._init_answer)

        layout.addWidget(group)

        # 按钮
        btn_layout = QHBoxLayout()
        self._init_btn = QPushButton("设置密码并进入")
        self._init_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                padding: 10px 30px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        self._init_btn.clicked.connect(self._on_initial_setup)
        btn_layout.addStretch()
        btn_layout.addWidget(self._init_btn)
        layout.addLayout(btn_layout)

        return page

    def _create_login_page(self) -> QWidget:
        """登录页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        info_label = QLabel("请输入登录密码以解锁编辑器")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #555;")
        layout.addWidget(info_label)

        self._login_pwd = QLineEdit()
        self._login_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._login_pwd.setPlaceholderText("输入登录密码")
        self._login_pwd.returnPressed.connect(self._on_login)
        layout.addWidget(self._login_pwd)

        # 按钮
        btn_layout = QHBoxLayout()

        self._recovery_link = QPushButton("忘记密码？")
        self._recovery_link.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #4A90D9;
                border: none;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #357ABD;
            }
        """)
        self._recovery_link.clicked.connect(lambda: self._stack.setCurrentIndex(2))
        btn_layout.addWidget(self._recovery_link)

        btn_layout.addStretch()

        self._login_btn = QPushButton("登录")
        self._login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                padding: 10px 30px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        self._login_btn.clicked.connect(self._on_login)
        btn_layout.addWidget(self._login_btn)

        layout.addLayout(btn_layout)

        return page

    def _create_recovery_page(self) -> QWidget:
        """密码找回页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        info_label = QLabel("密码找回（仅本地验证）\n请回答您设置的安全问题")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555;")
        layout.addWidget(info_label)

        self._rec_question_label = QLabel("")
        self._rec_question_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self._rec_question_label)

        self._rec_answer = QLineEdit()
        self._rec_answer.setPlaceholderText("输入您的答案")
        layout.addWidget(self._rec_answer)

        self._rec_new_pwd = QLineEdit()
        self._rec_new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._rec_new_pwd.setPlaceholderText(f"新密码（至少{MIN_PASSWORD_LENGTH}位）")
        layout.addWidget(self._rec_new_pwd)

        btn_layout = QHBoxLayout()
        back_btn = QPushButton("返回登录")
        back_btn.setStyleSheet("background: transparent; color: #4A90D9; border: none;")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()

        reset_btn = QPushButton("重置密码")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 30px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        reset_btn.clicked.connect(self._on_reset_password)
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)

        return page

    # ========== 业务逻辑 ==========

    def _on_initial_setup(self):
        """首次设置密码"""
        pwd = self._init_pwd.text()
        pwd_confirm = self._init_pwd_confirm.text()

        if len(pwd) < MIN_PASSWORD_LENGTH:
            self._hint_label.setText(f"密码长度不能少于{MIN_PASSWORD_LENGTH}位")
            return

        if pwd != pwd_confirm:
            self._hint_label.setText("两次密码输入不一致")
            return

        try:
            email = self._init_email.text()
            question = self._init_question.currentText()
            answer = self._init_answer.text()

            master_key = self._auth.set_initial_password(
                pwd, email, question, answer
            )
            self.login_success.emit(master_key)
            self.accept()
        except AuthError as e:
            QMessageBox.warning(self, "设置失败", str(e))

    def _on_login(self):
        """登录验证"""
        pwd = self._login_pwd.text()
        if not pwd:
            self._hint_label.setText("请输入密码")
            return

        try:
            master_key = self._auth.login(pwd)
            self.login_success.emit(master_key)
            self.accept()
        except AuthError as e:
            self._hint_label.setText(str(e))
            self._login_pwd.clear()

    def _on_reset_password(self):
        """重置密码"""
        answer = self._rec_answer.text()
        new_pwd = self._rec_new_pwd.text()

        if not answer:
            self._hint_label.setText("请输入安全答案")
            return

        if len(new_pwd) < MIN_PASSWORD_LENGTH:
            self._hint_label.setText(f"新密码长度不能少于{MIN_PASSWORD_LENGTH}位")
            return

        try:
            master_key = self._auth.reset_password_with_recovery(answer, new_pwd)
            QMessageBox.information(self, "密码重置", "密码已重置，请记住您的新密码。\n注意：由于密钥变更，旧数据将无法解密。")
            self.login_success.emit(master_key)
            self.accept()
        except AuthError as e:
            self._hint_label.setText(str(e))
