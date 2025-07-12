import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    default_config = {
        "startup": False,
        "close_behavior": "ask",  # 可为 ask / exit / minimize
        "last_mode": "HIGH"
    }
    if not os.path.exists(CONFIG_PATH):
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {**default_config, **config}
    except Exception:
        return default_config


def save_config(config: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")
