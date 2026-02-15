"""
客户端用户接口抽象层：通过消息传递机制通知 UI 更新，不直接依赖 CLI 或 GUI 实现。
"""
import threading
from core.sound import playsound, playsounds
from core.playingrules import judge_and_transform_cards, CardType
from core.card import Card
from core.FieldInfo import FieldInfo
from gui import update_gui, init_gui, UIFramework
from cli.terminal_utils import disable_echo, enable_echo

INTERFACE_TYPE = "CLI"
_MODE_CLI = "CLI"
_MODE_GUI = "GUI"
_MODE_GUI_FLET = "GUI_FLET"
_MODE_GUI_KIVY = "GUI_KIVY"

_ui_handler = None
_simulation_mode = False


def set_simulation_mode(enabled: bool) -> None:
    """开启/关闭模拟模式：自动出牌、跳过，不等待真实用户输入。"""
    global _simulation_mode
    _simulation_mode = enabled


def is_simulation_mode() -> bool:
    """是否处于模拟模式。"""
    return _simulation_mode


def set_interface_type(type: str):
    global INTERFACE_TYPE
    INTERFACE_TYPE = type


def get_interface_type() -> str:
    return INTERFACE_TYPE


def set_ui_handler(handler):
    """注册 UI 处理器，用于接收等待大厅、牌局、游戏结束等通知。"""
    global _ui_handler
    _ui_handler = handler


def get_ui_handler():
    return _ui_handler


def waiting_hall_interface(users_name, users_error) -> None:
    """通知 UI 更新等待大厅信息。"""
    if _ui_handler and hasattr(_ui_handler, "on_waiting_hall"):
        _ui_handler.on_waiting_hall(users_name, users_error)


def main_interface(
    is_start, is_player, client_cards, client_player: int,
    users_name, users_score, users_cards_num, users_cards,
    users_played_cards, head_master, now_score, now_player, last_player,
    his_now_score, his_last_player,
) -> None:
    """通知 UI 更新牌局信息。"""
    field_info = FieldInfo(
        is_start, is_player, client_player, client_cards,
        users_name, users_score, users_cards_num, users_cards,
        users_played_cards, head_master, now_score, now_player,
        last_player, his_now_score, his_last_player,
    )

    if _ui_handler and hasattr(_ui_handler, "on_field_info"):
        _ui_handler.on_field_info(field_info)
    else:
        # 回退：直接推送到 GUI（兼容 gui_flet 独立启动等场景）
        from gui import update_gui
        update_gui(field_info)
        try:
            import sys
            gf = sys.modules.get("gui_flet.gui_flet")
            if gf is not None and hasattr(gf, "_update_queue"):
                gf._update_queue.put(field_info)
        except Exception:
            pass

    _play_sound(
        is_start=is_start,
        last_player=last_player,
        now_player=now_player,
        his_last_player=his_last_player,
        his_now_score=his_now_score,
        users_played_cards=users_played_cards,
    )


def _play_sound(
    is_start: bool,
    last_player: int,
    now_player: int,
    his_last_player: int,
    his_now_score: int,
    users_played_cards: list,
):
    if not is_start:
        playsounds(["start", "open"], True)
    elif last_player == now_player and his_now_score > 0:
        playsound("fen", True, None)
    elif last_player == his_last_player:
        playsound("pass", True, None)
    else:
        last_played_cards = [c.value for c in users_played_cards[last_player]]
        last_played_cards.sort(reverse=True)
        (cardtype, _) = judge_and_transform_cards(last_played_cards)
        assert cardtype != CardType.illegal_type, (last_player, last_played_cards)
        bombs = [
            CardType.black_joker_bomb,
            CardType.red_joker_bomb,
            CardType.normal_bomb,
        ]
        if cardtype in bombs:
            if len(last_played_cards) >= 7:
                playsound("bomb3", True, None)
            elif len(last_played_cards) >= 5:
                playsound("bomb2", True, None)
            else:
                playsound("bomb1", True, None)
        else:
            if len(last_played_cards) >= 5:
                playsound("throw2", True, None)
            else:
                playsound("throw1", True, None)


def game_over_interface(client_player: int, if_game_over: int) -> None:
    """通知 UI 游戏结束。"""
    if _ui_handler and hasattr(_ui_handler, "on_game_over"):
        _ui_handler.on_game_over(client_player, if_game_over)
    else:
        from core.sound import playsound
        if (client_player + 1) % 2 == (if_game_over + 2) % 2:
            print("游戏结束，你的队伍获得了胜利", end="")
            if if_game_over < 0:
                print("，并成功双统")
        else:
            print("游戏结束，你的队伍未能取得胜利", end="")
            if if_game_over < 0:
                print("，并被对方双统")
        playsound("clap", False, None)


def run_client(client, mode: str) -> None:
    """
    根据 mode 启动客户端并运行游戏，负责接口类型设置、GUI 初始化及连接/运行逻辑。
    mode: "CLI" | "GUI" | "GUI_FLET" | "GUI_KIVY"
    """
    mode = (mode or _MODE_CLI).upper()
    if mode not in (_MODE_CLI, _MODE_GUI, _MODE_GUI_FLET, _MODE_GUI_KIVY):
        client.logger.warning("未知 mode %r，回退到 CLI", mode)
        mode = _MODE_CLI

    if mode == _MODE_CLI:
        from cli.interface_cli import create_cli_handler
        from core.sound import playsound
        set_ui_handler(create_cli_handler(playsound))
    elif mode in (_MODE_GUI, _MODE_GUI_FLET, _MODE_GUI_KIVY):
        set_ui_handler(_create_gui_handler())

    def _do_run():
        client.connect(client.config.ip, client.config.port)
        disable_echo()
        client.run()
        enable_echo()
        client.close()

    if mode == _MODE_GUI:
        client.logger.info("启动GUI模式 (tkinter)")
        set_interface_type("GUI")
        init_gui(client.logger, UIFramework.TKINTER)
        _do_run()
    elif mode == _MODE_GUI_FLET:
        client.logger.info("启动GUI模式 (flet)")
        set_interface_type("GUI")
        init_gui(client.logger, UIFramework.FLET, client=client)
    elif mode == _MODE_GUI_KIVY:
        client.logger.info("启动GUI模式 (kivy)")
        set_interface_type("GUI")
        init_gui(client.logger, UIFramework.KIVY, client=client)
    else:
        client.logger.info("启动命令行模式")
        _do_run()


def _create_gui_handler():
    """创建 GUI 端处理器：将 on_field_info 转发给 update_gui。"""

    class GUIHandler:
        def on_waiting_hall(self, users_name, users_error):
            pass  # GUI 由自身流程处理等待大厅

        def on_field_info(self, field_info):
            update_gui(field_info)
            try:
                import sys
                gf = sys.modules.get("gui_flet.gui_flet")
                if gf is not None and hasattr(gf, "_update_queue"):
                    gf._update_queue.put(field_info)
                gk = sys.modules.get("gui_kivy.gui_kivy")
                if gk is not None and hasattr(gk, "_update_queue"):
                    gk._update_queue.put(field_info)
            except Exception:
                pass

        def on_game_over(self, client_player: int, if_game_over: int):
            from core.sound import playsound
            playsound("clap", False, None)

    return GUIHandler()
