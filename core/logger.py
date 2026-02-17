import os
import time
import logging

from logging import info

# 设置日志目录路径，位于当前脚本所在目录下的 'log' 文件夹中
LOGGER_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')

def __check_logger_dir():
    if os.access(LOGGER_DIR, os.F_OK) is False:
        os.mkdir(LOGGER_DIR)

    # 清除过期日志（跳过被其他进程占用的文件，避免 PermissionError）
    for filename in os.listdir(LOGGER_DIR):
        filepath = os.path.join(LOGGER_DIR, filename)
        try:
            stat = os.stat(filepath)
            if time.time() - stat.st_atime > 600:
                os.remove(filepath)
        except (PermissionError, OSError):
            pass  # 文件被占用或无法删除时跳过

def init_logger():
    __check_logger_dir()
    logging.basicConfig(
        filename=os.path.join(LOGGER_DIR, str(os.getpid()) + ".log"),
    	level=logging.INFO,
        format='%(message)s'
    )