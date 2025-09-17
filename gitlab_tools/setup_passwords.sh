#!/bin/bash
# -*- coding: utf-8 -*-
"""
密码设置脚本
帮助用户优雅地设置数据库密码
"""

set -e

echo "🔐 GitLab同步工具 - 密码设置向导"
echo "=================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查必要的Python包
echo "📦 检查Python依赖..."
python3 -c "import keyring, cryptography" 2>/dev/null || {
    echo "⚠️ 缺少必要的Python包，正在安装..."
    pip3 install keyring cryptography
}

echo "✅ Python环境检查完成"
echo ""

# 创建配置目录
CONFIG_DIR="$(dirname "$0")/config"
mkdir -p "$CONFIG_DIR"

# 创建配置模板
echo "📝 创建配置模板..."
python3 "$(dirname "$0")/utils/database_config.py" template

echo ""
echo "🔑 设置数据库密码..."
echo ""

# 设置密码
python3 "$(dirname "$0")/utils/database_config.py" setup

echo ""
echo "🧪 测试数据库连接..."
echo ""

# 测试连接
if python3 "$(dirname "$0")/utils/database_config.py" test --user issue; then
    echo "✅ issue用户连接测试成功"
else
    echo "❌ issue用户连接测试失败"
fi

if python3 "$(dirname "$0")/utils/database_config.py" test --user root; then
    echo "✅ root用户连接测试成功"
else
    echo "❌ root用户连接测试失败"
fi

echo ""
echo "🎉 密码设置完成！"
echo ""
echo "📋 后续操作："
echo "1. 运行健康检查: python3 main.py health-check"
echo "2. 运行系统监控: python3 main.py monitor"
echo "3. 查看已存储的密码: python3 utils/password_manager.py list"
echo ""
echo "🔒 安全提示："
echo "- 密码已安全存储在系统密钥环或本地加密文件中"
echo "- 敏感配置文件已添加到.gitignore，不会被提交到版本控制"
echo "- 如需修改密码，请使用: python3 utils/password_manager.py store --service database --username <用户名>"
