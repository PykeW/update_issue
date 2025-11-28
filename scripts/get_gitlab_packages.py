#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用token获取GitLab上的可下载文件（packages）
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any, cast

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class GitLabPackageManager:
    """GitLab Packages管理器"""

    def __init__(self, gitlab_url: str, token: str, base_dir: Optional[str] = None):
        """
        初始化GitLab API客户端

        Args:
            gitlab_url: GitLab服务器地址，例如 https://dev.heils.cn
            token: GitLab访问token（Personal Access Token或Project Access Token）
            base_dir: 文件保存的基础目录，默认为项目根目录
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        self.token = token
        self.headers = {
            'PRIVATE-TOKEN': token,
            'Content-Type': 'application/json'
        }
        self.base_dir = base_dir if base_dir else str(project_root)

    def get_project_id_by_path(self, project_path: str) -> Optional[int]:
        """
        通过项目路径获取项目ID

        Args:
            project_path: 项目路径，例如 aoi-public/aoi-smartvision

        Returns:
            项目ID，如果失败返回None
        """
        # URL编码项目路径
        encoded_path = urllib.parse.quote(project_path, safe='')
        api_url = f"{self.gitlab_url}/api/v4/projects/{encoded_path}"

        try:
            req = urllib.request.Request(api_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                project_info = cast(Dict[str, Any], json.loads(resp_body))
                project_id = project_info.get('id')
                if project_id is None:
                    return None
                print(f"✅ 项目ID: {project_id}")
                return int(project_id)
        except urllib.error.HTTPError as e:
            print(f"❌ 获取项目信息失败: HTTP {e.code}")
            try:
                error_body = e.read().decode('utf-8')
                print(f"错误详情: {error_body}")
            except Exception:
                pass
            return None
        except Exception as e:
            print(f"❌ 获取项目信息异常: {e}")
            return None

    def list_packages(self, project_id: int, package_type: Optional[str] = None,
                     per_page: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        列出项目的packages

        Args:
            project_id: 项目ID
            package_type: 包类型过滤（可选），例如 'generic', 'maven', 'npm' 等
            per_page: 每页数量

        Returns:
            packages列表，如果失败返回None
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/packages"

        params: Dict[str, Any] = {'per_page': str(per_page)}
        if package_type:
            params['package_type'] = package_type

        try:
            url = api_url + '?' + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                packages = cast(List[Dict[str, Any]], json.loads(resp_body))
                print(f"✅ 找到 {len(packages)} 个packages")
                return packages
        except urllib.error.HTTPError as e:
            print(f"❌ 获取packages列表失败: HTTP {e.code}")
            try:
                error_body = e.read().decode('utf-8')
                print(f"错误详情: {error_body}")
            except Exception:
                pass
            return None
        except Exception as e:
            print(f"❌ 获取packages列表异常: {e}")
            return None

    def get_package_files(self, project_id: int, package_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        获取package的文件列表

        Args:
            project_id: 项目ID
            package_id: Package ID

        Returns:
            package文件列表，如果失败返回None
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/packages/{package_id}/package_files"

        try:
            req = urllib.request.Request(api_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                files = cast(List[Dict[str, Any]], json.loads(resp_body))
                return files
        except urllib.error.HTTPError as e:
            print(f"❌ 获取package文件列表失败: HTTP {e.code}")
            return None
        except Exception as e:
            print(f"❌ 获取package文件列表异常: {e}")
            return None

    def download_package_file(self, project_id: int, package_id: int,
                             file_id: int, save_path: Optional[str] = None,
                             project_path: Optional[str] = None) -> bool:
        """
        下载package文件

        Args:
            project_id: 项目ID
            package_id: Package ID
            file_id: Package File ID
            save_path: 保存路径（可选），如果不指定则使用文件名

        Returns:
            是否下载成功
        """
        # 先获取文件信息以确认文件存在
        files_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/packages/{package_id}/package_files"
        try:
            req = urllib.request.Request(files_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode('utf-8')
                files = cast(List[Dict[str, Any]], json.loads(resp_body))

                # 查找目标文件
                target_file = None
                for file_info in files:
                    if file_info.get('id') == file_id:
                        target_file = file_info
                        break

                if not target_file:
                    print(f"❌ 在package {package_id}中未找到file_id={file_id}")
                    print(f"   可用的file_id: {[f.get('id') for f in files]}")
                    return False

                file_name = target_file.get('file_name', f'package_file_{file_id}')
                print(f"✅ 找到文件: {file_name} (ID: {file_id})")
        except Exception as e:
            print(f"⚠️  无法获取文件列表，将直接尝试下载: {e}")
            file_name = f'package_file_{file_id}'

        # 使用Web界面URL格式（适用于自建GitLab，已验证成功）
        project_path_encoded = None
        try:
            # 获取项目路径
            project_url = f"{self.gitlab_url}/api/v4/projects/{project_id}"
            req_proj = urllib.request.Request(project_url, method='GET')
            for k, v in self.headers.items():
                req_proj.add_header(k, v)
            with urllib.request.urlopen(req_proj, timeout=30) as resp_proj:
                project_info = cast(Dict[str, Any], json.loads(resp_proj.read().decode('utf-8')))
                project_path_encoded = project_info.get('path_with_namespace', '').replace('/', '%2F')
        except Exception:
            pass

        # 使用Web界面URL格式（已验证成功）
        if project_path_encoded:
            download_url = f"{self.gitlab_url}/{project_path_encoded}/-/package_files/{file_id}/download"
        else:
            # 如果无法获取项目路径，使用传入的项目路径
            if project_path is not None:
                project_path_encoded = project_path.replace('/', '%2F')
            else:
                project_path_encoded = 'aoi-public%2Faoi-smartvision'
            download_url = f"{self.gitlab_url}/{project_path_encoded}/-/package_files/{file_id}/download"

        download_urls = [download_url]

        # 使用Web界面URL格式下载（已验证成功）
        api_url = download_urls[0]
        print(f"📥 下载URL: {api_url}")
        try:
            req = urllib.request.Request(api_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=60) as resp:
                # 从Content-Disposition头获取文件名
                content_disposition = resp.headers.get('Content-Disposition', '')
                filename = None
                if 'filename=' in content_disposition:
                    # 处理多种格式: filename="xxx" 或 filename*=UTF-8''xxx
                    if "filename*=" in content_disposition:
                        # 处理 RFC 5987 格式: filename*=UTF-8''web_zc_liuyan-0.4+heils.main.55d9bf50-py3-none-any.whl
                        parts = content_disposition.split("filename*=")
                        if len(parts) > 1:
                            encoded_name = parts[1].strip().split(";")[0].strip()
                            if encoded_name.startswith("UTF-8''"):
                                filename = encoded_name[7:]  # 移除 UTF-8'' 前缀
                    if not filename:
                        # 标准格式: filename="xxx"
                        filename = content_disposition.split('filename=')[1].split(';')[0].strip('"\'')

                # 如果没有从header获取到文件名，使用之前获取的文件名
                if not filename:
                    filename = file_name if 'file_name' in locals() else f"package_file_{file_id}"

                # 确定保存路径
                if save_path:
                    final_save_path = save_path
                else:
                    final_save_path = os.path.join(self.base_dir, filename)

                # 确保目录存在
                dir_path = os.path.dirname(final_save_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)

                # 下载文件
                total_size = 0
                chunk_size = 8192
                with open(final_save_path, 'wb') as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        total_size += len(chunk)
                        if total_size % (1024 * 1024) == 0:
                            print(f"   已下载: {total_size / 1024 / 1024:.2f} MB", end='\r')

                file_size = os.path.getsize(final_save_path)
                print(f"\n✅ 文件已下载: {final_save_path}")
                print(f"   文件大小: {file_size:,} 字节 ({file_size / 1024 / 1024:.2f} MB)")
                return True

        except urllib.error.HTTPError as e:
            print(f"❌ 下载失败: HTTP {e.code}")
            if e.code == 404:
                print(f"💡 404错误可能原因:")
                print(f"   1. Token权限不足（需要read_package_registry scope）")
                print(f"   2. 项目路径不正确")
            elif e.code == 403:
                print(f"💡 403错误: Token权限不足，需要read_package_registry权限")
            elif e.code == 401:
                print(f"💡 401错误: Token无效或已过期")
            try:
                error_body = e.read().decode('utf-8')
                if error_body:
                    print(f"错误详情: {error_body}")
            except Exception:
                pass
            return False
        except Exception as e:
            print(f"❌ 下载异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def find_package_by_file_id(self, project_id: int, file_id: int) -> Optional[Dict[str, Any]]:
        """
        通过file_id查找对应的package

        Args:
            project_id: 项目ID
            file_id: Package File ID

        Returns:
            包含package_id和file信息的字典，如果未找到返回None
        """
        packages = self.list_packages(project_id, per_page=100)
        if not packages:
            return None

        for pkg in packages:
            pkg_id = pkg.get('id')
            if pkg_id is not None and isinstance(pkg_id, (int, str)):
                files = self.get_package_files(project_id, int(pkg_id))
                if files:
                    for file_info in files:
                        if file_info.get('id') == file_id:
                            return {
                                'package_id': int(pkg_id),
                                'package': pkg,
                                'file': file_info
                            }
        return None

    def download_package_file_by_id(self, project_id: int, file_id: int,
                                    save_path: Optional[str] = None) -> bool:
        """
        通过file_id直接下载package文件（自动查找package_id）

        Args:
            project_id: 项目ID
            file_id: Package File ID
            save_path: 保存路径（可选）

        Returns:
            是否下载成功
        """
        print(f"🔍 正在查找file_id={file_id}对应的package...")
        result = self.find_package_by_file_id(project_id, file_id)

        if not result:
            print(f"❌ 未找到file_id={file_id}对应的package")
            return False

        package_id = result['package_id']
        file_info = result['file']
        file_name = file_info.get('file_name', f'package_file_{file_id}')

        print(f"✅ 找到package (ID: {package_id}, 文件名: {file_name})")
        return self.download_package_file(project_id, package_id, file_id, save_path, None)

    def download_generic_package(self, project_id: int, package_name: str,
                                package_version: str, file_name: str,
                                save_path: Optional[str] = None) -> bool:
        """
        下载Generic Package文件（适用于Generic Package Registry）

        Args:
            project_id: 项目ID
            package_name: 包名称
            package_version: 包版本
            file_name: 文件名
            save_path: 保存路径（可选）

        Returns:
            是否下载成功
        """
        api_url = f"{self.gitlab_url}/api/v4/projects/{project_id}/packages/generic/{package_name}/{package_version}/{file_name}"

        try:
            req = urllib.request.Request(api_url, method='GET')
            for k, v in self.headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=60) as resp:
                if save_path:
                    final_save_path = save_path
                else:
                    final_save_path = os.path.join(self.base_dir, file_name)

                dir_path = os.path.dirname(final_save_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)

                with open(final_save_path, 'wb') as f:
                    f.write(resp.read())

                print(f"✅ Generic Package文件已下载: {final_save_path}")
                return True
        except urllib.error.HTTPError as e:
            print(f"❌ 下载Generic Package文件失败: HTTP {e.code}")
            try:
                error_body = e.read().decode('utf-8')
                print(f"错误详情: {error_body}")
            except Exception:
                pass
            return False
        except Exception as e:
            print(f"❌ 下载Generic Package文件异常: {e}")
            return False


def load_config() -> Optional[Dict[str, Any]]:
    """从配置文件加载GitLab配置"""
    config_path = project_root / 'config' / 'wps_gitlab_config.json'

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            gitlab_config = config.get('gitlab', {})
            return {
                'url': gitlab_config.get('url', ''),
                'token': gitlab_config.get('token', '')
            }
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("GitLab Packages 下载工具")
    print("=" * 60)

    # 从配置文件加载或使用命令行参数
    config = load_config()

    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python get_gitlab_packages.py <project_path> [action] [options]")
        print("\n示例:")
        print("  # 列出所有packages")
        print("  python get_gitlab_packages.py aoi-public/aoi-smartvision list")
        print("\n  # 通过file_id直接下载（推荐）")
        print("  python get_gitlab_packages.py aoi-public/aoi-smartvision download-file <file_id> [save_path]")
        print("\n  # 下载指定package文件（需要package_id和file_id）")
        print("  python get_gitlab_packages.py aoi-public/aoi-smartvision download <package_id> <file_id> [save_path]")
        print("\n  # 下载Generic Package")
        print("  python get_gitlab_packages.py aoi-public/aoi-smartvision download-generic <package_name> <version> <file_name> [save_path]")
        sys.exit(1)

    project_path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else 'list'

    # 获取配置
    if config:
        gitlab_url = config['url']
        token = config['token']
    else:
        gitlab_url = os.getenv('GITLAB_URL', 'https://dev.heils.cn')
        token = os.getenv('GITLAB_TOKEN', '')
        if not token:
            print("❌ 请设置GITLAB_TOKEN环境变量或确保config/wps_gitlab_config.json存在")
            sys.exit(1)

    print(f"\n📋 项目路径: {project_path}")
    print(f"🔗 GitLab URL: {gitlab_url}")

    # 创建管理器（文件保存到项目根目录）
    manager = GitLabPackageManager(gitlab_url, token, base_dir=str(project_root))

    # 获取项目ID
    print("\n🔍 正在获取项目ID...")
    project_id = manager.get_project_id_by_path(project_path)
    if not project_id:
        print("❌ 无法获取项目ID，请检查项目路径和token权限")
        sys.exit(1)

    # 执行操作
    if action == 'list':
        print("\n📦 正在获取packages列表...")
        packages = manager.list_packages(project_id)

        if packages:
            print(f"\n找到 {len(packages)} 个packages:\n")
            for i, pkg in enumerate(packages, 1):
                print(f"{i}. Package ID: {pkg.get('id')}")
                print(f"   名称: {pkg.get('name', 'N/A')}")
                print(f"   版本: {pkg.get('version', 'N/A')}")
                print(f"   类型: {pkg.get('package_type', 'N/A')}")
                print(f"   创建时间: {pkg.get('created_at', 'N/A')}")

                # 获取文件列表
                pkg_id = pkg.get('id')
                if pkg_id is not None and isinstance(pkg_id, (int, str)):
                    files = manager.get_package_files(project_id, int(pkg_id))
                    if files:
                        print(f"   文件数量: {len(files)}")
                        for file_info in files:
                            print(f"     - {file_info.get('file_name', 'N/A')} (ID: {file_info.get('id')})")
                print()

    elif action == 'download-file':
        if len(sys.argv) < 4:
            print("❌ 下载命令需要file_id参数")
            print("用法: python get_gitlab_packages.py <project_path> download-file <file_id> [package_id] [save_path]")
            print("     如果知道package_id，可以指定以加快下载速度")
            sys.exit(1)

        file_id = int(sys.argv[3])
        # 如果提供了package_id，直接使用；否则自动查找
        if len(sys.argv) > 4 and sys.argv[4].isdigit():
            package_id = int(sys.argv[4])
            save_path = sys.argv[5] if len(sys.argv) > 5 else None
            print(f"\n⬇️  正在下载文件 (Package ID: {package_id}, File ID: {file_id})...")
            success = manager.download_package_file(project_id, package_id, file_id, save_path)
        else:
            save_path = sys.argv[4] if len(sys.argv) > 4 else None
            print(f"\n⬇️  正在下载文件 (File ID: {file_id})...")
            success = manager.download_package_file_by_id(project_id, file_id, save_path)

        if not success:
            sys.exit(1)

    elif action == 'download':
        if len(sys.argv) < 5:
            print("❌ 下载命令需要package_id和file_id参数")
            print("用法: python get_gitlab_packages.py <project_path> download <package_id> <file_id> [save_path]")
            print("\n💡 提示: 如果不确定file_id，可以先列出package的文件:")
            print("   python get_gitlab_packages.py <project_path> list-files <package_id>")
            sys.exit(1)

        package_id = int(sys.argv[3])
        file_id = int(sys.argv[4])
        save_path = sys.argv[5] if len(sys.argv) > 5 else None

        print(f"\n⬇️  正在下载文件 (Package ID: {package_id}, File ID: {file_id})...")
        success = manager.download_package_file(project_id, package_id, file_id, save_path, project_path)
        if not success:
            sys.exit(1)

    elif action == 'list-files':
        if len(sys.argv) < 4:
            print("❌ 需要package_id参数")
            print("用法: python get_gitlab_packages.py <project_path> list-files <package_id>")
            sys.exit(1)

        package_id = int(sys.argv[3])
        print(f"\n📁 正在获取package {package_id}的文件列表...")
        files = manager.get_package_files(project_id, package_id)

        if files:
            print(f"\n找到 {len(files)} 个文件:\n")
            for i, file_info in enumerate(files, 1):
                file_id_val = file_info.get('id')
                file_name = file_info.get('file_name', 'N/A')
                file_size = file_info.get('size', 'N/A')
                if file_id_val is not None:
                    print(f"{i}. File ID: {file_id_val}")
                    print(f"   文件名: {file_name}")
                    print(f"   大小: {file_size}")
                    print()
        else:
            print(f"❌ 未找到文件或package不存在")

    elif action == 'download-generic':
        if len(sys.argv) < 6:
            print("❌ Generic Package下载命令需要package_name、version和file_name参数")
            print("用法: python get_gitlab_packages.py <project_path> download-generic <package_name> <version> <file_name> [save_path]")
            sys.exit(1)

        package_name = sys.argv[3]
        package_version = sys.argv[4]
        file_name = sys.argv[5]
        save_path = sys.argv[6] if len(sys.argv) > 6 else None

        print(f"\n⬇️  正在下载Generic Package文件...")
        print(f"   包名: {package_name}")
        print(f"   版本: {package_version}")
        print(f"   文件名: {file_name}")
        success = manager.download_generic_package(project_id, package_name, package_version, file_name, save_path)
        if not success:
            sys.exit(1)

    else:
        print(f"❌ 未知操作: {action}")
        sys.exit(1)

    print("\n✅ 操作完成")


if __name__ == "__main__":
    main()
