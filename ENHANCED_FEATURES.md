# 增强版WPS数据接收API功能说明

## 🚀 新功能特性

### 1. 智能数据更新
- **唯一标识**: 使用 `serial_number + project_name` 组合作为唯一标识
- **数据哈希**: 自动生成数据哈希值，检测数据变更
- **智能判断**: 自动判断是插入新数据还是更新现有数据
- **变更检测**: 只有数据真正发生变化时才执行更新操作

### 2. GitLab同步管理
- **同步状态跟踪**: 记录每个议题的GitLab同步状态
- **进度跟踪**: 实时显示议题在GitLab上的进度
- **标签映射**: 智能映射严重程度、状态和议题类型到GitLab标签
- **双向同步**: 支持数据库到GitLab的同步和进度回写

### 3. 数据操作类型
- **insert**: 新插入的数据
- **update**: 更新的数据
- **sync**: 同步到GitLab的操作
- **变更日志**: 记录所有数据变更历史

## 📊 数据库结构增强

### 新增字段
```sql
-- GitLab同步相关
gitlab_url VARCHAR(500) COMMENT 'GitLab议题链接',
gitlab_id INT COMMENT 'GitLab议题ID',
gitlab_labels JSON COMMENT 'GitLab议题标签',
sync_status ENUM('pending', 'synced', 'failed', 'updated') DEFAULT 'pending',
last_sync_time TIMESTAMP NULL COMMENT '最后同步时间',
gitlab_progress VARCHAR(50) COMMENT 'GitLab议题进度',

-- 数据操作相关
operation_type ENUM('insert', 'update') DEFAULT 'insert',
data_hash VARCHAR(64) COMMENT '数据哈希值',
```

### 唯一约束
```sql
UNIQUE KEY unique_issue (serial_number, project_name)
```

## 🔧 API接口

### 1. 数据上传接口
```
POST /api/wps/upload
```
- 支持智能数据更新
- 自动检测数据变更
- 返回详细处理结果

### 2. 议题管理接口
```
GET /api/database/issues
```
- 获取议题列表
- 显示同步状态
- 显示GitLab进度

### 3. GitLab同步接口
```
POST /api/gitlab/sync
```
- 同步数据库议题到GitLab
- 支持创建和更新操作
- 返回同步结果

### 4. 同步状态接口
```
GET /api/gitlab/sync-status
```
- 查询同步状态统计
- 显示各状态议题数量

### 5. 进度更新接口
```
POST /api/gitlab/update-progress
```
- 更新议题进度
- 同步到数据库

## 🏷️ 标签映射规则

### 严重程度映射
- 1级 → `客户需求::紧急` (红色)
- 2级 → `客户需求::中等` (橙色)
- 3-4级 → `客户需求::一般` (绿色)

### 状态进度映射
- `open` → `进度::To do`
- `in_progress` → `进度::Doing`
- `closed` → `进度::Done`
- `resolved` → `进度::Done`

### 智能议题类型识别
- **Bug关键词**: bug、错误、故障、问题、崩溃、异常 → `议题类型::Bug`
- **算法关键词**: 算法、模型、检测、识别、分析、计算、深度学习、机器学习、ai、神经网络 → `议题类型::算法需求`
- **新功能关键词**: 新增、添加、开发、实现、功能、模块 → `议题类型::新增功能`
- **优化关键词**: 优化、改进、提升、性能、速度、响应 → `议题类型::功能优化`

## 🚀 使用方法

### 1. 启动增强版API服务器
```bash
./start_enhanced_api.sh
```

### 2. 管理GitLab同步
```bash
cd gitlab_tools
python3 manage_sync.py
```

### 3. 手动同步到GitLab
```bash
cd gitlab_tools
python3 enhanced_sync_database_to_gitlab.py
```

### 4. 检查同步状态
```bash
cd gitlab_tools
python3 manage_sync.py
# 选择选项1: 检查同步状态
```

## 📈 监控和统计

### 数据库统计
- 总议题数
- 已同步议题数
- 待同步议题数
- 同步失败议题数
- 插入议题数
- 更新议题数

### 同步状态
- `pending`: 待同步
- `synced`: 已同步
- `failed`: 同步失败
- `updated`: 已更新

## 🔄 工作流程

1. **数据上传**: WPS表格数据通过API上传
2. **智能判断**: 系统根据 `serial_number + project_name` 判断是插入还是更新
3. **数据存储**: 存储到数据库，标记操作类型和同步状态
4. **GitLab同步**: 自动或手动同步到GitLab平台
5. **进度跟踪**: 实时跟踪议题在GitLab上的进度
6. **状态回写**: 将GitLab状态同步回数据库

## 🛠️ 技术实现

### 数据哈希算法
```python
def generate_data_hash(self, row_data):
    hash_fields = [
        'serial_number', 'project_name', 'problem_category',
        'severity_level', 'problem_description', 'solution',
        'action_priority', 'action_record', 'initiator',
        'responsible_person', 'status', 'remarks'
    ]

    hash_string = ""
    for field in hash_fields:
        value = str(row_data.get(field, ''))
        hash_string += f"{field}:{value}|"

    return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
```

### 智能更新判断
```python
def should_update_issue(self, existing_issue, new_data, new_hash):
    # 比较数据哈希值
    if existing_issue.get('data_hash') == new_hash:
        return False

    # 比较关键字段
    key_fields = ['problem_description', 'solution', 'status', 'responsible_person']
    for field in key_fields:
        if str(existing_issue.get(field, '')) != str(new_data.get(field, '')):
            return True

    return False
```

## 📝 注意事项

1. **数据唯一性**: 确保 `serial_number + project_name` 组合的唯一性
2. **时间格式**: 支持多种时间格式的自动转换
3. **字符编码**: 所有文本数据使用UTF-8编码
4. **错误处理**: 完善的错误处理和日志记录
5. **性能优化**: 使用索引优化数据库查询性能

## 🔍 故障排除

### 常见问题
1. **数据库连接失败**: 检查MySQL服务状态和配置
2. **GitLab同步失败**: 检查GitLab配置和网络连接
3. **数据更新异常**: 检查数据格式和唯一约束
4. **标签映射错误**: 检查GitLab标签配置

### 日志文件
- API服务器日志: `/var/log/wps_api_enhanced.log`
- 数据库日志: MySQL错误日志
- GitLab同步日志: 控制台输出
