import copy
import tkinter as tk
import threading
from tkinter import PhotoImage
from PIL import Image, ImageTk

import logger
from card import Card, Suits
from FieldInfo import FieldInfo
import utils
import queue
from logging import Logger
import playingrules

# 创建一个线程安全的队列，用于传递用户选中的卡牌
card_queue = queue.Queue()

# users_name = []
# my_cards = []
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 810
DEFAULT_VERTICAL_MARGIN = 40

HORIZONTAL_CARD_MARGIN = 120
VERTICAL_CARD_SPACING = 26
DEFAULT_CARD_WIDTH = 71
DEFAULT_CARD_HEIGHT = 100
DEFAULT_CARD_SPACING = 20
PLAYED_CARD_SPACING = 30
UPPER_CARD_Y = DEFAULT_VERTICAL_MARGIN + DEFAULT_CARD_HEIGHT * 2 + VERTICAL_CARD_SPACING * 2
LOWER_CARD_Y = UPPER_CARD_Y + DEFAULT_CARD_HEIGHT + VERTICAL_CARD_SPACING

DEFAULT_LINE_SPACING = 30

class GUI:
    def __init__(self, root: tk.Tk, logger: Logger):
        self.root = root
        self.field_info = None
        self.selected_card_flag = [False] * 36
        self.my_card_labels = []
        self.logger = logger # 绑定对应client的logger
        self.button_drawn = False
        self.buttons = []

def update_gui(info: FieldInfo):
    gui_obj.logger.info("update gui")   
    gui_obj.field_info = info
    gui_obj.root.event_generate("<<UpdateEvent>>")

def init_gui(logger):
    logger.info("init_gui")
    def start_gui():
        # 用Tkinter初始化界面
        root = tk.Tk()
        root.title("LiuJiaTong")
        root.geometry("1440x810")
        root.bind("<<UpdateEvent>>", handle_update_event)
        # root.bind('<Configure>', on_resize) # 绑定窗口大小变化事件
        global gui_obj
        gui_obj = GUI(root, logger)
        root.mainloop()

    # 启动 GUI 线程
    gui_thread = threading.Thread(target=start_gui)
    gui_thread.daemon = True # 设置为守护线程，这样主程序退出时 GUI 也会退出
    gui_thread.start()

# Event Handler
def handle_update_event(event):
    gui_obj.logger.info("handle_update_event")

    # 清空界面
    for widget in gui_obj.root.winfo_children():
        if widget in gui_obj.buttons:
            continue
        widget.destroy()

    # 重新绘制界面
    draw_user_cards()
    if not gui_obj.button_drawn:
        draw_buttons()
        gui_obj.button_drawn = True
    draw_scores()

def on_resize(event):
    # 获取窗口的宽度
    window_width = event.width
    window_height = event.height

    global label1, label2, label3, label4, label5
    label1_x = window_width - label1.winfo_width()
    label2_x = window_width - label2.winfo_width()
    label3_y = window_height + label3.winfo_height()
    label4_x = window_width + label4.winfo_width()
    label5_x = window_width + label5.winfo_width()
    # print(f"Lable 1 width: {label1.winfo_width()}. Lable 2 width: {label2.winfo_width()}. Lable 3 height: {label3.winfo_height()}. Lable 4 width: {label4.winfo_width()}. Lable 5 width: {label5.winfo_width()}")

    # 更新Label的位置
    label1.place(x=label1_x, y=400)
    label2.place(x=label2_x, y=200)
    label3.place(x=window_width * 0.3, y=label3_y + 50)
    label4.place(x=label4_x, y=200)
    label5.place(x=label5_x, y=400)

# UI 绘制方法
def card_to_photo(card: Card) -> ImageTk.PhotoImage:
    # 卡牌素材来源：https://gitcode.com/open-source-toolkit/77d38/?utm_source=tools_gitcode&index=bottom&type=card&
    if card.suit == Suits.empty:
        image_path = "client/images/JOKER-B.png" if card.value == 16 else "client/images/JOKER-A.png"
    elif card.value > 10:
        image_path = "client/images/" + card.suit.value + utils.int_to_str(card.value) + ".png"
    else:
        image_path = "client/images/" + card.suit.value + str(card.value) + ".png"
    image = Image.open(image_path) # 打开图片

    # 等比例缩小图片至高度为100像素
    target_height = 100
    width, height = image.size
    scale = target_height / height
    new_width = int(width * scale) # 71
    image = image.resize((new_width, target_height))
    return ImageTk.PhotoImage(image)

def draw_one_card(card: Card, x: int, y: int) -> tk.Label:
    # 在 GUI 中显示图片
    photo = card_to_photo(card)
    label = tk.Label(gui_obj.root, image=photo) # 这里的image参数是必须指定的，与下一行不冲突
    label.image = photo
    label.place(x=x, y=y)
    label.bind("<Button-1>", on_my_card_click)
    return label

def grid_one_card(card: Card, row: int, column: int):
    photo = card_to_photo(card)
    label = tk.Label(gui_obj.root, image=photo)
    label.image = photo
    label.grid(row=row, column=column)

def draw_background(x: int, y: int, anchor: str='nw'):
    image = Image.open("client/images/Background.png") # 打开图片

    # 等比例缩小图片至高度为75像素
    target_height = 100
    width, height = image.size
    scale = target_height / height
    new_width = int(width * scale)
    image = image.resize((new_width, target_height))

    photo = ImageTk.PhotoImage(image)
    label = tk.Label(gui_obj.root, image=photo) # 这里的image参数是必须指定的，与下一行不冲突
    label.image = photo
    label.place(x=x, y=y, anchor=anchor)

def draw_user_cards():
    gui_obj.logger.info("draw_user_cards")
    draw_vertical_user_pairs()
    draw_upper_horizontal_user_pairs()
    draw_lower_horizontal_user_pairs()

def draw_vertical_user_pairs():
    horizontal_margin = 100
    vertical_margin = DEFAULT_VERTICAL_MARGIN + DEFAULT_CARD_HEIGHT / 2

    # My Info
    my_name = gui_obj.field_info.user_names[gui_obj.field_info.client_id]
    my_cards_num = gui_obj.field_info.users_cards_num[gui_obj.field_info.client_id]
    my_score = gui_obj.field_info.user_scores[gui_obj.field_info.client_id]
    my_info = f"{my_name}\n剩{my_cards_num}张\n得分{my_score}"
    my_info_label = tk.Label(gui_obj.root, text=my_info, font=("Arial", 20))
    my_info_label.place(x=horizontal_margin, y=DEFAULT_WINDOW_HEIGHT - vertical_margin, anchor='w')

    # My Cards
    gui_obj.my_card_labels = [] # 先清空，不然每次都会变长
    gui_obj.selected_card_flag = [False] * len(gui_obj.field_info.client_cards)
    for i in range(len(gui_obj.field_info.client_cards)):
        card_x = (DEFAULT_WINDOW_WIDTH - DEFAULT_CARD_WIDTH - DEFAULT_CARD_SPACING * 36) / 2 + i * DEFAULT_CARD_SPACING
        label = draw_one_card(gui_obj.field_info.client_cards[i], card_x, DEFAULT_WINDOW_HEIGHT - 140)
        gui_obj.my_card_labels.append(label)

    # My Played Cards
    my_played_cards = gui_obj.field_info.users_played_cards[gui_obj.field_info.client_id]
    gui_obj.logger.info(f"my_played_cards: {my_played_cards}")
    for i in range(len(my_played_cards)):
        card_x = (DEFAULT_WINDOW_WIDTH - DEFAULT_CARD_WIDTH - DEFAULT_CARD_SPACING * len(my_played_cards)) / 2 + i * DEFAULT_CARD_SPACING
        card_y = DEFAULT_WINDOW_HEIGHT - DEFAULT_VERTICAL_MARGIN - DEFAULT_CARD_HEIGHT * 2 - VERTICAL_CARD_SPACING
        draw_one_card(my_played_cards[i], card_x, card_y)

    # Top User INFO
    top_user_name = gui_obj.field_info.user_names[(gui_obj.field_info.client_id + 3) % 6]
    top_user_cards_num = gui_obj.field_info.users_cards_num[(gui_obj.field_info.client_id + 3) % 6]
    top_user_score = gui_obj.field_info.user_scores[(gui_obj.field_info.client_id + 3) % 6]
    top_user_info = f"{top_user_name}\n剩{top_user_cards_num}张\n得分{top_user_score}"
    top_user_info_label = tk.Label(gui_obj.root, text=top_user_info, font=("Arial", 20))
    top_user_info_label.place(x=horizontal_margin, y=vertical_margin, anchor='w')

    # Top User Cards
    for i in range(gui_obj.field_info.users_cards_num[(gui_obj.field_info.client_id + 3) % 6]):
        card_x = (DEFAULT_WINDOW_WIDTH - DEFAULT_CARD_WIDTH - DEFAULT_CARD_SPACING * 36) / 2 + i * DEFAULT_CARD_SPACING
        draw_background(card_x, 40)
    
    # Top User Played Cards
    top_user_played_cards = gui_obj.field_info.users_played_cards[(gui_obj.field_info.client_id + 3) % 6]
    gui_obj.logger.info(f"top_user_played_cards: {top_user_played_cards}")
    for i in range(len(top_user_played_cards)):
        card_x = (DEFAULT_WINDOW_WIDTH - DEFAULT_CARD_WIDTH - DEFAULT_CARD_SPACING * len(top_user_played_cards)) / 2 + i * DEFAULT_CARD_SPACING
        card_y = DEFAULT_VERTICAL_MARGIN + DEFAULT_CARD_HEIGHT + VERTICAL_CARD_SPACING
        draw_one_card(top_user_played_cards[i], card_x, card_y)

def draw_upper_horizontal_user_pairs():
    horizontal_margin = 20
    vertical_margin = UPPER_CARD_Y + DEFAULT_CARD_HEIGHT / 2

    # North-West User Info
    north_west_user_name = gui_obj.field_info.user_names[(gui_obj.field_info.client_id + 4) % 6]
    north_west_user_cards_num = gui_obj.field_info.users_cards_num[(gui_obj.field_info.client_id + 4) % 6]
    north_west_user_score = gui_obj.field_info.user_scores[(gui_obj.field_info.client_id + 4) % 6]
    north_west_user_info = f"{north_west_user_name}\n剩{north_west_user_cards_num}张\n得分{north_west_user_score}"
    north_west_user_info_label = tk.Label(gui_obj.root, text=north_west_user_info, font=("Arial", 20))
    north_west_user_info_label.place(x=horizontal_margin, y=vertical_margin, anchor='w')

    # North-East User Info
    north_east_user_name = gui_obj.field_info.user_names[(gui_obj.field_info.client_id + 2) % 6]
    north_east_user_cards_num = gui_obj.field_info.users_cards_num[(gui_obj.field_info.client_id + 2) % 6]
    north_east_user_score = gui_obj.field_info.user_scores[(gui_obj.field_info.client_id + 2) % 6]
    north_east_user_info = f"{north_east_user_name}\n剩{north_east_user_cards_num}张\n得分{north_east_user_score}"
    north_east_user_info_label = tk.Label(gui_obj.root, text=north_east_user_info, font=("Arial", 20))
    north_east_user_info_label.place(x=DEFAULT_WINDOW_WIDTH - horizontal_margin, y=vertical_margin, anchor='e')

    # North-West User Cards
    draw_background(HORIZONTAL_CARD_MARGIN, UPPER_CARD_Y)
    north_west_user_played_cards = gui_obj.field_info.users_played_cards[(gui_obj.field_info.client_id + 4) % 6]
    gui_obj.logger.info(f"north_west_user_played_cards: {north_west_user_played_cards}")
    for i in range(len(north_west_user_played_cards)):
        card_x = HORIZONTAL_CARD_MARGIN + DEFAULT_CARD_WIDTH + PLAYED_CARD_SPACING + DEFAULT_CARD_SPACING * i
        draw_one_card(north_west_user_played_cards[i], card_x, UPPER_CARD_Y)

    # North-East User Cards
    draw_background(DEFAULT_WINDOW_WIDTH - HORIZONTAL_CARD_MARGIN, UPPER_CARD_Y, "ne")
    north_east_user_played_cards = gui_obj.field_info.users_played_cards[(gui_obj.field_info.client_id + 2) % 6]
    gui_obj.logger.info(f"north_east_user_played_cards: {north_east_user_played_cards}")
    for i in range(len(north_east_user_played_cards)):
        card_x = DEFAULT_WINDOW_WIDTH - HORIZONTAL_CARD_MARGIN - DEFAULT_CARD_WIDTH * 2 - PLAYED_CARD_SPACING - DEFAULT_CARD_SPACING * (len(north_east_user_played_cards) - 1 - i)
        draw_one_card(north_east_user_played_cards[i], card_x, UPPER_CARD_Y)

def draw_lower_horizontal_user_pairs():
    horizontal_margin = 20
    vertical_margin = LOWER_CARD_Y + DEFAULT_CARD_HEIGHT / 2

    # South-West User Info
    south_west_user_name = gui_obj.field_info.user_names[(gui_obj.field_info.client_id + 5) % 6]
    south_west_user_cards_num = gui_obj.field_info.users_cards_num[(gui_obj.field_info.client_id + 5) % 6]
    south_west_user_score = gui_obj.field_info.user_scores[(gui_obj.field_info.client_id + 5) % 6]
    south_west_user_info = f"{south_west_user_name}\n剩{south_west_user_cards_num}张\n得分{south_west_user_score}"
    south_west_user_info_label = tk.Label(gui_obj.root, text=south_west_user_info, font=("Arial", 20))
    south_west_user_info_label.place(x=horizontal_margin, y=vertical_margin, anchor='w')

    # South-East User Info
    south_east_user_name = gui_obj.field_info.user_names[(gui_obj.field_info.client_id + 1) % 6]
    south_east_user_cards_num = gui_obj.field_info.users_cards_num[(gui_obj.field_info.client_id + 1) % 6]
    south_east_user_score = gui_obj.field_info.user_scores[(gui_obj.field_info.client_id + 1) % 6]
    south_east_user_info = f"{south_east_user_name}\n剩{south_east_user_cards_num}张\n得分{south_east_user_score}"
    south_east_user_info_label = tk.Label(gui_obj.root, text=south_east_user_info, font=("Arial", 20))
    south_east_user_info_label.place(x=DEFAULT_WINDOW_WIDTH - horizontal_margin, y=vertical_margin, anchor='e')

    # South-West User Cards
    draw_background(HORIZONTAL_CARD_MARGIN, LOWER_CARD_Y)
    south_west_user_played_cards = gui_obj.field_info.users_played_cards[(gui_obj.field_info.client_id + 5) % 6]
    gui_obj.logger.info(f"south_west_user_played_cards: {south_west_user_played_cards}")
    for i in range(len(south_west_user_played_cards)):
        card_x = HORIZONTAL_CARD_MARGIN + DEFAULT_CARD_WIDTH + PLAYED_CARD_SPACING + DEFAULT_CARD_SPACING * i
        draw_one_card(south_west_user_played_cards[i], card_x, LOWER_CARD_Y)

    # South-East User Cards
    draw_background(DEFAULT_WINDOW_WIDTH - HORIZONTAL_CARD_MARGIN, LOWER_CARD_Y, "ne")
    south_east_user_played_cards = gui_obj.field_info.users_played_cards[(gui_obj.field_info.client_id + 1) % 6]
    gui_obj.logger.info(f"south_east_user_played_cards: {south_east_user_played_cards}")
    for i in range(len(south_east_user_played_cards)):
        card_x = DEFAULT_WINDOW_WIDTH - HORIZONTAL_CARD_MARGIN - DEFAULT_CARD_WIDTH * 2 - PLAYED_CARD_SPACING - DEFAULT_CARD_SPACING * (len(south_east_user_played_cards) - 1 - i)
        draw_one_card(south_east_user_played_cards[i], card_x, LOWER_CARD_Y)

def draw_buttons():
    gui_obj.logger.info("draw_buttons")
    reset_button = tk.Button(gui_obj.root, text="重置", width=18, command=on_reset_button_click)
    reset_button.place(x=DEFAULT_WINDOW_WIDTH - 30, y=DEFAULT_WINDOW_HEIGHT - 150, anchor='ne')
    gui_obj.buttons.append(reset_button)

    confirm_button = tk.Button(gui_obj.root, text="确定", width=18, command=on_confirm_button_click)
    confirm_button.place(x=DEFAULT_WINDOW_WIDTH - 30, y=DEFAULT_WINDOW_HEIGHT - 100, anchor='ne')
    gui_obj.buttons.append(confirm_button)

    skip_button = tk.Button(gui_obj.root, text="跳过", width=18, command=on_skip_button_click)
    skip_button.place(x=DEFAULT_WINDOW_WIDTH - 30, y=DEFAULT_WINDOW_HEIGHT - 50, anchor='ne')
    gui_obj.buttons.append(skip_button)
    
def draw_scores():
    client_id = gui_obj.field_info.client_id
    scores = gui_obj.field_info.user_scores
    my_team_score, opposing_team_score = utils.calculate_team_scores(gui_obj.field_info.head_master, client_id, gui_obj.field_info.users_cards_num, scores)
    
    my_team_score_text = f"己方得分: {my_team_score}"
    opposing_team_score_text = f"对方得分: {opposing_team_score}"
    field_score = gui_obj.field_info.now_score
    field_score_text = f"场上分数: {field_score}"
    now_player_name = gui_obj.field_info.user_names[gui_obj.field_info.now_player]
    now_player_name_text = f"当前出牌: {now_player_name}"
    head_master = gui_obj.field_info.users_names[gui_obj.field_info.head_master] if gui_obj.field_info.head_master != -1 else "无"
    head_master_text = f"头科: {head_master}"
    score_label = tk.Label(gui_obj.root, text=f"{my_team_score_text}\n{opposing_team_score_text}\n{field_score_text}\n{now_player_name_text}\n{head_master_text}", font=("Arial", 20))
    score_label.place(x=DEFAULT_WINDOW_WIDTH - 50, y=DEFAULT_VERTICAL_MARGIN, anchor='ne')

# Click Event
def on_my_card_click(event):
    gui_obj.logger.info("on_my_card_click")
    # 获取当前Label的x和y坐标
    label = event.widget
    current_x = label.winfo_x()
    current_y = label.winfo_y()
    
    # 遍历my_card_labels，找到对应的索引，然后判断是否选中了
    for i in range(len(gui_obj.my_card_labels)):
        if gui_obj.my_card_labels[i] != label:
            continue

        if gui_obj.selected_card_flag[i]:
            # 将Label向下移动20个单位
            new_y = current_y + 20
            label.place(x=current_x, y=new_y)
        else:
            # 将Label向上移动20个单位
            new_y = current_y - 20
            label.place(x=current_x, y=new_y)

        gui_obj.selected_card_flag[i] = not gui_obj.selected_card_flag[i]

def on_reset_button_click():
    gui_obj.logger.info("on_reset_button_click")
    # 遍历label
    for label in gui_obj.my_card_labels:
        # 撤销所有选中的牌
        label_index = gui_obj.my_card_labels.index(label)
        if gui_obj.selected_card_flag[label_index]:
            label.place(x=label.winfo_x(), y=label.winfo_y() + 20)
            gui_obj.selected_card_flag[label_index] = False

def on_confirm_button_click():
    gui_obj.logger.info("on_confirm_button_click")
    # 检查卡牌合法性

    # 抽出卡牌
    selected_cards = []
    for label in gui_obj.my_card_labels:
        # 撤销所有选中的牌
        label_index = gui_obj.my_card_labels.index(label)
        if gui_obj.selected_card_flag[label_index]:
            selected_cards.append(gui_obj.field_info.client_cards[label_index])
    
    valid_result = playingrules.validate_user_selected_cards(
        selected_cards, 
        gui_obj.field_info.client_cards, 
        gui_obj.field_info.users_played_cards[gui_obj.field_info.last_player] if gui_obj.field_info.last_player != gui_obj.field_info.client_id else None
    )

    if not valid_result:
        gui_obj.logger.info("卡牌不合法")
        return

    # 告知服务器
    selected_cards_str = [str(c) for c in selected_cards]
    gui_obj.logger.info(f"selected_cards: {selected_cards_str}")
    card_queue.put(selected_cards)

def on_skip_button_click():
    gui_obj.logger.info("on_skip_button_click")
    # 重置卡牌
    on_reset_button_click()

    # 告知服务器
    card_queue.put(['F'])
