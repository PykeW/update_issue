#!/bin/bash

# WPS API服务器启动脚本

echo "=== WPS API服务器启动脚本 ==="

# 检查Python依赖（基础版本不需要外部依赖）
echo "检查Python环境..."
python3 --version

# 检查MySQL连接
echo "检查MySQL连接..."
mysql -u issue -p'hszc8888' -e "SELECT 1;" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ MySQL连接失败，请检查数据库服务"
    exit 1
fi

# 创建日志目录
echo "创建日志目录..."
mkdir -p /var/log/wps_api
mkdir -p /var/log/nginx

# 设置文件权限
chmod +x /root/update_issue/basic_wps_api.py

# 启动Python API服务器（后台运行）
echo "启动Python API服务器..."
cd /root/update_issue
nohup python3 basic_wps_api.py > /var/log/wps_api/server.log 2>&1 &
API_PID=$!
echo "API服务器PID: $API_PID"

# 等待API服务器启动
sleep 3

# 检查API服务器是否启动成功
curl -s http://localhost:5000/ > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Python API服务器启动成功"
else
    echo "❌ Python API服务器启动失败"
    exit 1
fi

# 配置nginx
echo "配置nginx..."
cp /root/update_issue/nginx_wps_api.conf /etc/nginx/conf.d/wps_api.conf

# 测试nginx配置
nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx配置正确"
    # 重新加载nginx
    systemctl reload nginx
    echo "✅ Nginx重新加载完成"
else
    echo "❌ Nginx配置错误"
    exit 1
fi

# 测试80端口服务
echo "测试80端口服务..."
curl -s http://localhost/ > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 80端口服务正常"
else
    echo "❌ 80端口服务异常"
fi

echo ""
echo "=== 启动完成 ==="
echo "API服务器PID: $API_PID"
echo "服务地址: http://$(curl -s ifconfig.me)/"
echo "健康检查: http://$(curl -s ifconfig.me)/api/status"
echo "API文档: http://$(curl -s ifconfig.me)/api/test"
echo ""
echo "日志文件:"
echo "  - API日志: /var/log/wps_api/server.log"
echo "  - Nginx访问日志: /var/log/nginx/wps_api_access.log"
echo "  - Nginx错误日志: /var/log/nginx/wps_api_error.log"
echo ""
echo "停止服务: kill $API_PID"
