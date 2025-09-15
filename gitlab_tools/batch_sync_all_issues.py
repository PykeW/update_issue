#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量同步所有未同步的议题到GitLab
"""

import os
import sys
import subprocess
import time
from typing import Dict, List, Any, Union

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_sync_database_to_gitlab import sync_issues_to_gitlab, DB_CONFIG

def get_unsynced_count() -> int:
    """
    获取未同步的议题数量
    """
    try:
        cmd: List[str] = [
            'mysql', '-u', str(DB_CONFIG['user']), f'-p{str(DB_CONFIG["password"])}',
            '-h', str(DB_CONFIG['host']), '-P', str(DB_CONFIG['port']),
            '-e', f"""
            USE {DB_CONFIG['database']};
            SELECT COUNT(*) as unsynced_count
            FROM issues
            WHERE (gitlab_url IS NULL OR gitlab_url = '') AND status = 'open' AND (sync_status IS NULL OR sync_status = 'pending' OR sync_status = 'failed');
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            return int(lines[1])
        return 0
    except Exception as e:
        print(f"❌ 获取未同步议题数量失败: {e}")
        return 0

def batch_sync_all_issues() -> None:
    """
    批量同步所有未同步的议题
    """
    print("=" * 60)
    print("批量同步所有未同步议题到GitLab")
    print("=" * 60)

    # 获取初始未同步数量
    initial_count = get_unsynced_count()
    print(f"📊 初始状态为open且未同步的议题数量: {initial_count}")

    if initial_count == 0:
        print("✅ 所有状态为open的议题都已同步，无需处理")
        return

    batch_size = 20
    total_batches = (initial_count + batch_size - 1) // batch_size
    print(f"📦 预计需要处理 {total_batches} 个批次")
    print()

    success_count = 0
    failed_count = 0

    for batch_num in range(1, total_batches + 1):
        print(f"🔄 处理第 {batch_num}/{total_batches} 批次...")

        try:
            # 运行同步工具
            success = sync_issues_to_gitlab()

            if success:
                success_count += 1
                print(f"✅ 第 {batch_num} 批次处理成功")
            else:
                failed_count += 1
                print(f"❌ 第 {batch_num} 批次处理失败")

            # 检查剩余未同步数量
            remaining_count = get_unsynced_count()
            print(f"📊 剩余未同步议题: {remaining_count}")

            if remaining_count == 0:
                print("🎉 所有议题已同步完成！")
                break

            # 批次间暂停，避免API限制
            if batch_num < total_batches:
                print("⏳ 等待 3 秒后处理下一批次...")
                time.sleep(3)

        except Exception as e:
            print(f"❌ 第 {batch_num} 批次处理异常: {e}")
            failed_count += 1
            continue

    print(f"\n📊 批量同步完成:")
    print(f"  ✅ 成功批次: {success_count}")
    print(f"  ❌ 失败批次: {failed_count}")
    print(f"  📋 最终未同步议题: {get_unsynced_count()}")

if __name__ == "__main__":
    batch_sync_all_issues()
