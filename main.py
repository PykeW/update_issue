#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
议题同步系统 - 统一入口
提供命令行接口管理所有功能
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='议题同步系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py api start         # 启动 API 服务
  python main.py sync manual       # 手动批量同步
  python main.py sync status       # 查看同步队列状态
  python main.py test              # 运行测试
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # API 命令
    api_parser = subparsers.add_parser('api', help='API 服务管理')
    api_parser.add_argument('action', choices=['start', 'status'], help='操作')
    api_parser.add_argument('--port', type=int, default=80, help='端口号 (默认: 80)')

    # 同步命令
    sync_parser = subparsers.add_parser('sync', help='同步管理')
    sync_parser.add_argument('action',
                            choices=['manual', 'status', 'close', 'create'],
                            help='操作')
    sync_parser.add_argument('--limit', type=int, default=50, help='处理限制 (默认: 50)')
    sync_parser.add_argument('--action-filter', choices=['close', 'create', 'create_and_close'],
                            help='操作类型过滤')

    # 测试命令
    test_parser = subparsers.add_parser('test', help='运行测试')
    test_parser.add_argument('--type', choices=['sync', 'api', 'all'], default='all',
                            help='测试类型 (默认: all)')

    # 健康检查命令
    subparsers.add_parser('health', help='健康检查')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 执行相应命令
    if args.command == 'api':
        handle_api_command(args)
    elif args.command == 'sync':
        handle_sync_command(args)
    elif args.command == 'test':
        handle_test_command(args)
    elif args.command == 'health':
        handle_health_command(args)

def handle_api_command(args):
    """处理 API 命令"""
    if args.action == 'start':
        print(f"🚀 启动 API 服务 (端口: {args.port})...")
        from src.api.wps_api import app
        app.run(host='0.0.0.0', port=args.port)
    elif args.action == 'status':
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'wps_api.py' in result.stdout or 'wps_upload_api.py' in result.stdout:
            print("✅ API 服务正在运行")
            # 显示进程信息
            for line in result.stdout.split('\n'):
                if 'wps_api.py' in line or 'wps_upload_api.py' in line:
                    print(f"  {line}")
        else:
            print("❌ API 服务未运行")

def handle_sync_command(args):
    """处理同步命令"""
    if args.action == 'manual':
        print(f"🔄 手动批量同步...")
        from src.gitlab.services.manual_sync import process_pending_sync_queue
        from src.gitlab.core.database_manager import DatabaseManager
        from src.gitlab.core.config_manager import ConfigManager

        db_manager = DatabaseManager()
        config_manager = ConfigManager()

        result = process_pending_sync_queue(
            db_manager,
            config_manager,
            args.action_filter,
            args.limit
        )
        print(f"✅ 同步完成:")
        print(f"  处理: {result['processed']} 个")
        print(f"  成功: {result['success']} 个")
        print(f"  失败: {result['failed']} 个")
        print(f"  跳过: {result['skipped']} 个")

    elif args.action == 'status':
        print(f"📊 同步队列状态...")
        from src.gitlab.services.manual_sync import show_queue_status
        from src.gitlab.core.database_manager import DatabaseManager

        db_manager = DatabaseManager()
        show_queue_status(db_manager)

def handle_test_command(args):
    """处理测试命令"""
    print(f"🧪 运行测试 (类型: {args.type})...")

    if args.type in ['sync', 'all']:
        print("\n📋 测试同步功能...")
        import subprocess
        result = subprocess.run([sys.executable, 'scripts/test_immediate_sync.py'])
        if result.returncode != 0:
            print("❌ 同步测试失败")
            return

    if args.type == 'all':
        print("\n✅ 所有测试通过")

def handle_health_command(args):
    """处理健康检查命令"""
    print("🔍 系统健康检查...")
    from src.gitlab.services.health_check import HealthChecker

    checker = HealthChecker()
    success = checker.run_health_check()

    if success:
        print("✅ 系统健康检查通过")
        sys.exit(0)
    else:
        print("❌ 系统健康检查失败")
        sys.exit(1)

if __name__ == "__main__":
    main()

