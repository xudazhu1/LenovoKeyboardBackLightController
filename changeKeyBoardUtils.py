import clr
import sys
import os
import pythoncom
import System
import config

from System import String
from System.Reflection import BindingFlags


def get_base_path():
    if getattr(sys, 'frozen', False):  # 打包后
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_dll_path(*relative_parts):
    base = get_base_path()
    return os.path.join(base, *relative_parts)


# 加载 DLL
dll_path = get_dll_path("dll", "SmartEngine", "1.0.70.10091", "Views", "UIKeypadBacklight.dll")


# dll_path = r"D:\project\PyLenovoKeyboard\dll\SmartEngine\1.0.70.10091\Views\UIKeypadBacklight.dll"


def set_status(str_status):
    # 初始化为 STA 模式
    pythoncom.CoInitialize()  # 必须加！
    clr.AddReference(dll_path)

    # 获取类型
    from UIKeypadBacklight import UCKeypadBacklight

    # 获取单例对象：UCKeypadBacklight.Instance
    instance = UCKeypadBacklight.get_Instance()

    # 获取私有字段 "KbdBackLightVM"
    field_info = instance.GetType().GetField(
        "KbdBackLightVM",
        BindingFlags.NonPublic | BindingFlags.Instance
    )

    kbdBackLightVM = field_info.GetValue(instance)

    # 调用 SetKbdledMode("HIGH") KbdBackLightModel.EnumKbdBackLightStatus
    enum_type_str = "UIKeypadBacklight.Model.KbdBackLightModel+EnumKbdBackLightStatus, UIKeypadBacklight"
    enum_type = System.Type.GetType(enum_type_str)
    # mode_new = System.Enum.Parse(enum_type, "HIGH")
    # mode_new = System.Enum.Parse(enum_type, "LOW")
    # mode_new = System.Enum.Parse(enum_type, "OFF")
    mode_new = System.Enum.Parse(enum_type, str_status)

    result = kbdBackLightVM.SetKbdledMode(mode_new)
    print(f"SetKbdledMode 返回值: {result}")

    # 可选：调用 GetPluginStatus 方法
    get_plugin_status = instance.GetType().GetMethod("GetPluginStatus")
    status = get_plugin_status.Invoke(instance, None)
    print(f"插件状态: {status}")
    return status


def get_status():
    # 初始化为 STA 模式
    pythoncom.CoInitialize()  # 必须加！
    clr.AddReference(dll_path)

    # 获取类型
    from UIKeypadBacklight import UCKeypadBacklight

    # 获取单例对象：UCKeypadBacklight.Instance
    instance = UCKeypadBacklight.get_Instance()

    # 可选：调用 GetPluginStatus 方法
    get_plugin_status = instance.GetType().GetMethod("GetPluginStatus")
    status = get_plugin_status.Invoke(instance, None)
    print(f"插件状态: {status}")
    return int(status) - 1
