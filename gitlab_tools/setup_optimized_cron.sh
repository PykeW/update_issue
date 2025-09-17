#!/bin/bash
# -*- coding: utf-8 -*-
"""
优化版自动化同步设置脚本
配置智能的定时任务和监控
"""

set -e

echo "🚀 GitLab同步工具 - 优化版自动化设置"
echo "======================================"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查必要的Python包
echo "📦 检查Python依赖..."
python3 -c "import keyring, cryptography, mysql.connector" 2>/dev/null || {
    echo "⚠️ 缺少必要的Python包，正在安装..."
    pip3 install keyring cryptography mysql-connector-python
}

echo "✅ Python环境检查完成"
echo ""

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 创建日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 创建备份目录
BACKUP_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUP_DIR"

echo "📁 目录结构:"
echo "  项目根目录: $PROJECT_ROOT"
echo "  日志目录: $LOG_DIR"
echo "  备份目录: $BACKUP_DIR"
echo ""

# 设置数据库优化触发器
echo "🗄️ 设置数据库优化触发器..."
cd "$SCRIPT_DIR"

# 检查MySQL连接
if ! python3 -c "
import sys
sys.path.append('$PROJECT_ROOT')
from gitlab_tools.utils.database_config import DatabaseConfig
db_config = DatabaseConfig()
if db_config.test_connection('issue'):
    print('✅ 数据库连接正常')
else:
    print('❌ 数据库连接失败')
    sys.exit(1)
"; then
    echo "❌ 数据库连接失败，请检查配置"
    exit 1
fi

# 执行SQL脚本
echo "📝 执行数据库优化脚本..."
mysql -u issue -phszc8888 issue_database < setup_optimized_triggers.sql

if [ $? -eq 0 ]; then
    echo "✅ 数据库优化脚本执行成功"
else
    echo "❌ 数据库优化脚本执行失败"
    exit 1
fi

echo ""

# 创建cron任务
echo "⏰ 设置定时任务..."

# 备份现有cron
crontab -l > "$BACKUP_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true

# 创建新的cron配置
CRON_FILE="/tmp/gitlab_sync_cron"
cat > "$CRON_FILE" << EOF
# GitLab同步工具 - 优化版定时任务
# 生成时间: $(date)

# 变更监控 - 每10秒检查一次变更
* * * * * cd $PROJECT_ROOT && python3 gitlab_tools/core/change_detector.py single >/dev/null 2>&1

# 队列处理 - 每分钟处理一次队列
* * * * * cd $PROJECT_ROOT && python3 gitlab_tools/scripts/optimized_auto_sync.py queue --batch-size 5 >/dev/null 2>&1

# 完整同步 - 每天上午8点和下午1点
0 8 * * * cd $PROJECT_ROOT && python3 gitlab_tools/scripts/optimized_auto_sync.py single --batch-size 20 >> $LOG_DIR/daily_sync.log 2>&1
0 13 * * * cd $PROJECT_ROOT && python3 gitlab_tools/scripts/optimized_auto_sync.py single --batch-size 20 >> $LOG_DIR/daily_sync.log 2>&1

# 系统监控 - 每5分钟检查一次状态
*/5 * * * * cd $PROJECT_ROOT && python3 gitlab_tools/scripts/optimized_auto_sync.py status >> $LOG_DIR/system_status.log 2>&1

# 健康检查 - 每小时检查一次
0 * * * * cd $PROJECT_ROOT && python3 gitlab_tools/main.py health-check >> $LOG_DIR/health_check.log 2>&1

# 日志轮转 - 每天凌晨2点清理日志
0 2 * * * cd $PROJECT_ROOT && python3 gitlab_tools/scripts/log_rotation.py >> $LOG_DIR/log_rotation.log 2>&1

# 数据清理 - 每周日凌晨3点清理过期数据
0 3 * * 0 cd $PROJECT_ROOT && python3 gitlab_tools/scripts/optimized_auto_sync.py cleanup --days 30 >> $LOG_DIR/cleanup.log 2>&1

# 数据库备份 - 每天凌晨4点备份
0 4 * * * cd $PROJECT_ROOT && python3 gitlab_tools/utils/helpers.py backup_database >> $LOG_DIR/backup.log 2>&1
EOF

# 安装cron任务
crontab "$CRON_FILE"
rm "$CRON_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 定时任务设置成功"
else
    echo "❌ 定时任务设置失败"
    exit 1
fi

echo ""

# 创建systemd服务（可选）
echo "🔧 创建systemd服务（可选）..."
SERVICE_FILE="/etc/systemd/system/gitlab-sync.service"
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=GitLab Sync Service
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/python3 gitlab_tools/scripts/optimized_auto_sync.py continuous --interval 30
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ systemd服务文件已创建: $SERVICE_FILE"
echo ""

# 创建管理脚本
echo "📝 创建管理脚本..."
MANAGEMENT_SCRIPT="$PROJECT_ROOT/manage_sync.sh"
cat > "$MANAGEMENT_SCRIPT" << 'EOF'
#!/bin/bash
# GitLab同步工具管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

case "$1" in
    start)
        echo "🚀 启动GitLab同步服务..."
        systemctl start gitlab-sync
        systemctl enable gitlab-sync
        ;;
    stop)
        echo "🛑 停止GitLab同步服务..."
        systemctl stop gitlab-sync
        ;;
    restart)
        echo "🔄 重启GitLab同步服务..."
        systemctl restart gitlab-sync
        ;;
    status)
        echo "📊 GitLab同步服务状态:"
        systemctl status gitlab-sync
        ;;
    logs)
        echo "📋 GitLab同步服务日志:"
        journalctl -u gitlab-sync -f
        ;;
    test)
        echo "🧪 测试同步功能..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py single
        ;;
    monitor)
        echo "👁️ 启动变更监控..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/core/change_detector.py continuous --interval 10
        ;;
    queue)
        echo "⚙️ 处理同步队列..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py queue --batch-size 10
        ;;
    cleanup)
        echo "🧹 清理系统数据..."
        cd "$PROJECT_ROOT"
        python3 gitlab_tools/scripts/optimized_auto_sync.py cleanup --days 30
        ;;
    *)
        echo "GitLab同步工具管理脚本"
        echo "用法: $0 {start|stop|restart|status|logs|test|monitor|queue|cleanup}"
        echo ""
        echo "命令说明:"
        echo "  start    - 启动同步服务"
        echo "  stop     - 停止同步服务"
        echo "  restart  - 重启同步服务"
        echo "  status   - 查看服务状态"
        echo "  logs     - 查看服务日志"
        echo "  test     - 测试同步功能"
        echo "  monitor  - 启动变更监控"
        echo "  queue    - 处理同步队列"
        echo "  cleanup  - 清理系统数据"
        ;;
esac
EOF

chmod +x "$MANAGEMENT_SCRIPT"
echo "✅ 管理脚本已创建: $MANAGEMENT_SCRIPT"
echo ""

# 创建监控脚本
echo "📊 创建监控脚本..."
MONITOR_SCRIPT="$PROJECT_ROOT/monitor_sync.sh"
cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# GitLab同步工具监控脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "📊 GitLab同步工具 - 系统监控报告"
echo "=================================="
echo ""

# 系统状态
echo "🖥️ 系统状态:"
echo "  时间: $(date)"
echo "  负载: $(uptime | awk -F'load average:' '{print $2}')"
echo "  内存: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  磁盘: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')"
echo ""

# 服务状态
echo "🔧 服务状态:"
if systemctl is-active --quiet gitlab-sync; then
    echo "  GitLab同步服务: ✅ 运行中"
else
    echo "  GitLab同步服务: ❌ 未运行"
fi

if systemctl is-active --quiet mysql; then
    echo "  MySQL服务: ✅ 运行中"
else
    echo "  MySQL服务: ❌ 未运行"
fi
echo ""

# 数据库状态
echo "🗄️ 数据库状态:"
cd "$PROJECT_ROOT"
python3 -c "
import sys
sys.path.append('$PROJECT_ROOT')
from gitlab_tools.scripts.optimized_auto_sync import OptimizedAutoSync
sync = OptimizedAutoSync()
status = sync.get_system_status()
print('  队列状态:', status.get('queue_status', {}))
print('  数据库统计:', status.get('database_stats', {}))
print('  同步统计:', status.get('sync_statistics', {}))
"
echo ""

# 日志状态
echo "📋 日志状态:"
LOG_DIR="$PROJECT_ROOT/logs"
if [ -d "$LOG_DIR" ]; then
    echo "  日志目录: $LOG_DIR"
    echo "  日志文件:"
    ls -lh "$LOG_DIR"/*.log 2>/dev/null | awk '{print "    " $9 ": " $5 " (" $6 " " $7 " " $8 ")"}'
else
    echo "  日志目录: 不存在"
fi
echo ""

# 定时任务状态
echo "⏰ 定时任务状态:"
echo "  当前cron任务:"
crontab -l 2>/dev/null | grep -E "(gitlab|sync)" | sed 's/^/    /'
echo ""

echo "✅ 监控报告完成"
EOF

chmod +x "$MONITOR_SCRIPT"
echo "✅ 监控脚本已创建: $MONITOR_SCRIPT"
echo ""

# 最终提示
echo "🎉 优化版自动化同步设置完成！"
echo ""
echo "📋 设置摘要:"
echo "  ✅ 数据库优化触发器已安装"
echo "  ✅ 定时任务已配置"
echo "  ✅ systemd服务已创建"
echo "  ✅ 管理脚本已创建"
echo "  ✅ 监控脚本已创建"
echo ""
echo "🚀 快速开始:"
echo "  1. 启动服务: $MANAGEMENT_SCRIPT start"
echo "  2. 查看状态: $MANAGEMENT_SCRIPT status"
echo "  3. 测试功能: $MANAGEMENT_SCRIPT test"
echo "  4. 查看监控: $MONITOR_SCRIPT"
echo ""
echo "📚 更多信息:"
echo "  - 管理脚本: $MANAGEMENT_SCRIPT"
echo "  - 监控脚本: $MONITOR_SCRIPT"
echo "  - 日志目录: $LOG_DIR"
echo "  - 备份目录: $BACKUP_DIR"
echo ""
echo "⚠️ 注意事项:"
echo "  - 请确保MySQL服务正在运行"
echo "  - 请确保GitLab连接配置正确"
echo "  - 建议定期检查日志文件"
echo "  - 建议定期运行健康检查"
