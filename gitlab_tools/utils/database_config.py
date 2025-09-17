#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置管理器
优雅地管理数据库连接配置和密码
"""

import os
import sys
from pathlib import Path
from typing import Dict
sys.path.append(str(Path(__file__).parent))

from password_manager import PasswordManager

class DatabaseConfig:
    """数据库配置管理器"""

    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / "config"
        self.env_file = self.config_dir / "database.env"
        self.password_manager = PasswordManager(self.config_dir)

    def load_config(self) -> Dict[str, str]:
        """加载数据库配置"""
        config = {}

        # 从环境变量加载
        env_vars = [
            'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
            'ROOT_USER', 'ROOT_PASSWORD', 'DB_POOL_SIZE', 'DB_POOL_TIMEOUT',
            'BACKUP_DIR', 'BACKUP_RETENTION_DAYS'
        ]

        for var in env_vars:
            config[var.lower()] = os.getenv(var, '')

        # 从配置文件加载
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.lower()] = value

        return config

    def get_database_config(self) -> Dict[str, str]:
        """获取数据库连接配置"""
        config = self.load_config()

        # 获取密码
        db_password = self._get_password('database', 'issue', config.get('db_password', ''))
        root_password = self._get_password('database', 'root', config.get('root_password', ''))

        return {
            'host': config.get('db_host', 'localhost'),
            'port': int(config.get('db_port', '3306')),
            'database': config.get('db_name', 'issue_database'),
            'user': config.get('db_user', 'issue'),
            'password': db_password,
            'root_user': config.get('root_user', 'root'),
            'root_password': root_password,
            'pool_size': int(config.get('db_pool_size', '10')),
            'pool_timeout': int(config.get('db_pool_timeout', '30')),
            'backup_dir': config.get('backup_dir', '/root/update_issue/backups'),
            'backup_retention_days': int(config.get('backup_retention_days', '30'))
        }

    def _get_password(self, service: str, username: str, fallback: str = '') -> str:
        """获取密码，优先从密码管理器获取"""
        # 首先尝试从密码管理器获取
        password = self.password_manager.get_password(service, username)
        if password:
            return password

        # 如果密码管理器中没有，使用配置文件中的密码
        if fallback:
            return fallback

        # 如果都没有，提示用户输入
        return self.password_manager.get_or_prompt_password(
            service, username, f"请输入数据库 {username} 用户的密码: "
        )

    def setup_passwords(self):
        """设置密码"""
        print("🔐 设置数据库密码...")

        # 设置普通用户密码
        issue_password = self.password_manager.get_or_prompt_password(
            'database', 'issue', "请输入数据库 issue 用户的密码: "
        )

        # 设置root用户密码
        root_password = self.password_manager.get_or_prompt_password(
            'database', 'root', "请输入数据库 root 用户的密码: "
        )

        print("✅ 密码设置完成")
        return {
            'issue_password': issue_password,
            'root_password': root_password
        }

    def test_connection(self, user_type: str = 'issue') -> bool:
        """测试数据库连接"""
        import subprocess

        config = self.get_database_config()

        if user_type == 'root':
            user = config['root_user']
            password = config['root_password']
        else:
            user = config['user']
            password = config['password']

        try:
            cmd = [
                'mysql', '-u', user, f'-p{password}',
                '-h', config['host'], '-P', str(config['port']),
                '-e', 'SELECT 1;'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.returncode == 0
        except Exception:
            return False

    def create_config_template(self):
        """创建配置模板"""
        template = """# 数据库连接配置
# 注意：此文件包含敏感信息，请勿提交到版本控制系统

# MySQL连接配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=issue_database
DB_USER=issue
# DB_PASSWORD=  # 密码将通过密码管理器管理

# Root用户配置（用于管理操作）
ROOT_USER=root
# ROOT_PASSWORD=  # 密码将通过密码管理器管理

# 连接池配置
DB_POOL_SIZE=10
DB_POOL_TIMEOUT=30

# 备份配置
BACKUP_DIR=/root/update_issue/backups
BACKUP_RETENTION_DAYS=30
"""

        if not self.env_file.exists():
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(template)
            print(f"✅ 已创建配置模板: {self.env_file}")
        else:
            print(f"⚠️ 配置文件已存在: {self.env_file}")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='数据库配置管理工具')
    parser.add_argument('action', choices=['setup', 'test', 'template'], help='操作类型')
    parser.add_argument('--user', choices=['issue', 'root'], default='issue', help='测试连接的用户类型')

    args = parser.parse_args()

    db_config = DatabaseConfig()

    if args.action == 'setup':
        db_config.setup_passwords()
    elif args.action == 'test':
        if db_config.test_connection(args.user):
            print(f"✅ {args.user} 用户连接测试成功")
        else:
            print(f"❌ {args.user} 用户连接测试失败")
    elif args.action == 'template':
        db_config.create_config_template()

if __name__ == "__main__":
    main()
