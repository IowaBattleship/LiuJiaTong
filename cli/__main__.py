"""
CLI 入口模块。Client 类已迁移至 client.client，此处仅保留兼容性导入与包检查。
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.terminal_utils import check_packages

check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})

# 兼容：原从 cli.__main__ 导入 Client 的代码仍可使用
from client.client import Client
