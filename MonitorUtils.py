import ctypes
from ctypes import wintypes
import win32con


# 定义 DISPLAY_DEVICE 结构
class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('DeviceName', wintypes.WCHAR * 32),
        ('DeviceString', wintypes.WCHAR * 128),
        ('StateFlags', wintypes.DWORD),
        ('DeviceID', wintypes.WCHAR * 128),
        ('DeviceKey', wintypes.WCHAR * 128),
    ]


# 获取主显示器适配器信息
def get_primary_monitor_adapter():
    i = 0
    user32 = ctypes.windll.user32
    while True:
        device = DISPLAY_DEVICE()
        device.cb = ctypes.sizeof(DISPLAY_DEVICE)

        if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(device), 0):
            break

        if device.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE:
            print(f"主显示器设备名: {device.DeviceName}")
            print(f"描述信息（显卡名）: {device.DeviceString}")
            print(f"设备ID: {device.DeviceID}")
            print(f"设备Key: {device.DeviceKey}")
            return {
                "Name": device.DeviceName,
                "Adapter": device.DeviceString,
                "DeviceID": device.DeviceID,
                "DeviceKey": device.DeviceKey,
            }

        i += 1


# 调用函数
info = get_primary_monitor_adapter()
