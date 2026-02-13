import os
import threading
import platform
import subprocess
from cli.terminal_utils import fatal

def check_sound_player():
    def __checker(cmd: list[str], obj: str):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
        except:
            fatal(f'This game needs "{obj}" to play sound, please install it')
    
    if platform.system() == "Darwin":
        __checker(["afplay"], "afplay")
    elif platform.system() == "Linux":
        __checker(["aplay"], "aplay")
    elif platform.system() == "Windows":
        __checker(["powershell", "-c", "New-Object", "Media.SoundPlayer"], "Media.SoundPlayer")
    else:
        raise RuntimeError('Unknown os') 

def __playsound(paths: list[str], playtime):
    '''
    播放音频
    :param paths: 需要播放的音频文件
    :param playtime: 该参数无效
    '''
    for path in paths:
        assert os.path.isabs(path), path
        cmd = ""
        if platform.system() == "Darwin":
            cmd = f"afplay {path}"
        elif platform.system() == "Linux":
            cmd = f"aplay -q {path}"
        elif platform.system() == "Windows":
            cmd = f"powershell -c (New-Object Media.SoundPlayer '{path}').PlaySync()"
        else:
            raise RuntimeError('Unknown os') 
        subprocess.Popen(
            cmd.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).wait()

def playsound(basename: str, async_flow: bool, playtime):
    assert playtime is None
    path = os.path.join(os.path.dirname(__file__), basename + ".wav")
    if async_flow:
        thread = threading.Thread(target=__playsound, args=([path], playtime, ))
        thread.start()
    else:
        __playsound([path], playtime)
    
def playsounds(basenames: list[str], async_flow: bool):
    paths = []
    for basename in basenames:
        path = os.path.join(os.path.dirname(__file__), basename + ".wav")
        paths.append(path)
    if async_flow:
        thread = threading.Thread(target=__playsound, args=(paths, None, ))
        thread.start()
    else:
        __playsound(paths, None)