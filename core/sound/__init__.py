import os
import threading
import platform
import subprocess


class SoundEnvironmentError(RuntimeError):
    """音效环境不可用时由 check_sound_player 抛出，由调用方决定是否退出。"""
    pass


def check_sound_player() -> None:
    """
    检查当前平台是否具备播放音效的能力。
    - macOS: 需要 afplay
    - Linux: 需要 aplay
    - Windows: 使用标准库 winsound，无需额外依赖

    若环境不满足则抛出 SoundEnvironmentError，由调用方捕获后决定退出或提示。
    """

    def __checker(cmd: list[str], obj: str) -> None:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
        except Exception:
            raise SoundEnvironmentError(f'This game needs "{obj}" to play sound, please install it')

    system = platform.system()
    if system == "Darwin":
        __checker(["afplay"], "afplay")
    elif system == "Linux":
        __checker(["aplay"], "aplay")
    elif system == "Windows":
        try:
            import winsound  # noqa: F401
        except Exception:
            raise SoundEnvironmentError(
                'This game needs "winsound" (Python standard lib) to play sound on Windows.'
            )
    else:
        raise RuntimeError("Unknown os")


def __playsound(paths: list[str], playtime):
    """
    播放音频
    :param paths: 需要播放的音频文件（绝对路径）
    :param playtime: 该参数无效
    """
    system = platform.system()

    # Windows: 使用 winsound，避免频繁启动 powershell 进程导致内存/句柄占用
    if system == "Windows":
        import winsound

        for path in paths:
            assert os.path.isabs(path), path
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME)
            except Exception:
                # 播放失败时忽略，避免影响游戏逻辑
                continue
        return

    # 其他平台仍然通过外部播放器播放
    for path in paths:
        assert os.path.isabs(path), path
        if system == "Darwin":
            cmd = ["afplay", path]
        elif system == "Linux":
            cmd = ["aplay", "-q", path]
        else:
            raise RuntimeError("Unknown os")

        subprocess.Popen(
            cmd,
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