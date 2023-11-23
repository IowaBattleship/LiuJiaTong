import os
import threading

def __playsound(paths: list[str], playtime):
    for path in paths:
        assert os.path.isabs(path), path
        cmd = ""
        if os.name == "posix":
            cmd = f"aplay -q {path} 2>/dev/null"
        elif os.name == "nt":
            cmd = f"powershell -c (New-Object Media.SoundPlayer '{path}').PlaySync()"
        else:
            raise RuntimeError('unknow os!') 
        os.system(cmd)

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