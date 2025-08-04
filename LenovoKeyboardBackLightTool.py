import sys
import os
import threading
import ctypes
import time
from gc import enable

import win32api
import win32con
import win32gui
from PyQt5 import QtWidgets, QtGui, QtCore
import pystray
from PyQt5.QtCore import pyqtSlot
from adodbapi.apibase import changeNamedToQmark
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from pystray import MenuItem as item, Menu
from PIL import Image
import winreg

import DisplayUtils
import changeKeyBoardUtils
import config
import deviceTools

APP_NAME = "KeyboardBacklightController"
EXE_PATH = os.path.realpath(sys.argv[0])

CONFIG = config.load_config()


# 设置开机启动
def set_startup(enable: bool):
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    command = f'"{EXE_PATH}" --silent'  # 添加 --silent 参数
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_ALL_ACCESS) as regkey:
        if enable:
            winreg.SetValueEx(regkey, APP_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(regkey, APP_NAME)
            except FileNotFoundError:
                pass
    print(f"设置开机启动: {enable}", )
    CONFIG["startup"] = enable
    config.save_config(CONFIG)


buttons = ['OFF', 'LOW', 'HIGH', 'AUTO']
display_mode = ['Optimus', 'NVIDIA']
performance_mode = ['节能', '智能', '野兽', '极客']


# 主窗口
def set_mode(idx: int):
    print(f"选择了模式 {buttons[idx]}")
    changeKeyBoardUtils.set_status(buttons[idx])
    # 设置之后 保存给配置文件
    CONFIG["last_mode"] = buttons[idx]
    config.save_config(CONFIG)


class MainWindow(QtWidgets.QWidget):
    show_window_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOGA PRO14s 至尊版配置器")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)
        self.setFixedSize(350, 200)
        # 设置窗口图标
        self.setWindowIcon(QtGui.QIcon("Icon.ico"))

        self.button_groups = {}
        main_layout = QtWidgets.QVBoxLayout()
        config = [
            ("显示模式", display_mode, current_display_mode_idx),
            ("键盘背光", buttons, current_mode_idx),
            ("性能模式", performance_mode, 2),
            # ("颜色深度", ["24 bit", "32 bit"], 1)
        ]
        for title, options, default_index in config:
            self.add_radio_group(main_layout, title, options, default_index)

        # self.radio_display_group.buttonClicked[int].connect(set_display_mode)
        self.setLayout(main_layout)

        # # 定时刷新传感器值
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_sensor_status)
        self.timer.start(1000)  # 每1秒刷新
        # 连接信号到槽
        self.show_window_signal.connect(self.show_and_raise)
        self.show_window_signal.connect(self.slot_close)

    def add_radio_group(self, layout, title, options, default_index=0):
        # 添加标题（单独一行）
        label = QtWidgets.QLabel(title)
        layout.addWidget(label)

        # 单独一行用于放 radio 按钮
        radio_layout = QtWidgets.QHBoxLayout()
        group = QtWidgets.QButtonGroup(self)
        self.button_groups[title] = group

        for i, text in enumerate(options):
            radio = QtWidgets.QRadioButton(text)
            group.addButton(radio, i)
            radio_layout.addWidget(radio)
            if i == default_index:
                radio.setChecked(True)

        group.buttonClicked.connect(lambda btn, t=title: self.on_radio_selected(t, btn.text()))
        layout.addLayout(radio_layout)

    def on_radio_selected(self, group_title, option_text):
        print(f"[{group_title}] 选中：{option_text}")
        if group_title == "显示模式":
            if option_text == "NVIDIA":
                DisplayUtils.switch_NVIDIA_LaunchGPU()
            else:
                DisplayUtils.switch_Optimus()
        if group_title == "键盘背光":
            changeKeyBoardUtils.set_status(option_text)
            # 设置之后 保存给配置文件
            CONFIG["last_mode"] = option_text
            config.save_config(CONFIG)

    def get_selected_option(self, group_title):
        group = self.button_groups.get(group_title)
        if group:
            checked = group.checkedButton()
            if checked:
                return checked.text()
        return None

    def set_selected_option(self, group_title, option_text):
        """
        程序设置指定组的选中按钮
        """
        group = self.button_groups.get(group_title)
        if not group:
            print(f"⚠️ 未找到分组：{group_title}")
            return False

        for button in group.buttons():
            if button.text() == option_text:
                button.setChecked(True)
                return True

        print(f"⚠️ 未找到选项：{option_text} in {group_title}")
        return False

    @pyqtSlot()
    def show_and_raise(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def update_sensor_status(self):
        if not (self.isVisible() and not self.isMinimized()):
            return
        try:
            refresh_mode()
            self.set_selected_option("键盘背光", buttons[current_mode_idx])
            self.set_selected_option("显示模式", current_display_mode)


        except Exception as e:
            self.status_label.setText("读取失败")
            print("传感器读取异常:", e)

    @pyqtSlot()
    def slot_close(self):
        self.close()

    def closeEvent(self, event):
        behavior = CONFIG.get("close_behavior", "ask")

        if behavior == "exit":
            event.accept()
        elif behavior == "minimize":
            event.ignore()
            self.hide()
        else:
            reply = QtWidgets.QMessageBox.question(
                self,
                "退出选项",
                "最小化到托盘？",
                QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Apply,
                QtWidgets.QMessageBox.Apply
            )
            if reply == QtWidgets.QMessageBox.Cancel:
                CONFIG["close_behavior"] = "exit"
                config.save_config(CONFIG)
                event.accept()
            else:
                CONFIG["close_behavior"] = "minimize"
                config.save_config(CONFIG)
                event.ignore()
                self.hide()


def is_tray_icon_actually_visible(tray_icon: QtWidgets.QSystemTrayIcon) -> bool:
    try:
        rect = tray_icon.geometry()
        return rect.isValid() and not rect.isNull()
    except Exception:
        return False


current_mode_idx = changeKeyBoardUtils.get_status()
current_display_mode = "Optimus"
current_display_mode_idx = 0
is_gpu = DisplayUtils.is_nvidia_gpu()
if is_gpu:
    current_display_mode = "NVIDIA"
    current_display_mode_idx = 1


def refresh_mode():
    global current_mode_idx
    global current_display_mode
    global current_display_mode_idx
    current_mode_idx = changeKeyBoardUtils.get_status()

    is_nvidia_gpu = DisplayUtils.is_nvidia_gpu()
    if is_nvidia_gpu:
        current_display_mode = "NVIDIA"
        current_display_mode_idx = 1
    else:
        current_display_mode = "Optimus"
        current_display_mode_idx = 0


# 系统托盘逻辑
class PystrayTrayIcon:
    def __init__(self, window):
        self.window = window
        self.icon = None

        self.startup_enabled = CONFIG["startup"]  # 这里你可以绑定配置的开机启动状态

        # 创建托盘图标的PIL Image，自己替换成你的icon路径即可
        self.icon_image = self.load_icon_image(changeKeyBoardUtils.get_dll_path("Icon.ico"))

        # 启动托盘线程
        self.icon = pystray.Icon("KeyboardBacklightController", self.icon_image, "键盘背光控制器")
        # self.icon.menu = self._build_menu  # 设置为方法（注意：不要加括号）
        self.icon.menu = Menu(self._build_menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def _build_menu(self):
        print("1213")
        # 每次右键点击时，重新构建菜单
        refresh_mode()
        return Menu(
            item('打开主界面', self._show_window),
            item('开机自启动', self._toggle_startup, checked=lambda item: self.startup_enabled),
            item('-', None),
            *[
                item(
                    f"模式 {btn}",
                    self._make_select_mode_cb(i),
                    checked=lambda item, idx=i: idx == current_mode_idx,
                    radio=True
                ) for i, btn in enumerate(buttons)
            ],
            item('-', None),
            *[
                item(
                    f"显卡 {btn}",
                    self._make_select_display_mode_cb(i),
                    checked=lambda item, idx=i: current_display_mode in item.text,
                    radio=True
                ) for i, btn in enumerate(display_mode)
            ],
            item('-', None),
            item('退出程序', self._exit_app)
        )

    def load_icon_image(self, icon_path):
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        # 默认画个蓝色方块代替
        from PIL import ImageDraw
        img = Image.new('RGBA', (64, 64), (0, 0, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle((16, 16, 48, 48), fill=(255, 255, 255, 255))
        return img

    def _show_window(self, icon, item):
        # 交给 Qt 主线程去显示窗口
        QtCore.QMetaObject.invokeMethod(self.window, "show_and_raise", QtCore.Qt.QueuedConnection)

    def _toggle_startup(self, icon, item):
        self.startup_enabled = not self.startup_enabled
        # 这里你需要调用之前的设置开机启动函数
        set_startup(self.startup_enabled)
        # 并保存配置文件
        # CONFIG["startup"] = self.startup_enabled
        # config.save_config(CONFIG)

        # 更新菜单勾选状态
        self.icon.update_menu()

    def _make_select_mode_cb(self, idx):
        def callback(icon, item):
            self.current_mode = idx
            # 通知主窗口切换模式 不用通知呗 主窗口自己获取值的时候判断
            # QtCore.QMetaObject.invokeMethod(
            #     self.window,
            #     "handle_button",
            #     QtCore.Qt.QueuedConnection,
            #     QtCore.Q_ARG(int, idx)
            # )
            # 调用设置状态函数
            changeKeyBoardUtils.set_status(buttons[idx])
            # 更新菜单勾选状态
            self.icon.update_menu()

        return callback

    def _make_select_display_mode_cb(self, idx):
        def callback(icon, item):
            self.current_mode = idx
            # 调用设置状态函数
            # win32api.MessageBox(0, display_mode[idx], "显卡模式", win32con.MB_OK)
            if display_mode[idx] == "Optimus":
                DisplayUtils.switch_Optimus()
            if display_mode[idx] == "NVIDIA":
                DisplayUtils.switch_NVIDIA_LaunchGPU()

            # 更新菜单勾选状态
            self.icon.update_menu()

        return callback

    def _exit_app(self, icon, item):
        self.icon.stop()
        QtCore.QMetaObject.invokeMethod(
            self.window,
            "slot_close",
            QtCore.Qt.QueuedConnection
        )
        QtCore.QCoreApplication.quit()  # 退出 Qt 事件循环，结束程序


class TrayIcon:
    def __init__(self, window):
        self.window = window
        self.startup_enabled = CONFIG["startup"]
        self.tray_icon = QSystemTrayIcon(QtGui.QIcon(changeKeyBoardUtils.get_dll_path("Icon.ico")), window)
        self.menu = QMenu()
        self.build_menu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("键盘背光控制器")
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def build_menu(self):
        self.menu.clear()
        # 刷新传感器的值
        refresh_mode()
        # 打开主界面
        open_action = QAction("打开主界面", self.menu)
        open_action.triggered.connect(self.window.show)
        self.menu.addAction(open_action)

        # 开机自启动
        self.startup_action = QAction("开机自启动", self.menu, checkable=True)
        self.startup_action.setChecked(self.startup_enabled)
        self.startup_action.triggered.connect(self.toggle_startup)
        self.menu.addAction(self.startup_action)

        self.menu.addSeparator()

        # 模式选择（radio）
        self.mode_group = []
        for i, btn in enumerate(buttons):
            action = QAction(f"模式 {btn}", self.menu, checkable=True)
            action.setChecked(i == current_mode_idx)
            action.triggered.connect(self.make_select_mode_cb(i))
            self.menu.addAction(action)
            self.mode_group.append(action)

        self.menu.addSeparator()

        # 显卡模式选择（radio）
        self.display_mode_group = []
        for i, btn in enumerate(display_mode):
            action = QAction(f"显卡 {btn}", self.menu, checkable=True)
            action.setChecked(btn in current_display_mode)
            action.triggered.connect(self.make_select_display_mode_cb(i))
            self.menu.addAction(action)
            self.display_mode_group.append(action)

        self.menu.addSeparator()

        # 退出程序
        exit_action = QAction("退出程序", self.menu)
        exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(exit_action)

    def toggle_startup(self):
        self.startup_enabled = not self.startup_enabled
        CONFIG["startup"] = self.startup_enabled
        self.startup_action.setChecked(self.startup_enabled)
        set_startup(self.startup_enabled)
        config.save_config(CONFIG)

    def make_select_mode_cb(self, idx):
        def cb():
            global current_mode_idx
            current_mode_idx = idx
            set_mode(idx)
            self.build_menu()  # 刷新菜单以更新勾选状态
        return cb

    def make_select_display_mode_cb(self, idx):
        def cb():
            global current_display_mode
            current_display_mode = display_mode[idx]
            # set_display_mode(idx)
            if current_display_mode == "Optimus":
                DisplayUtils.switch_Optimus()
            else:
                DisplayUtils.switch_NVIDIA_LaunchGPU()
            self.build_menu()
        return cb

    def exit_app(self):
        QtWidgets.qApp.quit()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Context:
            self.build_menu()
        elif reason == QSystemTrayIcon.Trigger:
            self.window.show()


# 是否是开机启动静默模式
def is_silent_start():
    return "--silent" in sys.argv


def run_app():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    if not is_silent_start():
        window.show()

    # tray = PystrayTrayIcon(window)
    tray = TrayIcon(window)
    tray.backlight_on = True  # 默认初始状态
    # tray.show()

    sys.exit(app.exec_())


# 打包命令 进入python目录
# cd .\venv\Scripts\
# 打包成exe
# pyinstaller --noconfirm --noconsole --icon=../../Icon.ico --add-data "../../Icon.ico;." ../../LenovoKeyboardBackLightTool.py
if __name__ == "__main__":
    # # 第一次运行时可启用自动启动
    if CONFIG["startup"]:
        set_startup(True)

    # # 如果要求刷新某设备
    # print(CONFIG)
    # if CONFIG["needRefreshDevice"]:
    #     deviceTools.disable_enable_device(CONFIG["refreshDevice"])
    # 从配置文件运行默认背光模式
    if CONFIG["last_mode"]:
        changeKeyBoardUtils.set_status(CONFIG["last_mode"])
    run_app()
