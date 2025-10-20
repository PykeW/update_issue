#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心模块单元测试
测试 DatabaseManager, ConfigManager, GitLabOperations 等核心功能
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class TestModuleImports(unittest.TestCase):
    """测试模块导入"""
    
    def test_core_module_imports(self):
        """测试核心模块导入"""
        try:
            from src.gitlab.core.database_manager import DatabaseManager
            from src.gitlab.core.config_manager import ConfigManager
            from src.gitlab.core.gitlab_operations import GitLabOperations
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"核心模块导入失败: {e}")
    
    def test_service_module_imports(self):
        """测试服务模块导入"""
        try:
            from src.gitlab.services.manual_sync import main as manual_sync_main
            from src.gitlab.services.health_check import main as health_check_main
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"服务模块导入失败: {e}")
    
    def test_api_module_imports(self):
        """测试API模块导入"""
        try:
            from src.api.wps_api import app
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"API模块导入失败: {e}")
    
    def test_main_entry_point(self):
        """测试主入口点"""
        try:
            import main
            self.assertTrue(hasattr(main, 'main'))
        except ImportError as e:
            self.fail(f"主入口点导入失败: {e}")

class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""
    
    def setUp(self):
        """测试前准备"""
        from src.gitlab.core.config_manager import ConfigManager
        self.config_manager = ConfigManager()
    
    @patch('builtins.open', create=True)
    @patch('json.load')
    def test_load_gitlab_config(self, mock_json_load, mock_open):
        """测试GitLab配置加载"""
        mock_json_load.return_value = {
            'gitlab': {
                'url': 'https://test.gitlab.com',
                'token': 'test_token',
                'project_id': '1',
                'project_path': 'test/project'
            }
        }
        
        config = self.config_manager.load_gitlab_config()
        self.assertIsNotNone(config)
        self.assertEqual(config['gitlab_url'], 'https://test.gitlab.com')

class TestGitLabOperations(unittest.TestCase):
    """测试GitLab操作"""
    
    def setUp(self):
        """测试前准备"""
        with patch('src.gitlab.core.gitlab_operations.load_config') as mock_config:
            mock_config.return_value = {
                'gitlab_url': 'https://test.gitlab.com',
                'private_token': 'test_token',
                'project_id': '1',
                'project_path': 'test/project'
            }
            from src.gitlab.core.gitlab_operations import GitLabOperations
            self.gitlab_ops = GitLabOperations()
    
    def test_extract_issue_id_from_url(self):
        """测试从URL提取议题ID"""
        test_url = "https://test.gitlab.com/test/project/-/issues/123"
        issue_id = self.gitlab_ops.extract_issue_id_from_url(test_url)
        self.assertEqual(issue_id, 123)
    
    def test_extract_issue_id_invalid_url(self):
        """测试无效URL"""
        test_url = "https://test.gitlab.com/test/project"
        issue_id = self.gitlab_ops.extract_issue_id_from_url(test_url)
        self.assertIsNone(issue_id)

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)