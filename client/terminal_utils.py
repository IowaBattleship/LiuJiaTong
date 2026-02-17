"""命令行终端工具：薄封装，统一从 common.console 导出，便于 client 现有代码兼容。"""

from common.console import (
    verbose,
    success,
    warn,
    error,
    fatal,
    user_confirm,
    check_packages,
    register_signal_handler,
    disable_echo,
    enable_echo,
)

__all__ = [
    "verbose",
    "success",
    "warn",
    "error",
    "fatal",
    "user_confirm",
    "check_packages",
    "register_signal_handler",
    "disable_echo",
    "enable_echo",
]
