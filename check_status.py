#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一状态检查脚本
从项目根目录运行
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
gitlab_tools_dir = project_root / "gitlab_tools"
sys.path.append(str(project_root))
sys.path.append(str(gitlab_tools_dir))

# 导入模块
from gitlab_tools.scripts.optimized_auto_sync import OptimizedAutoSync

def main():
    print("📊 检查系统状态...")

    sync = OptimizedAutoSync()
    status = sync.get_system_status()

    print("📋 系统状态:")
    print(f"  队列状态: {status.get('queue_status', {})}")
    print(f"  数据库统计: {status.get('database_stats', {})}")
    print(f"  同步统计: {status.get('sync_statistics', {})}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
