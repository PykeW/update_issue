-- 增强版issues表结构，支持GitLab同步和进度跟踪
USE issue_database;

-- 备份现有数据
CREATE TABLE IF NOT EXISTS issues_backup AS SELECT * FROM issues;

-- 删除现有表
DROP TABLE IF EXISTS issues;

-- 创建增强版issues表
CREATE TABLE issues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(50) COMMENT '序号',
    project_name VARCHAR(255) NOT NULL COMMENT '项目名称',
    problem_category VARCHAR(100) COMMENT '问题分类',
    severity_level INT DEFAULT 0 COMMENT '严重程度',
    problem_description TEXT COMMENT '问题/需求描述',
    solution TEXT COMMENT '解决方案',
    action_priority INT DEFAULT 0 COMMENT '行动优先级',
    action_record TEXT COMMENT '行动记录',
    initiator VARCHAR(100) COMMENT '发起人',
    responsible_person VARCHAR(100) COMMENT '责任人',
    status ENUM('open', 'in_progress', 'closed', 'resolved') DEFAULT 'open' COMMENT '状态',
    start_time DATETIME COMMENT '开始时间',
    target_completion_time DATETIME COMMENT '目标完成时间',
    actual_completion_time DATETIME COMMENT '实完时间',
    remarks TEXT COMMENT '备注',

    -- GitLab同步相关字段
    gitlab_url VARCHAR(500) COMMENT 'GitLab议题链接',
    gitlab_id INT COMMENT 'GitLab议题ID',
    gitlab_labels JSON COMMENT 'GitLab议题标签',
    sync_status ENUM('pending', 'synced', 'failed', 'updated') DEFAULT 'pending' COMMENT '同步状态',
    last_sync_time TIMESTAMP NULL COMMENT '最后同步时间',
    gitlab_progress VARCHAR(50) COMMENT 'GitLab议题进度',

    -- 数据操作相关字段
    operation_type ENUM('insert', 'update') DEFAULT 'insert' COMMENT '操作类型',
    data_hash VARCHAR(64) COMMENT '数据哈希值，用于检测变更',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 唯一约束：serial_number + project_name 组合唯一
    UNIQUE KEY unique_issue (serial_number, project_name),

    -- 索引
    INDEX idx_project_name (project_name),
    INDEX idx_problem_category (problem_category),
    INDEX idx_status (status),
    INDEX idx_responsible_person (responsible_person),
    INDEX idx_sync_status (sync_status),
    INDEX idx_gitlab_id (gitlab_id),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='增强版问题清单表';

-- 创建数据变更日志表
CREATE TABLE IF NOT EXISTS issue_change_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL COMMENT '关联的议题ID',
    operation_type ENUM('insert', 'update', 'sync_to_gitlab', 'sync_from_gitlab') NOT NULL COMMENT '操作类型',
    old_data JSON COMMENT '变更前数据',
    new_data JSON COMMENT '变更后数据',
    change_fields TEXT COMMENT '变更字段列表',
    sync_status ENUM('pending', 'success', 'failed') DEFAULT 'pending' COMMENT '同步状态',
    error_message TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    INDEX idx_issue_id (issue_id),
    INDEX idx_operation_type (operation_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='议题变更日志表';

-- 插入示例数据
INSERT INTO issues (
    serial_number, project_name, problem_category, severity_level,
    problem_description, solution, action_priority, action_record,
    initiator, responsible_person, status, start_time,
    target_completion_time, actual_completion_time, remarks,
    operation_type, data_hash
) VALUES (
    '1', '管壳六面检', '软件', 2,
    '深度学习模型标注不准确', '优化算法逻辑', 2, '7/29开始处理',
    '甘伪民', '蒋盟', 'open', '2025-07-25 00:00:00',
    '2025-07-29 00:00:00', NULL, '',
    'insert', MD5(CONCAT('1', '管壳六面检', '深度学习模型标注不准确'))
);
