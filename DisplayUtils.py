import subprocess
import os
import sys
import time
import csv
import tempfile

import psutil

import MonitorUtils

# 指定 exe 所在目录和文件名
exe_path = r"D:\winTools\lenovoKeyboardTools\LaunchGPU.exe"
tool_path = r"D:\winTools\lenovoKeyboardTools\MultiMonitorTool.exe"  # 改为你的路径

if getattr(sys, 'frozen', False):
    # 如果是 PyInstaller 打包后的程序
    exe_path = os.path.join(os.path.dirname(sys.executable), "LaunchGPU.exe")
    tool_path = os.path.join(os.path.dirname(tool_path), "MultiMonitorTool.exe")


# CONFIG_PATH = os.path.join(os.path.dirname(exe_path), "LaunchGPU.exe")


# 方法 1：直接运行（最常用）
def switch_NVIDIA_LaunchGPU():
    subprocess.Popen(exe_path)


def get_all_monitors(multimonitor_tool_path: str):
    # 创建临时 CSV 文件
    temp_csv = os.path.join(tempfile.gettempdir(), "monitors.csv")

    # 执行 MultiMonitorTool 导出命令
    try:
        subprocess.run(
            [multimonitor_tool_path, "/scomma", temp_csv],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print("❌ 执行 MultiMonitorTool 失败，请检查路径或权限。")
        return []

    # 读取 CSV 文件
    monitors = []
    with open(temp_csv, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            monitors.append({k.strip(): v.strip() for k, v in row.items()})

    # 删除临时文件（可选）
    os.remove(temp_csv)

    return monitors


def get_primary_display():
    return MonitorUtils.get_primary_monitor_adapter()


def get_primary_display_old():
    monitors = get_all_monitors(tool_path)

    if not monitors:
        print("未获取到任何显示器信息")
        exit()

    # 主显示器
    primary = next((m for m in monitors if m.get("Primary", "").lower() == "yes"), None)
    if primary:
        return primary
    return None


def is_nvidia_gpu():
    monitors = get_primary_display()
    # 获取 主显示器的显卡
    print(monitors["Adapter"])
    if "NVIDIA" in monitors["Adapter"]:
        return True
    return False


# 示例调用
def diable_now_display():
    # 主显示器
    primary = get_primary_display()
    if primary:
        print("⭐ 主显示器:")
        # 使用Name禁用独显显示器 系统会自动切换回集成显卡
        subprocess.run([tool_path, "/disable", primary["Name"]])
        # for key, val in primary.items():
        #     print(f"  {key}: {val}")
    else:
        print("⚠️ 未找到主显示器")


# if __name__ == "__main__":
# switch_Optimus()
# switch_NVIDIA_LaunchGPU()

# 方法 2：如果需要指定工作目录
# subprocess.Popen(["your_program.exe"], cwd=r"C:\Path\To\YourApp")

def switch_Optimus():
    # 先切换回核显,
    # 获取显示器 ID 列表：可通过 `MultiMonitorTool.exe /scomma out.csv` 看到编号
    # 示例：关闭显示器 2，打开显示器 1
    # subprocess.run([tool_path, "/disable", "2"])
    diable_now_display()
    # 再结束所有 LaunchGPU.exe 的进程
    target_name = "LaunchGPU.exe"
    time.sleep(1)
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == target_name.lower():
                print(f"Terminating PID {proc.pid} - {proc.info['name']}")
                proc.terminate()
                proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


