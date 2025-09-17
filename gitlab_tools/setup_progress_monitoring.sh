#!/bin/bash
# -*- coding: utf-8 -*-
"""
GitLab进度监控设置脚本
设置定时任务监控未关闭议题的进度变化
"""

set -e

echo "🔍 GitLab进度监控设置"
echo "====================="
echo ""

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GITLAB_TOOLS_DIR="$PROJECT_ROOT/gitlab_tools"

echo "📁 项目目录: $PROJECT_ROOT"
echo "📁 GitLab工具目录: $GITLAB_TOOLS_DIR"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

echo "✅ Python环境检查通过"
echo ""

# 测试进度监控功能
echo "🧪 测试进度监控功能..."
cd "$PROJECT_ROOT"

if python3 monitor_progress.py; then
    echo "✅ 进度监控功能测试成功"
else
    echo "❌ 进度监控功能测试失败"
    exit 1
fi

echo ""

# 创建cron任务
echo "⏰ 设置定时任务..."

# 备份现有cron
crontab -l > "$PROJECT_ROOT/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true

# 创建新的cron配置
CRON_FILE="/tmp/progress_monitoring_cron"
cat > "$CRON_FILE" << EOF
# GitLab进度监控定时任务
# 生成时间: $(date)

# 每5分钟检查一次进度变化
*/5 * * * * cd $PROJECT_ROOT && python3 monitor_progress.py >> logs/progress_monitor.log 2>&1

# 每小时执行一次完整监控
0 * * * * cd $GITLAB_TOOLS_DIR && python3 main.py monitor-progress >> logs/progress_monitor.log 2>&1

# 每天凌晨2点清理监控日志
0 2 * * * find $PROJECT_ROOT/logs -name "progress_monitor.log" -size +10M -exec truncate -s 5M {} \;
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

# 创建监控管理脚本
echo "📝 创建监控管理脚本..."
MANAGEMENT_SCRIPT="$PROJECT_ROOT/manage_progress_monitoring.sh"
cat > "$MANAGEMENT_SCRIPT" << 'EOF'
#!/bin/bash
# GitLab进度监控管理脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$1" in
    test)
        echo "🧪 测试进度监控功能..."
        cd "$PROJECT_ROOT"
        python3 monitor_progress.py
        ;;
    run)
        echo "🔍 运行单次进度监控..."
        cd "$PROJECT_ROOT"
        python3 monitor_progress.py
        ;;
    continuous)
        echo "🔄 启动持续进度监控..."
        cd "$PROJECT_ROOT/gitlab_tools"
        python3 core/progress_monitor.py continuous --interval 300
        ;;
    status)
        echo "📊 查看监控状态..."
        cd "$PROJECT_ROOT/gitlab_tools"
        python3 core/progress_monitor.py stats
        ;;
    logs)
        echo "📋 查看监控日志..."
        if [ -f "$PROJECT_ROOT/logs/progress_monitor.log" ]; then
            tail -f "$PROJECT_ROOT/logs/progress_monitor.log"
        else
            echo "日志文件不存在"
        fi
        ;;
    cron)
        echo "⏰ 当前定时任务:"
        crontab -l | grep -E "(progress|monitor)" | sed 's/^/  /'
        ;;
    *)
        echo "GitLab进度监控管理脚本"
        echo "用法: $0 {test|run|continuous|status|logs|cron}"
        echo ""
        echo "命令说明:"
        echo "  test       - 测试进度监控功能"
        echo "  run        - 运行单次进度监控"
        echo "  continuous - 启动持续进度监控"
        echo "  status     - 查看监控状态"
        echo "  logs       - 查看监控日志"
        echo "  cron       - 查看定时任务"
        ;;
esac
EOF

chmod +x "$MANAGEMENT_SCRIPT"
echo "✅ 管理脚本已创建: $MANAGEMENT_SCRIPT"
echo ""

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"
echo "✅ 日志目录已创建: $PROJECT_ROOT/logs"
echo ""

# 最终提示
echo "🎉 GitLab进度监控设置完成！"
echo ""
echo "📋 设置摘要:"
echo "  ✅ 进度监控功能已测试"
echo "  ✅ 定时任务已配置（每5分钟检查一次）"
echo "  ✅ 管理脚本已创建"
echo "  ✅ 日志目录已创建"
echo ""
echo "🚀 快速开始:"
echo "  # 测试功能"
echo "  $MANAGEMENT_SCRIPT test"
echo ""
echo "  # 运行单次监控"
echo "  $MANAGEMENT_SCRIPT run"
echo ""
echo "  # 查看监控状态"
echo "  $MANAGEMENT_SCRIPT status"
echo ""
echo "  # 查看监控日志"
echo "  $MANAGEMENT_SCRIPT logs"
echo ""
echo "📚 定时任务:"
echo "  - 每5分钟自动检查进度变化"
echo "  - 每小时执行完整监控"
echo "  - 每天凌晨2点清理日志"
echo ""
echo "⚠️ 注意事项:"
echo "  - 确保GitLab连接配置正确"
echo "  - 定期检查监控日志"
echo "  - 监控功能会自动更新数据库中的进度信息"
