import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from PyQt5 import __file__ as pyqt5_file

handler = RotatingFileHandler("DimCalculator.log", maxBytes=1204*1024, backupCount=3)
logging.basicConfig(level=logging.ERROR,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[handler],
                    )

# 【本地运行 + 打包后 双兼容】
if getattr(sys, 'frozen', False):
    # 打包后：从exe临时目录找
    plugin_path = os.path.join(sys._MEIPASS, 'platforms')
else:
    # 本地运行：自动从PyQt5安装目录找
    plugin_path = os.path.join(os.path.dirname(pyqt5_file), 'Qt5', 'plugins', 'platforms')

# 强制设置插件路径
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

# 【关键修复】如果本地路径不存在，尝试另一个常见路径
if not os.path.exists(plugin_path):
    plugin_path = os.path.join(os.path.dirname(pyqt5_file), 'plugins', 'platforms')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

# 下面正常导入PyQt5
from PyQt5.QtWidgets import QApplication, QMessageBox
# from PyQt5.QtGui import QIcon
from gui import DimCalculatorGUI
# import ctypes

if __name__ == '__main__':
    try:
        # raise SyntaxError("111")
        app = QApplication(sys.argv)
        # ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('dimcalculator.ljx.v1.0')  # 设置窗口ID，确保任务栏图标正常显示
        # app.setWindowIcon(QIcon("icon.ico"))
        window = DimCalculatorGUI()  # todo: try
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(type(e).__name__ + ": " + str(e))
        try:
            # 检查是否已有 QApplication 实例
            app = QApplication.instance()
            if app is None:
                # 创建临时实例用于弹窗
                temp_app = QApplication(sys.argv)
                QMessageBox.critical(None, "程序崩溃", "错误日志已保存至 DimCalculator.log")
                temp_app.quit()
        except:
            pass
        sys.exit(-1)
