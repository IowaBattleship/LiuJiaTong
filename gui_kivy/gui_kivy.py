"""Kivy-based GUI implementation, mirroring gui_flet UI and update mechanism."""

import os
import sys
import queue
import logging
import threading
from logging import Logger


# 使用项目内字体 core/fonts/ZiTiGuanJiaFangSongTi-2.ttf，在 init_gui_kivy() 中注册
FONT_CN_NAME = "FangSong"
FONT_CN = FONT_CN_NAME

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_client_dir = os.path.join(_project_root, "client")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _client_dir not in sys.path:
    sys.path.insert(0, _client_dir)

import core.logger as logger_module
from core.card import Card, Suits
from core.FieldInfo import FieldInfo
from cli.card_utils import int_to_str, calculate_team_scores
from cli.terminal_utils import disable_echo, enable_echo
from core import playingrules
from core.auto_play.strategy import auto_select_cards

# Default layout constants (same as gui_flet)
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 810
DEFAULT_VERTICAL_MARGIN = 40
HORIZONTAL_CARD_MARGIN = 160
VERTICAL_CARD_SPACING = 110
DEFAULT_CARD_WIDTH = 71
DEFAULT_CARD_HEIGHT = 100
DEFAULT_CARD_SPACING = 20
PLAYED_CARD_SPACING = 30

PLAYER_CARD_AVATAR_BG = "#2d4a6f"
PLAYER_CARD_TEXT_COLOR = (0.91, 0.91, 0.91, 1)  # #e8e8e8
PLAYER_CARD_BORDER = "#3d5a80"
PLAYER_CARD_PADDING = 8
PLAYER_CARD_AVATAR_SIZE = 36
PLAYER_CARD_RADIUS = 14
PLAYER_NAME_MAX_LEN = 8
UNIFIED_INFO_SECTION_WIDTH = 155
UNIFIED_INFO_SECTION_HEIGHT = 68
PLAYER_CARD_GRADIENT_START = "#0f2035"
PLAYER_CARD_GRADIENT_END = "#1e3a52"

SCORE_PANEL_GRADIENT_START = "#0d1820"
SCORE_PANEL_GRADIENT_END = "#1e3a52"
SCORE_PANEL_RADIUS = 16
SCORE_NUMBER_FONT = 26
SCORE_LABEL_FONT = 13

PLAYER_OFFSET_SE, PLAYER_OFFSET_NE, PLAYER_OFFSET_TOP = 1, 2, 3
PLAYER_OFFSET_NW, PLAYER_OFFSET_SW = 4, 5

_images_dir = os.path.join(_project_root, "core", "assets")

_gui_kivy_logger = None


def _get_card_queue():
    """从 client.gui 获取 card_queue。"""
    from gui import card_queue
    return card_queue


def _run_client_thread(client) -> None:
    """在后台线程中运行客户端网络循环。"""
    client.connect(client.config.ip, client.config.port)
    disable_echo()
    client.run()
    enable_echo()
    client.close()


def _card_image_path(card: Card, target_height: int) -> str:
    if card.suit == Suits.empty:
        name = "JOKER-B.png" if card.value == 16 else "JOKER-A.png"
    elif card.value > 10:
        name = card.suit.value + int_to_str(card.value) + ".png"
    else:
        name = card.suit.value + str(card.value) + ".png"
    return os.path.abspath(os.path.join(_images_dir, name))


def _background_path() -> str:
    return os.path.abspath(os.path.join(_images_dir, "Background.png"))


def _truncate_name(name: str, max_len: int) -> str:
    if not name:
        return "?"
    if len(name) <= max_len:
        return name
    return name[: max_len - 1] + "…"


def _centered_row_start(layout, card_count: int) -> int:
    total_width = layout.card_width + layout.card_spacing * max(card_count, 1)
    return (layout.width - total_width) // 2


class LayoutParams:
    """Layout parameters computed from window (width, height). Same logic as gui_flet."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.scale_x = width / DEFAULT_WINDOW_WIDTH
        self.scale_y = height / DEFAULT_WINDOW_HEIGHT
        self.scale = min(self.scale_x, self.scale_y, 1.5)

        self.vertical_margin = int(DEFAULT_VERTICAL_MARGIN * self.scale_y)
        self.card_width = int(DEFAULT_CARD_WIDTH * self.scale)
        self.card_height = int(DEFAULT_CARD_HEIGHT * self.scale)
        self.card_spacing = int(DEFAULT_CARD_SPACING * self.scale)
        self.played_card_spacing = int(PLAYED_CARD_SPACING * self.scale)
        self.vertical_card_spacing = int(VERTICAL_CARD_SPACING * self.scale)
        self.horizontal_card_margin = int(HORIZONTAL_CARD_MARGIN * self.scale_x)

        self.info_section_width = int(UNIFIED_INFO_SECTION_WIDTH * self.scale)
        self.info_section_height = int(UNIFIED_INFO_SECTION_HEIGHT * self.scale)

        bottom_margin = int(40 * self.scale_y)

        self.my_played_cards_y = height - self.vertical_margin - self.card_height * 2 - self.vertical_card_spacing
        self.top_played_cards_y = self.vertical_margin + self.card_height + self.vertical_card_spacing

        self.button_right_margin = int(30 * self.scale_x)
        self.button_bottom_margin = int(40 * self.scale_y)
        self.button_spacing = int(55 * self.scale_y)
        self.score_anchor_x = width - int(50 * self.scale_x)
        self.font_size = max(12, int(20 * self.scale))

        self.avatar_size = int(PLAYER_CARD_AVATAR_SIZE * self.scale)
        self.score_number_size = max(18, int(24 * self.scale))
        self.score_label_size = max(9, int(11 * self.scale))

        self.info_section_offset = self.card_height // 2 - self.info_section_height // 2
        self.horizontal_info_section_margin = int(180 * self.scale_x)

        self.bottom_card_y = height - bottom_margin - self.card_height
        self.bottom_info_section_y = height - bottom_margin - self.info_section_height - self.info_section_offset

        self.top_card_y = self.vertical_margin
        self.top_info_section_y = self.top_card_y + self.info_section_offset

        self.horizontal_info_margin = int(20 * self.scale_x)
        self.horizontal_card_margin = self.horizontal_info_margin + self.info_section_width + int(20 * self.scale_x)

        top_center = self.top_card_y + self.card_height / 2
        bottom_center = self.bottom_card_y + self.card_height / 2
        band_gap = (bottom_center - top_center) / 3
        upper_center = top_center + band_gap
        lower_center = top_center + 2 * band_gap

        self.upper_card_y = int(upper_center - self.card_height / 2)
        self.lower_card_y = int(lower_center - self.card_height / 2)
        self.upper_info_section_y = self.upper_card_y + self.info_section_offset
        self.lower_info_section_y = self.lower_card_y + self.info_section_offset


_update_queue = queue.Queue()
_kivy_client = None


def _to_kivy_y(layout, top: int, widget_height: int) -> int:
    """Flet 使用 top（距顶部），Kivy 使用 y（距底部）。"""
    return layout.height - top - widget_height


class KivyGUIProxy:
    """无界面的代理，update() 将 FieldInfo 放入队列，供主线程消费。"""

    def __init__(self, logger: Logger, client=None):
        self.logger = logger
        self.client = client

    def update(self, info: FieldInfo) -> None:
        if _gui_kivy_logger:
            _gui_kivy_logger.info("KivyGUIProxy.update: received FieldInfo, client_id=%s", info.client_id)
        _update_queue.put(info)


class LiuJiaTongApp:
    """Kivy App 入口，持有 KivyGUI 并轮询更新队列。"""

    def __init__(self, logger: Logger, client=None):
        self.logger = logger
        self.client = client or _kivy_client
        self.kivy_gui = None  # 在 build() 里创建并赋值

    def build(self):
        from kivy.core.window import Window
        from kivy.uix.floatlayout import FloatLayout
        from kivy.clock import Clock

        Window.clearcolor = (0.05, 0.09, 0.13, 1)  # #0d1820
        Window.size = (DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        Window.minimum_width = 800
        Window.minimum_height = 500

        self.root = FloatLayout(size_hint=(1, 1))
        self.kivy_gui = KivyGUI(self.root, self.logger, self.client)
        self.kivy_gui._update_start_screen()

        import gui as gui_module
        gui_module.register_gui_page(self.kivy_gui)
        Clock.schedule_once(lambda dt: gui_module.register_gui_fully_ready(), 0)

        Clock.schedule_interval(self._poll_updates, 0.1)
        from kivy.core.window import Window
        Window.bind(size=self._on_resize)
        return self.root

    def _on_resize(self, *args):
        if self.kivy_gui and self.kivy_gui.field_info is not None:
            self.kivy_gui.build_and_update(self.kivy_gui.field_info)

    def _poll_updates(self, dt):
        try:
            info = _update_queue.get_nowait()
            if _gui_kivy_logger:
                _gui_kivy_logger.info("_poll_updates: got FieldInfo, client_id=%s", info.client_id)
            if self.kivy_gui:
                self.kivy_gui.build_and_update(info)
        except queue.Empty:
            pass


class KivyGUI:
    """主 Kivy 界面控制器，与 FletGUI 结构对应。"""

    def __init__(self, root, logger: Logger, client=None):
        self.root = root
        self.logger = logger
        self.client = client or _kivy_client
        self.field_info: FieldInfo | None = None
        self.selected_card_flag: list[bool] = []
        self.auto_play_enabled: bool = False
        self._last_auto_play_state: tuple | None = None
        self._start_screen_state: str = "no_config"

    def _get_layout(self):
        from kivy.core.window import Window
        w = max(Window.width or 800, 800)
        h = max(Window.height or 500, 500)
        return LayoutParams(int(w), int(h))

    def _update_start_screen(self) -> None:
        self.root.clear_widgets()
        self.root.add_widget(self._build_start_screen_container())

    def _build_start_screen_container(self):
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from kivy.uix.textinput import TextInput
        from kivy.uix.floatlayout import FloatLayout

        layout = FloatLayout(size_hint=(1, 1))

        if self.client is None:
            box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(400, 120),
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
            box.add_widget(Label(text="六家统", font_name=FONT_CN, font_size="24sp", bold=True, color=PLAYER_CARD_TEXT_COLOR))
            box.add_widget(Label(text="等待游戏开始...", font_name=FONT_CN, font_size="18sp", color=(0.63, 0.63, 0.63, 1)))
            layout.add_widget(box)
            return layout

        if self.client.config is not None:
            self._start_screen_state = "has_config"
            box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(400, 220),
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
            cfg = self.client.config
            box.add_widget(Label(text="六家统", font_name=FONT_CN, font_size="24sp", bold=True, color=PLAYER_CARD_TEXT_COLOR))
            box.add_widget(Label(text="欢迎回来", font_name=FONT_CN, font_size="18sp", color=(0.63, 0.63, 0.63, 1)))
            box.add_widget(Label(text=f"服务器: {cfg.ip}:{cfg.port}", font_name=FONT_CN, font_size="14sp", color=PLAYER_CARD_TEXT_COLOR))
            box.add_widget(Label(text=f"用户名: {cfg.name}", font_name=FONT_CN, font_size="14sp", color=PLAYER_CARD_TEXT_COLOR))

            join_btn = Button(text="加入房间", font_name=FONT_CN, size_hint=(None, None), size=(120, 44),
                              pos_hint={"center_x": 0.5})
            join_btn.bind(on_press=lambda x: self._on_join_room())
            logout_btn = Button(text="退出登录", font_name=FONT_CN, size_hint=(None, None), size=(120, 44))
            logout_btn.bind(on_press=lambda x: self._on_logout())

            btn_row = BoxLayout(orientation="horizontal", size_hint=(None, None), size=(260, 44),
                               pos_hint={"center_x": 0.5}, spacing=20)
            btn_row.add_widget(join_btn)
            btn_row.add_widget(logout_btn)
            box.add_widget(btn_row)
            layout.add_widget(box)
            return layout

        self._start_screen_state = "no_config"
        ip_field = TextInput(hint_text="如 192.168.1.100", font_name=FONT_CN, multiline=False, size_hint=(None, None), size=(280, 40))
        port_field = TextInput(hint_text="如 8081", font_name=FONT_CN, multiline=False, size_hint=(None, None), size=(280, 40),
                               input_filter="int")
        name_field = TextInput(hint_text="请输入用户名", font_name=FONT_CN, multiline=False, size_hint=(None, None), size=(280, 40))

        def on_confirm(instance):
            ip = (ip_field.text or "").strip()
            port_str = (port_field.text or "").strip()
            name = (name_field.text or "").strip()
            if not ip or not port_str or not name:
                return
            try:
                port = int(port_str)
            except ValueError:
                return
            from core.config import Config
            self.client.config = Config(ip, port, name)
            self.client.config.dump()
            self.client.init_logger()
            self._on_join_room()

        box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(320, 320),
                        pos_hint={"center_x": 0.5, "center_y": 0.5}, spacing=12)
        box.add_widget(Label(text="六家统", font_name=FONT_CN, font_size="24sp", bold=True, color=PLAYER_CARD_TEXT_COLOR))
        box.add_widget(Label(text="请输入服务器信息", font_name=FONT_CN, font_size="18sp", color=(0.63, 0.63, 0.63, 1)))
        box.add_widget(ip_field)
        box.add_widget(port_field)
        box.add_widget(name_field)
        box.add_widget(Button(text="确认连接", font_name=FONT_CN, size_hint=(None, None), size=(120, 44), on_press=on_confirm))
        layout.add_widget(box)
        return layout

    def _on_join_room(self) -> None:
        if not self.client or not self.client.config:
            return
        self._start_screen_state = "waiting"
        t = threading.Thread(target=_run_client_thread, args=(self.client,), daemon=True)
        t.start()
        self.root.clear_widgets()
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(400, 120),
                        pos_hint={"center_x": 0.5, "center_y": 0.5})
        box.add_widget(Label(text="六家统", font_name=FONT_CN, font_size="24sp", bold=True, color=PLAYER_CARD_TEXT_COLOR))
        box.add_widget(Label(text="等待游戏开始...", font_name=FONT_CN, font_size="18sp", color=(0.63, 0.63, 0.63, 1)))
        self.root.add_widget(box)

    def _on_logout(self) -> None:
        if self.client:
            self.client.clear_config()
        self._update_start_screen()

    def update(self, info: FieldInfo) -> None:
        _update_queue.put(info)

    def _build_player_info_cards(self, info: FieldInfo, layout: LayoutParams):
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.label import Label
        from kivy.uix.widget import Widget
        from kivy.graphics import Color, RoundedRectangle, Canvas
        from kivy.metrics import sp

        client_id = info.client_id
        widgets = []
        H = layout.height

        def add_info_card(name, cards_num, score, left_or_right_x, top_y, anchor_w):
            w, h = layout.info_section_width, layout.info_section_height
            pad = int(PLAYER_CARD_PADDING * layout.scale)
            display_name = _truncate_name(name, PLAYER_NAME_MAX_LEN)
            initial = name[0] if name else "N"

            if anchor_w == "e":
                x = layout.width - layout.horizontal_info_margin - w
            else:
                x = layout.horizontal_info_section_margin if left_or_right_x == 0 else layout.horizontal_info_margin
            if left_or_right_x == 0 and not anchor_w == "e":
                x = left_or_right_x if anchor_w == "w" else (layout.width - w - layout.horizontal_info_section_margin)
            if anchor_w == "w" and left_or_right_x != 0:
                x = layout.horizontal_info_margin
            if anchor_w == "e":
                x = layout.width - layout.horizontal_info_margin - w

            y = _to_kivy_y(layout, top_y, h)

            container = FloatLayout(size_hint=(None, None), size=(w, h), pos=(x, y))

            with container.canvas.before:
                Color(0.06, 0.13, 0.21, 1)  # gradient start
                RoundedRectangle(pos=container.pos, size=container.size, radius=[PLAYER_CARD_RADIUS])

            avatar = Label(text=initial, font_name=FONT_CN, size_hint=(None, None), size=(layout.avatar_size, layout.avatar_size),
                           pos=(pad, (h - layout.avatar_size) // 2), color=PLAYER_CARD_TEXT_COLOR,
                           bold=True, font_size=sp(max(10, layout.font_size)))
            container.add_widget(avatar)

            name_lbl = Label(text=display_name, font_name=FONT_CN, size_hint=(None, None),
                             size=(w - layout.avatar_size - pad * 2 - 40, 20),
                             pos=(pad + layout.avatar_size + pad, h - pad - 22),
                             color=PLAYER_CARD_TEXT_COLOR, bold=True,
                             font_size=sp(max(9, int(layout.font_size * 0.9))), halign="left")
            name_lbl.bind(size=lambda n, v: setattr(name_lbl, 'text_size', v))
            container.add_widget(name_lbl)

            cards_lbl = Label(text=f"剩{cards_num}张", font_name=FONT_CN, size_hint=(None, None),
                              size=(w - layout.avatar_size - pad * 2 - 40, 18),
                              pos=(pad + layout.avatar_size + pad, h - pad - 40),
                              color=PLAYER_CARD_TEXT_COLOR,
                              font_size=sp(max(8, int(layout.font_size * 0.8))), halign="left")
            cards_lbl.bind(size=lambda n, v: setattr(cards_lbl, 'text_size', v))
            container.add_widget(cards_lbl)

            score_lbl = Label(text=str(score), font_name=FONT_CN, size_hint=(None, None), size=(36, 24),
                              pos=(w - pad - 40, (h - 24) // 2), color=PLAYER_CARD_TEXT_COLOR, bold=True,
                              font_size=sp(max(10, int(layout.font_size * 0.9))), halign="right")
            score_lbl.bind(size=lambda n, v: setattr(score_lbl, 'text_size', v))
            container.add_widget(score_lbl)

            widgets.append(container)
            return container

        # 底部（自己）
        add_info_card(
            info.user_names[client_id], info.users_cards_num[client_id], info.user_scores[client_id],
            layout.horizontal_info_section_margin, layout.bottom_info_section_y, "w"
        )
        # 顶部
        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        add_info_card(
            info.user_names[top_id], info.users_cards_num[top_id], info.user_scores[top_id],
            layout.horizontal_info_section_margin, layout.top_info_section_y, "w"
        )
        # 四侧
        for user_id, is_left, is_upper in [
            ((client_id + PLAYER_OFFSET_SE) % 6, False, False),
            ((client_id + PLAYER_OFFSET_NE) % 6, False, True),
            ((client_id + PLAYER_OFFSET_NW) % 6, True, True),
            ((client_id + PLAYER_OFFSET_SW) % 6, True, False),
        ]:
            y_pos = layout.upper_info_section_y if is_upper else layout.lower_info_section_y
            add_info_card(
                info.user_names[user_id], info.users_cards_num[user_id], info.user_scores[user_id],
                layout.horizontal_info_margin, y_pos, "w" if is_left else "e"
            )

        return widgets

    def _build_player_info_cards_fixed(self, info: FieldInfo, layout: LayoutParams):
        """简化：用 Label 表示每个玩家信息块，位置与 gui_flet 一致。"""
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.label import Label
        from kivy.graphics import Color, RoundedRectangle
        from kivy.metrics import sp

        client_id = info.client_id
        widgets = []
        w, h = layout.info_section_width, layout.info_section_height

        # 顺序：自己(底)、对家(顶)、SE(右下)、NE(右上)、NW(左上)、SW(左下)
        positions = [
            (layout.horizontal_info_section_margin, layout.bottom_info_section_y, "w"),
            (layout.horizontal_info_section_margin, layout.top_info_section_y, "w"),
            (layout.horizontal_info_margin, layout.lower_info_section_y, "e"),  # SE
            (layout.horizontal_info_margin, layout.upper_info_section_y, "e"),  # NE
            (layout.horizontal_info_margin, layout.upper_info_section_y, "w"),  # NW
            (layout.horizontal_info_margin, layout.lower_info_section_y, "w"),  # SW
        ]
        ids_order = [
            client_id,
            (client_id + PLAYER_OFFSET_TOP) % 6,
            (client_id + PLAYER_OFFSET_SE) % 6,
            (client_id + PLAYER_OFFSET_NE) % 6,
            (client_id + PLAYER_OFFSET_NW) % 6,
            (client_id + PLAYER_OFFSET_SW) % 6,
        ]

        for idx, (x_off, top_y, anchor) in enumerate(positions):
            uid = ids_order[idx]
            name = _truncate_name(info.user_names[uid], PLAYER_NAME_MAX_LEN)
            cards_num = info.users_cards_num[uid]
            score = info.user_scores[uid]
            if anchor == "e":
                x = layout.width - layout.horizontal_info_margin - w
            else:
                x = x_off
            y = _to_kivy_y(layout, top_y, h)

            container = FloatLayout(size_hint=(None, None), size=(w, h), pos=(x, y))
            with container.canvas.before:
                Color(0.06, 0.13, 0.21, 1)
                RoundedRectangle(pos=(0, 0), size=(w, h), radius=[PLAYER_CARD_RADIUS])

            text = f"{name}\n剩{cards_num}张  {score}分"
            lbl = Label(text=text, font_name=FONT_CN, size_hint=(1, 1), pos=(0, 0), color=PLAYER_CARD_TEXT_COLOR,
                       font_size=sp(max(9, int(layout.font_size * 0.85))), halign="left", valign="middle")
            lbl.bind(size=lambda n, v: setattr(lbl, 'text_size', v))
            container.add_widget(lbl)
            widgets.append(container)

        return widgets

    def _build_hand_cards(self, info: FieldInfo, layout: LayoutParams):
        from kivy.uix.image import Image
        from kivy.uix.behaviors import ButtonBehavior

        class CardImage(ButtonBehavior, Image):
            pass

        client_id = info.client_id
        widgets = []
        start_x = _centered_row_start(layout, 36)

        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        top_cards_num = info.users_cards_num[top_id]
        for i in range(top_cards_num):
            x = start_x + i * layout.card_spacing
            y = _to_kivy_y(layout, layout.vertical_margin, layout.card_height)
            from kivy.uix.image import Image
            img = Image(source=_background_path(), size_hint=(None, None),
                        size=(layout.card_width, layout.card_height), pos=(x, y))
            widgets.append(img)

        if len(self.selected_card_flag) != len(info.client_cards):
            self.selected_card_flag = [False] * len(info.client_cards)

        for i, card in enumerate(info.client_cards):
            y_off = 20 if self.selected_card_flag[i] else 0
            y = _to_kivy_y(layout, layout.bottom_card_y, layout.card_height) + y_off
            x = start_x + i * layout.card_spacing
            idx = i

            def make_callback(ii):
                def cb(instance):
                    self._on_card_click(ii, info)
                return cb

            img = CardImage(source=_card_image_path(card, layout.card_height), size_hint=(None, None),
                           size=(layout.card_width, layout.card_height), pos=(x, y), allow_stretch=True)
            img.bind(on_press=make_callback(i))
            widgets.append(img)

        return widgets

    def _on_card_click(self, idx: int, info: FieldInfo) -> None:
        if idx < len(self.selected_card_flag):
            self.selected_card_flag[idx] = not self.selected_card_flag[idx]
        self.build_and_update(info)

    def _build_played_cards(self, info: FieldInfo, layout: LayoutParams):
        from kivy.uix.image import Image

        client_id = info.client_id
        widgets = []

        my_played = info.users_played_cards[client_id]
        if my_played:
            sx = _centered_row_start(layout, len(my_played))
            ty = _to_kivy_y(layout, layout.my_played_cards_y, layout.card_height)
            for i, card in enumerate(my_played):
                widgets.append(Image(
                    source=_card_image_path(card, layout.card_height),
                    size_hint=(None, None), size=(layout.card_width, layout.card_height),
                    pos=(sx + i * layout.card_spacing, ty), allow_stretch=True
                ))

        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        top_played = info.users_played_cards[top_id]
        if top_played:
            sx = _centered_row_start(layout, len(top_played))
            ty = _to_kivy_y(layout, layout.top_played_cards_y, layout.card_height)
            for i, card in enumerate(top_played):
                widgets.append(Image(
                    source=_card_image_path(card, layout.card_height),
                    size_hint=(None, None), size=(layout.card_width, layout.card_height),
                    pos=(sx + i * layout.card_spacing, ty), allow_stretch=True
                ))

        def _cy(is_upper):
            return layout.upper_card_y if is_upper else layout.lower_card_y

        for user_id, is_left, is_upper in [
            ((client_id + PLAYER_OFFSET_NW) % 6, True, True),
            ((client_id + PLAYER_OFFSET_NE) % 6, False, True),
            ((client_id + PLAYER_OFFSET_SW) % 6, True, False),
            ((client_id + PLAYER_OFFSET_SE) % 6, False, False),
        ]:
            played = info.users_played_cards[user_id]
            cy = _cy(is_upper)
            cy_kivy = _to_kivy_y(layout, cy, layout.card_height)
            if is_left:
                widgets.append(Image(source=_background_path(), size_hint=(None, None),
                                     size=(layout.card_width, layout.card_height),
                                     pos=(layout.horizontal_card_margin, cy_kivy)))
                for i, card in enumerate(played):
                    widgets.append(Image(
                        source=_card_image_path(card, layout.card_height),
                        size_hint=(None, None), size=(layout.card_width, layout.card_height),
                        pos=(layout.horizontal_card_margin + layout.card_width + layout.played_card_spacing + i * layout.card_spacing, cy_kivy),
                        allow_stretch=True
                    ))
            else:
                back_x = layout.width - layout.horizontal_card_margin - layout.card_width
                widgets.append(Image(source=_background_path(), size_hint=(None, None),
                                    size=(layout.card_width, layout.card_height),
                                    pos=(back_x, cy_kivy)))
                for i, card in enumerate(played):
                    rx = layout.width - (layout.horizontal_card_margin + layout.card_width + layout.played_card_spacing + (len(played) - 1 - i) * layout.card_spacing) - layout.card_width
                    widgets.append(Image(
                        source=_card_image_path(card, layout.card_height),
                        size_hint=(None, None), size=(layout.card_width, layout.card_height),
                        pos=(rx, cy_kivy), allow_stretch=True
                    ))

        return widgets

    def _build_score_panel(self, layout: LayoutParams, info: FieldInfo):
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.label import Label
        from kivy.graphics import Color, RoundedRectangle
        from kivy.metrics import sp

        client_id = info.client_id
        my_team, opp_team = calculate_team_scores(
            info.head_master, client_id, info.users_cards_num, info.user_scores
        )
        now_player = _truncate_name(info.user_names[info.now_player], 6)
        head_master = _truncate_name(
            info.user_names[info.head_master] if info.head_master != -1 else "无", 6
        )
        panel_w = int(200 * layout.scale_x)
        panel_h = int(200 * layout.scale_y)
        gap_y = int(10 * layout.scale_y)
        top = layout.vertical_margin
        score_bottom = top + panel_h
        player_top = layout.upper_info_section_y
        player_bottom = player_top + layout.info_section_height
        if score_bottom > player_top:
            candidate_top = player_bottom + gap_y
            max_top = max(0, layout.height - panel_h - gap_y)
            top = min(candidate_top, max_top)

        x = layout.width - layout.score_anchor_x - panel_w
        y = _to_kivy_y(layout, top, panel_h)
        label_font = max(SCORE_LABEL_FONT, layout.score_label_size + 1)

        container = FloatLayout(size_hint=(None, None), size=(panel_w, panel_h), pos=(x, y))
        with container.canvas.before:
            Color(0.05, 0.09, 0.13, 1)
            RoundedRectangle(pos=(0, 0), size=(panel_w, panel_h), radius=[SCORE_PANEL_RADIUS])

        rows = [
            ("己方得分", str(my_team)),
            ("对方得分", str(opp_team)),
            ("场上分数", str(info.now_score)),
            ("当前出牌", now_player),
            ("头科", head_master),
        ]
        bl = []
        for i, (label, value) in enumerate(rows):
            bl.append(f"{label}  {value}")
        text = "━━ 比分面板 ━━\n" + "\n".join(bl)
        lbl = Label(text=text, font_name=FONT_CN, size_hint=(1, 1), pos=(14, 14), color=(1, 0.84, 0, 1),
                    font_size=sp(label_font), halign="left", valign="middle")
        lbl.bind(size=lambda n, v: setattr(lbl, 'text_size', v))
        container.add_widget(lbl)
        return container

    def _build_buttons(self, info: FieldInfo, layout: LayoutParams):
        from kivy.uix.button import Button
        from kivy.uix.floatlayout import FloatLayout

        widgets = []
        button_defs = [
            ("重置", lambda: self._on_reset(info)),
            ("确定", lambda: self._on_confirm(info)),
            ("取消托管" if self.auto_play_enabled else "托管", lambda: self._on_toggle_auto_play(info)),
            ("跳过", lambda: self._on_skip(info)),
        ]
        last_idx = len(button_defs) - 1
        for i, (label, handler) in enumerate(button_defs):
            bottom = layout.button_bottom_margin + (last_idx - i) * layout.button_spacing
            y = _to_kivy_y(layout, bottom, 44) if bottom + 44 <= layout.height else 0
            x = layout.width - layout.button_right_margin - 100
            btn = Button(text=label, font_name=FONT_CN, size_hint=(None, None), size=(100, 44), pos=(x, y))
            btn.bind(on_press=lambda b, h=handler: h())
            widgets.append(btn)
        return widgets

    def _on_reset(self, info: FieldInfo) -> None:
        for i in range(len(self.selected_card_flag)):
            self.selected_card_flag[i] = False
        self.build_and_update(info)

    def _on_confirm(self, info: FieldInfo) -> None:
        selected = [info.client_cards[i] for i in range(len(info.client_cards)) if self.selected_card_flag[i]]
        last_played = info.users_played_cards[info.last_player] if info.last_player != info.client_id else None
        if playingrules.validate_user_selected_cards(selected, info.client_cards, last_played):
            _get_card_queue().put(selected)
        for i in range(len(self.selected_card_flag)):
            self.selected_card_flag[i] = False
        self.build_and_update(info)

    def _on_skip(self, info: FieldInfo) -> None:
        for i in range(len(self.selected_card_flag)):
            self.selected_card_flag[i] = False
        _get_card_queue().put(["F"])
        self.build_and_update(info)

    def _on_toggle_auto_play(self, info: FieldInfo) -> None:
        self.auto_play_enabled = not self.auto_play_enabled
        self._last_auto_play_state = None
        self.build_and_update(info)

    def _is_my_turn(self, info: FieldInfo) -> bool:
        return (
            info.start_flag
            and info.is_player
            and info.now_player == info.client_id
            and len(info.client_cards) > 0
        )

    def _maybe_auto_play(self, info: FieldInfo) -> None:
        if not self.auto_play_enabled or not self._is_my_turn(info):
            return
        state_fingerprint = (
            info.now_player,
            tuple(card.value for card in info.client_cards),
            info.last_player,
            info.now_score,
        )
        if self._last_auto_play_state == state_fingerprint:
            return
        self._last_auto_play_state = state_fingerprint
        selected = auto_select_cards(info)
        last_played = (
            info.users_played_cards[info.last_player]
            if info.last_player != info.client_id
            else None
        )
        if selected:
            if playingrules.validate_user_selected_cards(selected, info.client_cards, last_played):
                _get_card_queue().put(selected)
                return
        _get_card_queue().put(["F"])

    def _build_full_content(self, info: FieldInfo):
        layout = self._get_layout()
        widgets = []
        widgets.extend(self._build_player_info_cards_fixed(info, layout))
        widgets.extend(self._build_hand_cards(info, layout))
        widgets.extend(self._build_played_cards(info, layout))
        widgets.extend(self._build_buttons(info, layout))
        widgets.append(self._build_score_panel(layout, info))
        return widgets

    def build_and_update(self, info: FieldInfo) -> None:
        if self.root is None:
            return
        self.field_info = info
        try:
            self.root.clear_widgets()
            for w in self._build_full_content(info):
                self.root.add_widget(w)
        except Exception as ex:
            if _gui_kivy_logger:
                _gui_kivy_logger.exception("build_and_update: render error: %s", ex)
            from kivy.uix.label import Label
            from kivy.uix.floatlayout import FloatLayout
            self.root.clear_widgets()
            err = FloatLayout(size_hint=(1, 1))
            err.add_widget(Label(text=f"渲染错误\n{ex}", font_name=FONT_CN, font_size="18sp", color=(1, 0.42, 0.42, 1),
                                 size_hint=(None, None), size=(400, 100), pos_hint={"center_x": 0.5, "center_y": 0.5}))
            self.root.add_widget(err)
        try:
            self._maybe_auto_play(info)
        except Exception as ex:
            if _gui_kivy_logger:
                _gui_kivy_logger.exception("_maybe_auto_play error: %s", ex)


def update_gui(info: FieldInfo) -> None:
    """Public API: push new field info to GUI."""
    if _gui_kivy_logger:
        _gui_kivy_logger.info("update_gui: push FieldInfo to queue, client_id=%s", info.client_id)
    _update_queue.put(info)


def init_gui_kivy(client_logger: Logger, client=None) -> None:
    """启动 Kivy GUI。主线程运行，阻塞直到窗口关闭。"""
    # 禁用 Kivy 自带的参数解析，避免把 client 的 --ip/--port/--user-name 等误当作 Kivy 选项
    os.environ["KIVY_NO_ARGS"] = "1"

    # 注册项目内中文字体，供所有 Label/Button/TextInput 使用
    _font_path = os.path.join(_project_root, "core", "fonts", "ZiTiGuanJiaFangSongTi-2.ttf")
    if os.path.isfile(_font_path):
        from kivy.core.text import LabelBase
        LabelBase.register(name=FONT_CN_NAME, fn_regular=_font_path)
    else:
        client_logger.warning("init_gui_kivy: 字体文件不存在 %s，中文可能显示异常", _font_path)

    global _gui_kivy_logger, _kivy_client
    _gui_kivy_logger = client_logger
    _kivy_client = client
    client_logger.info("init_gui_kivy: Starting Kivy GUI (main thread)")

    import gui as gui_module
    gui_module.register_gui_proxy(KivyGUIProxy(client_logger, client=client))

    from kivy.app import App
    app = LiuJiaTongApp(client_logger, client=client)

    class WrapperApp(App):
        def build(self):
            return app.build()

    WrapperApp().run()
