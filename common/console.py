"""终端输出与交互：彩色输出、确认、信号处理、回显控制等。供 server 与 client 共用。"""

import os
import sys
import threading
import importlib

_if_need_restart = False


def verbose(string: str) -> None:
    print(f"\x1b[30m\x1b[1m{string}\x1b[0m")


def success(string: str) -> None:
    print(f"\x1b[32m\x1b[1m{string}\x1b[0m")


def warn(string: str) -> None:
    print(f"\x1b[33m\x1b[1m{string}\x1b[0m")


def error(string: str) -> None:
    print(f"\x1b[31m\x1b[1m{string}\x1b[0m")


def user_confirm(prompt: str, default: bool) -> bool:
    while True:
        print(prompt, end="")
        print("[Y/n]" if default is True else "[y/N]", end="")
        print(": ", end="")
        while True:
            try:
                resp = input().upper()
            except EOFError:
                pass
            else:
                break
        if resp == "":
            return default
        elif resp == "Y":
            return True
        elif resp == "N":
            return False
        else:
            print("非法输入，", end="")


def _try_to_import(package_info: tuple) -> None:
    global _if_need_restart
    package, install = package_info
    try:
        importlib.import_module(package)
    except ImportError:
        os.system(f"pip3 install {package if install is None else install}")
        _if_need_restart = True


def check_packages(packages: dict) -> None:
    global _if_need_restart
    for package_info in packages.get(os.name, []):
        _try_to_import(package_info)
    for package_info in packages.get("default", []):
        _try_to_import(package_info)
    if _if_need_restart:
        success("Packages are installed, please restart program to update system enviroment")
        sys.exit(0)


def register_signal_handler(ctrl_c_handler) -> None:
    if os.name == "posix":
        import signal

        def console_ctrl_handler(sig, frame):
            threading.Thread(target=ctrl_c_handler).start()

        signal.signal(signal.SIGINT, console_ctrl_handler)
    elif os.name == "nt":
        import win32api  # type: ignore
        import win32con  # type: ignore

        def console_ctrl_handler(ctrl_type):
            if ctrl_type == win32con.CTRL_C_EVENT:
                threading.Thread(target=ctrl_c_handler).start()
                return True

        win32api.SetConsoleCtrlHandler(console_ctrl_handler, True)
    else:
        raise RuntimeError("Unknown os")


def fatal(string: str) -> None:
    error(string)
    enable_echo()
    os._exit(1)


# 终端回显控制
if os.name == "posix":
    import termios

    _old_termios_setting = termios.tcgetattr(sys.stdin)

    def disable_echo() -> None:
        termios_setting = termios.tcgetattr(sys.stdin)
        termios_setting[3] &= ~termios.ECHO
        termios_setting[3] &= ~termios.ICANON
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, termios_setting)

    def enable_echo() -> None:
        global _old_termios_setting
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, _old_termios_setting)

elif os.name == "nt":

    def disable_echo() -> None:
        pass

    def enable_echo() -> None:
        pass

else:
    raise RuntimeError("Unknown os")
