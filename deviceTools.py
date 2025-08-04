import os
import subprocess
import sys
import time

# DEVICE_ID = "ACPI\VEN_TIAS&DEV_2781&SUBSYS_17AA38BE"
if getattr(sys, 'frozen', False):
    # 如果是 PyInstaller 打包后的程序
    exe_path = sys.executable
else:
    # 否则是脚本运行
    exe_path = os.path.abspath(__file__)

DEVCON_PATH = os.path.join(os.path.dirname(exe_path), "devcon.exe")
# DEVCON_PATH = r"C:\Users\xudaz\AppData\Roaming\DevCon\devcon.exe"  # 修改为你的实际路径
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒



def get_device_status(device_id):
    try:
        result = subprocess.run(
            [DEVCON_PATH, "status", device_id],
            capture_output=True, text=True, check=True
        )
        output = result.stdout.lower()
        if "disabled" in output:
            return "disabled"
        elif "running" in output or "started" in output:
            return "enabled"
        else:
            return "unknown"
    except subprocess.CalledProcessError as e:
        print(f"[!] 获取设备状态失败: {e}")
        return "error"


def set_device_state(device_id, target_state):
    for attempt in range(MAX_RETRIES):
        print(f"[{attempt+1}/{MAX_RETRIES}] 设置设备为 {target_state} 中...")
        try:
            if target_state == "disable":
                subprocess.run([DEVCON_PATH, "disable", device_id], check=True)
            else:
                subprocess.run([DEVCON_PATH, "enable", device_id], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[!] 操作失败: {e}")

        time.sleep(RETRY_DELAY)

        current_state = get_device_status(device_id)
        print(f"    当前状态: {current_state}")

        if (target_state == "disable" and current_state == "disabled") or \
           (target_state == "enable" and current_state == "enabled"):
            print("    ✅ 状态设置成功")
            return True
        else:
            print("    ⚠️ 状态未达到预期，重试中...")

    print(f"❌ 最多重试 {MAX_RETRIES} 次仍失败。")
    return False


def disable_enable_device(device_id):
    print("=== 禁用设备 ===")
    if not set_device_state(device_id, "disable"):
        print("[X] 禁用失败，终止流程")
        return

    time.sleep(1)

    print("=== 启用设备 ===")
    if not set_device_state(device_id, "enable"):
        print("[X] 启用失败")
    else:
        print("[√] 启用成功")


if __name__ == "__main__":
    disable_enable_device(r"ACPI\VEN_TIAS&DEV_2781&SUBSYS_17AA38BE")
