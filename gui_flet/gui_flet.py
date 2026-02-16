"""Flet-based GUI implementation, mirroring gui.py logic."""

import os
import sys
import asyncio
import queue
import logging
import threading
import time
from logging import Logger

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_client_dir = os.path.join(_project_root, "client")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _client_dir not in sys.path:
    sys.path.insert(0, _client_dir)  # gui、interface 等模块在 client 下

import core.logger as logger_module
import flet as ft
from core.card import Card, Suits
from core.FieldInfo import FieldInfo
from cli.card_utils import int_to_str, calculate_team_scores
from cli.terminal_utils import disable_echo, enable_echo
from core import playingrules
from core.auto_play.strategy import auto_select_cards

def _get_card_queue():
    """从 client.gui 获取 card_queue（FLET 模式选牌时使用）。"""
    from gui import card_queue
    return card_queue

# DEFAULT_WINDOW_HEIGHT (810) = 4 * DEFAULT_CARD_HEIGHT (100) + 3 * VERTICAL_CARD_SPACING (110) + 2 * DEFAULT_VERTICAL_MARGIN (40)

# Default layout constants (same as gui.py)
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 810
DEFAULT_VERTICAL_MARGIN = 40
HORIZONTAL_CARD_MARGIN = 160 # Card's left margin from the edge of the window
VERTICAL_CARD_SPACING = 110
DEFAULT_CARD_WIDTH = 71
DEFAULT_CARD_HEIGHT = 100
DEFAULT_CARD_SPACING = 20
PLAYED_CARD_SPACING = 30

# Player info card styling
PLAYER_CARD_AVATAR_BG = "#2d4a6f"
PLAYER_CARD_TEXT_COLOR = "#e8e8e8"
PLAYER_CARD_BORDER = "#3d5a80"
PLAYER_CARD_PADDING = 8
PLAYER_CARD_AVATAR_SIZE = 36
PLAYER_CARD_RADIUS = 14
PLAYER_NAME_MAX_LEN = 8
# Slightly wider player info cards to better fit three columns (avatar / name+cards / score)
UNIFIED_INFO_SECTION_WIDTH = 155
UNIFIED_INFO_SECTION_HEIGHT = 68
PLAYER_CARD_GRADIENT_START = "#0f2035"
PLAYER_CARD_GRADIENT_END = "#1e3a52"

# Score panel styling
SCORE_PANEL_GRADIENT_START = "#0d1820"
SCORE_PANEL_GRADIENT_END = "#1e3a52"
SCORE_PANEL_RADIUS = 16
# 数字稍大、标签字号也适度放大，保证可读性
SCORE_NUMBER_FONT = 26
SCORE_LABEL_FONT = 13

# Player position offsets
PLAYER_OFFSET_SE, PLAYER_OFFSET_NE, PLAYER_OFFSET_TOP, PLAYER_OFFSET_NW, PLAYER_OFFSET_SW = 1, 2, 3, 4, 5

_images_dir = os.path.join(_project_root, "core", "assets")

_gui_flet_logger = None


def _run_client_thread(client) -> None:
    """在后台线程中运行客户端网络循环。"""
    client.connect(client.config.ip, client.config.port)
    disable_echo()
    client.run()
    enable_echo()
    client.close()

def _card_image_path(card: Card, target_height: int) -> str:
    """Return absolute path to card image for Flet."""
    if card.suit == Suits.empty:
        name = "JOKER-B.png" if card.value == 16 else "JOKER-A.png"
    elif card.value > 10:
        name = card.suit.value + int_to_str(card.value) + ".png"
    else:
        name = card.suit.value + str(card.value) + ".png"
    return os.path.abspath(os.path.join(_images_dir, name))


def _background_path() -> str:
    return os.path.abspath(os.path.join(_images_dir, "Background.png"))


class LayoutParams:
    """Layout parameters computed from window (width, height)."""

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

        # Leave a bit more breathing room at the bottom so that
        # hand cards are not visually flush with the window edge.
        bottom_margin = int(40 * self.scale_y)

        self.my_played_cards_y = height - self.vertical_margin - self.card_height * 2 - self.vertical_card_spacing
        self.top_played_cards_y = self.vertical_margin + self.card_height + self.vertical_card_spacing

        # Action buttons are anchored from the bottom-right corner so they
        # always stay within the visible area even after window resize or
        # a full UI rebuild triggered by hand-card clicks.
        self.button_right_margin = int(30 * self.scale_x)
        self.button_bottom_margin = int(40 * self.scale_y)
        self.button_spacing = int(55 * self.scale_y)
        self.score_anchor_x = width - int(50 * self.scale_x)
        self.font_size = max(12, int(20 * self.scale))
        
        self.avatar_size = int(PLAYER_CARD_AVATAR_SIZE * self.scale)
        self.score_number_size = max(18, int(24 * self.scale))
        self.score_label_size = max(9, int(11 * self.scale))

        # Y offsets between卡牌和 info 卡片中心，用于垂直居中 info section
        self.info_section_offset = self.card_height // 2 - self.info_section_height // 2
        # 顶部/底部 info section 距离左右边缘的水平边距
        self.horizontal_info_section_margin = int(180 * self.scale_x)

        # --- 底部区域：以底边为基线 ---
        # 底部手牌以 bottom_margin 为基线贴底；
        # info section 与手牌底边对齐（而不是以前的“上下居中”）。
        self.bottom_card_y = height - bottom_margin - self.card_height
        self.bottom_info_section_y = height - bottom_margin - self.info_section_height - self.info_section_offset

        # 顶部玩家：仍然以 vertical_margin 为顶部基线，info section 与牌面垂直居中
        self.top_card_y = self.vertical_margin
        self.top_info_section_y = self.top_card_y + self.info_section_offset

        # 左右两侧玩家：在竖直方向等间距分布（top / upper / lower / bottom 四层卡牌中心等间距）
        self.horizontal_info_margin = int(20 * self.scale_x)  # 左右侧 info section 与窗口边缘的水平边距
        self.horizontal_card_margin = self.horizontal_info_margin + self.info_section_width + int(20 * self.scale_x)

        # 计算四层卡牌中心的等间距位置
        top_center = self.top_card_y + self.card_height / 2
        bottom_center = self.bottom_card_y + self.card_height / 2
        band_gap = (bottom_center - top_center) / 3

        upper_center = top_center + band_gap
        lower_center = top_center + 2 * band_gap

        # 侧边玩家（NW/NE/SE/SW）的牌面 Y 坐标
        self.upper_card_y = int(upper_center - self.card_height / 2)
        self.lower_card_y = int(lower_center - self.card_height / 2)

        # 对应 info section 继续与牌面垂直居中
        self.upper_info_section_y = self.upper_card_y + self.info_section_offset
        self.lower_info_section_y = self.lower_card_y + self.info_section_offset

_update_queue = queue.Queue()
# 由 init_gui_flet 设置，供 main() 创建 FletGUI 时获取 client
_flet_client = None


class FletGUI:
    """Main Flet GUI controller. Holds field state and draws all game elements.
    Mirrors gui.GUI structure (tkinter)."""

    def __init__(self, page: ft.Page | None, logger: Logger, client=None):
        self.page = page
        self.logger = logger
        self.client = client or _flet_client  # 由 init_gui_flet 传入
        self.field_info: FieldInfo | None = None  # Updated on each round
        self.selected_card_flag: list[bool] = []  # Per-card selection state
        self.content_stack: ft.Stack | None = None  # Game content container, set when page exists
        # 托管相关状态：是否开启托管、以及上一轮自动出牌时的状态快照，防止重复自动出牌
        self.auto_play_enabled: bool = False
        self._last_auto_play_state: tuple | None = None
        # 开始界面状态："has_config" 有配置，"no_config" 无配置，"waiting" 已连接等待大厅
        self._start_screen_state: str = "no_config"

        if page is not None:
            self._setup_page()

    def _setup_page(self) -> None:
        """Initialize page window and content stack. Called when page is available."""
        page = self.page
        page.title = "LiuJiaTong"
        page.window.width = DEFAULT_WINDOW_WIDTH
        page.window.height = DEFAULT_WINDOW_HEIGHT
        page.window.min_width = 800
        page.window.min_height = 500
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = "#0d1820"

        self.content_stack = ft.Stack(expand=True, fit=ft.StackFit.EXPAND)
        main_container = ft.Container(
            content=self.content_stack,
            expand=True,
            bgcolor="#0d1820",
        )
        page.add(main_container)

        # 开始界面：根据 client.config 显示不同内容
        self._update_start_screen()
        # Rebuild layout when window is resized so all controls stay aligned.
        page.on_resize = self._on_page_resize
        page.update()

    def _update_start_screen(self) -> None:
        """根据当前状态更新开始界面内容。"""
        if self.content_stack is None:
            return
        self.content_stack.controls = [self._build_start_screen_container()]
        self.page.update()

    def _build_start_screen_container(self) -> ft.Container:
        """构建开始界面（有配置时显示 加入房间/退出登录，无配置时显示输入表单）。
        当 client 为 None 时（如从 __main__ 启动、客户端已预先连接），直接显示等待大厅。"""
        if self.client is None:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text("六家统", size=32, weight=ft.FontWeight.BOLD, color=PLAYER_CARD_TEXT_COLOR),
                        ft.Text("等待游戏开始...", size=18, color="#a0a0a0"),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        if self.client.config is not None:
            self._start_screen_state = "has_config"
            content = self._build_start_screen_with_config()
        else:
            self._start_screen_state = "no_config"
            content = self._build_start_screen_input_form()
        return ft.Container(
            content=content,
            alignment=ft.Alignment.CENTER,
            expand=True,
        )

    def _build_start_screen_with_config(self) -> ft.Column:
        """有配置时：显示服务器信息和用户名，以及 加入房间、退出登录 按钮。"""
        cfg = self.client.config
        return ft.Column(
            [
                ft.Text("六家统", size=32, weight=ft.FontWeight.BOLD, color=PLAYER_CARD_TEXT_COLOR),
                ft.Text("欢迎回来", size=20, color="#a0a0a0"),
                ft.Container(height=20),
                ft.Text(f"服务器: {cfg.ip}:{cfg.port}", size=16, color=PLAYER_CARD_TEXT_COLOR),
                ft.Text(f"用户名: {cfg.name}", size=16, color=PLAYER_CARD_TEXT_COLOR),
                ft.Container(height=30),
                ft.Row(
                    [
                        ft.ElevatedButton("加入房间", on_click=lambda e: self._on_join_room(e)),
                        ft.OutlinedButton("退出登录", on_click=lambda e: self._on_logout(e)),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _build_start_screen_input_form(self) -> ft.Column:
        """无配置时：输入框（IP、端口、用户名）+ 确认连接。"""
        ip_field = ft.TextField(label="服务器地址", hint_text="如 192.168.1.100", width=280)
        port_field = ft.TextField(label="端口", hint_text="如 8081", width=280, keyboard_type=ft.KeyboardType.NUMBER)
        name_field = ft.TextField(label="用户名", hint_text="请输入用户名", width=280)

        def on_confirm(e):
            ip = (ip_field.value or "").strip()
            port_str = (port_field.value or "").strip()
            name = (name_field.value or "").strip()
            if not ip or not port_str or not name:
                # 可在此添加错误提示
                return
            try:
                port = int(port_str)
            except ValueError:
                return
            from core.config import Config
            self.client.config = Config(ip, port, name)
            self.client.config.dump()
            self.client.init_logger()
            self._on_join_room(e)

        return ft.Column(
            [
                ft.Text("六家统", size=32, weight=ft.FontWeight.BOLD, color=PLAYER_CARD_TEXT_COLOR),
                ft.Text("请输入服务器信息", size=18, color="#a0a0a0"),
                ft.Container(height=30),
                ip_field,
                port_field,
                name_field,
                ft.Container(height=20),
                ft.ElevatedButton("确认连接", on_click=on_confirm),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )

    def _on_join_room(self, e) -> None:
        """加入房间：启动客户端线程并进入等待大厅。"""
        if not self.client or not self.client.config:
            return
        self._start_screen_state = "waiting"
        t = threading.Thread(target=_run_client_thread, args=(self.client,), daemon=True)
        t.start()
        self.content_stack.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("六家统", size=32, weight=ft.FontWeight.BOLD, color=PLAYER_CARD_TEXT_COLOR),
                        ft.Text("等待游戏开始...", size=18, color="#a0a0a0"),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ]
        self.page.update()

    def _on_logout(self, e) -> None:
        """退出登录：清空配置并显示输入表单。"""
        if self.client:
            self.client.clear_config()
        self._update_start_screen()

    def update(self, info: FieldInfo) -> None:
        """Public method: push new field info to update queue (client thread safe)."""
        if _gui_flet_logger:
            _gui_flet_logger.info("FletGUI.update: received FieldInfo, client_id=%s", info.client_id)
        _update_queue.put(info)

    def _on_page_resize(self, e: ft.ControlEvent) -> None:
        """Handle window resize: recompute layout and redraw using last FieldInfo."""
        if _gui_flet_logger:
            _gui_flet_logger.info(
                "page resized: width=%s, height=%s",
                self.page.width,
                self.page.height,
            )
        if self.field_info is not None:
            # Rebuild current frame with new LayoutParams based on updated window size.
            self.build_and_update(self.field_info)

    def _get_layout(self) -> LayoutParams:
        """
        根据当前页面的实际可见宽高计算布局参数。

        注意：在 Flet 中，用户拖动调整窗口大小时，`page.width/height` 会先反映
        实际尺寸，而 `page.window.width/height` 可能仍然是上一次的目标值，
        这会导致我们总是用“上一帧”的尺寸来重建 UI（表现为拖动第二次才生效）。

        这里优先使用 `page.width/height`，只有在其为 0 时才退回到
        `page.window.width/height`，从而避免一帧延迟的问题。
        """
        page_w = self.page.width or self.page.window.width or 800
        page_h = self.page.height or self.page.window.height or 500
        w = max(page_w, 800)
        h = max(page_h, 500)
        return LayoutParams(w, h)

    def _build_avatar(self, initial: str, layout: LayoutParams) -> ft.Container:
        return ft.Container(
            width=layout.avatar_size,
            height=layout.avatar_size,
            border_radius=layout.avatar_size // 2,
            bgcolor=PLAYER_CARD_AVATAR_BG,
            content=ft.Text(
                initial, size=layout.font_size, weight=ft.FontWeight.BOLD,
                color=PLAYER_CARD_TEXT_COLOR, text_align=ft.TextAlign.CENTER
            ),
        )

    """
    Build user info text column: name + remaining cards (middle column).

    Text size and wrapping are adjusted to fit within the player info
    card width so that we avoid ugly truncation or multi-line wrapping
    even on smaller windows.
    """
    def _build_user_info_text_column(
        self, name: str, cards_num: int, layout: LayoutParams
    ) -> ft.Column:
        # 中间列字号稍小一些，保证在三列布局下仍然简洁清晰。
        title_sz = max(11, int(layout.font_size * 0.9))
        sub_sz = max(9, int(layout.font_size * 0.8))

        return ft.Column(
            [
                ft.Text(
                    name,
                    size=title_sz,
                    weight=ft.FontWeight.BOLD,
                    color=PLAYER_CARD_TEXT_COLOR,
                    no_wrap=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    f"剩{cards_num}张",
                    size=sub_sz,
                    color=PLAYER_CARD_TEXT_COLOR,
                    no_wrap=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=2,
            tight=True,
        )

    """
    Build player info card: circular avatar + gradient panel with name, cards, score. Unified size for all 6.
    """
    def _build_single_player_info_card(
        self,
        name: str,
        cards_num: int,
        score: int,
        x: int, # x coordinate of the upper left point of the card
        y: int, # y coordinate of the upper left point of the card
        layout: LayoutParams,
        anchor: str = "w",
    ) -> ft.Container:
        if _gui_flet_logger:
            _gui_flet_logger.info("_build_single_player_info_card: name=%s, cards_num=%s, score=%s", name, cards_num, score)

        w, h = layout.info_section_width, layout.info_section_height
        pad = int(PLAYER_CARD_PADDING * layout.scale)
        display_name = _truncate_name(name, PLAYER_NAME_MAX_LEN)
        initial = name[0] if name else "N"

        # Stack positioning: left/right are distances from stack edges.
        # For "e" (east), right = distance from parent's right to control's right = horizontal_info_margin.
        left = x if anchor == "w" else None
        right = x if anchor == "e" else None
        top = y

        # 左：头像；中：玩家名 + 剩余手牌；右：得分，形成三列布局。
        score_title_sz = max(9, int(layout.font_size * 0.75))
        score_value_sz = max(11, int(layout.font_size * 0.9))

        content_row = ft.Row(
            [
                # Avatar (left column)
                self._build_avatar(initial, layout),

                # Name + remaining cards (middle column)
                ft.Container(
                    content=self._build_user_info_text_column(display_name, cards_num, layout),
                    expand=True,
                ),

                # Score (right column)
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "得分",
                                size=score_title_sz,
                                color="#b0b0b0",
                                weight=ft.FontWeight.NORMAL,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            ft.Text(
                                str(score),
                                size=score_value_sz,
                                color=PLAYER_CARD_TEXT_COLOR,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                        ],
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
            spacing=pad,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=content_row,
            width=w,
            height=h,
            padding=pad,
            border_radius=PLAYER_CARD_RADIUS,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=[PLAYER_CARD_GRADIENT_START, PLAYER_CARD_GRADIENT_END],
            ),
            border=ft.border.all(1, PLAYER_CARD_BORDER),
            left=left,
            right=right,
            top=top,
        )

    def _build_player_info_cards(self, info: FieldInfo, layout: LayoutParams) -> list[ft.Control]:
        """Build all 6 player info cards (self, top, and 4 sides)."""
        client_id = info.client_id
        controls: list[ft.Control] = []

        # My info card (bottom)
        controls.append(
            self._build_single_player_info_card(
                info.user_names[client_id],
                info.users_cards_num[client_id],
                info.user_scores[client_id],
                layout.horizontal_info_section_margin,
                layout.bottom_info_section_y,
                layout,
                "w",
            )
        )

        # Top player info card
        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        controls.append(
            self._build_single_player_info_card(
                info.user_names[top_id],
                info.users_cards_num[top_id],
                info.user_scores[top_id],
                layout.horizontal_info_section_margin,
                layout.top_info_section_y,
                layout,
                "w",
            )
        )

        # Left / right players (NW, NE, SW, SE)
        for user_id, is_left, is_upper in [
            ((client_id + PLAYER_OFFSET_SE) % 6, False, False),
            ((client_id + PLAYER_OFFSET_NE) % 6, False, True),
            ((client_id + PLAYER_OFFSET_NW) % 6, True, True),
            ((client_id + PLAYER_OFFSET_SW) % 6, True, False),
        ]:
            controls.append(
                self._build_single_player_info_card(
                    info.user_names[user_id],
                    info.users_cards_num[user_id],
                    info.user_scores[user_id],
                    layout.horizontal_info_margin,
                    layout.upper_info_section_y if is_upper else layout.lower_info_section_y,
                    layout,
                    "w" if is_left else "e",
                )
            )

        return controls

    def _build_hand_cards(self, info: FieldInfo, layout: LayoutParams) -> list[ft.Control]:
        """Build top player's hand backs and my own hand cards."""
        client_id = info.client_id
        controls: list[ft.Control] = []

        # Top player card backs
        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        start_x = _centered_row_start(layout, 36)
        top_cards_num = info.users_cards_num[top_id]
        for i in range(top_cards_num):
            controls.append(
                ft.Container(
                    content=ft.Image(src=_background_path(), fit=ft.BoxFit.CONTAIN, height=layout.card_height),
                    left=start_x + i * layout.card_spacing,
                    top=layout.vertical_margin,
                )
            )

        # My hand cards
        if len(self.selected_card_flag) != len(info.client_cards):
            self.selected_card_flag = [False] * len(info.client_cards)

        for i, card in enumerate(info.client_cards):
            y_off = -20 if self.selected_card_flag[i] else 0
            idx = i
            # Absolute positioning must be on the Stack's direct child, so we put
            # left/top on GestureDetector instead of wrapping Container.
            controls.append(
                ft.GestureDetector(
                    content=ft.Image(
                        src=_card_image_path(card, layout.card_height),
                        fit=ft.BoxFit.CONTAIN,
                        height=layout.card_height,
                    ),
                    left=start_x + i * layout.card_spacing,
                    top=layout.bottom_card_y + y_off,
                    on_tap=lambda e, i=idx: self._on_card_click(e, i, info),
                )
            )

        return controls

    def _build_played_cards(self, info: FieldInfo, layout: LayoutParams) -> list[ft.Control]:
        """Build all played cards on the table for every player."""
        client_id = info.client_id
        controls: list[ft.Control] = []

        # My played cards (bottom centre)
        my_played = info.users_played_cards[client_id]
        if my_played:
            sx = _centered_row_start(layout, len(my_played))
            for i, card in enumerate(my_played):
                controls.append(
                    ft.Container(
                        content=ft.Image(
                            src=_card_image_path(card, layout.card_height),
                            fit=ft.BoxFit.CONTAIN,
                            height=layout.card_height,
                        ),
                        left=sx + i * layout.card_spacing,
                        top=layout.my_played_cards_y,
                    )
                )

        # Top player's played cards
        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        top_played = info.users_played_cards[top_id]
        if top_played:
            sx = _centered_row_start(layout, len(top_played))
            for i, card in enumerate(top_played):
                controls.append(
                    ft.Container(
                        content=ft.Image(
                            src=_card_image_path(card, layout.card_height),
                            fit=ft.BoxFit.CONTAIN,
                            height=layout.card_height,
                        ),
                        left=sx + i * layout.card_spacing,
                        top=layout.top_played_cards_y,
                    )
                )

        # Side players' backs and played cards
        def _cy(is_upper: bool) -> int:
            return layout.upper_card_y if is_upper else layout.lower_card_y

        for user_id, is_left, is_upper in [
            ((client_id + PLAYER_OFFSET_NW) % 6, True, True),
            ((client_id + PLAYER_OFFSET_NE) % 6, False, True),
            ((client_id + PLAYER_OFFSET_SW) % 6, True, False),
            ((client_id + PLAYER_OFFSET_SE) % 6, False, False),
        ]:
            played = info.users_played_cards[user_id]
            cy = _cy(is_upper)
            if is_left:
                controls.append(
                    ft.Container(
                        content=ft.Image(
                            src=_background_path(),
                            fit=ft.BoxFit.CONTAIN,
                            height=layout.card_height,
                        ),
                        left=layout.horizontal_card_margin,
                        top=cy,
                    )
                )
                for i, card in enumerate(played):
                    controls.append(
                        ft.Container(
                            content=ft.Image(
                                src=_card_image_path(card, layout.card_height),
                                fit=ft.BoxFit.CONTAIN,
                                height=layout.card_height,
                            ),
                            left=layout.horizontal_card_margin
                            + layout.card_width
                            + layout.played_card_spacing
                            + i * layout.card_spacing,
                            top=cy,
                        )
                    )
            else:
                controls.append(
                    ft.Container(
                        content=ft.Image(
                            src=_background_path(),
                            fit=ft.BoxFit.CONTAIN,
                            height=layout.card_height,
                        ),
                        right=layout.horizontal_card_margin,
                        top=cy,
                    )
                )
                for i, card in enumerate(played):
                    controls.append(
                        ft.Container(
                            content=ft.Image(
                                src=_card_image_path(card, layout.card_height),
                                fit=ft.BoxFit.CONTAIN,
                                height=layout.card_height,
                            ),
                            right=layout.horizontal_card_margin
                            + layout.card_width
                            + layout.played_card_spacing
                            + (len(played) - 1 - i) * layout.card_spacing,
                            top=cy,
                        )
                    )

        return controls

    def _build_score_panel(self, layout: LayoutParams, info: FieldInfo) -> ft.Container:
        if _gui_flet_logger:
            _gui_flet_logger.info("_build_score_panel: client_id=%s, now_score=%s", info.client_id, info.now_score)
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
        pad = int(14 * layout.scale)
        rows = [
            ("己方得分", str(my_team)),
            ("对方得分", str(opp_team)),
            ("场上分数", str(info.now_score)),
            ("当前出牌", now_player),
            ("头科", head_master),
        ]

        # --- Responsive positioning ---
        # 默认放在右上角，但当窗口高度较小、计分板高度较大时，可能会覆盖右上角玩家信息卡。
        # 这里通过简单的碰撞检测，让计分板在需要时“躲开”右上的玩家：
        #   1. 正常情况：top = vertical_margin（靠近顶部）
        #   2. 如果会与右上方玩家的 info 卡垂直重叠，则移动到该 info 卡下方留出一点间距
        gap_y = int(10 * layout.scale_y)
        top = layout.vertical_margin

        score_bottom = top + panel_h
        player_top = layout.upper_info_section_y
        player_bottom = player_top + layout.info_section_height

        # 如果默认位置会与右上玩家 info 卡垂直重叠，则把计分板移到玩家下方
        if score_bottom > player_top:
            candidate_top = player_bottom + gap_y
            # 避免计分板超出窗口底部
            max_top = max(0, layout.height - panel_h - gap_y)
            top = min(candidate_top, max_top)
        # 放大标签字号，使“己方得分 / 对方得分”等文字更清晰
        label_font = max(SCORE_LABEL_FONT, layout.score_label_size + 1)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "━━ 比分面板 ━━",
                        size=label_font,
                        weight=ft.FontWeight.BOLD,
                        color=PLAYER_CARD_TEXT_COLOR,
                    ),
                    *[
                        ft.Row(
                            [
                                ft.Text(label, size=label_font, color="#a0a0a0"),
                                ft.Text(
                                    value,
                                    size=SCORE_NUMBER_FONT if i < 3 else label_font,
                                    weight=ft.FontWeight.BOLD if i < 3 else None,
                                    color="#ffd700",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        )
                        for i, (label, value) in enumerate(rows)
                    ],
                ],
                spacing=6,
                expand=True,
            ),
            width=panel_w,
            height=panel_h,
            padding=pad,
            border_radius=SCORE_PANEL_RADIUS,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=[SCORE_PANEL_GRADIENT_START, SCORE_PANEL_GRADIENT_END],
            ),
            right=layout.width - layout.score_anchor_x,
            top=top,
        )

    def _build_full_content(self, info: FieldInfo) -> list:
        if _gui_flet_logger:
            _gui_flet_logger.info("_build_full_content: client_id=%s, client_cards=%d", info.client_id, len(info.client_cards))
        layout = self._get_layout()
        client_id = info.client_id
        controls = []

        # 1. 玩家信息卡片（6 个玩家）
        controls.extend(self._build_player_info_cards(info, layout))

        # 2. 顶部玩家手牌背面 + 我方手牌
        controls.extend(self._build_hand_cards(info, layout))

        # 3. 场上已出牌
        controls.extend(self._build_played_cards(info, layout))

        # Build action buttons (reset / confirm / skip).
        # They are positioned from the bottom-right so that even when the
        # window height is small or the UI is rebuilt after hand-card
        # clicks, the lowest button ("跳过") will not be pushed out of view.
        button_defs = [
            ("重置", lambda e: self._on_reset(e, info)),
            ("确定", lambda e: self._on_confirm(e, info)),
            # 托管 / 取消托管 按钮
            (
                "取消托管" if self.auto_play_enabled else "托管",
                lambda e: self._on_toggle_auto_play(e, info),
            ),
            ("跳过", lambda e: self._on_skip(e, info)),
        ]
        last_idx = len(button_defs) - 1
        for i, (label, handler) in enumerate(button_defs):
            # Place "跳过" closest to the bottom edge.
            bottom = layout.button_bottom_margin + (last_idx - i) * layout.button_spacing
            controls.append(
                ft.Container(
                    content=ft.ElevatedButton(content=label, on_click=handler),
                    right=layout.button_right_margin,
                    bottom=bottom,
                )
            )

        # Build score panel
        controls.append(self._build_score_panel(layout, info))

        if _gui_flet_logger:
            _gui_flet_logger.info("_build_full_content: done, total controls=%d", len(controls))
        return controls

    def _on_card_click(self, e, idx: int, info: FieldInfo) -> None:
        if _gui_flet_logger:
            _gui_flet_logger.info("_on_card_click: idx=%s, card=%s", idx, info.client_cards[idx] if idx < len(info.client_cards) else "?")
        self.selected_card_flag[idx] = not self.selected_card_flag[idx]
        self.build_and_update(info)

    def _on_reset(self, e, info: FieldInfo) -> None:
        if _gui_flet_logger:
            _gui_flet_logger.info("_on_reset: clear all selected cards")
        for i in range(len(self.selected_card_flag)):
            self.selected_card_flag[i] = False
        self.build_and_update(info)

    def _on_confirm(self, e, info: FieldInfo) -> None:
        selected = [info.client_cards[i] for i in range(len(info.client_cards)) if self.selected_card_flag[i]]
        if _gui_flet_logger:
            _gui_flet_logger.info("_on_confirm: selected=%s", [str(c) for c in selected])
        last_played = info.users_played_cards[info.last_player] if info.last_player != info.client_id else None
        if playingrules.validate_user_selected_cards(selected, info.client_cards, last_played):
            _get_card_queue().put(selected)
            if _gui_flet_logger:
                _gui_flet_logger.info("_on_confirm: validated, sent to card_queue")
        else:
            if _gui_flet_logger:
                _gui_flet_logger.info("_on_confirm: validation failed, invalid card selection")
        for i in range(len(self.selected_card_flag)):
            self.selected_card_flag[i] = False
        self.build_and_update(info)

    def _on_skip(self, e, info: FieldInfo) -> None:
        if _gui_flet_logger:
            _gui_flet_logger.info("_on_skip: pass turn")
        for i in range(len(self.selected_card_flag)):
            self.selected_card_flag[i] = False
        _get_card_queue().put(["F"])
        self.build_and_update(info)

    def _on_toggle_auto_play(self, e, info: FieldInfo) -> None:
        """切换托管状态，并刷新按钮文本。"""
        self.auto_play_enabled = not self.auto_play_enabled
        # 切换状态后清空上一轮自动出牌快照，防止新一轮无法触发
        self._last_auto_play_state = None
        if _gui_flet_logger:
            _gui_flet_logger.info(
                "_on_toggle_auto_play: auto_play_enabled=%s", self.auto_play_enabled
            )
        self.build_and_update(info)

    def _is_my_turn(self, info: FieldInfo) -> bool:
        """是否轮到本客户端玩家出牌。"""
        return (
            info.start_flag
            and info.is_player
            and info.now_player == info.client_id
            and len(info.client_cards) > 0
        )

    def _maybe_auto_play(self, info: FieldInfo) -> None:
        """在托管开启且轮到本玩家出牌时，自动选择并出牌/跳过。"""
        if not self.auto_play_enabled or not self._is_my_turn(info):
            return

        # 使用 (当前出牌人, 手牌值序列, 上家出牌人, 场上分) 作为一次出牌状态的“指纹”，防止重复自动出牌
        state_fingerprint = (
            info.now_player,
            tuple(card.value for card in info.client_cards),
            info.last_player,
            info.now_score,
        )
        if self._last_auto_play_state == state_fingerprint:
            return

        self._last_auto_play_state = state_fingerprint

        # 生成自动要出的牌
        selected = auto_select_cards(info)
        last_played = (
            info.users_played_cards[info.last_player]
            if info.last_player != info.client_id
            else None
        )

        if selected:
            if _gui_flet_logger:
                _gui_flet_logger.info(
                    "_maybe_auto_play: auto play cards=%s",
                    [str(c) for c in selected],
                )
            # 再次用 playingrules 校验一遍，保证和手动出牌逻辑一致
            if playingrules.validate_user_selected_cards(
                selected, info.client_cards, last_played
            ):
                _get_card_queue().put(selected)
                return

        # 没有任何合法且可出的牌型，或都无法大过场上牌：自动跳过
        if _gui_flet_logger:
            _gui_flet_logger.info("_maybe_auto_play: no valid move, auto skip")
        _get_card_queue().put(["F"])

    def build_and_update(self, info: FieldInfo) -> None:
        if self.content_stack is None:
            return
        if _gui_flet_logger:
            _gui_flet_logger.info("build_and_update: start, client_id=%s", info.client_id)
        self.field_info = info
        setattr(self.page, "_last_info", info)
        try:
            self.content_stack.controls = self._build_full_content(info)
            if _gui_flet_logger:
                _gui_flet_logger.info("build_and_update: success, calling page.update()")
        except Exception as ex:
            if _gui_flet_logger:
                _gui_flet_logger.exception("build_and_update: render error: %s", ex)
            self.content_stack.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("渲染错误", size=24, color="#ff6b6b"),
                            ft.Text(str(ex), size=14, color="#a0a0a0"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        expand=True,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                )
            ]
        # 构建完界面后检查是否需要进行自动托管出牌
        try:
            self._maybe_auto_play(info)
        except Exception as ex:
            if _gui_flet_logger:
                _gui_flet_logger.exception("_maybe_auto_play error: %s", ex)
        self.page.update()

    async def _poll_updates(self) -> None:
        if _gui_flet_logger:
            _gui_flet_logger.info("_poll_updates: started")
        while True:
            await asyncio.sleep(0.1)
            try:
                info = _update_queue.get_nowait()
                if _gui_flet_logger:
                    _gui_flet_logger.info("_poll_updates: got FieldInfo, client_id=%s", info.client_id)
                self.build_and_update(info)
            except queue.Empty:
                pass


def update_gui(info: FieldInfo) -> None:
    """Public API: push new field info to GUI."""
    if _gui_flet_logger:
        _gui_flet_logger.info("update_gui: push FieldInfo to queue, client_id=%s", info.client_id)
    _update_queue.put(info)


def _truncate_name(name: str, max_len: int) -> str:
    if not name:
        return "?"
    if len(name) <= max_len:
        return name
    return name[: max_len - 1] + "…"


def _calc_text_line_positions(h: int, pad: int, font_sz: int, line_count: int = 3) -> tuple:
    sub_font = max(8, font_sz - 1)
    base_line_height = max(14, int(max(font_sz, sub_font) * 1.4))
    available = max(0, h - 2 * pad)
    line_height = max(10, min(available // line_count, base_line_height))
    total_height = line_height * line_count
    start_y = pad + max(0, (available - total_height) // 2)
    return line_height, tuple(start_y + i * line_height for i in range(line_count))


def _centered_row_start(layout: LayoutParams, card_count: int) -> int:
    total_width = layout.card_width + layout.card_spacing * max(card_count, 1)
    return (layout.width - total_width) // 2


async def main(page: ft.Page):
    """Flet main entry point (async)."""
    if _gui_flet_logger:
        _gui_flet_logger.info("main: Flet page started")

    gui = FletGUI(page, _gui_flet_logger or logging.getLogger("gui_flet"), client=_flet_client)
    # IMPORTANT: use the same `gui` module as __main__ (`from gui import ...`)
    # to avoid creating two separate module instances (`gui` vs `client.gui`)
    # which would desynchronise GUI state and pending updates.
    import gui as gui_module
    gui_module.register_gui_page(gui)

    page.run_task(gui._poll_updates)
    gui_module.register_gui_fully_ready()


def init_gui_flet(client_logger: Logger, client=None) -> None:
    """Start Flet GUI. Must run in main thread (Flet uses signal.signal). Blocks until window closes.
    client: Client 实例，用于开始界面（加载/清空配置、连接）。若为 None 则不显示开始界面。
    """
    global _gui_flet_logger, _flet_client
    _gui_flet_logger = client_logger
    _flet_client = client
    client_logger.info("init_gui_flet: Starting Flet GUI (main thread)")

    # Same reason as above: keep a single shared `gui` module.
    import gui as gui_module
    gui_module.register_gui_proxy(FletGUI(None, client_logger, client=client))

    ft.app(target=main, assets_dir=os.path.join(_project_root, "core", "assets"))
