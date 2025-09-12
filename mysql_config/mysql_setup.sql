-- MySQL 数据库初始化脚本
-- 设置新密码和创建用户

-- 设置 root 用户密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'NewRootPassword123!';

-- 创建应用数据库
CREATE DATABASE IF NOT EXISTS issue_database
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 创建应用用户（本地连接）
CREATE USER IF NOT EXISTS 'issue'@'localhost' IDENTIFIED BY 'hszc8888';

-- 创建应用用户（远程连接）
CREATE USER IF NOT EXISTS 'issue'@'%' IDENTIFIED BY 'hszc8888';

-- 授权给应用用户
GRANT ALL PRIVILEGES ON issue_database.* TO 'issue'@'localhost';
GRANT ALL PRIVILEGES ON issue_database.* TO 'issue'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示创建的数据库
SHOW DATABASES;

-- 显示用户信息
SELECT User, Host FROM mysql.user WHERE User IN ('root', 'issue');

-- 显示权限信息
SHOW GRANTS FOR 'issue'@'localhost';
SHOW GRANTS FOR 'issue'@'%';

-- 使用issue_database数据库
USE issue_database;

-- 创建issue表
CREATE TABLE IF NOT EXISTS issues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL COMMENT '问题标题',
    description TEXT COMMENT '问题描述',
    status ENUM('open', 'in_progress', 'closed', 'resolved') DEFAULT 'open' COMMENT '问题状态',
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium' COMMENT '优先级',
    assignee VARCHAR(100) COMMENT '指派人',
    reporter VARCHAR(100) COMMENT '报告人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    due_date DATE COMMENT '截止日期',
    tags JSON COMMENT '标签',
    attachments JSON COMMENT '附件信息'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问题跟踪表';

-- 创建索引
CREATE INDEX idx_status ON issues(status);
CREATE INDEX idx_priority ON issues(priority);
CREATE INDEX idx_assignee ON issues(assignee);
CREATE INDEX idx_created_at ON issues(created_at);

-- 插入示例数据
INSERT INTO issues (title, description, status, priority, assignee, reporter) VALUES
('系统登录问题', '用户无法正常登录系统', 'open', 'high', '张三', '李四'),
('页面加载缓慢', '首页加载时间过长', 'in_progress', 'medium', '王五', '赵六'),
('数据同步错误', '数据同步过程中出现错误', 'closed', 'urgent', '孙七', '周八');

-- 显示表结构
DESCRIBE issues;

-- 显示示例数据
SELECT * FROM issues;
