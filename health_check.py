#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一健康检查脚本
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
from gitlab_tools.scripts.health_check import HealthChecker

def main():
    print("🔍 执行健康检查...")

    checker = HealthChecker()
    success = checker.run_health_check()

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
