#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志轮转脚本
定期清理和压缩旧日志文件
"""

import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import logging

class LogRotator:
    """日志轮转器"""

    def __init__(self, log_dir: Optional[str] = None, max_days: int = 30, max_size_mb: int = 100):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / "logs"
        self.max_days = max_days
        self.max_size_mb = max_size_mb
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger('log_rotator')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def compress_log_file(self, file_path: Path):
        """压缩日志文件"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')

            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 删除原文件
            file_path.unlink()

            self.logger.info(f"压缩日志文件: {file_path.name} -> {compressed_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"压缩日志文件失败 {file_path.name}: {str(e)}")
            return False

    def cleanup_old_logs(self):
        """清理旧日志文件"""
        if not self.log_dir.exists():
            self.logger.warning(f"日志目录不存在: {self.log_dir}")
            return

        cutoff_date = datetime.now() - timedelta(days=self.max_days)
        cleaned_count = 0

        for log_file in self.log_dir.glob("*.log*"):
            try:
                # 获取文件修改时间
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                if file_mtime < cutoff_date:
                    log_file.unlink()
                    cleaned_count += 1
                    self.logger.info(f"删除旧日志文件: {log_file.name}")

            except Exception as e:
                self.logger.error(f"删除日志文件失败 {log_file.name}: {str(e)}")

        self.logger.info(f"清理完成，删除了 {cleaned_count} 个旧日志文件")

    def rotate_large_logs(self):
        """轮转大日志文件"""
        if not self.log_dir.exists():
            return

        rotated_count = 0

        for log_file in self.log_dir.glob("*.log"):
            try:
                # 检查文件大小
                size_mb = log_file.stat().st_size / (1024 * 1024)

                if size_mb > self.max_size_mb:
                    # 创建带时间戳的备份文件名
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
                    backup_path = log_file.parent / backup_name

                    # 移动文件
                    shutil.move(str(log_file), str(backup_path))

                    # 压缩备份文件
                    self.compress_log_file(backup_path)

                    rotated_count += 1
                    self.logger.info(f"轮转大日志文件: {log_file.name} ({size_mb:.2f} MB)")

            except Exception as e:
                self.logger.error(f"轮转日志文件失败 {log_file.name}: {str(e)}")

        self.logger.info(f"轮转完成，处理了 {rotated_count} 个大日志文件")

    def get_log_stats(self):
        """获取日志统计信息"""
        if not self.log_dir.exists():
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'oldest_file': None,
                'newest_file': None
            }

        log_files = list(self.log_dir.glob("*.log*"))

        if not log_files:
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'oldest_file': None,
                'newest_file': None
            }

        total_size = sum(f.stat().st_size for f in log_files)
        file_times = [(f, datetime.fromtimestamp(f.stat().st_mtime)) for f in log_files]

        oldest_file = min(file_times, key=lambda x: x[1])[0].name
        newest_file = max(file_times, key=lambda x: x[1])[0].name

        return {
            'total_files': len(log_files),
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_file': oldest_file,
            'newest_file': newest_file
        }

    def run_rotation(self):
        """执行完整的日志轮转"""
        self.logger.info("开始日志轮转...")

        # 获取轮转前统计
        stats_before = self.get_log_stats()
        self.logger.info(f"轮转前: {stats_before['total_files']} 个文件, {stats_before['total_size_mb']:.2f} MB")

        # 轮转大文件
        self.rotate_large_logs()

        # 清理旧文件
        self.cleanup_old_logs()

        # 获取轮转后统计
        stats_after = self.get_log_stats()
        self.logger.info(f"轮转后: {stats_after['total_files']} 个文件, {stats_after['total_size_mb']:.2f} MB")

        self.logger.info("日志轮转完成")

def main():
    """主函数"""
    rotator = LogRotator()
    rotator.run_rotation()

if __name__ == "__main__":
    main()
