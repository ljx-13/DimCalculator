import sys
import os
from PyQt5 import __file__ as pyqt5_file

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
from PyQt5.QtWidgets import QApplication
from gui import DimCalculatorGUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DimCalculatorGUI()  # todo: try
    window.show()
    sys.exit(app.exec_())
