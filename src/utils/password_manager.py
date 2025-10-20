#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
密码管理器
提供安全的密码存储和获取功能
"""

import os
import getpass
import keyring
import json
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet
import base64

class PasswordManager:
    """密码管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / "config"
        self.secrets_file = self.config_dir / ".secrets"
        self.key_file = self.config_dir / ".key"
        self._key = None

    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        if self._key:
            return self._key

        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self._key = f.read()
        else:
            self._key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self._key)
            # 设置文件权限，只有所有者可读写
            os.chmod(self.key_file, 0o600)

        return self._key

    def _encrypt_password(self, password: str) -> str:
        """加密密码"""
        key = self._get_or_create_key()
        f = Fernet(key)
        encrypted = f.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()

    def _decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        key = self._get_or_create_key()
        f = Fernet(key)
        encrypted = base64.b64decode(encrypted_password.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()

    def store_password(self, service: str, username: str, password: str) -> bool:
        """存储密码"""
        try:
            # 尝试使用系统密钥环
            keyring.set_password(service, username, password)
            return True
        except Exception:
            # 如果系统密钥环不可用，使用本地加密存储
            try:
                secrets = self._load_secrets()
                secrets[f"{service}:{username}"] = self._encrypt_password(password)
                self._save_secrets(secrets)
                return True
            except Exception as e:
                print(f"存储密码失败: {e}")
                return False

    def get_password(self, service: str, username: str) -> Optional[str]:
        """获取密码"""
        try:
            # 首先尝试从系统密钥环获取
            password = keyring.get_password(service, username)
            if password:
                return password
        except Exception:
            pass

        # 如果系统密钥环不可用，从本地加密存储获取
        try:
            secrets = self._load_secrets()
            encrypted_password = secrets.get(f"{service}:{username}")
            if encrypted_password:
                return self._decrypt_password(encrypted_password)
        except Exception as e:
            print(f"获取密码失败: {e}")

        return None

    def _load_secrets(self) -> Dict[str, str]:
        """加载本地加密的密码"""
        if not self.secrets_file.exists():
            return {}

        with open(self.secrets_file, 'r') as f:
            return json.load(f)

    def _save_secrets(self, secrets: Dict[str, str]):
        """保存本地加密的密码"""
        with open(self.secrets_file, 'w') as f:
            json.dump(secrets, f, indent=2)
        # 设置文件权限，只有所有者可读写
        os.chmod(self.secrets_file, 0o600)

    def prompt_for_password(self, service: str, username: str, prompt: Optional[str] = None) -> str:
        """提示用户输入密码"""
        if prompt is None:
            prompt = f"请输入 {service} 的 {username} 密码: "

        password = getpass.getpass(prompt)
        if self.store_password(service, username, password):
            print("✅ 密码已安全存储")
        else:
            print("⚠️ 密码存储失败，请手动管理")

        return password

    def get_or_prompt_password(self, service: str, username: str, prompt: Optional[str] = None) -> str:
        """获取密码，如果不存在则提示输入"""
        password = self.get_password(service, username)
        if password:
            return password

        return self.prompt_for_password(service, username, prompt)

    def list_stored_passwords(self) -> Dict[str, str]:
        """列出已存储的密码服务"""
        stored = {}

        # 从系统密钥环获取
        try:
            # 这里需要根据具体的密钥环实现来获取
            pass
        except Exception:
            pass

        # 从本地存储获取
        try:
            secrets = self._load_secrets()
            for key in secrets.keys():
                service, username = key.split(':', 1)
                stored[key] = f"{service} - {username}"
        except Exception:
            pass

        return stored

    def remove_password(self, service: str, username: str) -> bool:
        """删除存储的密码"""
        try:
            # 从系统密钥环删除
            keyring.delete_password(service, username)
        except Exception:
            pass

        # 从本地存储删除
        try:
            secrets = self._load_secrets()
            key = f"{service}:{username}"
            if key in secrets:
                del secrets[key]
                self._save_secrets(secrets)
                return True
        except Exception as e:
            print(f"删除密码失败: {e}")

        return False

def main():
    """主函数 - 密码管理工具"""
    import argparse

    parser = argparse.ArgumentParser(description='密码管理工具')
    parser.add_argument('action', choices=['store', 'get', 'list', 'remove'], help='操作类型')
    parser.add_argument('--service', help='服务名称')
    parser.add_argument('--username', help='用户名')
    parser.add_argument('--prompt', help='密码提示信息')

    args = parser.parse_args()

    pm = PasswordManager()

    if args.action == 'store':
        if not args.service or not args.username:
            print("❌ 存储密码需要指定 --service 和 --username")
            return

        password = getpass.getpass(f"请输入 {args.service} 的 {args.username} 密码: ")
        if pm.store_password(args.service, args.username, password):
            print("✅ 密码存储成功")
        else:
            print("❌ 密码存储失败")

    elif args.action == 'get':
        if not args.service or not args.username:
            print("❌ 获取密码需要指定 --service 和 --username")
            return

        password = pm.get_password(args.service, args.username)
        if password:
            print(f"密码: {password}")
        else:
            print("❌ 未找到密码")

    elif args.action == 'list':
        passwords = pm.list_stored_passwords()
        if passwords:
            print("已存储的密码:")
            for desc in passwords.values():
                print(f"  - {desc}")
        else:
            print("没有存储的密码")

    elif args.action == 'remove':
        if not args.service or not args.username:
            print("❌ 删除密码需要指定 --service 和 --username")
            return

        if pm.remove_password(args.service, args.username):
            print("✅ 密码删除成功")
        else:
            print("❌ 密码删除失败")

if __name__ == "__main__":
    main()
