# 项目结构说明

## 📁 项目目录结构

```
/root/update_issue/
├── basic_wps_api.py          # WPS API服务器 (核心)
├── wps_upload_script_v3.py   # WPS表格上传脚本 (核心)
├── start_wps_api.sh          # 启动脚本
├── README.md                 # 项目说明文档
├── PROJECT_STRUCTURE.md      # 项目结构说明
└── mysql_config/             # MySQL配置目录
    ├── install_mysql.sh      # MySQL安装脚本
    ├── mysql_service.sh      # MySQL服务管理脚本
    ├── mysql_setup.sql       # 数据库初始化脚本
    └── mysql.cnf             # MySQL配置文件
```

## 🎯 核心文件说明

### 1. API服务器
- **`basic_wps_api.py`** - 主要的WPS数据接收API服务器
  - 监听端口: 80
  - 接收WPS表格数据并写入数据库
  - 支持状态映射和优先级映射
  - 包含详细的日志记录

### 2. 上传脚本
- **`wps_upload_script_v3.py`** - WPS表格数据上传脚本
  - 支持从WPS表格读取数据
  - 智能识别列名位置
  - 筛选软件相关记录
  - 分批上传数据

### 3. 启动脚本
- **`start_wps_api.sh`** - 一键启动API服务器
  - 停止现有服务
  - 启动新的API服务器
  - 设置正确的权限

### 4. MySQL配置
- **`mysql_config/`** - MySQL相关配置文件
  - `install_mysql.sh` - 安装MySQL 8.0
  - `mysql_service.sh` - 管理MySQL服务
  - `mysql_setup.sql` - 创建数据库和用户
  - `mysql.cnf` - MySQL配置文件

## 🚀 使用方法

### 启动服务
```bash
cd /root/update_issue
chmod +x start_wps_api.sh
./start_wps_api.sh
```

### 上传数据
```bash
python3 wps_upload_script_v3.py
```

## 📊 数据库信息
- **数据库名**: `issue_database`
- **用户名**: `issue`
- **密码**: `hszc8888`
- **端口**: 3306

## 🔧 功能特性
- ✅ 支持WPS表格数据读取
- ✅ 智能列名识别
- ✅ 软件记录筛选
- ✅ 状态和优先级映射
- ✅ 分批数据上传
- ✅ 详细日志记录
- ✅ 错误处理和重试
- ✅ 数据库连接管理

## 📝 注意事项
- 确保MySQL服务正在运行
- API服务器监听80端口
- 支持远程数据库连接
- 自动处理数据格式转换
