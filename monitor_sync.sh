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
