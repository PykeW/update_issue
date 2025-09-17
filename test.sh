#!/bin/bash
# 统一测试脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/gitlab_tools"
export PATH="/root/miniconda3/bin:$PATH"

# 运行健康检查
python3 "$PROJECT_ROOT/health_check.py"
