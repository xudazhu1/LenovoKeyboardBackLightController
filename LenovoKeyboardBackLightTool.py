import sys
import os
import threading
import ctypes
from gc import enable

import win32gui
from PyQt5 import QtWidgets, QtGui, QtCore
import pystray
from PyQt5.QtCore import pyqtSlot
from adodbapi.apibase import changeNamedToQmark
from pystray import MenuItem as item, Menu
from PIL import Image
import winreg
import changeKeyBoardUtils
import config

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
        self.setWindowTitle("联想键盘背光控制器")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)
        self.setFixedSize(350, 200)
        # 设置窗口图标
        self.setWindowIcon(QtGui.QIcon("Icon.ico"))

        layout = QtWidgets.QGridLayout()

        # 状态标签
        self.status_label = QtWidgets.QLabel("当前背光亮度：未知")
        layout.addWidget(self.status_label, 2, 0, 1, 2)  # 第3行，占两列

        # 定时刷新传感器值
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_sensor_status)
        self.timer.start(1000)  # 每1秒刷新

        self.radio_buttons = []
        self.radio_group = QtWidgets.QButtonGroup(self)

        # 创建4个单选按钮
        for i in range(4):
            radio = QtWidgets.QRadioButton(buttons[i])
            self.radio_buttons.append(radio)
            self.radio_group.addButton(radio, i)
            layout.addWidget(radio, i // 2, i % 2)

        self.radio_group.buttonClicked[int].connect(set_mode)
        self.setLayout(layout)

        # 初始化当前模式
        self.update_ui(changeKeyBoardUtils.get_status())
        # 连接信号到槽
        self.show_window_signal.connect(self.show_and_raise)
        self.show_window_signal.connect(self.handle_button)
        self.show_window_signal.connect(self.slot_close)

    @pyqtSlot()
    def show_and_raise(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def update_sensor_status(self):
        if not (self.isVisible() and not self.isMinimized()):
            return
        try:
            value = changeKeyBoardUtils.get_status()
            self.status_label.setText(f"当前背光亮度：{buttons[value]}")
            # 更新radio的值
            self.radio_group.button(value).setChecked(True)


        except Exception as e:
            self.status_label.setText("读取失败")
            print("传感器读取异常:", e)

    def update_ui(self, mode: int):
        if 0 <= mode < 4:
            self.radio_buttons[mode].setChecked(True)

    @pyqtSlot()
    def handle_button(self, idx: int):
        # 兼容托盘菜单调用
        self.radio_buttons[idx].setChecked(True)
        set_mode(idx)

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


# 系统托盘逻辑
class PystrayTrayIcon:
    def __init__(self, window):
        self.window = window
        self.icon = None
        self.current_mode = changeKeyBoardUtils.get_status()
        self.startup_enabled = CONFIG["startup"]  # 这里你可以绑定配置的开机启动状态

        # 创建托盘图标的PIL Image，自己替换成你的icon路径即可
        self.icon_image = self.load_icon_image(changeKeyBoardUtils.get_dll_path("Icon.ico"))

        # 启动托盘线程
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def load_icon_image(self, icon_path):
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        # 默认画个蓝色方块代替
        from PIL import ImageDraw
        img = Image.new('RGBA', (64, 64), (0, 0, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle((16, 16, 48, 48), fill=(255, 255, 255, 255))
        return img

    def _run(self):
        menu = Menu(
            item(
                '打开主界面',
                self._show_window
            ),
            item(
                '开机自启动',
                self._toggle_startup,
                checked=lambda item: self.startup_enabled
            ),
            item(
                '-', None  # 分隔线
            ),
            # 模式菜单，动态生成4个菜单项，勾选当前模式
            *[
                item(
                    f"模式 {btn}",
                    self._make_select_mode_cb(i),
                    checked=lambda item, idx=i: idx == self.current_mode,
                    radio=True
                ) for i, btn in enumerate(buttons)
            ],
            item(
                '-', None
            ),
            item(
                '退出程序',
                self._exit_app
            )
        )

        self.icon = pystray.Icon("KeyboardBacklightController", self.icon_image, "键盘背光控制器", menu)
        self.icon.run()


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

    def _exit_app(self, icon, item):
        self.icon.stop()
        QtCore.QMetaObject.invokeMethod(
            self.window,
            "slot_close",
            QtCore.Qt.QueuedConnection
        )
        QtCore.QCoreApplication.quit()  # 退出 Qt 事件循环，结束程序


# 是否是开机启动静默模式
def is_silent_start():
    return "--silent" in sys.argv


def run_app():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    if not is_silent_start():
        window.show()

    tray = PystrayTrayIcon(window)
    # tray = TrayIcon(window)
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
    # 从配置文件运行默认背光模式
    if CONFIG["last_mode"]:
        changeKeyBoardUtils.set_status(CONFIG["last_mode"])
    run_app()
