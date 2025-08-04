import sys

import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import time
import os

import changeKeyBoardUtils
import config
import deviceTools

# DEVICE_ID = "HDAUDIO\\FUNC_01&VEN_10EC&DEV_0298&SUBSYS_10280579"
# DEVCON_PATH = r"C:\Tools\devcon.exe"
if getattr(sys, 'frozen', False):
    # 如果是 PyInstaller 打包后的程序
    exe_path = sys.executable
else:
    # 否则是脚本运行
    exe_path = os.path.abspath(__file__)
DEVCON_PATH = os.path.join(exe_path, "devcon.exe")


if __name__ == '__main__':
    CONFIG = config.load_config()
    print(DEVCON_PATH)
    print(CONFIG)
    print("尝试重启声卡！！！")
    deviceTools.disable_enable_device(CONFIG["refreshDevice"])
    # 从配置文件运行默认背光模式
    if CONFIG["last_mode"]:
        changeKeyBoardUtils.set_status(CONFIG["last_mode"])
