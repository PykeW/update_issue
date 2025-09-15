#!/bin/bash
# 设置定时任务

echo "设置GitLab同步定时任务..."

# 创建crontab条目
CRON_ENTRY1="0 8 * * * /usr/bin/python3 /root/update_issue/gitlab_tools/scheduled_sync.py >> /root/update_issue/gitlab_tools/cron.log 2>&1"
CRON_ENTRY2="0 13 * * * /usr/bin/python3 /root/update_issue/gitlab_tools/scheduled_sync.py >> /root/update_issue/gitlab_tools/cron.log 2>&1"

# 检查是否已存在相同的crontab条目
if ! crontab -l 2>/dev/null | grep -q "scheduled_sync.py"; then
    # 添加新的crontab条目
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY1"; echo "$CRON_ENTRY2") | crontab -
    echo "✅ 定时任务已添加"
    echo "   - 每天上午8点执行同步"
    echo "   - 每天下午1点执行同步"
else
    echo "⚠️  定时任务已存在"
fi

# 显示当前的crontab
echo "当前定时任务:"
crontab -l

echo "定时任务设置完成！"
