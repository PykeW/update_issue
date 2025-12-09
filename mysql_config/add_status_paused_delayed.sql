-- 添加paused和delayed状态到issues表
-- 执行前请先备份数据库

USE issue_database;

-- 修改status字段，添加paused和delayed状态
ALTER TABLE issues
MODIFY COLUMN status ENUM('open', 'in_progress', 'closed', 'resolved', 'paused', 'delayed')
DEFAULT 'open'
COMMENT '状态';

-- 验证修改
SELECT COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'issue_database'
  AND TABLE_NAME = 'issues'
  AND COLUMN_NAME = 'status';

