import os
import threading
import platform
import subprocess

def __playsound(paths: list[str], playtime):
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
            raise RuntimeError('unknow os!') 
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