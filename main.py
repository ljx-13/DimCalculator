DEBUG = False
if DEBUG:
    import cProfile
    import pstats
    from pstats import SortKey
    profiler = cProfile.Profile()
    profiler.enable()

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
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
# from PyQt5.QtGui import QIcon
# import ctypes

if __name__ == '__main__':
    try:
        # raise SyntaxError("111")
        app = QApplication(sys.argv)
        # 创建启动画面
        from PyQt5.QtGui import QPainter, QColor, QPixmap, QFont, QPixmap
        splash_pixmap = QPixmap(400, 300)
        splash_pixmap.fill(Qt.white)
        painter = QPainter(splash_pixmap)
        painter.setPen(QColor(0, 120, 215))
        painter.setFont(QFont("Microsoft YaHei", 24))
        painter.drawText(splash_pixmap.rect(), Qt.AlignCenter, "DimCalculator")
        painter.end()
        splash = QSplashScreen(splash_pixmap)
        splash.show()
        # 延迟加载主窗口
        def load_main_window():
            from gui import DimCalculatorGUI
            window = DimCalculatorGUI()
            window.show()
            splash.finish(window)
        QTimer.singleShot(0, load_main_window)
        # window = DimCalculatorGUI()
        # window.show()
        if DEBUG:
            profiler.disable()
            profiler.dump_stats('startup_profile.prof')
            # 打印前20个最耗时的函数
            stats = pstats.Stats(profiler)
            stats.sort_stats(SortKey.CUMULATIVE)
            stats.print_stats(20)
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
