# 安全指南 - 密码管理

## 🔐 优雅的密码管理方案

本项目实现了优雅的密码管理系统，避免在代码中硬编码敏感信息，提供安全的密码存储和获取功能。

## 🚀 快速开始

### 1. 初始化密码管理器

```bash
cd gitlab_tools
python3 utils/database_config.py setup
```

### 2. 测试数据库连接

```bash
# 测试普通用户连接
python3 utils/database_config.py test --user issue

# 测试root用户连接
python3 utils/database_config.py test --user root
```

## 📋 密码管理命令

### 存储密码

```bash
# 存储数据库用户密码
python3 utils/password_manager.py store --service database --username issue

# 存储root用户密码
python3 utils/password_manager.py store --service database --username root
```

### 查看已存储的密码

```bash
python3 utils/password_manager.py list
```

### 获取密码

```bash
# 获取特定服务的密码
python3 utils/password_manager.py get --service database --username issue
```

### 删除密码

```bash
# 删除已存储的密码
python3 utils/password_manager.py remove --service database --username issue
```

## 🔒 安全特性

### 1. 多层密码存储

- **系统密钥环**: 优先使用操作系统的密钥环服务
- **本地加密存储**: 如果系统密钥环不可用，使用本地加密文件
- **文件权限控制**: 敏感文件设置为仅所有者可读写 (600)

### 2. 加密保护

- 使用 `cryptography` 库的 `Fernet` 对称加密
- 自动生成和管理加密密钥
- 密码在存储前进行加密，获取时自动解密

### 3. 版本控制保护

以下文件已添加到 `.gitignore`，不会被提交到版本控制：

```
# 敏感配置文件
.secrets
.key
*_secrets.json
*_keys.json
database.env
*.env
```

## 🛠️ 技术实现

### 密码管理器 (`password_manager.py`)

- 支持系统密钥环和本地加密存储
- 提供密码的存储、获取、删除功能
- 自动处理加密和解密过程

### 数据库配置管理器 (`database_config.py`)

- 统一管理数据库连接配置
- 自动从密码管理器获取密码
- 提供连接测试功能

### 配置文件模板 (`database.env`)

```bash
# 数据库连接配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=issue_database
DB_USER=issue
# DB_PASSWORD=  # 密码通过密码管理器管理

# Root用户配置
ROOT_USER=root
# ROOT_PASSWORD=  # 密码通过密码管理器管理

# 连接池配置
DB_POOL_SIZE=10
DB_POOL_TIMEOUT=30

# 备份配置
BACKUP_DIR=/root/update_issue/backups
BACKUP_RETENTION_DAYS=30
```

## 🔧 集成使用

### 在代码中使用

```python
from utils.database_config import DatabaseConfig

# 初始化配置管理器
db_config = DatabaseConfig()

# 获取数据库配置（自动处理密码）
config = db_config.get_database_config()

# 使用配置连接数据库
import mysql.connector
conn = mysql.connector.connect(
    host=config['host'],
    port=config['port'],
    database=config['database'],
    user=config['user'],
    password=config['password']
)
```

### 在脚本中使用

```python
from utils.password_manager import PasswordManager

pm = PasswordManager()

# 获取密码
password = pm.get_password('database', 'issue')

# 如果密码不存在，提示用户输入
password = pm.get_or_prompt_password('database', 'issue')
```

## ⚠️ 安全建议

1. **定期更换密码**: 建议定期更换数据库密码
2. **备份密钥**: 如果使用本地加密存储，请备份密钥文件
3. **权限控制**: 确保敏感文件只有必要的用户可访问
4. **监控访问**: 定期检查密码访问日志
5. **环境隔离**: 在不同环境中使用不同的密码

## 🆘 故障排除

### 常见问题

1. **密钥环不可用**
   - 解决方案: 系统会自动回退到本地加密存储

2. **权限错误**
   - 解决方案: 检查文件权限，确保只有所有者可读写

3. **密码获取失败**
   - 解决方案: 重新运行 `python3 utils/database_config.py setup`

### 重置密码

```bash
# 删除所有存储的密码
python3 utils/password_manager.py remove --service database --username issue
python3 utils/password_manager.py remove --service database --username root

# 重新设置密码
python3 utils/database_config.py setup
```

## 📚 相关文档

- [README.md](../README.md) - 项目总体说明
- [数据库配置文档](config/database.env) - 配置文件模板
- [安全最佳实践](https://docs.python.org/3/library/getpass.html) - Python密码输入最佳实践
