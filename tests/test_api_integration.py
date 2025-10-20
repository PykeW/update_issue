#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API服务集成测试
测试WPS API的完整功能
"""

import unittest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class TestWPSAPI(unittest.TestCase):
    """测试WPS API"""
    
    def setUp(self):
        """测试前准备"""
        self.app = None
        try:
            from src.api.wps_api import app
            self.app = app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
        except ImportError:
            self.skipTest("WPS API模块不可用")
    
    def test_api_health(self):
        """测试API健康状态"""
        if not self.app:
            self.skipTest("API不可用")
        
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
    
    @patch('src.api.wps_api.DatabaseManager')
    def test_upload_endpoint(self, mock_db):
        """测试上传端点"""
        if not self.app:
            self.skipTest("API不可用")
        
        # 模拟数据库管理器
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.execute_query.return_value = []
        mock_db_instance.execute_update.return_value = True
        
        test_data = {
            'table_data': [{
                'project_name': '测试项目',
                'problem_category': '软件',
                'severity_level': '2',
                'problem_description': '测试问题',
                'solution': '测试解决方案',
                'action_priority': '2',
                'action_record': '测试记录',
                'initiator': '测试用户',
                'responsible_person': '测试负责人',
                'status': 'O',
                'start_time': '2025-10-20 10:00:00',
                'target_completion_time': '2025-10-22 18:00:00',
                'actual_completion_time': '',
                'remarks': '测试备注'
            }]
        }
        
        response = self.client.post('/upload', 
                                  data=json.dumps(test_data),
                                  content_type='application/json')
        
        # 检查响应状态
        self.assertIn(response.status_code, [200, 201])
        
        # 检查响应内容
        if response.status_code in [200, 201]:
            response_data = response.get_json()
            self.assertIn('success', response_data)
            self.assertIn('message', response_data)

class TestManualSync(unittest.TestCase):
    """测试手动同步功能"""
    
    def test_manual_sync_import(self):
        """测试手动同步模块导入"""
        try:
            from src.gitlab.services.manual_sync import main as manual_sync_main
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"手动同步模块导入失败: {e}")

class TestHealthCheck(unittest.TestCase):
    """测试健康检查功能"""
    
    def test_health_check_import(self):
        """测试健康检查模块导入"""
        try:
            from src.gitlab.services.health_check import main as health_check_main
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"健康检查模块导入失败: {e}")

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
