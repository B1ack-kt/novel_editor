"""
本地存储管理模块 - 纯本地文件IO抽象层
所有数据仅存储在本地磁盘，绝不涉及云端
支持外接硬盘路径管理
"""

import os
import shutil
import json
import time
from typing import Optional, Callable
from pathlib import Path

from .crypto import encrypt_json, decrypt_json, CryptoError
from config.constants import ENCRYPTED_FILE_EXT


class StorageError(Exception):
    """存储操作错误"""
    pass


class StorageManager:
    """
    本地存储管理器
    负责文件读写、加密存储、路径管理
    """

    def __init__(self, master_key: Optional[bytes] = None):
        self._master_key = master_key
        self._base_dir = ""

    def set_master_key(self, key: bytes):
        """设置主加密密钥"""
        self._master_key = key

    def set_base_dir(self, path: str):
        """设置存储根目录"""
        self._base_dir = os.path.abspath(path)
        os.makedirs(self._base_dir, exist_ok=True)

    def get_base_dir(self) -> str:
        return self._base_dir

    def _ensure_dir(self, path: str):
        """确保目录存在"""
        os.makedirs(path, exist_ok=True)

    def write_encrypted(self, relative_path: str, data: dict) -> str:
        """
        将字典数据加密写入文件

        Args:
            relative_path: 相对路径(如 "projects/xxx/meta.enc")
            data: 要写入的字典

        Returns:
            写入文件的绝对路径
        """
        if not self._master_key:
            raise StorageError("主密钥未设置，无法加密写入")
        full_path = os.path.join(self._base_dir, relative_path)
        self._ensure_dir(os.path.dirname(full_path))
        encrypted = encrypt_json(data, self._master_key)
        with open(full_path, 'wb') as f:
            f.write(encrypted)
        return full_path

    def read_encrypted(self, relative_path: str, key: Optional[bytes] = None) -> dict:
        """
        解密读取文件为字典

        Args:
            relative_path: 相对路径
            key: 解密密钥(不传则用主密钥)

        Returns:
            解密后的字典
        """
        use_key = key or self._master_key
        if not use_key:
            raise StorageError("解密密钥未设置")
        full_path = os.path.join(self._base_dir, relative_path)
        if not os.path.exists(full_path):
            raise StorageError(f"文件不存在: {full_path}")
        with open(full_path, 'rb') as f:
            encrypted = f.read()
        return decrypt_json(encrypted, use_key)

    def write_text(self, relative_path: str, content: str) -> str:
        """写入明文文本文件"""
        full_path = os.path.join(self._base_dir, relative_path)
        self._ensure_dir(os.path.dirname(full_path))
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return full_path

    def read_text(self, relative_path: str) -> str:
        """读取明文文本文件"""
        full_path = os.path.join(self._base_dir, relative_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        """写入二进制文件"""
        full_path = os.path.join(self._base_dir, relative_path)
        self._ensure_dir(os.path.dirname(full_path))
        with open(full_path, 'wb') as f:
            f.write(data)
        return full_path

    def read_bytes(self, relative_path: str) -> bytes:
        """读取二进制文件"""
        full_path = os.path.join(self._base_dir, relative_path)
        with open(full_path, 'rb') as f:
            return f.read()

    def file_exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""
        return os.path.exists(os.path.join(self._base_dir, relative_path))

    def list_dir(self, relative_path: str) -> list:
        """列出目录内容"""
        full_path = os.path.join(self._base_dir, relative_path)
        if os.path.exists(full_path):
            return os.listdir(full_path)
        return []

    def delete_file(self, relative_path: str):
        """删除文件"""
        full_path = os.path.join(self._base_dir, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)

    def delete_dir(self, relative_path: str):
        """删除目录"""
        full_path = os.path.join(self._base_dir, relative_path)
        if os.path.exists(full_path):
            shutil.rmtree(full_path)

    def copy_file(self, src_rel: str, dst_rel: str):
        """复制文件"""
        src = os.path.join(self._base_dir, src_rel)
        dst = os.path.join(self._base_dir, dst_rel)
        self._ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)

    def get_absolute_path(self, relative_path: str) -> str:
        """获取绝对路径"""
        return os.path.abspath(os.path.join(self._base_dir, relative_path))

    def get_free_space(self, path: str = None) -> int:
        """获取磁盘剩余空间(字节)"""
        check_path = path or self._base_dir
        if os.path.exists(check_path):
            return shutil.disk_usage(check_path).free
        return 0

    def is_external_drive(self, path: str) -> bool:
        """
        检测路径是否在外接硬盘上（简易检测）
        通过判断路径是否在系统常用磁盘之外
        """
        path = os.path.abspath(path)
        if os.name == 'nt':  # Windows
            # Windows: C: D: 等是系统盘，其他可能是外接
            drive = os.path.splitdrive(path)[0]
            if drive and drive[0].upper() not in ('C', 'D'):
                return True
            return False
        else:  # Mac/Linux
            # 挂载在 /Volumes 或 /mnt 下的通常是外接
            return path.startswith('/Volumes/') or path.startswith('/media/') or path.startswith('/mnt/')

    def drive_exists(self, path: str) -> bool:
        """检查路径所在驱动器是否存在（用于外接硬盘检测）"""
        return os.path.exists(path)

    def is_path_accessible(self, path: str) -> bool:
        """检查路径是否可读写"""
        try:
            if os.path.exists(path):
                return os.access(path, os.R_OK | os.W_OK)
            # 检查父目录
            parent = os.path.dirname(path)
            while not os.path.exists(parent):
                parent = os.path.dirname(parent)
            return os.access(parent, os.R_OK | os.W_OK)
        except Exception:
            return False
