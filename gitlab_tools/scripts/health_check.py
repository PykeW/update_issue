#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统健康检查脚本
检查GitLab同步系统的各个组件状态
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from gitlab_tools.core.database_manager import DatabaseManager
from gitlab_tools.core.gitlab_operations import GitLabOperations
from gitlab_tools.core.config_manager import ConfigManager

class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.issues = []
        self.errors = []
        self.warnings = []

    def check_database_connection(self):
        """检查数据库连接"""
        try:
            result = self.db_manager.execute_query("SELECT 1 as test")
            if result:
                print("✅ 数据库连接正常")
                return True
            else:
                self.errors.append("数据库连接失败")
                return False
        except Exception as e:
            self.errors.append(f"数据库连接异常: {str(e)}")
            return False

    def check_gitlab_connection(self):
        """检查GitLab连接"""
        try:
            gitlab_ops = GitLabOperations()
            # 尝试获取项目信息
            project_info = gitlab_ops.manager.get_project_info(gitlab_ops.project_id)
            if project_info:
                print("✅ GitLab连接正常")
                return True
            else:
                self.errors.append("GitLab连接失败")
                return False
        except Exception as e:
            self.errors.append(f"GitLab连接异常: {str(e)}")
            return False

    def check_config_files(self):
        """检查配置文件"""
        config_files = [
            'config/gitlab.env',
            'config/wps_gitlab_config.json',
            'config/user_mapping.json',
            'config/auto_sync_config.json'
        ]

        all_good = True
        for config_file in config_files:
            file_path = Path(__file__).parent.parent / config_file
            if file_path.exists():
                print(f"✅ 配置文件存在: {config_file}")
            else:
                self.warnings.append(f"配置文件缺失: {config_file}")
                all_good = False

        return all_good

    def check_database_schema(self):
        """检查数据库表结构"""
        try:
            # 检查主要表是否存在
            tables = ['issues', 'sync_queue']
            for table in tables:
                result = self.db_manager.execute_query(f"SHOW TABLES LIKE '{table}'")
                if result:
                    print(f"✅ 数据表存在: {table}")
                else:
                    self.errors.append(f"数据表缺失: {table}")
                    return False

            # 检查issues表结构
            result = self.db_manager.execute_query("DESCRIBE issues")
            required_columns = ['id', 'project_name', 'problem_description', 'status', 'gitlab_url']
            existing_columns = [row['Field'] for row in result]

            missing_columns = [col for col in required_columns if col not in existing_columns]
            if missing_columns:
                self.errors.append(f"issues表缺少字段: {missing_columns}")
                return False
            else:
                print("✅ issues表结构正常")

            return True
        except Exception as e:
            self.errors.append(f"数据库结构检查异常: {str(e)}")
            return False

    def check_sync_status(self):
        """检查同步状态"""
        try:
            # 检查待同步的议题数量
            pending_issues = self.db_manager.execute_query('''
                SELECT COUNT(*) as count FROM issues
                WHERE status = 'open'
                AND (gitlab_url IS NULL OR gitlab_url = '')
            ''')

            if pending_issues:
                count = int(pending_issues[0]['count'])
                if count > 0:
                    self.warnings.append(f"有 {count} 个议题待同步")
                else:
                    print("✅ 所有open议题已同步")

            # 检查同步队列
            queue_items = self.db_manager.execute_query('''
                SELECT COUNT(*) as count FROM sync_queue
                WHERE status = 'pending'
            ''')

            if queue_items:
                count = int(queue_items[0]['count'])
                if count > 0:
                    self.warnings.append(f"同步队列中有 {count} 个待处理项")
                else:
                    print("✅ 同步队列为空")

            return True
        except Exception as e:
            self.errors.append(f"同步状态检查异常: {str(e)}")
            return False

    def check_log_files(self):
        """检查日志文件"""
        log_dir = Path(__file__).parent.parent / 'logs'
        if not log_dir.exists():
            self.warnings.append("日志目录不存在")
            return False

        log_files = list(log_dir.glob('*.log'))
        if log_files:
            print(f"✅ 找到 {len(log_files)} 个日志文件")

            # 检查最近的日志文件
            recent_logs = [f for f in log_files if f.stat().st_mtime > (datetime.now() - timedelta(days=1)).timestamp()]
            if recent_logs:
                print(f"✅ 有 {len(recent_logs)} 个最近24小时内的日志文件")
            else:
                self.warnings.append("没有最近24小时内的日志文件")
        else:
            self.warnings.append("没有找到日志文件")

        return True

    def run_health_check(self):
        """运行完整健康检查"""
        print("=" * 60)
        print("🔍 GitLab同步系统健康检查")
        print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 执行各项检查
        checks = [
            ("数据库连接", self.check_database_connection),
            ("GitLab连接", self.check_gitlab_connection),
            ("配置文件", self.check_config_files),
            ("数据库结构", self.check_database_schema),
            ("同步状态", self.check_sync_status),
            ("日志文件", self.check_log_files)
        ]

        passed = 0
        total = len(checks)

        for check_name, check_func in checks:
            print(f"\n🔍 检查 {check_name}...")
            if check_func():
                passed += 1

        # 显示结果
        print("\n" + "=" * 60)
        print("📊 健康检查结果")
        print("=" * 60)
        print(f"✅ 通过: {passed}/{total}")

        if self.errors:
            print(f"\n❌ 错误 ({len(self.errors)} 个):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n⚠️  警告 ({len(self.warnings)} 个):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.errors and not self.warnings:
            print("\n🎉 系统状态良好，所有检查通过！")
            return True
        elif not self.errors:
            print("\n✅ 系统基本正常，但有一些警告需要注意")
            return True
        else:
            print("\n💥 系统存在问题，需要修复")
            return False

def main():
    """主函数"""
    checker = HealthChecker()
    success = checker.run_health_check()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
