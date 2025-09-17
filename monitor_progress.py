#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一GitLab进度监控脚本
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
from gitlab_tools.core.progress_monitor import ProgressMonitor

def main():
    print("🔍 GitLab进度监控 - 监控未关闭议题的进度变化")
    print("=" * 60)

    monitor = ProgressMonitor()

    # 获取监控统计
    stats = monitor.get_monitoring_stats()
    print("📊 监控统计:")
    print(f"  有GitLab链接的开放议题: {stats.get('open_issues_with_gitlab', 0)} 个")
    print(f"  最近24小时进度变更: {stats.get('recent_progress_changes', 0)} 次")
    print(f"  缓存大小: {stats.get('cache_size', 0)} 个")
    print("")

    # 执行单次监控
    results = monitor.run_single_check()

    print("=" * 60)
    print("📊 监控结果:")
    print(f"  更新: {results.get('updated', 0)} 个")
    print(f"  失败: {results.get('failed', 0)} 个")
    print(f"  跳过: {results.get('skipped', 0)} 个")

    if results.get('error'):
        print(f"  错误: {results['error']}")

    print("=" * 60)

    return results.get('updated', 0) > 0 or results.get('failed', 0) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
