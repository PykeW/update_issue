#!/bin/bash
# 启动增强版WPS API服务器

echo "启动增强版WPS数据接收API服务器..."
echo "功能特性: 智能数据更新、GitLab同步、进度跟踪"
echo "端口: 5000"
echo "================================================"

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3 未安装"
    exit 1
fi

# 检查MySQL是否运行
if ! systemctl is-active --quiet mysql; then
    echo "启动MySQL服务..."
    systemctl start mysql
    if [ $? -ne 0 ]; then
        echo "错误: 无法启动MySQL服务"
        exit 1
    fi
fi

# 检查数据库连接
echo "检查数据库连接..."
mysql -u issue -phszc8888 -h localhost -P 3306 -e "USE issue_database; SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "错误: 无法连接到数据库"
    exit 1
fi

echo "✅ 数据库连接正常"

# 启动API服务器
echo "启动API服务器..."
python3 enhanced_wps_api.py
