#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新需求立即同步到GitLab功能
"""

import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_immediate_sync():
    """测试立即同步功能"""
    try:
        # 准备测试数据
        unique_id = datetime.now().strftime("%H%M%S")
        test_data = {
            'table_data': [{
                'project_name': f'测试立即同步-{unique_id}',
                'problem_category': '软件',
                'severity_level': '2',
                'problem_description': f'测试新需求立即同步到GitLab功能-{unique_id}',
                'solution': '验证立即同步功能',
                'action_priority': '2',
                'action_record': '测试中',
                'initiator': '测试用户',
                'responsible_person': '陆杰',
                'status': 'O',  # Open状态
                'start_time': '2025-10-20 16:00:00',
                'target_completion_time': '2025-10-22 18:00:00',
                'actual_completion_time': '',
                'remarks': '测试立即同步功能'
            }],
            'metadata': {
                'upload_time': datetime.now().isoformat(),
                'source': 'test_immediate_sync'
            }
        }

        print(f"🧪 开始测试立即同步功能...")
        print(f"📋 测试项目: {test_data['table_data'][0]['project_name']}")

        # 发送请求到API
        api_url = "http://127.0.0.1:80/api/wps/upload"
        response = requests.post(
            api_url,
            data=json.dumps(test_data),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        print(f"📡 API响应状态: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ API响应成功")
            print(f"📊 处理结果: {result.get('message', '')}")

            # 检查是否有GitLab URL
            if 'gitlab_url' in str(result):
                print(f"🎉 立即同步成功！议题已创建到GitLab")
                return True
            else:
                print(f"⚠️ 未检测到GitLab URL，可能进入了队列")
                return False
        else:
            print(f"❌ API请求失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

if __name__ == "__main__":
    success = test_immediate_sync()
    if success:
        print("\n🎉 测试通过：新需求能立即同步到GitLab")
    else:
        print("\n❌ 测试失败：新需求未能立即同步到GitLab")
