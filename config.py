import json
import os
import sys


if getattr(sys, 'frozen', False):
    # 如果是 PyInstaller 打包后的程序
    exe_path = sys.executable
else:
    # 否则是脚本运行
    exe_path = os.path.abspath(__file__)

CONFIG_PATH = os.path.join(os.path.dirname(exe_path), "config.json")


def load_config():
    default_config = {
        "startup": False,
        "close_behavior": "ask",  # 可为 ask / exit / minimize
        "last_mode": "HIGH",
        "needRefreshDevice": False,  # 刷新声卡驱动 修复声卡异常的问题
        "refreshDevice": r"ACPI\VEN_TIAS&DEV_2781&SUBSYS_17AA38BE"  # 刷新声卡驱动 修复声卡异常的问题
    }
    if not os.path.exists(CONFIG_PATH):
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {**default_config, **config}
    except Exception as e:
        print(e)
        return default_config


def save_config(config: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")
