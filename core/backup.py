"""
增量备份与回滚模块
支持自动备份(5/10/30分钟/手动)、保留最近10个版本、一键回滚
备份加密分享功能(.nev格式)
"""

import os
import json
import time
import shutil
import hashlib
from typing import Optional, List, Callable
from dataclasses import dataclass, field

from .crypto import (
    encrypt_data, decrypt_data, encrypt_bytes, decrypt_bytes,
    derive_key, generate_salt, hash_password, verify_password,
    CryptoError
)
from config.constants import BACKUP_MAX_VERSIONS, ENCRYPTED_BACKUP_EXT
from models.backup_item import BackupItem


class BackupError(Exception):
    """备份操作错误"""
    pass


class BackupManager:
    """
    备份管理器
    提供增量备份、版本管理、回滚、加密分享功能
    """

    def __init__(self, storage_manager=None, master_key: Optional[bytes] = None):
        self._storage = storage_manager
        self._master_key = master_key
        self._backup_records: dict[str, List[BackupItem]] = {}  # project_id -> [BackupItem]

    def set_master_key(self, key: bytes):
        self._master_key = key

    def create_backup(
        self,
        project_id: str,
        project_data: dict,
        chapters_data: list,
        settings_data: dict,
        description: str = ""
    ) -> BackupItem:
        """
        创建项目备份

        Args:
            project_id: 项目ID
            project_data: 项目元数据
            chapters_data: 章节数据列表
            settings_data: 设定库数据
            description: 备份说明

        Returns:
            BackupItem: 备份记录
        """
        if not self._master_key:
            raise BackupError("主密钥未设置，无法创建加密备份")

        # 组装备份包
        backup_content = {
            "project": project_data,
            "chapters": chapters_data,
            "settings_lib": settings_data,
            "description": description,
            "backup_time": time.time()
        }

        # 序列化并加密
        json_str = json.dumps(backup_content, ensure_ascii=False)
        encrypted = encrypt_data(json_str, self._master_key)

        # 确定版本号
        existing = self._backup_records.get(project_id, [])
        version = len(existing) + 1

        # 写入备份文件
        backup_dir = os.path.join(
            self._storage.get_base_dir(),
            "projects", project_id, "backup"
        )
        os.makedirs(backup_dir, exist_ok=True)

        backup_filename = f"v{version:03d}{ENCRYPTED_BACKUP_EXT}"
        backup_path = os.path.join(backup_dir, backup_filename)

        with open(backup_path, 'wb') as f:
            f.write(encrypted)

        # 创建记录
        item = BackupItem(
            project_id=project_id,
            file_path=backup_path,
            version=version,
            file_size=len(encrypted),
            description=description,
            is_encrypted=True
        )

        # 更新记录
        self._backup_records.setdefault(project_id, []).append(item)

        # 清理旧备份（仅保留最近 BACKUP_MAX_VERSIONS 个版本）
        self._prune_old_backups(project_id)

        return item

    def _prune_old_backups(self, project_id: str):
        """清理超出数量限制的旧备份"""
        records = self._backup_records.get(project_id, [])
        if len(records) <= BACKUP_MAX_VERSIONS:
            return

        # 按版本号排序，删除最旧的
        records.sort(key=lambda x: x.version)
        to_remove = records[:-BACKUP_MAX_VERSIONS]

        for item in to_remove:
            try:
                if os.path.exists(item.file_path):
                    os.remove(item.file_path)
            except OSError:
                pass

        self._backup_records[project_id] = records[-BACKUP_MAX_VERSIONS:]

    def get_backup_list(self, project_id: str) -> List[BackupItem]:
        """获取项目备份列表"""
        return self._backup_records.get(project_id, [])

    def restore_backup(self, project_id: str, version: int) -> dict:
        """
        从备份恢复项目数据

        Args:
            project_id: 项目ID
            version: 备份版本号

        Returns:
            {'project': dict, 'chapters': list, 'settings_lib': dict}
        """
        records = self._backup_records.get(project_id, [])
        target = None
        for r in records:
            if r.version == version:
                target = r
                break

        if not target or not os.path.exists(target.file_path):
            raise BackupError(f"备份版本 v{version} 不存在或文件已损坏")

        with open(target.file_path, 'rb') as f:
            encrypted = f.read()

        json_str = decrypt_data(encrypted, self._master_key)
        return json.loads(json_str)

    def export_encrypted_backup(
        self,
        project_id: str,
        export_path: str,
        share_password: str,
        project_password: str = ""
    ) -> str:
        """
        导出加密备份包(.nev格式) - 支持双重加密

        Args:
            project_id: 项目ID
            export_path: 导出目标路径
            share_password: 分享密码
            project_password: 项目独立密码(如有)

        Returns:
            导出文件的绝对路径
        """
        # 读取最新的备份数据
        records = self._backup_records.get(project_id, [])
        if not records:
            raise BackupError("没有可导出的备份数据，请先创建备份")

        # 取最新版本
        latest = max(records, key=lambda x: x.version)
        with open(latest.file_path, 'rb') as f:
            encrypted_content = f.read()

        # 第一层：项目密码加密 (如果有独立密码)
        packaged = encrypted_content
        project_hash = ""
        if project_password:
            p_salt = generate_salt()
            p_key = derive_key(project_password, p_salt)
            packaged = encrypt_bytes(packaged, p_key)
            p_salt_b64 = __import__('base64').b64encode(p_salt).decode('utf-8')
            p_hash_b64 = hash_password(project_password, p_salt)[1]
            project_hash = f"{p_salt_b64}:{p_hash_b64}"

        # 第二层：分享密码加密
        s_salt = generate_salt()
        s_key = derive_key(share_password, s_salt)
        final_package = encrypt_bytes(packaged, s_key)

        # 组装 .nev 格式
        nev_data = {
            "version": "1.0",
            "project_id": project_id,
            "has_project_password": bool(project_password),
            "project_salt": project_hash.split(":")[0] if project_hash else "",
            "project_hash": project_hash.split(":")[1] if project_hash else "",
            "share_salt": __import__('base64').b64encode(s_salt).decode('utf-8'),
            "data": __import__('base64').b64encode(final_package).decode('utf-8')
        }

        nev_json = json.dumps(nev_data, ensure_ascii=False)

        # 确保扩展名
        if not export_path.endswith(ENCRYPTED_BACKUP_EXT):
            export_path += ENCRYPTED_BACKUP_EXT

        with open(export_path, 'wb') as f:
            f.write(nev_json.encode('utf-8'))

        return export_path

    def import_encrypted_backup(
        self,
        nev_file_path: str,
        share_password: str,
        project_password: str = ""
    ) -> dict:
        """
        导入加密备份包(.nev格式)

        Args:
            nev_file_path: .nev文件路径
            share_password: 分享密码
            project_password: 项目独立密码(如导出时设置)

        Returns:
            解密后的备份数据字典
        """
        with open(nev_file_path, 'rb') as f:
            nev_json = f.read().decode('utf-8')

        nev_data = json.loads(nev_json)

        if nev_data.get("version") != "1.0":
            raise BackupError("不支持的备份包版本")

        # 第一层解密：分享密码
        final_package = __import__('base64').b64decode(nev_data["data"])
        s_salt = __import__('base64').b64decode(nev_data["share_salt"])
        s_key = derive_key(share_password, s_salt)

        try:
            packaged = decrypted = decrypt_bytes(final_package, s_key)
        except CryptoError:
            raise BackupError("分享密码错误")

        # 第二层解密：项目密码(如有)
        if nev_data.get("has_project_password"):
            if not project_password:
                raise BackupError("此备份包含项目独立密码，请输入")
            p_salt = __import__('base64').b64decode(nev_data["project_salt"])
            p_key = derive_key(project_password, p_salt)
            try:
                packaged = decrypt_bytes(packaged, p_key)
            except CryptoError:
                raise BackupError("项目独立密码错误")

        # 解密核心数据(用主密钥)
        json_str = decrypt_data(packaged, self._master_key)
        return json.loads(json_str)

    def load_backup_records(self, records_data: dict):
        """从持久化存储加载备份记录"""
        self._backup_records = {}
        for pid, items in records_data.items():
            self._backup_records[pid] = [BackupItem.from_dict(i) for i in items]

    def to_dict(self) -> dict:
        """导出所有备份记录为字典"""
        return {
            pid: [item.to_dict() for item in items]
            for pid, items in self._backup_records.items()
        }
