#!/bin/bash
# 激活项目虚拟环境脚本

echo "🐍 激活 update-issue 项目虚拟环境..."

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 显示环境信息
echo "✅ 虚拟环境已激活"
echo "📍 Python 路径: $(which python)"
echo "📦 Python 版本: $(python --version)"
echo "📋 已安装包数量: $(pip list | wc -l)"

# 设置项目路径
export PYTHONPATH="/root/update_issue:/root/update_issue/gitlab_tools:$PYTHONPATH"
echo "🔧 PYTHONPATH 已设置"

echo ""
echo "🚀 现在可以使用以下命令:"
echo "  python gitlab_tools/main.py health-check"
echo "  python gitlab_tools/core/change_detector.py single"
echo "  pip list  # 查看已安装的包"
echo ""
echo "💡 提示: 使用 'deactivate' 命令退出虚拟环境"
