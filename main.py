"""
应用入口：供 Flet 桌面运行 / flet build apk / buildozer 打包使用。

- Flet 模式：flet run / flet build apk 使用 gui_flet
- Buildozer Kivy 模式：buildozer android/ios/osx 打包时排除 gui_flet，回退到 Kivy 客户端
"""
if __name__ == "__main__":
    try:
        from gui_flet.main import run

        run()
    except ImportError:
        # Buildozer Kivy 打包：gui_flet 已排除，使用 Kivy 客户端入口
        import os
        import sys
        import logging

        _root = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, _root)

        from cli.terminal_utils import register_signal_handler
        import core.logger as logger
        from client.client import Client
        from client.interface import run_client

        logger.init_logger()
        register_signal_handler(lambda: sys.exit(0))

        client = Client(no_cookie=True)
        client.load_config_silent()
        if client.logger is None:
            client.logger = logging.getLogger("liujiatong")

        run_client(client, "GUI_KIVY")
