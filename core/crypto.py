"""
AES-256加密/解密模块 - 全项目数据安全核心
所有敏感数据均通过此模块加密存储
"""

import os
import hashlib
import json
import base64
from typing import Optional, Tuple
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

from config.constants import (
    AES_KEY_SIZE, AES_IV_SIZE,
    PBKDF2_ITERATIONS, SALT_SIZE
)


class CryptoError(Exception):
    """加密/解密错误"""
    pass


def derive_key(password: str, salt: bytes) -> bytes:
    """
    从密码派生AES密钥 (PBKDF2-HMAC-SHA256)

    Args:
        password: 用户密码
        salt: 随机盐值

    Returns:
        32字节AES-256密钥
    """
    try:
        key = PBKDF2(
            password.encode('utf-8'),
            salt,
            dkLen=AES_KEY_SIZE,
            count=PBKDF2_ITERATIONS,
            hmac_hash_module=hashlib.sha256
        )
        return key
    except Exception as e:
        raise CryptoError(f"密钥派生失败: {e}")


def generate_salt() -> bytes:
    """生成随机盐值"""
    return get_random_bytes(SALT_SIZE)


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """
    哈希密码（用于密码验证，不可逆）

    Args:
        password: 明文密码
        salt: 盐值(不传则生成新值)

    Returns:
        (salt_base64, hash_base64)
    """
    if salt is None:
        salt = generate_salt()
    key = derive_key(password, salt)
    # 对派生密钥再做一次哈希，用于存储验证
    hashed = hashlib.sha256(key + salt).digest()
    return (
        base64.b64encode(salt).decode('utf-8'),
        base64.b64encode(hashed).decode('utf-8')
    )


def verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    """
    验证密码是否正确

    Args:
        password: 待验证密码
        salt_b64: Base64编码的盐值
        hash_b64: Base64编码的密码哈希

    Returns:
        True=密码正确
    """
    salt = base64.b64decode(salt_b64.encode('utf-8'))
    expected_hash = base64.b64decode(hash_b64.encode('utf-8'))
    key = derive_key(password, salt)
    actual_hash = hashlib.sha256(key + salt).digest()
    return actual_hash == expected_hash


def encrypt_data(plaintext: str, key: bytes) -> bytes:
    """
    AES-256-CBC加密数据

    Args:
        plaintext: 明文字符串
        key: 32字节AES密钥

    Returns:
        加密后的字节串 (IV + Ciphertext)
    """
    try:
        iv = get_random_bytes(AES_IV_SIZE)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
        ciphertext = cipher.encrypt(padded_data)
        return iv + ciphertext
    except Exception as e:
        raise CryptoError(f"加密失败: {e}")


def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """
    AES-256-CBC解密数据

    Args:
        encrypted_data: 加密数据 (IV + Ciphertext)
        key: 32字节AES密钥

    Returns:
        解密后的明文字符串
    """
    try:
        iv = encrypted_data[:AES_IV_SIZE]
        ciphertext = encrypted_data[AES_IV_SIZE:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(ciphertext)
        plaintext = unpad(padded_plaintext, AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        raise CryptoError(f"解密失败: 密码错误或数据损坏 ({e})")


def encrypt_file(input_path: str, output_path: str, key: bytes) -> None:
    """
    加密文件

    Args:
        input_path: 源文件路径
        output_path: 加密后保存路径
        key: AES密钥
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    encrypted = encrypt_data(content, key)
    with open(output_path, 'wb') as f:
        f.write(encrypted)


def decrypt_file(input_path: str, output_path: str, key: bytes) -> None:
    """
    解密文件

    Args:
        input_path: 加密文件路径
        output_path: 解密后保存路径
        key: AES密钥
    """
    with open(input_path, 'rb') as f:
        encrypted = f.read()
    decrypted = decrypt_data(encrypted, key)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(decrypted)


def encrypt_json(data: dict, key: bytes) -> bytes:
    """
    将JSON字典加密为加密数据

    Args:
        data: 字典
        key: AES密钥

    Returns:
        加密字节串
    """
    json_str = json.dumps(data, ensure_ascii=False)
    return encrypt_data(json_str, key)


def decrypt_json(encrypted_data: bytes, key: bytes) -> dict:
    """
    将加密数据解密为JSON字典

    Args:
        encrypted_data: 加密字节串
        key: AES密钥

    Returns:
        字典
    """
    json_str = decrypt_data(encrypted_data, key)
    return json.loads(json_str)


def encrypt_bytes(plain_data: bytes, key: bytes) -> bytes:
    """
    AES-256-CBC加密字节数据

    Args:
        plain_data: 明文字节串
        key: 32字节AES密钥

    Returns:
        IV + 密文字节串
    """
    iv = get_random_bytes(AES_IV_SIZE)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(plain_data, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    return iv + ciphertext


def decrypt_bytes(encrypted_data: bytes, key: bytes) -> bytes:
    """
    AES-256-CBC解密字节数据

    Args:
        encrypted_data: IV + 密文字节串
        key: 32字节AES密钥

    Returns:
        明文字节串
    """
    iv = encrypted_data[:AES_IV_SIZE]
    ciphertext = encrypted_data[AES_IV_SIZE:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = cipher.decrypt(ciphertext)
    return unpad(padded_plaintext, AES.block_size)


def generate_project_key(project_password: str) -> Tuple[bytes, str, str]:
    """
    为项目独立密码生成密钥和哈希

    Returns:
        (aes_key, salt_b64, hash_b64)
    """
    salt = generate_salt()
    key = derive_key(project_password, salt)
    hashed = hashlib.sha256(key + salt).digest()
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    hash_b64 = base64.b64encode(hashed).decode('utf-8')
    return key, salt_b64, hash_b64
