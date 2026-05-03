"""
项目管理模块 - 项目的创建/读取/更新/删除
支持自定义存储路径、外接硬盘兼容、项目独立加密
"""

import os
import json
import time
import shutil
from typing import Optional, List, Dict
from pathlib import Path

from models.project import Project
from models.chapter import Chapter
from models.character import Character
from models.world import WorldRule
from models.backup_item import BackupItem
from core.crypto import (
    derive_key, generate_salt, hash_password, verify_password,
    encrypt_json, decrypt_json, CryptoError
)
from core.storage import StorageManager, StorageError


class ProjectError(Exception):
    """项目管理错误"""
    pass


class ProjectManager:
    """
    项目管理器
    管理所有小说项目，支持多项目切换
    """

    def __init__(self, storage_manager: StorageManager, master_key: bytes):
        self._storage = storage_manager
        self._master_key = master_key
        self._projects: Dict[str, Project] = {}           # id -> Project
        self._chapters: Dict[str, Dict[str, Chapter]] = {} # project_id -> {chapter_id -> Chapter}
        self._characters: Dict[str, Dict[str, Character]] = {}
        self._world_rules: Dict[str, Dict[str, WorldRule]] = {}
        self._current_project: Optional[Project] = None
        self._project_keys: Dict[str, bytes] = {}          # project_id -> project_key (独立加密)

    # ========== 项目管理 ==========

    def create_project(
        self,
        name: str,
        storage_path: str = "",
        password: str = "",
        is_encrypted: bool = False
    ) -> Project:
        """
        创建新小说项目

        Args:
            name: 项目名称
            storage_path: 自定义存储路径(空=使用默认路径)
            password: 项目独立密码
            is_encrypted: 是否启用独立加密

        Returns:
            Project实例
        """
        project = Project(
            name=name,
            storage_path=storage_path or self._storage.get_base_dir(),
            is_encrypted=is_encrypted and bool(password)
        )

        # 如果启用独立加密
        if project.is_encrypted and password:
            from core.crypto import generate_project_key
            proj_key, salt_b64, hash_b64 = generate_project_key(password)
            project.password_hash = hash_b64
            project.password_salt = salt_b64
            self._project_keys[project.id] = proj_key

        # 确保项目目录存在
        project_dir = os.path.join(project.storage_path, "projects", project.id)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(os.path.join(project_dir, "chapters"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "backup"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "exports"), exist_ok=True)

        self._projects[project.id] = project
        self._chapters[project.id] = {}
        self._characters[project.id] = {}
        self._world_rules[project.id] = {}

        # 保存项目元数据
        self._save_project_meta(project)

        return project

    def open_project(self, project_id: str, password: str = "") -> Project:
        """
        打开项目

        Args:
            project_id: 项目ID
            password: 项目独立密码(如启用)

        Returns:
            Project实例
        """
        if project_id not in self._projects:
            # 尝试从存储加载
            project = self._load_project_meta(project_id)
            if not project:
                raise ProjectError("项目不存在或数据已损坏")

        project = self._projects[project_id]

        # 验证独立密码
        if project.is_encrypted:
            if not password:
                raise ProjectError("此项目启用了独立加密，请输入项目密码")
            if not verify_password(password, project.password_salt, project.password_hash):
                raise ProjectError("项目密码错误")

            # 派生项目密钥
            salt_bytes = __import__('base64').b64decode(project.password_salt.encode('utf-8'))
            proj_key = derive_key(password, salt_bytes)
            self._project_keys[project.id] = proj_key

        # 加载章节和人设
        self._load_project_data(project.id)
        self._current_project = project
        return project

    def delete_project(self, project_id: str):
        """删除项目及其所有数据"""
        if project_id not in self._projects:
            raise ProjectError("项目不存在")

        project = self._projects[project_id]
        project_dir = os.path.join(project.storage_path, "projects", project_id)

        # 删除所有数据
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        # 清理内存
        self._projects.pop(project_id, None)
        self._chapters.pop(project_id, None)
        self._characters.pop(project_id, None)
        self._world_rules.pop(project_id, None)
        self._project_keys.pop(project_id, None)

        if self._current_project and self._current_project.id == project_id:
            self._current_project = None

    def list_projects(self) -> List[Project]:
        """获取所有项目列表"""
        return list(self._projects.values())

    def get_current_project(self) -> Optional[Project]:
        """获取当前打开的项目"""
        return self._current_project

    def set_current_project(self, project: Project):
        """设置当前项目"""
        self._current_project = project

    def update_project_name(self, project_id: str, new_name: str):
        """更新项目名称"""
        project = self._projects.get(project_id)
        if not project:
            raise ProjectError("项目不存在")
        project.name = new_name
        project.touch()
        self._save_project_meta(project)

    def change_project_storage(self, project_id: str, new_path: str):
        """
        更改项目存储路径（支持外接硬盘迁移）
        """
        project = self._projects.get(project_id)
        if not project:
            raise ProjectError("项目不存在")

        old_dir = os.path.join(project.storage_path, "projects", project_id)
        new_dir = os.path.join(new_path, "projects", project_id)

        if os.path.exists(old_dir):
            os.makedirs(os.path.dirname(new_dir), exist_ok=True)
            shutil.copytree(old_dir, new_dir)
            shutil.rmtree(old_dir)

        project.storage_path = new_path
        project.touch()
        self._save_project_meta(project)

    def get_project_password_key(self, project_id: str) -> Optional[bytes]:
        """获取项目独立加密密钥"""
        return self._project_keys.get(project_id)

    # ========== 章节管理 ==========

    def create_chapter(self, project_id: str, title: str = "新章节", content_type: str = "text") -> Chapter:
        """创建新章节"""
        chapter = Chapter(
            project_id=project_id,
            title=title,
            content_type=content_type,
            order=len(self._chapters.get(project_id, {}))
        )
        self._chapters.setdefault(project_id, {})[chapter.id] = chapter
        self._projects[project_id].chapters.append(chapter.id)
        self._projects[project_id].touch()
        self._save_chapter(chapter)
        self._save_project_meta(self._projects[project_id])
        return chapter

    def update_chapter(self, chapter: Chapter):
        """更新章节"""
        if chapter.project_id not in self._chapters:
            raise ProjectError("项目不存在")
        self._chapters[chapter.project_id][chapter.id] = chapter
        chapter.touch()
        self._save_chapter(chapter)

    def delete_chapter(self, project_id: str, chapter_id: str):
        """删除章节"""
        chapters = self._chapters.get(project_id, {})
        if chapter_id in chapters:
            chapters.pop(chapter_id)
            self._projects[project_id].chapters.remove(chapter_id)
            self._projects[project_id].touch()
            self._save_project_meta(self._projects[project_id])
            # 删除文件
            self._delete_chapter_file(project_id, chapter_id)

    def get_chapter(self, project_id: str, chapter_id: str) -> Optional[Chapter]:
        """获取单个章节"""
        return self._chapters.get(project_id, {}).get(chapter_id)

    def get_chapters(self, project_id: str) -> List[Chapter]:
        """获取项目的所有章节(按order排序)"""
        chapters = list(self._chapters.get(project_id, {}).values())
        chapters.sort(key=lambda c: c.order)
        return chapters

    def reorder_chapters(self, project_id: str, chapter_ids: List[str]):
        """重新排序章节"""
        for i, cid in enumerate(chapter_ids):
            chapter = self._chapters.get(project_id, {}).get(cid)
            if chapter:
                chapter.order = i
                self._save_chapter(chapter)
        # 更新项目章节列表顺序
        self._projects[project_id].chapters = chapter_ids
        self._projects[project_id].touch()
        self._save_project_meta(self._projects[project_id])

    # ========== 人设管理 ==========

    def add_character(self, project_id: str, name: str) -> Character:
        """添加人设"""
        character = Character(project_id=project_id, name=name)
        self._characters.setdefault(project_id, {})[character.id] = character
        self._projects[project_id].character_ids.append(character.id)
        self._projects[project_id].touch()
        self._save_settings_lib(project_id)
        self._save_project_meta(self._projects[project_id])
        return character

    def update_character(self, character: Character):
        """更新人设"""
        self._characters[character.project_id][character.id] = character
        character.touch()
        self._save_settings_lib(character.project_id)

    def delete_character(self, project_id: str, character_id: str):
        """删除人设"""
        chars = self._characters.get(project_id, {})
        if character_id in chars:
            chars.pop(character_id)
            self._projects[project_id].character_ids.remove(character_id)
            self._projects[project_id].touch()
            self._save_settings_lib(project_id)
            self._save_project_meta(self._projects[project_id])

    def get_characters(self, project_id: str) -> List[Character]:
        """获取项目所有人设"""
        return list(self._characters.get(project_id, {}).values())

    # ========== 世界观管理 ==========

    def add_world_rule(self, project_id: str, category: str, name: str, parent_id: str = "") -> WorldRule:
        """添加世界观规则"""
        rule = WorldRule(
            project_id=project_id,
            category=category,
            name=name,
            parent_id=parent_id
        )
        self._world_rules.setdefault(project_id, {})[rule.id] = rule
        self._projects[project_id].world_rule_ids.append(rule.id)

        # 如果是子规则，更新父规则的children列表
        if parent_id and parent_id in self._world_rules.get(project_id, {}):
            self._world_rules[project_id][parent_id].children.append(rule.id)

        self._projects[project_id].touch()
        self._save_settings_lib(project_id)
        self._save_project_meta(self._projects[project_id])
        return rule

    def update_world_rule(self, rule: WorldRule):
        """更新世界观规则"""
        self._world_rules[rule.project_id][rule.id] = rule
        rule.touch()
        self._save_settings_lib(rule.project_id)

    def delete_world_rule(self, project_id: str, rule_id: str):
        """删除世界观规则"""
        rules = self._world_rules.get(project_id, {})
        if rule_id in rules:
            rule = rules[rule_id]
            # 从父规则移除
            if rule.parent_id and rule.parent_id in rules:
                if rule_id in rules[rule.parent_id].children:
                    rules[rule.parent_id].children.remove(rule_id)
            # 删除子规则
            for child_id in rule.children:
                if child_id in rules:
                    rules.pop(child_id)
            rules.pop(rule_id)
            self._projects[project_id].world_rule_ids.remove(rule_id)
            self._projects[project_id].touch()
            self._save_settings_lib(project_id)
            self._save_project_meta(self._projects[project_id])

    def get_world_rules(self, project_id: str, category: str = "") -> List[WorldRule]:
        """获取世界观规则(可选按分类过滤)"""
        rules = list(self._world_rules.get(project_id, {}).values())
        if category:
            rules = [r for r in rules if r.category == category]
        return rules

    # ========== 持久化 ==========

    def _save_project_meta(self, project: Project):
        """保存项目元数据(加密)"""
        key = self._project_keys.get(project.id, self._master_key)
        encrypt_json(project.to_dict(), key)
        meta_path = os.path.join(
            project.storage_path, "projects", project.id, "project_meta.enc"
        )
        encrypted = encrypt_json(project.to_dict(), key)
        with open(meta_path, 'wb') as f:
            f.write(encrypted)

    def _load_project_meta(self, project_id: str) -> Optional[Project]:
        """加载项目元数据"""
        # 扫描所有可能的存储位置
        base_dir = self._storage.get_base_dir()
        for root, dirs, files in os.walk(os.path.join(base_dir, "projects")):
            if root.endswith(project_id) and "project_meta.enc" in files:
                meta_path = os.path.join(root, "project_meta.enc")
                with open(meta_path, 'rb') as f:
                    encrypted = f.read()
                data = decrypt_json(encrypted, self._master_key)
                project = Project.from_dict(data)
                self._projects[project.id] = project
                return project
        return None

    def _save_chapter(self, chapter: Chapter):
        """保存章节到加密文件"""
        project = self._projects.get(chapter.project_id)
        if not project:
            return
        key = self._project_keys.get(project.id, self._master_key)
        chapter_path = os.path.join(
            project.storage_path, "projects", project.id, "chapters",
            f"{chapter.id}.enc"
        )
        encrypted = encrypt_json(chapter.to_dict(), key)
        with open(chapter_path, 'wb') as f:
            f.write(encrypted)

    def _delete_chapter_file(self, project_id: str, chapter_id: str):
        """删除章节文件"""
        project = self._projects.get(project_id)
        if not project:
            return
        chapter_path = os.path.join(
            project.storage_path, "projects", project_id, "chapters",
            f"{chapter_id}.enc"
        )
        if os.path.exists(chapter_path):
            os.remove(chapter_path)

    def _save_settings_lib(self, project_id: str):
        """保存设定库(人设+世界观)到加密文件"""
        project = self._projects.get(project_id)
        if not project:
            return
        key = self._project_keys.get(project.id, self._master_key)
        data = {
            "characters": {cid: c.to_dict() for cid, c in
                           self._characters.get(project_id, {}).items()},
            "world_rules": {rid: r.to_dict() for rid, r in
                            self._world_rules.get(project_id, {}).items()}
        }
        lib_path = os.path.join(
            project.storage_path, "projects", project_id, "settings_lib.enc"
        )
        encrypted = encrypt_json(data, key)
        with open(lib_path, 'wb') as f:
            f.write(encrypted)

    def _load_project_data(self, project_id: str):
        """加载项目的章节和设定数据"""
        project = self._projects.get(project_id)
        if not project:
            return

        key = self._project_keys.get(project.id, self._master_key)

        # 加载章节
        chapters_dir = os.path.join(
            project.storage_path, "projects", project_id, "chapters"
        )
        self._chapters.setdefault(project_id, {})
        if os.path.exists(chapters_dir):
            for filename in os.listdir(chapters_dir):
                if filename.endswith('.enc'):
                    filepath = os.path.join(chapters_dir, filename)
                    with open(filepath, 'rb') as f:
                        encrypted = f.read()
                    chapter = Chapter.from_dict(decrypt_json(encrypted, key))
                    self._chapters[project_id][chapter.id] = chapter

        # 加载设定库
        lib_path = os.path.join(
            project.storage_path, "projects", project_id, "settings_lib.enc"
        )
        if os.path.exists(lib_path):
            with open(lib_path, 'rb') as f:
                encrypted = f.read()
            data = decrypt_json(encrypted, key)

            self._characters.setdefault(project_id, {})
            for cid, cdata in data.get("characters", {}).items():
                self._characters[project_id][cid] = Character.from_dict(cdata)

            self._world_rules.setdefault(project_id, {})
            for rid, rdata in data.get("world_rules", {}).items():
                self._world_rules[project_id][rid] = WorldRule.from_dict(rdata)

    def load_all_projects(self):
        """扫描并加载所有项目元数据"""
        base_dir = self._storage.get_base_dir()
        projects_dir = os.path.join(base_dir, "projects")
        if not os.path.exists(projects_dir):
            return
        for dirname in os.listdir(projects_dir):
            meta_path = os.path.join(projects_dir, dirname, "project_meta.enc")
            if os.path.exists(meta_path):
                with open(meta_path, 'rb') as f:
                    encrypted = f.read()
                try:
                    data = decrypt_json(encrypted, self._master_key)
                    project = Project.from_dict(data)
                    self._projects[project.id] = project
                except CryptoError:
                    # 加密密钥不匹配，跳过
                    continue

    def get_export_data(self, project_id: str) -> dict:
        """获取项目完整导出数据"""
        project = self._projects.get(project_id)
        if not project:
            raise ProjectError("项目不存在")
        return {
            "project": project.to_dict(),
            "chapters": [c.to_dict() for c in self.get_chapters(project_id)],
            "settings_lib": {
                "characters": {cid: c.to_dict() for cid, c in
                               self._characters.get(project_id, {}).items()},
                "world_rules": {rid: r.to_dict() for rid, r in
                                self._world_rules.get(project_id, {}).items()}
            }
        }
