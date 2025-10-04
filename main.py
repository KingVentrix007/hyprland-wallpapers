# wallpaper_gui.py (headless daemon update)
import time
import os
import sys
import json
import subprocess
import tempfile
import asyncio
import GPUtil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QComboBox, QHBoxLayout, QScrollArea,QRadioButton,QAbstractItemView
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QSize, Qt

import system_interface  # your backend

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CONFIG_FILE = os.path.expanduser("~/.config/hypr_wallpapers.json")
SUPPORTED_IMAGE_EXT = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
SUPPORTED_VIDEO_EXT = [".mp4", ".mkv", ".mov", ".webm"]

multi_papers = {} # screen_name: {current_paper:0,papers:[]}

def get_monitors():
    """Fetch monitors via hyprctl."""
    result = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True)
    try:
        return [mon["name"] for mon in json.loads(result.stdout)]
    except Exception:
        return []


def generate_video_thumbnail(path, size=(200, 200)):
    """Generate a thumbnail for video using ffmpeg."""
    thumb_path = os.path.join(tempfile.gettempdir(), f"thumb_{os.path.basename(path)}.jpg")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ss", "00:00:01", "-vframes", "1", "-vf",
             f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease",
             thumb_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return thumb_path if os.path.exists(thumb_path) else None
    except Exception:
        return None


def save_wallpaper_config(wallpapers: dict):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(wallpapers, f, indent=2)


def load_wallpaper_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


is_multi_paper = False
global_multi_papers = None
sleep_time = 30
async def cycle_papers():
    # global global_multi_papers
    while True:
        apply_wallpapers(global_multi_papers)
        await asyncio.sleep(sleep_time)
        gpus = GPUtil.getGPUs()
        gpu = gpus[0]
        if((gpu.load * 100) >= 90):
            subprocess.run(["pkill", "mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Cycle")
def apply_wallpapers(wallpapers):
    global is_multi_paper,global_multi_papers
    """Apply wallpapers to all monitors in the dict."""
    # Kill any existing mpv processes first
    
    global_multi_papers = wallpapers
    for monitor, path in wallpapers.items():
        if(type(path) == dict):
            is_multi_paper = True
            paper_num = path.get("current_paper",0)
            paper_list = path.get("papers",[])
            path_to_use = paper_list[paper_num]
            if(paper_num-1 >= 0):
                current_paper = paper_list[paper_num-1]
            else:
                current_paper = paper_list[len(paper_list)-1]
            if(paper_num+1 > len(paper_list)-1):
                paper_num = 0
                wallpapers[monitor]["current_paper"] = paper_num

            else:
                paper_num+=1
                wallpapers[monitor]["current_paper"] = paper_num
            # if(system_interface.detect_media_type(current_paper) != "image"):
            #     subprocess.run(["swww", "img"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            #     subprocess.run(["pkill", "mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            system_interface.set_wallpaper(path_to_use, monitor)
        

        else:
            system_interface.set_wallpaper(path, monitor)


class ConfigHandler(FileSystemEventHandler):
    """Watchdog handler for config changes."""
    def on_modified(self, event):
        if event.src_path == CONFIG_FILE:
            wallpapers = load_wallpaper_config()
            apply_wallpapers(wallpapers)


async def run_headless_daemon():
    """Run wallpaper daemon that watches config changes."""
    subprocess.run(["pkill", "mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Apply immediately at startup
    wallpapers = load_wallpaper_config()
    apply_wallpapers(wallpapers)

    # Set up watchdog observer
    event_handler = ConfigHandler()
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname(CONFIG_FILE), recursive=False)
    observer.start()
    print("Wallpaper daemon running. Watching config for changes...")
    if(is_multi_paper == True):

        await cycle_papers()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# --- GUI part remains mostly unchanged ---
class WallpaperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hyprland Wallpaper Manager")
        self.resize(1200, 700)

        self.monitors = get_monitors()
        self.folder = None
        self.wallpaper_config = load_wallpaper_config()

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Top bar with folder chooser + monitor selector
        top_bar = QHBoxLayout()
        self.folder_btn = QPushButton("📂 Choose Folder")
        self.folder_btn.clicked.connect(self.choose_folder)
        top_bar.addWidget(self.folder_btn)

        self.monitor_selector = QComboBox()
        self.monitor_selector.addItems(self.monitors if self.monitors else ["No Monitors Found"])
        top_bar.addWidget(QLabel("🖥️ Monitor:"))
        top_bar.addWidget(self.monitor_selector)

        self.use_multiple_button = QPushButton("Single Paper")
        self.use_multiple_button.clicked.connect(self.set_select_mode)
        self.select_mode = 1 # 1: 1 paper, 2: Multiple papers

        # top_bar.addWidget(QLabel("Multiple Papers: "))
        top_bar.addWidget(self.use_multiple_button)



        # self.
        main_layout.addLayout(top_bar)

        # Scroll area for wallpapers
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.file_list = QListWidget()
        self.file_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.file_list.setIconSize(QSize(220, 220))
        self.file_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.file_list.setSpacing(15)
        self.scroll.setWidget(self.file_list)
        main_layout.addWidget(self.scroll)

        # Apply button
        self.apply_btn = QPushButton("🎨 Apply Wallpaper")
        self.apply_btn.clicked.connect(self.apply_wallpaper)
        self.apply_btn.setFixedHeight(45)
        main_layout.addWidget(self.apply_btn)

        # Dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #f0f0f0;
                font-size: 15px;
            }
            QPushButton {
                background-color: #3a3a5c;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #505080;
            }
            QListWidget {
                background-color: #252538;
                border-radius: 10px;
                padding: 10px;
            }
            QComboBox {
                background-color: #3a3a5c;
                border-radius: 6px;
                padding: 6px;
            }
             QRadioButton {
                background-color: #3a3a5c;
                border: none;
                
            }
        """)

    def set_select_mode(self):
        if(self.select_mode == 1):
            self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            self.select_mode = 2
            self.use_multiple_button.setText("Multiple Papers")
        elif(self.select_mode == 2):
            self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.select_mode = 1
            self.use_multiple_button.setText("Single Paper")
        else:
             self.use_multiple_button.setText("Single WHAT")
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Wallpaper Folder")
        if not folder:
            return
        self.folder = folder
        self.populate_files()

    def populate_files(self):
        """Load all images and videos from folder into list widget with thumbnails."""
        self.file_list.clear()
        for file in os.listdir(self.folder):
            path = os.path.join(self.folder, file)
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_IMAGE_EXT + SUPPORTED_VIDEO_EXT:
                item = QListWidgetItem(file)

                if ext in SUPPORTED_IMAGE_EXT:
                    pixmap = QPixmap(path).scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                    item.setIcon(QIcon(pixmap))
                else:
                    thumb = generate_video_thumbnail(path)
                    if thumb:
                        pixmap = QPixmap(thumb).scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                                       Qt.TransformationMode.SmoothTransformation)
                        item.setIcon(QIcon(pixmap))
                    else:
                        item.setIcon(QIcon.fromTheme("video-x-generic"))

                item.setData(256, path)  # store path in UserRole
                self.file_list.addItem(item)

    def apply_wallpaper(self):
        if(self.select_mode == 1):
            selected_item = self.file_list.currentItem()
            if not selected_item:
                QMessageBox.warning(self, "No selection", "Please select a file first.")
                return

            file_path = selected_item.data(256)
            monitor = self.monitor_selector.currentText()

            result = system_interface.set_wallpaper(file_path, monitor)
            if result == 0:
                # Save to config
                self.wallpaper_config[monitor] = file_path
                save_wallpaper_config(self.wallpaper_config)
                QMessageBox.information(self, "Success", f"Wallpaper set for {monitor}!")
            else:
                QMessageBox.critical(self, "Error", "Failed to set wallpaper.")
        else:
            selected_items = self.file_list.selectedItems()
            selected_file_paths = []
            for item in selected_items:
                file_path = item.data(256)
                selected_file_paths.append(file_path)
            monitor = self.monitor_selector.currentText()
            self.wallpaper_config[monitor] = {"current_paper":0,"papers":selected_file_paths,"sleep_time":60}
            apply_wallpapers(self.wallpaper_config)
            # self.wallpaper_config[monitor] = {"current_paper":0,"papers":selected_file_paths}
            
            save_wallpaper_config(self.wallpaper_config)


                



def main():
    if "--no-ui" in sys.argv:
        # Run async headless daemon
        asyncio.run(run_headless_daemon())
        return

    app = QApplication(sys.argv)
    win = WallpaperApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
