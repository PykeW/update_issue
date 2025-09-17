#!/bin/bash
# 统一运行脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITLAB_TOOLS_DIR="$PROJECT_ROOT/gitlab_tools"

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$GITLAB_TOOLS_DIR"
export PATH="/root/miniconda3/bin:$PATH"

# 进入GitLab工具目录
cd "$GITLAB_TOOLS_DIR"

# 执行命令
exec "$@"
