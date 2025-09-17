#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版自动化同步脚本
统一入口，避免功能重复
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from gitlab_tools.core.auto_sync_manager import AutoSyncManager

def main():
    """主函数"""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = 'full'

    sync_manager = AutoSyncManager()

    if mode == 'new':
        result = sync_manager.sync_new_issues()
        print(f"新议题同步完成: 创建 {result['created']} 个，失败 {result['failed']} 个")
    elif mode == 'progress':
        result = sync_manager.sync_progress()
        print(f"进度同步完成: 更新 {result['updated']} 个，跳过 {result['skipped']} 个，失败 {result['failed']} 个，关闭 {result['closed']} 个")
    elif mode == 'queue':
        result = sync_manager.process_sync_queue()
        print(f"队列处理完成: 处理 {result['processed']} 个，失败 {result['failed']} 个")
    elif mode == 'full':
        result = sync_manager.run_full_sync()
        print(f"完整同步完成，耗时 {result['duration']:.2f} 秒")
    else:
        print("用法: python simple_auto_sync.py [new|progress|queue|full]")
        print("  new     - 只同步新议题")
        print("  progress - 只同步进度")
        print("  queue   - 只处理队列")
        print("  full    - 完整同步流程（默认）")

if __name__ == "__main__":
    main()
