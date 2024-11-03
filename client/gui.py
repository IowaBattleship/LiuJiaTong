import copy
import tkinter as tk
import threading
from tkinter import PhotoImage
from PIL import Image, ImageTk

import logger

my_cards = []

def update_gui(client_cards: list[str]):
    logger.info("update gui")
    global my_cards
    my_cards = copy.deepcopy(client_cards)
    global root
    root.event_generate("<<UpdateEvent>>")

def init_gui():
    logger.info("init gui")
    def start_gui():
        # 用Tkinter初始化界面
        global root
        root = tk.Tk()
        root.title("LiuJiaTong")
        root.geometry("800x600")
        root.bind("<<UpdateEvent>>", handle_update_event)
        root.mainloop()

    # 启动 GUI 线程
    gui_thread = threading.Thread(target=start_gui)
    gui_thread.daemon = True # 设置为守护线程，这样主程序退出时 GUI 也会退出
    gui_thread.start()

def handle_update_event(event):
    logger.info("handle update event")
    image = Image.open("client/images/2.png") # 打开图片

    # 等比例缩小图片至高度为100像素
    target_height = 100
    width, height = image.size
    scale = target_height / height
    new_width = int(width * scale)
    image = image.resize((new_width, target_height))

    # 将图片转换为 PhotoImage 对象
    photo = ImageTk.PhotoImage(image)

    # # 加载图片
    # photo = PhotoImage(file="client/images/2.png")
    
    # 在 GUI 中显示图片
    label = tk.Label(root, image=photo) # 这里的image参数是必须指定的，与下一行不冲突
    label.image = photo
    label.place(x=50, y=50)

def draw_one_card(card: str, x: int, y: int):
    pass