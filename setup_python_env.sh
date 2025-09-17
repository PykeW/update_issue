#!/bin/bash
# -*- coding: utf-8 -*-
"""
统一Python环境设置脚本
确保项目使用一致的Python环境
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITLAB_TOOLS_DIR="$PROJECT_ROOT/gitlab_tools"

log_info "🔧 设置统一Python环境"
log_info "项目根目录: $PROJECT_ROOT"
log_info "GitLab工具目录: $GITLAB_TOOLS_DIR"

# 检查Python环境
check_python_env() {
    log_info "检查Python环境..."

    # 检查python3
    if command -v python3 &> /dev/null; then
        PYTHON3_PATH=$(which python3)
        PYTHON3_VERSION=$(python3 --version)
        log_success "Python3: $PYTHON3_PATH ($PYTHON3_VERSION)"
    else
        log_error "未找到python3"
        exit 1
    fi

    # 检查python
    if command -v python &> /dev/null; then
        PYTHON_PATH=$(which python)
        PYTHON_VERSION=$(python --version)
        log_success "Python: $PYTHON_PATH ($PYTHON_VERSION)"
    else
        log_warning "未找到python命令"
    fi

    # 检查pip3
    if command -v pip3 &> /dev/null; then
        PIP3_PATH=$(which pip3)
        log_success "Pip3: $PIP3_PATH"
    else
        log_error "未找到pip3"
        exit 1
    fi
}

# 安装Python依赖
install_dependencies() {
    log_info "安装Python依赖..."

    # 必需的包
    REQUIRED_PACKAGES=(
        "keyring"
        "cryptography"
        "mysql.connector"
        "requests"
        "dotenv"
    )

    for package in "${REQUIRED_PACKAGES[@]}"; do
        log_info "检查包: $package"
        if python3 -c "import $package" 2>/dev/null; then
            log_success "✅ $package 已安装"
        else
            log_warning "⚠️ $package 未安装，正在安装..."
            pip3 install "$package"
            if python3 -c "import $package" 2>/dev/null; then
                log_success "✅ $package 安装成功"
            else
                log_error "❌ $package 安装失败"
                exit 1
            fi
        fi
    done
}

# 创建环境配置文件
create_env_config() {
    log_info "创建环境配置文件..."

    # 创建.env文件
    cat > "$PROJECT_ROOT/.env" << EOF
# Python环境配置
PYTHON_PATH=$PYTHON3_PATH
PYTHON_VERSION=$PYTHON3_VERSION
PROJECT_ROOT=$PROJECT_ROOT
GITLAB_TOOLS_DIR=$GITLAB_TOOLS_DIR

# 环境变量
export PYTHONPATH="$PROJECT_ROOT:$GITLAB_TOOLS_DIR"
export PATH="$PYTHON3_PATH:\$PATH"
EOF

    log_success "环境配置文件已创建: $PROJECT_ROOT/.env"
}

# 创建统一启动脚本
create_unified_scripts() {
    log_info "创建统一启动脚本..."

    # 注意: test_system.py 已删除，使用 health_check.py 替代

    # 创建项目根目录的状态检查脚本
    cat > "$PROJECT_ROOT/check_status.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一状态检查脚本
从项目根目录运行
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
gitlab_tools_dir = project_root / "gitlab_tools"
sys.path.append(str(project_root))
sys.path.append(str(gitlab_tools_dir))

# 导入模块
from gitlab_tools.scripts.optimized_auto_sync import OptimizedAutoSync

def main():
    print("📊 检查系统状态...")

    sync = OptimizedAutoSync()
    status = sync.get_system_status()

    print("📋 系统状态:")
    print(f"  队列状态: {status.get('queue_status', {})}")
    print(f"  数据库统计: {status.get('database_stats', {})}")
    print(f"  同步统计: {status.get('sync_statistics', {})}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

    chmod +x "$PROJECT_ROOT/check_status.py"
    log_success "统一状态检查脚本已创建: $PROJECT_ROOT/check_status.py"

    # 创建项目根目录的健康检查脚本
    cat > "$PROJECT_ROOT/health_check.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一健康检查脚本
从项目根目录运行
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
gitlab_tools_dir = project_root / "gitlab_tools"
sys.path.append(str(project_root))
sys.path.append(str(gitlab_tools_dir))

# 导入模块
from gitlab_tools.scripts.health_check import HealthChecker

def main():
    print("🔍 执行健康检查...")

    checker = HealthChecker()
    success = checker.run_health_check()

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

    chmod +x "$PROJECT_ROOT/health_check.py"
    log_success "统一健康检查脚本已创建: $PROJECT_ROOT/health_check.py"
}

# 创建便捷命令脚本
create_convenience_scripts() {
    log_info "创建便捷命令脚本..."

    # 创建run.sh脚本
    cat > "$PROJECT_ROOT/run.sh" << 'EOF'
#!/bin/bash
# 统一运行脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITLAB_TOOLS_DIR="$PROJECT_ROOT/gitlab_tools"

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$GITLAB_TOOLS_DIR"
export PATH="/root/miniconda3/bin:$PATH"

# 进入GitLab工具目录
cd "$GITLAB_TOOLS_DIR"

# 执行命令
exec "$@"
EOF

    chmod +x "$PROJECT_ROOT/run.sh"
    log_success "便捷运行脚本已创建: $PROJECT_ROOT/run.sh"

    # 创建test.sh脚本
    cat > "$PROJECT_ROOT/test.sh" << 'EOF'
#!/bin/bash
# 统一测试脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/gitlab_tools"
export PATH="/root/miniconda3/bin:$PATH"

# 运行测试
python3 "$PROJECT_ROOT/health_check.py"
EOF

    chmod +x "$PROJECT_ROOT/test.sh"
    log_success "便捷测试脚本已创建: $PROJECT_ROOT/test.sh"
}

# 更新现有脚本的路径
update_existing_scripts() {
    log_info "更新现有脚本的路径..."

    # 更新manage_optimized_service.sh
    if [ -f "$GITLAB_TOOLS_DIR/manage_optimized_service.sh" ]; then
        sed -i 's|PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"|PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"|g' "$GITLAB_TOOLS_DIR/manage_optimized_service.sh"
        log_success "已更新manage_optimized_service.sh路径"
    fi
}

# 测试统一环境
test_unified_env() {
    log_info "测试统一环境..."

    # 测试项目根目录的脚本
    if python3 "$PROJECT_ROOT/health_check.py"; then
        log_success "✅ 统一测试脚本运行成功"
    else
        log_error "❌ 统一测试脚本运行失败"
        exit 1
    fi

    # 测试状态检查
    if python3 "$PROJECT_ROOT/check_status.py"; then
        log_success "✅ 统一状态检查脚本运行成功"
    else
        log_error "❌ 统一状态检查脚本运行失败"
        exit 1
    fi
}

# 主函数
main() {
    log_info "🚀 开始设置统一Python环境..."

    check_python_env
    install_dependencies
    create_env_config
    create_unified_scripts
    create_convenience_scripts
    update_existing_scripts
    test_unified_env

    log_success "🎉 统一Python环境设置完成！"

    echo ""
    echo "📋 可用命令:"
    echo "  python3 health_check.py    # 运行健康检查"
    echo "  python3 check_status.py     # 检查系统状态"
    echo "  python3 health_check.py     # 健康检查"
    echo "  ./test.sh                   # 便捷测试"
    echo "  ./run.sh python3 main.py health-check  # 便捷运行"
    echo ""
    echo "📁 环境配置:"
    echo "  Python路径: $PYTHON3_PATH"
    echo "  Python版本: $PYTHON3_VERSION"
    echo "  项目根目录: $PROJECT_ROOT"
    echo "  环境配置文件: $PROJECT_ROOT/.env"
}

# 执行主函数
main "$@"
