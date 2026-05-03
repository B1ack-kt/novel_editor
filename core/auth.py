"""
认证模块 - 软件登录/解锁/密钥验证
实现强制密码保护、密码修改、本地找回功能
"""

import os
import json
import time
import hashlib
import base64
from typing import Optional, Tuple
from dataclasses import dataclass, field

from .crypto import (
    hash_password, verify_password, generate_salt,
    derive_key, encrypt_data, decrypt_data, CryptoError
)
from config.constants import MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH


class AuthError(Exception):
    """认证错误"""
    pass


@dataclass
class AuthData:
    """认证数据结构"""
    salt_b64: str = ""
    hash_b64: str = ""
    recovery_email: str = ""       # 找回邮箱(本地存储)
    recovery_question: str = ""    # 找回安全问题(本地存储)
    recovery_answer_hash: str = "" # 安全问题答案哈希
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "salt_b64": self.salt_b64,
            "hash_b64": self.hash_b64,
            "recovery_email": self.recovery_email,
            "recovery_question": self.recovery_question,
            "recovery_answer_hash": self.recovery_answer_hash,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthData":
        return cls(
            salt_b64=data.get("salt_b64", ""),
            hash_b64=data.get("hash_b64", ""),
            recovery_email=data.get("recovery_email", ""),
            recovery_question=data.get("recovery_question", ""),
            recovery_answer_hash=data.get("recovery_answer_hash", ""),
            created_at=data.get("created_at", 0.0)
        )


class AuthManager:
    """
    认证管理器
    负责: 首次密码设置 / 登录验证 / 密码修改 / 密码找回
    全程本地化，不涉及云端
    """

    def __init__(self):
        self._auth_data: Optional[AuthData] = None
        self._master_key: Optional[bytes] = None
        self._auth_file = ""

    def is_first_time(self) -> bool:
        """检查是否为首次使用(未设密码)"""
        return self._auth_data is None or not self._auth_data.hash_b64

    def set_initial_password(
        self,
        password: str,
        recovery_email: str = "",
        recovery_question: str = "",
        recovery_answer: str = ""
    ) -> bytes:
        """
        首次设置登录密码（强制）

        Args:
            password: 登录密码
            recovery_email: 找回邮箱（本地存储，不发送）
            recovery_question: 找回安全问题
            recovery_answer: 安全问题答案

        Returns:
            master_key: 派生出的AES-256主密钥
        """
        # 验证密码强度
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"密码长度不能少于{MIN_PASSWORD_LENGTH}位")
        if len(password) > MAX_PASSWORD_LENGTH:
            raise AuthError(f"密码长度不能超过{MAX_PASSWORD_LENGTH}位")

        # 生成密码盐值并哈希
        salt = generate_salt()
        salt_b64, hash_b64 = hash_password(password, salt)

        # 派生主密钥(用于数据加密)
        master_key = derive_key(password, salt)

        # 处理找回答案
        answer_hash = ""
        if recovery_answer:
            ans_salt = generate_salt()
            ans_salt_b64, ans_hash_b64 = hash_password(recovery_answer, ans_salt)
            answer_hash = f"{ans_salt_b64}:{ans_hash_b64}"

        self._auth_data = AuthData(
            salt_b64=salt_b64,
            hash_b64=hash_b64,
            recovery_email=recovery_email,
            recovery_question=recovery_question,
            recovery_answer_hash=answer_hash,
            created_at=time.time()
        )

        self._master_key = master_key
        return master_key

    def load_auth_data(self, data: dict):
        """从文件加载认证数据"""
        self._auth_data = AuthData.from_dict(data)

    def get_auth_data(self) -> Optional[AuthData]:
        """获取认证数据"""
        return self._auth_data

    def login(self, password: str) -> bytes:
        """
        验证登录密码

        Args:
            password: 用户输入的密码

        Returns:
            master_key: AES-256主密钥(用于后续加解密)

        Raises:
            AuthError: 密码错误
        """
        if not self._auth_data:
            raise AuthError("未初始化认证数据")

        if not verify_password(password, self._auth_data.salt_b64, self._auth_data.hash_b64):
            raise AuthError("密码错误")

        # 密码正确，派生主密钥
        salt = base64.b64decode(self._auth_data.salt_b64.encode('utf-8'))
        self._master_key = derive_key(password, salt)
        return self._master_key

    def change_password(self, old_password: str, new_password: str) -> bytes:
        """
        修改登录密码

        Args:
            old_password: 旧密码
            new_password: 新密码

        Returns:
            new_master_key: 新主密钥

        注意: 修改密码后，所有已加密数据需要用新密钥重新加密！
        """
        # 验证旧密码
        if not verify_password(old_password, self._auth_data.salt_b64, self._auth_data.hash_b64):
            raise AuthError("旧密码错误")

        # 验证新密码强度
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"新密码长度不能少于{MIN_PASSWORD_LENGTH}位")

        # 生成新盐值和哈希
        new_salt = generate_salt()
        new_salt_b64, new_hash_b64 = hash_password(new_password, new_salt)

        self._auth_data.salt_b64 = new_salt_b64
        self._auth_data.hash_b64 = new_hash_b64

        # 派生新主密钥
        new_master_key = derive_key(new_password, new_salt)
        self._master_key = new_master_key
        return new_master_key

    def verify_recovery_answer(self, answer: str) -> bool:
        """验证找回密码答案"""
        if not self._auth_data or not self._auth_data.recovery_answer_hash:
            return False
        parts = self._auth_data.recovery_answer_hash.split(":", 1)
        if len(parts) != 2:
            return False
        ans_salt_b64, ans_hash_b64 = parts
        return verify_password(answer, ans_salt_b64, ans_hash_b64)

    def reset_password_with_recovery(
        self,
        answer: str,
        new_password: str
    ) -> bytes:
        """
        通过回答安全问题重置密码

        Args:
            answer: 安全答案
            new_password: 新密码

        Returns:
            new_master_key
        """
        if not self.verify_recovery_answer(answer):
            raise AuthError("安全答案错误")

        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"新密码长度不能少于{MIN_PASSWORD_LENGTH}位")

        new_salt = generate_salt()
        new_salt_b64, new_hash_b64 = hash_password(new_password, new_salt)
        self._auth_data.salt_b64 = new_salt_b64
        self._auth_data.hash_b64 = new_hash_b64

        new_master_key = derive_key(new_password, new_salt)
        self._master_key = new_master_key
        return new_master_key

    def get_master_key(self) -> Optional[bytes]:
        """获取当前主密钥"""
        return self._master_key

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self._master_key is not None
