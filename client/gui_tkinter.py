"""Tkinter-based GUI implementation extracted from gui.py."""

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
from logging import Logger

from card import Card, Suits
from FieldInfo import FieldInfo
import utils
import playingrules

# This module-level card_queue will be injected by gui.run_tkinter_gui.
card_queue = None

# Default layout constants (base values for dynamic scaling)
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 810
DEFAULT_VERTICAL_MARGIN = 40
HORIZONTAL_CARD_MARGIN = 145  # Must be > info_margin + UNIFIED_PLAYER_CARD_WIDTH
VERTICAL_CARD_SPACING = 26
DEFAULT_CARD_WIDTH = 71
DEFAULT_CARD_HEIGHT = 100
DEFAULT_CARD_SPACING = 20
PLAYED_CARD_SPACING = 30
DEFAULT_LINE_SPACING = 30

# Player info card styling (3D effect: shadow, base, highlight)
PLAYER_CARD_SHADOW = "#0a1520"       # External shadow / outer glow
PLAYER_CARD_BASE = "#1a2d45"         # Main base color
PLAYER_CARD_HIGHLIGHT = "#253d58"    # Top highlight for 3D
PLAYER_CARD_OVERLAY = "#1e3548"      # Semi-transparent overlay simulation
PLAYER_CARD_AVATAR_BG = "#2d4a6f"
PLAYER_CARD_TEXT_COLOR = "#e8e8e8"
PLAYER_CARD_BORDER = "#3d5a80"
PLAYER_CARD_PADDING = 8
PLAYER_CARD_AVATAR_SIZE = 36
PLAYER_CARD_RADIUS = 14  # Rounded corner radius for all player cards
PLAYER_NAME_MAX_LEN = 8  # Max chars before truncation for normal panel
PLAYER_NAME_MAX_LEN_COMPACT = 5
# Unified size for all 6 player cards (fits both vertical and horizontal layout)
UNIFIED_PLAYER_CARD_WIDTH = 110
UNIFIED_PLAYER_CARD_HEIGHT = 68
# Gradient colors for player card (matches score panel style)
PLAYER_CARD_GRADIENT_START = "#0f2035"
PLAYER_CARD_GRADIENT_END = "#1e3a52"

# Score panel styling (gradient, rounded like player cards)
SCORE_PANEL_GRADIENT_START = "#0d1820"
SCORE_PANEL_GRADIENT_END = "#1e3a52"
SCORE_PANEL_BORDER = "#2d4a6f"
SCORE_PANEL_RADIUS = 16  # Rounded corners like player cards
SCORE_NUMBER_FONT = ("Consolas", 24)  # LCD-style
SCORE_LABEL_FONT = ("Microsoft YaHei", 11)

# Player position offsets from client's perspective (clockwise: 1=SE, 2=NE, 3=Top, 4=NW, 5=SW)
PLAYER_OFFSET_TOP, PLAYER_OFFSET_NE, PLAYER_OFFSET_NW, PLAYER_OFFSET_SW, PLAYER_OFFSET_SE = 3, 2, 4, 5, 1

# Debounce delay (ms) before redraw after last Configure. Fires when user releases mouse (resize stops).
RESIZE_DEBOUNCE_MS = 100


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert #RRGGBB to (r, g, b)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


def _create_gradient_rounded_image(
    width: int, height: int, color_start: str, color_end: str, radius: int = 10
) -> ImageTk.PhotoImage:
    """Create gradient image with rounded corners for panel background."""
    if width < 2 or height < 2:
        return ImageTk.PhotoImage(Image.new("RGB", (max(1, width), max(1, height)), _hex_to_rgb(color_start)))
    c1, c2 = _hex_to_rgb(color_start), _hex_to_rgb(color_end)
    radius = min(radius, width // 2, height // 2)
    gradient = Image.new("RGB", (width, height))
    pix = gradient.load()
    for y in range(height):
        t = y / (height - 1) if height > 1 else 0
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        for x in range(width):
            pix[x, y] = (r, g, b)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    bg = Image.new("RGB", (width, height), c1)
    bg.paste(gradient, (0, 0), mask)
    return ImageTk.PhotoImage(bg)


class ImageCache:
    """Cache for card and background images to avoid repeated disk I/O."""

    def __init__(self):
        self._card_cache = {}  # key: (suit, value, target_height)
        self._background_cache = None  # (target_height, PhotoImage)
        self._gradient_cache = {}  # key: (w, h, start, end) -> PhotoImage

    def _card_cache_key(self, card: Card) -> tuple:
        """Return (suit, value) tuple for cache key. Jokers use ('joker', 15|16)."""
        if card.suit == Suits.empty:
            return ("joker", card.value)
        return (card.suit.value, card.value)

    def get_card_image(self, card: Card, target_height: int) -> ImageTk.PhotoImage:
        """Return cached or freshly loaded card image, scaled to target_height."""
        key = (*self._card_cache_key(card), target_height)
        if key not in self._card_cache:
            self._card_cache[key] = self._load_card_image(card, target_height)
        return self._card_cache[key]

    def _load_card_image(self, card: Card, target_height: int) -> ImageTk.PhotoImage:
        """Load card from disk and resize. J/Q/K/A use int_to_str for filename."""
        if card.suit == Suits.empty:
            path = "client/images/JOKER-B.png" if card.value == 16 else "client/images/JOKER-A.png"
        elif card.value > 10:
            path = "client/images/" + card.suit.value + utils.int_to_str(card.value) + ".png"
        else:
            path = "client/images/" + card.suit.value + str(card.value) + ".png"
        image = Image.open(path)
        w, h = image.size
        scale = target_height / h
        image = image.resize((int(w * scale), target_height))
        return ImageTk.PhotoImage(image)

    def get_background_image(self, target_height: int) -> ImageTk.PhotoImage:
        """Return cached or freshly loaded card-back image."""
        if self._background_cache is None or self._background_cache[0] != target_height:
            image = Image.open("client/images/Background.png")
            w, h = image.size
            image = image.resize((int(w * target_height / h), target_height))
            self._background_cache = (target_height, ImageTk.PhotoImage(image))
        return self._background_cache[1]

    def get_gradient_image(
        self, width: int, height: int, color_start: str, color_end: str, radius: int = 10
    ) -> ImageTk.PhotoImage:
        """Return cached or freshly created gradient rounded-rect image."""
        key = (width, height, color_start, color_end, radius)
        if key not in self._gradient_cache:
            self._gradient_cache[key] = _create_gradient_rounded_image(
                width, height, color_start, color_end, radius=radius
            )
        return self._gradient_cache[key]


class LayoutParams:
    """Layout parameters computed from window (width, height). All coordinates scale with window size."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.scale_x = width / DEFAULT_WINDOW_WIDTH
        self.scale_y = height / DEFAULT_WINDOW_HEIGHT
        self.scale = min(self.scale_x, self.scale_y, 1.5)  # Cap to avoid oversized UI

        # Margins and card dimensions
        self.vertical_margin = int(DEFAULT_VERTICAL_MARGIN * self.scale_y)
        self.card_width = int(DEFAULT_CARD_WIDTH * self.scale)
        self.card_height = int(DEFAULT_CARD_HEIGHT * self.scale)
        self.card_spacing = int(DEFAULT_CARD_SPACING * self.scale)
        self.played_card_spacing = int(PLAYED_CARD_SPACING * self.scale)
        self.vertical_card_spacing = int(VERTICAL_CARD_SPACING * self.scale)
        self.horizontal_card_margin = int(HORIZONTAL_CARD_MARGIN * self.scale_x)

        # Y-coordinates for card rows (top, upper, lower, my hand, my played, top played)
        self.upper_card_y = self.vertical_margin + self.card_height * 2 + self.vertical_card_spacing * 2
        self.lower_card_y = self.upper_card_y + self.card_height + self.vertical_card_spacing
        self.my_cards_y = height - int(140 * self.scale_y)
        self.my_played_cards_y = height - self.vertical_margin - self.card_height * 2 - self.vertical_card_spacing
        self.top_played_cards_y = self.vertical_margin + self.card_height + self.vertical_card_spacing

        # Anchors for info/buttons (right side of window)
        self.info_margin = int(20 * self.scale_x)
        self.button_anchor_x = width - int(30 * self.scale_x)
        self.button_y_base = height - int(150 * self.scale_y)
        self.button_spacing = int(50 * self.scale_y)
        self.score_anchor_x = width - int(50 * self.scale_x)
        self.font_size = max(12, int(20 * self.scale))
        # Unified size for all 6 player cards
        self.player_card_width = int(UNIFIED_PLAYER_CARD_WIDTH * self.scale)
        self.player_card_height = int(UNIFIED_PLAYER_CARD_HEIGHT * self.scale)
        self.avatar_size = int(PLAYER_CARD_AVATAR_SIZE * self.scale)
        self.score_number_size = max(18, int(24 * self.scale))
        self.score_label_size = max(9, int(11 * self.scale))


class GUI:
    """Main GUI controller. Holds field state, image cache, and draws all game elements."""

    def __init__(self, root: tk.Tk, logger: Logger):
        self.root = root
        self.field_info = None  # FieldInfo from game logic, updated on each round
        self.selected_card_flag = [False] * 36  # Per-card selection state
        self.my_card_labels = []  # Labels for my hand (clickable)
        self.logger = logger
        self.button_drawn = False
        self.buttons = []  # Reset/Confirm/Skip buttons (persist across redraws)
        self.image_cache = ImageCache()
        self._resize_after_id = None  # Pending after() id for resize debounce
        self._redraw_in_progress = False
        self._pending_redraw = False
        # Updaters for incremental reposition: list of callables (layout) -> None
        self._widget_updaters = []

        root.title("LiuJiaTong")
        root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        root.minsize(800, 500)
        root.bind("<<UpdateEvent>>", self._handle_update_event)
        root.bind("<<ResizeEvent>>", self._handle_resize_event)
        root.bind("<Configure>", self._on_resize)
        root.bind("<ButtonRelease-1>", self._on_mouse_release)
        root.bind("<ButtonRelease-2>", self._on_mouse_release)

    def _get_layout(self) -> LayoutParams:
        """Compute layout from current window size. Ensures min 800x500."""
        self.root.update_idletasks()
        return LayoutParams(max(self.root.winfo_width(), 800), max(self.root.winfo_height(), 500))

    def _on_resize(self, event):
        """Schedule redraw after resize ends. Debounced: redraw only when Configure events stop (user released)."""
        if event.widget != self.root or self.field_info is None:
            return
        w, h = event.width, event.height
        if w < 100 or h < 100:
            return
        if self._resize_after_id is not None:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(RESIZE_DEBOUNCE_MS, self._on_resize_done)

    def _on_mouse_release(self, event):
        """Mouse release triggers reposition. Cancel debounce and update now."""
        if event.widget != self.root or self.field_info is None:
            return
        if self._resize_after_id is not None:
            self.root.after_cancel(self._resize_after_id)
            self._resize_after_id = None
        self.root.event_generate("<<ResizeEvent>>")

    def _on_resize_done(self):
        """Called when resize debounce timer fires. Triggers incremental reposition."""
        self._resize_after_id = None
        self.root.event_generate("<<ResizeEvent>>")

    def _handle_resize_event(self, event):
        """Incremental update: reposition existing widgets only. No destroy/create."""
        if self.field_info is None:
            return
        if not self._widget_updaters:
            # No widgets yet, do full redraw
            self.root.event_generate("<<UpdateEvent>>")
            return
        layout = self._get_layout()
        for updater in self._widget_updaters:
            updater(layout)

    def update(self, info: FieldInfo):
        """Public method: set new field info and trigger redraw."""
        self.logger.info("update gui")
        self.field_info = info
        self.root.event_generate("<<UpdateEvent>>")

    def _handle_update_event(self, event):
        """Event handler for GUI update. Uses chunked redraw to avoid blocking - user can resize during redraw."""
        self.logger.info("handle_update_event")

        if self._redraw_in_progress:
            self._pending_redraw = True
            return

        self._redraw_in_progress = True
        self._pending_redraw = False
        self.root.after(0, self._redraw_step_destroy)

    def _redraw_step_destroy(self):
        """Step 1: Destroy all widgets and clear updaters. Yield to event loop before next step."""
        if not self._redraw_in_progress:
            return
        for widget in self.root.winfo_children():
            widget.destroy()
        self.buttons = []
        self.button_drawn = False
        self._widget_updaters = []
        self.root.after(0, self._redraw_step_cards)

    def _redraw_step_cards(self):
        """Step 2: Draw cards. Yield to event loop before next step."""
        if not self._redraw_in_progress:
            return
        self._draw_user_cards()
        self.root.after(0, self._redraw_step_finish)

    def _redraw_step_finish(self):
        """Step 3: Draw buttons and scores. If pending redraw, schedule another."""
        if not self._redraw_in_progress:
            return
        self._draw_buttons()
        self.button_drawn = True
        self._draw_scores()

        self._redraw_in_progress = False
        if self._pending_redraw:
            self._pending_redraw = False
            self.root.after(0, lambda: self._handle_update_event(None))

    def _draw_one_card(
        self,
        card: Card,
        x: int,
        y: int,
        layout: LayoutParams,
        clickable: bool = True,
        get_pos=None,
    ) -> tk.Label:
        """Draw a single card. If get_pos(layout)->(x,y), register updater for incremental reposition."""
        photo = self.image_cache.get_card_image(card, layout.card_height)
        label = tk.Label(self.root, image=photo)
        label.image = photo
        label.place(x=x, y=y)
        if clickable:
            label.bind("<Button-1>", self._on_my_card_click)
        if get_pos is not None:
            def updater(l, card=card, lab=label):
                lab.image = self.image_cache.get_card_image(card, l.card_height)
                lab.config(image=lab.image)
                px, py = get_pos(l)
                lab.place(x=px, y=py)
            self._widget_updaters.append(updater)
        return label

    def _draw_background(
        self,
        x: int,
        y: int,
        layout: LayoutParams,
        anchor: str = "nw",
        get_pos=None,
    ) -> tk.Label:
        """Draw card back. If get_pos(layout)->(x,y,anchor), register updater."""
        photo = self.image_cache.get_background_image(layout.card_height)
        label = tk.Label(self.root, image=photo)
        label.image = photo
        label.place(x=x, y=y, anchor=anchor)
        if get_pos is not None:
            def updater(l, lab=label):
                lab.image = self.image_cache.get_background_image(l.card_height)
                lab.config(image=lab.image)
                px, py, anc = get_pos(l)
                lab.place(x=px, y=py, anchor=anc)
            self._widget_updaters.append(updater)
        return label

    def _format_user_info(self, name: str, cards_num: int, score: int) -> str:
        """Format user info string: name, remaining cards, score."""
        return f"{name}\n剩{cards_num}张\n得分{score}"

    def _truncate_name(self, name: str, max_len: int) -> str:
        """Truncate name with ellipsis if too long."""
        if not name:
            return "?"
        if len(name) <= max_len:
            return name
        return name[: max_len - 1] + "…"

    def _calc_text_line_positions(
        self, h: int, pad: int, font_sz: int, line_count: int = 3
    ) -> tuple:
        """Compute y positions for text lines to avoid overlap. Returns (line_height, (y1, y2, ...))."""
        sub_font = max(8, font_sz - 1)
        # Line height: ~1.4x font size; larger of the two fonts
        base_line_height = max(14, int(max(font_sz, sub_font) * 1.4))
        available = max(0, h - 2 * pad)
        line_height = max(10, min(available // line_count, base_line_height))
        total_height = line_height * line_count
        start_y = pad + max(0, (available - total_height) // 2)
        return line_height, tuple(start_y + i * line_height for i in range(line_count))

    def _create_rounded_rect(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        fill: str = None,
        outline: str = None,
        **kwargs,
    ):
        """Draw anti-aliased rounded rectangle using create_polygon with smooth=True."""
        # Ensure radius doesn't exceed half of width or height
        r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)

        # Define polygon points with duplicated corners for smooth curve control
        # Points structure: (x, y) pairs arranged clockwise from top-left corner
        points = [
            # Top edge with rounded corners
            x1 + r, y1, x1 + r, y1,      # Top-left (duplicated)
            x2 - r, y1, x2 - r, y1,      # Top-right (duplicated)

            # Right edge with rounded corners
            x2, y1, x2, y1 + r,          # Top-right curve
            x2, y1 + r, x2, y2 - r,      # Right edge
            x2, y2 - r, x2, y2,          # Bottom-right curve

            # Bottom edge with rounded corners
            x2 - r, y2, x2 - r, y2,      # Bottom-right (duplicated)
            x1 + r, y2, x1 + r, y2,      # Bottom-left (duplicated)

            # Left edge with rounded corners
            x1, y2, x1, y2 - r,          # Bottom-left curve
            x1, y2 - r, x1, y1 + r,      # Left edge
            x1, y1 + r, x1, y1,          # Top-left curve
        ]

        # Configure polygon options
        opts = {
            "smooth": True,
            "splinesteps": 36,
        }

        if fill:
            opts["fill"] = fill
        if outline:
            opts["outline"] = outline

        opts.update(kwargs)

        return canvas.create_polygon(points, **opts)

    def _draw_player_card_background(
        self,
        canvas: tk.Canvas,
        w: int,
        h: int,
        radius: int = None,
    ):
        """Draw player card background: gradient base + shadow, overlay, border (like score panel)."""
        radius = radius or PLAYER_CARD_RADIUS
        pad = 2
        self._create_rounded_rect(
            canvas, pad + 2, pad + 2, w - pad + 2, h - pad + 2, radius + 1,
            fill=PLAYER_CARD_SHADOW, outline="",
        )
        grad_img = self.image_cache.get_gradient_image(
            w, h, PLAYER_CARD_GRADIENT_START, PLAYER_CARD_GRADIENT_END, radius=radius
        )
        canvas.create_image(w // 2, h // 2, image=grad_img)
        canvas.grad_img = grad_img
        hl_h = max(5, h // 5)
        self._create_rounded_rect(
            canvas, pad + 2, pad + 2, w - pad - 2, pad + 2 + hl_h, radius - 1,
            fill=PLAYER_CARD_HIGHLIGHT, outline="",
        )
        sh_h = max(6, h // 4)
        canvas.create_rectangle(
            pad + radius, h - pad - sh_h, w - pad - radius, h - pad,
            fill=PLAYER_CARD_SHADOW, outline="",
        )
        self._create_rounded_rect(
            canvas, pad + 1, pad + 1, w - pad - 1, h - pad - 1, radius - 1,
            fill=PLAYER_CARD_OVERLAY, outline="", stipple="gray75",
        )
        self._create_rounded_rect(
            canvas, pad, pad, w - pad, h - pad, radius,
            fill="", outline=PLAYER_CARD_BORDER,
        )

    def _draw_player_info_card(
        self,
        name: str,
        cards_num: int,
        score: int,
        x: int,
        y: int,
        layout: LayoutParams,
        anchor: str = "w",
        get_pos=None,
    ):
        """Draw player info card: circular avatar + gradient panel with name, cards, score. Unified size for all 6."""
        w = layout.player_card_width
        h = layout.player_card_height
        avatar_sz = layout.avatar_size
        pad = int(PLAYER_CARD_PADDING * layout.scale)
        font_sz = max(10, int(layout.font_size * 0.9))
        max_name_len = PLAYER_NAME_MAX_LEN
        display_name = self._truncate_name(name, max_name_len)
        initial = name[0] if name else "?"

        canvas = tk.Canvas(
            self.root,
            width=w,
            height=h,
            highlightthickness=0,
        )
        self._draw_player_card_background(canvas, w, h)
        canvas.place(x=x, y=y, anchor=anchor)

        ax, ay = pad + avatar_sz // 2, h // 2
        r = avatar_sz // 2 - 2
        canvas.create_oval(ax - r, ay - r, ax + r, ay + r, fill=PLAYER_CARD_AVATAR_BG, outline=PLAYER_CARD_BORDER)
        canvas.create_text(ax, ay, text=initial, fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", font_sz, "bold"))

        info_x = pad + avatar_sz + pad
        sub_font = max(8, font_sz - 1)
        _, (y1, y2, y3) = self._calc_text_line_positions(h, pad, font_sz)
        canvas.create_text(info_x, y1, text=display_name, fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", font_sz), anchor="nw")
        canvas.create_text(info_x, y2, text=f"剩{cards_num}张", fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", sub_font), anchor="nw")
        canvas.create_text(info_x, y3, text=f"得分{score}", fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", sub_font), anchor="nw")

        if get_pos is not None:
            def updater(l, c=canvas):
                nw = l.player_card_width
                nh = l.player_card_height
                av_sz = l.avatar_size
                pad2 = int(PLAYER_CARD_PADDING * l.scale)
                fnt = max(10, int(l.font_size * 0.9))
                _, (y1_u, y2_u, y3_u) = self._calc_text_line_positions(nh, pad2, fnt)
                c.config(width=nw, height=nh)
                c.delete("all")
                self._draw_player_card_background(c, nw, nh)
                ax2, ay2 = pad2 + av_sz // 2, nh // 2
                r2 = av_sz // 2 - 2
                c.create_oval(ax2 - r2, ay2 - r2, ax2 + r2, ay2 + r2, fill=PLAYER_CARD_AVATAR_BG, outline=PLAYER_CARD_BORDER)
                c.create_text(ax2, ay2, text=initial, fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", fnt, "bold"))
                ix = pad2 + av_sz + pad2
                sub_fnt = max(8, fnt - 1)
                c.create_text(ix, y1_u, text=display_name, fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", fnt), anchor="nw")
                c.create_text(ix, y2_u, text=f"剩{cards_num}张", fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", sub_fnt), anchor="nw")
                c.create_text(ix, y3_u, text=f"得分{score}", fill=PLAYER_CARD_TEXT_COLOR, font=("Microsoft YaHei", sub_fnt), anchor="nw")
                px, py, anc = get_pos(l)
                c.place(x=px, y=py, anchor=anc)
            self._widget_updaters.append(updater)

    def _centered_row_start(self, layout: LayoutParams, card_count: int) -> int:
        total_width = layout.card_width + layout.card_spacing * max(card_count, 1)
        return (layout.width - total_width) // 2

    def _draw_user_cards(self):
        self.logger.info("draw_user_cards")
        self._draw_vertical_user_pairs()
        self._draw_upper_horizontal_user_pairs()
        self._draw_lower_horizontal_user_pairs()

    def _draw_vertical_user_pairs(self):
        layout = self._get_layout()
        info_x = int(100 * layout.scale_x)
        info_y_offset = layout.vertical_margin + layout.card_height // 2
        client_id = self.field_info.client_id

        get_my_info_pos = lambda l: (int(100 * l.scale_x), l.height - (l.vertical_margin + l.card_height // 2), "w")
        self._draw_player_info_card(
            self.field_info.user_names[client_id],
            self.field_info.users_cards_num[client_id],
            self.field_info.user_scores[client_id],
            info_x,
            layout.height - info_y_offset,
            layout,
            anchor="w",
            get_pos=get_my_info_pos,
        )

        self.my_card_labels = []
        self.selected_card_flag = [False] * len(self.field_info.client_cards)
        start_x = self._centered_row_start(layout, 36)
        for i, card in enumerate(self.field_info.client_cards):
            def make_get_pos(idx):
                return lambda l: (self._centered_row_start(l, 36) + idx * l.card_spacing, l.my_cards_y - 20 if self.selected_card_flag[idx] else l.my_cards_y)
            get_pos = make_get_pos(i)
            x = start_x + i * layout.card_spacing
            y = layout.my_cards_y - 20 if self.selected_card_flag[i] else layout.my_cards_y
            label = self._draw_one_card(card, x, y, layout, clickable=True, get_pos=get_pos)
            self.my_card_labels.append(label)

        my_played = self.field_info.users_played_cards[client_id]
        self.logger.info(f"my_played_cards: {my_played}")
        if my_played:
            for i, card in enumerate(my_played):
                get_pos = lambda l, idx=i, n=len(my_played): (self._centered_row_start(l, n) + idx * l.card_spacing, l.my_played_cards_y)
                x = self._centered_row_start(layout, len(my_played)) + i * layout.card_spacing
                self._draw_one_card(card, x, layout.my_played_cards_y, layout, clickable=False, get_pos=get_pos)

        top_id = (client_id + PLAYER_OFFSET_TOP) % 6
        get_top_info_pos = lambda l: (int(100 * l.scale_x), l.vertical_margin + l.card_height // 2, "w")
        self._draw_player_info_card(
            self.field_info.user_names[top_id],
            self.field_info.users_cards_num[top_id],
            self.field_info.user_scores[top_id],
            info_x,
            info_y_offset,
            layout,
            anchor="w",
            get_pos=get_top_info_pos,
        )

        top_cards_num = self.field_info.users_cards_num[top_id]
        for i in range(top_cards_num):
            get_pos = lambda l, idx=i, n=36: (self._centered_row_start(l, n) + idx * l.card_spacing, l.vertical_margin, "nw")
            x = start_x + i * layout.card_spacing
            self._draw_background(x, layout.vertical_margin, layout, get_pos=get_pos)

        top_played = self.field_info.users_played_cards[top_id]
        self.logger.info(f"top_user_played_cards: {top_played}")
        if top_played:
            for i, card in enumerate(top_played):
                get_pos = lambda l, idx=i, n=len(top_played): (self._centered_row_start(l, n) + idx * l.card_spacing, l.top_played_cards_y)
                x = self._centered_row_start(layout, len(top_played)) + i * layout.card_spacing
                self._draw_one_card(card, x, layout.top_played_cards_y, layout, clickable=False, get_pos=get_pos)

    def _draw_horizontal_user_pair(self, user_id: int, card_y: int, is_left: bool, layout: LayoutParams, is_upper: bool):
        info_y = card_y + layout.card_height // 2
        played = self.field_info.users_played_cards[user_id]
        self.logger.info(f"user_{user_id}_played_cards: {played}")

        def _cy(l):
            return l.upper_card_y if is_upper else l.lower_card_y

        info_x = layout.info_margin if is_left else layout.width - layout.info_margin
        get_info_pos = lambda l: (l.info_margin if is_left else l.width - l.info_margin, _cy(l) + l.card_height // 2, "w" if is_left else "e")
        self._draw_player_info_card(
            self.field_info.user_names[user_id],
            self.field_info.users_cards_num[user_id],
            self.field_info.user_scores[user_id],
            info_x,
            info_y,
            layout,
            anchor="w" if is_left else "e",
            get_pos=get_info_pos,
        )

        if is_left:
            get_back_pos = lambda l: (l.horizontal_card_margin, _cy(l), "nw")
            self._draw_background(layout.horizontal_card_margin, card_y, layout, get_pos=get_back_pos)
            for i, card in enumerate(played):
                get_pos = lambda l, idx=i: (l.horizontal_card_margin + l.card_width + l.played_card_spacing + idx * l.card_spacing, _cy(l))
                x = layout.horizontal_card_margin + layout.card_width + layout.played_card_spacing + i * layout.card_spacing
                self._draw_one_card(card, x, card_y, layout, clickable=False, get_pos=get_pos)
        else:
            get_back_pos = lambda l: (l.width - l.horizontal_card_margin, _cy(l), "ne")
            self._draw_background(layout.width - layout.horizontal_card_margin, card_y, layout, "ne", get_pos=get_back_pos)
            cards_start_x = layout.width - layout.horizontal_card_margin - layout.card_width * 2 - layout.played_card_spacing - layout.card_spacing * (len(played) - 1) if played else 0
            for i, card in enumerate(played):
                n = len(played)
                get_pos = lambda l, idx=i, nn=n: (l.width - l.horizontal_card_margin - l.card_width * 2 - l.played_card_spacing - l.card_spacing * (nn - 1) + idx * l.card_spacing, _cy(l))
                x = cards_start_x + i * layout.card_spacing
                self._draw_one_card(card, x, card_y, layout, clickable=False, get_pos=get_pos)

    def _draw_upper_horizontal_user_pairs(self):
        layout = self._get_layout()
        self._draw_horizontal_user_pair((self.field_info.client_id + PLAYER_OFFSET_NW) % 6, layout.upper_card_y, True, layout, is_upper=True)
        self._draw_horizontal_user_pair((self.field_info.client_id + PLAYER_OFFSET_NE) % 6, layout.upper_card_y, False, layout, is_upper=True)

    def _draw_lower_horizontal_user_pairs(self):
        layout = self._get_layout()
        self._draw_horizontal_user_pair((self.field_info.client_id + PLAYER_OFFSET_SW) % 6, layout.lower_card_y, True, layout, is_upper=False)
        self._draw_horizontal_user_pair((self.field_info.client_id + PLAYER_OFFSET_SE) % 6, layout.lower_card_y, False, layout, is_upper=False)

    def _draw_buttons(self):
        self.logger.info("draw_buttons")
        layout = self._get_layout()
        for i, (text, cmd) in enumerate([("重置", self._on_reset_button_click), ("确定", self._on_confirm_button_click), ("跳过", self._on_skip_button_click)]):
            btn = tk.Button(self.root, text=text, width=18, command=cmd)
            btn.place(x=layout.button_anchor_x, y=layout.button_y_base + i * layout.button_spacing, anchor="ne")
            self.buttons.append(btn)
            get_pos = lambda l, idx=i: (l.button_anchor_x, l.button_y_base + idx * l.button_spacing, "ne")
            def make_updater(b, gp=get_pos):
                return lambda l: b.place(x=gp(l)[0], y=gp(l)[1], anchor="ne")
            self._widget_updaters.append(make_updater(btn, get_pos))

    def _draw_scores(self):
        layout = self._get_layout()
        client_id = self.field_info.client_id
        my_team, opp_team = utils.calculate_team_scores(
            self.field_info.head_master, client_id, self.field_info.users_cards_num, self.field_info.user_scores
        )
        now_player = self._truncate_name(self.field_info.user_names[self.field_info.now_player], 6)
        head_master = self._truncate_name(
            self.field_info.user_names[self.field_info.head_master] if self.field_info.head_master != -1 else "无", 6
        )
        panel_w = int(200 * layout.scale_x)
        panel_h = int(200 * layout.scale_y)
        pad = int(14 * layout.scale)
        canvas = tk.Canvas(self.root, width=panel_w, height=panel_h, highlightthickness=0)
        grad_img = self.image_cache.get_gradient_image(
            panel_w, panel_h, SCORE_PANEL_GRADIENT_START, SCORE_PANEL_GRADIENT_END, radius=SCORE_PANEL_RADIUS
        )
        canvas.create_image(panel_w // 2, panel_h // 2, image=grad_img)
        canvas.grad_img = grad_img
        canvas.place(x=layout.score_anchor_x, y=layout.vertical_margin, anchor="ne")
        canvas.create_text(
            panel_w // 2, pad + layout.score_label_size,
            text="━━ 比分面板 ━━",
            font=("Microsoft YaHei", layout.score_label_size, "bold"),
            fill=PLAYER_CARD_TEXT_COLOR,
        )
        y = pad + layout.score_label_size * 3
        row_h = max(22, layout.score_label_size + 10)
        rows = [
            ("己方得分", str(my_team), True),
            ("对方得分", str(opp_team), True),
            ("场上分数", str(self.field_info.now_score), True),
            ("当前出牌", now_player, False),
            ("头科", head_master, False),
        ]
        for i, (label_text, value, use_lcd) in enumerate(rows):
            yy = y + i * row_h
            canvas.create_text(pad, yy, text=label_text, font=(SCORE_LABEL_FONT[0], layout.score_label_size), fill="#a0a0a0", anchor="nw")
            val_font = ("Consolas", layout.score_number_size, "bold") if use_lcd else (SCORE_LABEL_FONT[0], layout.score_label_size)
            canvas.create_text(panel_w - pad, yy, text=value, font=val_font, fill="#ffd700", anchor="ne")

        def score_updater(l):
            pw, ph = int(200 * l.scale_x), int(200 * l.scale_y)
            grad = self.image_cache.get_gradient_image(
                pw, ph, SCORE_PANEL_GRADIENT_START, SCORE_PANEL_GRADIENT_END, radius=SCORE_PANEL_RADIUS
            )
            canvas.config(width=pw, height=ph)
            canvas.delete("all")
            canvas.create_image(pw // 2, ph // 2, image=grad)
            canvas.grad_img = grad
            canvas.create_text(pw // 2, int(14 * l.scale) + l.score_label_size, text="━━ 比分面板 ━━",
                font=("Microsoft YaHei", l.score_label_size, "bold"), fill=PLAYER_CARD_TEXT_COLOR)
            y_u = int(14 * l.scale) + l.score_label_size * 3
            rh = max(22, l.score_label_size + 10)
            for i, (label_text, value, use_lcd) in enumerate(rows):
                yy = y_u + i * rh
                canvas.create_text(int(14 * l.scale), yy, text=label_text, font=(SCORE_LABEL_FONT[0], l.score_label_size), fill="#a0a0a0", anchor="nw")
                vf = ("Consolas", l.score_number_size, "bold") if use_lcd else (SCORE_LABEL_FONT[0], l.score_label_size)
                canvas.create_text(pw - int(14 * l.scale), yy, text=value, font=vf, fill="#ffd700", anchor="ne")
            canvas.place(x=l.score_anchor_x, y=l.vertical_margin, anchor="ne")
        self._widget_updaters.append(score_updater)

    def _on_my_card_click(self, event):
        self.logger.info("on_my_card_click")
        label = event.widget
        try:
            i = self.my_card_labels.index(label)
        except ValueError:
            return
        dx, dy = label.winfo_x(), label.winfo_y()
        label.place(x=dx, y=dy + 20 if self.selected_card_flag[i] else dy - 20)
        self.selected_card_flag[i] = not self.selected_card_flag[i]

    def _on_reset_button_click(self):
        self.logger.info("on_reset_button_click")
        for i, label in enumerate(self.my_card_labels):
            if self.selected_card_flag[i]:
                label.place(x=label.winfo_x(), y=label.winfo_y() + 20)
                self.selected_card_flag[i] = False

    def _on_confirm_button_click(self):
        self.logger.info("on_confirm_button_click")
        selected_cards = [self.field_info.client_cards[i] for i, _ in enumerate(self.my_card_labels) if self.selected_card_flag[i]]
        last_played = self.field_info.users_played_cards[self.field_info.last_player] if self.field_info.last_player != self.field_info.client_id else None
        if not playingrules.validate_user_selected_cards(selected_cards, self.field_info.client_cards, last_played):
            self.logger.info("Invalid card selection")
            return
        self.logger.info(f"selected_cards: {[str(c) for c in selected_cards]}")
        card_queue.put(selected_cards)

    def _on_skip_button_click(self):
        self.logger.info("on_skip_button_click")
        self._on_reset_button_click()
        card_queue.put(["F"])


def run_tkinter_gui(logger: Logger, queue_obj, on_ready):
    """Bootstrap the Tkinter GUI and inform caller when ready."""
    global card_queue
    card_queue = queue_obj

    root = tk.Tk()
    gui = GUI(root, logger)
    on_ready(gui)
    try:
        root.mainloop()
    finally:
        logger.info("Tkinter GUI closed")

