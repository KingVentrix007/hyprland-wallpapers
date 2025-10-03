import os
import subprocess
import filetype
import json
import signal

# Store wallpaper processes here: {screen_name: {"path": str, "pid": int, "type": str}}
screen_wallpapers = {}

def run_command(command):
    run_cmd = []
    if isinstance(command, str):
        run_cmd = command.split(" ")
    else:
        run_cmd = command

    process = subprocess.Popen(run_cmd)
    return process

def detect_media_type(path: str) -> str:
    """
    Detect if a file is an image, gif, video, or other.
    Returns: "image", "gif", "video", or "other"
    """
    kind = filetype.guess(path)

    if kind is None:
        return "other"

    mime = kind.mime.lower()

    if mime.startswith("image/"):
        if mime == "image/gif":
            return "gif"
        return "image"

    if mime.startswith("video/"):
        return "video"

    return "other"

def stop_wallpaper(screen_name: str):
    """Stop wallpaper process for a given screen if it exists."""
    global screen_wallpapers
    if screen_name in screen_wallpapers:
        pid = screen_wallpapers[screen_name]["pid"]
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        del screen_wallpapers[screen_name]

def set_video_wallpaper(path=None, screen_name=None):
    if not path or not os.path.exists(path):
        return -1
    if not screen_name:
        return -1

    stop_wallpaper(screen_name)  # Kill any existing wallpaper for that screen

    if screen_name == "ALL":
        process = run_command(["mpvpaper", "-o", "--loop", path])
    else:
        process = run_command(["mpvpaper", "-o", "--loop", screen_name, path])

    # Save process info
    screen_wallpapers[screen_name] = {
        "path": path,
        "pid": process.pid,
        "type": "video"
    }
    return 0

def set_static_wallpaper(path=None, screen_name=None):
    if not path or not os.path.exists(path):
        return -1
    if not screen_name:
        return -1

    stop_wallpaper(screen_name)

    if screen_name == "ALL":
        process = run_command(["swww", "img", path])
    else:
        process = run_command(["swww", "img", "-o", screen_name, path])

    # Save process info (note: swww usually daemonizes, may not keep process.pid)
    screen_wallpapers[screen_name] = {
        "path": path,
        "pid": process.pid,
        "type": "image"
    }
    return 0

def validate_screen(screen):
    command = ["hyprctl","monitors","-j"]
    result = subprocess.run(command, capture_output=True, text=True)
    json_data = json.loads(result.stdout)
    for mon in json_data:
        if(mon.get("name",None) == screen):
            return 0
    return -1

def set_wallpaper(path,screen):
    if not path or not os.path.exists(path):
        return -1
    if validate_screen(screen) != 0:
        return -1
    file_type = detect_media_type(path)
    if file_type == "image":
        return set_static_wallpaper(path,screen)
    elif file_type in ("video", "gif"):
        return set_video_wallpaper(path,screen)
    else:
        return -1
