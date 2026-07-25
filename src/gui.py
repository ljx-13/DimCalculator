import json
import os
import traceback
from functools import wraps
import logging

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMainWindow, QLineEdit, QLabel, QHBoxLayout, QGridLayout, QPushButton, \
    QTabWidget, QTextEdit, QMessageBox, QApplication, QDialog, QAction, QTextBrowser, QScrollArea
# from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer

from .core import DimCalculatorCore

def catch_exceptions(msg=""):
    """捕获函数中的异常，弹出错误窗口并记录日志"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                logging.critical(error_msg)
                QMessageBox.critical(None, "程序崩溃", msg + "\n错误日志已保存至 log/DimCalculator.log")
                return None
        return wrapper
    return decorator

class DimCalculatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.core = DimCalculatorCore()
        self.is_convert_mode = False
        self.unit_buttons = []
        self.const_buttons = []
        self.func_buttons = []
        self.panel_cols = 3  # 右侧面板共用列数
        self.initUI()
        QTimer.singleShot(100, self.update_button_layout)

    @catch_exceptions("初始化窗口时崩溃")
    def initUI(self):  # todo: init外定义
        self.setWindowTitle("DimCalculator - 智能量纲计算器")
        self.setMinimumSize(800, 750)
        # self.setMaximumWidth(1250)
        self.setWindowIcon(QIcon("datas/icon.ico"))
        self.setStyleSheet("""
            QMainWindow { background-color: #f3f3f3; }
            QMenuBar {
                background-color: #f3f3f3;
                border: none;
                color: #333;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QLineEdit#exprEdit {
                font-size: 20px;
                color: #505050;
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
            }
            QLabel#resultLabel {
                font-size: 40px;
                font-weight: bold;
                color: #000000;
                padding: 10px;
            }
            QPushButton {
                font-size: 25px;
                font-weight: 500;
                border-radius: 30px;
                background-color: #ffffff;
                border: 1px solid #dddddd;
                min-width: 60px;
                min-height: 60px;
            }
            QPushButton:hover { background-color: #e6e6e6; }
            QPushButton:pressed { background-color: #cccccc; }
            QPushButton#opBtn:checked {background-color: #cccccc;  /* 和数字按钮按下的灰色完全一致 */}
            QPushButton#opBtn { background-color: #f0f0f0; font-weight: bold; color: #0078d7; }
            QPushButton#unitBtn { background-color: #f9f9f9; font-size: 20px; }
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
                border: 1px solid #dddddd;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QTextEdit { border-radius: 8px; border: 1px solid #dddddd; background-color: #ffffff; font-size: 14px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 可编辑的表达式输入框
        self.expr_edit = QLineEdit()
        self.expr_edit.setObjectName("exprEdit")
        self.expr_edit.setPlaceholderText("例如 3m+5km 或 sin(30°)")
        self.expr_edit.returnPressed.connect(self.calculate)  # 回车直接计算
        main_layout.addWidget(self.expr_edit)

        # 结果显示  todo: copy
        self.result_label = QLabel("结果")
        self.result_label.setObjectName("resultLabel")
        self.result_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.result_label)

        # 主内容区域（左右分栏）
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # 左侧：数字与运算符网格
        left_widget = QWidget()
        left_grid = QGridLayout()
        left_grid.setSpacing(8)
        buttons = [
            ('单位转换', 0, 0, True, '将结果转换到目标单位'), ('(', 0, 1, True, ''), (')', 0, 2, True, ''), ('⌫', 0, 3, True, '退格'),
            ('CE', 1, 0, True, '清除输入'), ('∧', 1, 1, True, '幂运算'), ('√', 1, 2, True, '平方根'), ('÷', 1, 3, True, ''),
            ('7', 2, 0, False, ''), ('8', 2, 1, False, ''), ('9', 2, 2, False, ''), ('×', 2, 3, True, ''),
            ('4', 3, 0, False, ''), ('5', 3, 1, False, ''), ('6', 3, 2, False, ''), ('-', 3, 3, True, ''),
            ('1', 4, 0, False, ''), ('2', 4, 1, False, ''), ('3', 4, 2, False, ''), ('+', 4, 3, True, ''),
            ('ans', 5, 0, True, '插入上一次计算结果'), ('0', 5, 1, False, ''), ('.', 5, 2, False, ''), ('=', 5, 3, True, ''),
        ]
        for text, row, col, is_op, tip in buttons:
            btn = QPushButton(text)
            if text == "单位转换":
                btn.setCheckable(True)
            if is_op:
                btn.setObjectName("opBtn")
            if text == '=':
                btn.setStyleSheet("background-color: #0078d7; color: white;")
            btn.setToolTip(tip)
            btn.clicked.connect(self.on_button_clicked)
            left_grid.addWidget(btn, row, col)
        left_widget.setLayout(left_grid)
        left_widget.setMaximumWidth(600)
        left_widget.setMaximumHeight(800)

        # 右侧面板（单位、常数、函数）
        right_tabs = QTabWidget()
        right_tabs.setTabPosition(QTabWidget.North)

        @catch_exceptions("处理单位输入时崩溃")
        def handle_unit_click(symbol, name=None):
            if self.is_convert_mode:
                # 处于转换模式：执行单位转换
                if self.is_convert_mode:
                    converted_result, error = self.core.convert_unit(symbol)
                    if error:
                        self.result_label.setText("转换错误")
                        self.info_text.setText(error)
                    else:
                        self.result_label.setText(converted_result)
                        # 退出转换模式，恢复按钮状态
                        self.is_convert_mode = False
                        # 找到“单位转换”按钮并弹起
                        for btn in self.findChildren(QPushButton):
                            if btn.text() == "单位转换":
                                btn.setChecked(False)
                                break
            else:
                # 非转换模式：正常插入单位符号
                self.expr_edit.insert(symbol)

        @catch_exceptions("处理常数输入时崩溃")
        def handle_const_click(symbol, name):
            if name.startswith("_"):
                self.expr_edit.insert("_" + symbol)
            else:
                self.expr_edit.insert(symbol)

        @catch_exceptions("处理函数输入时崩溃")
        def handle_func_click(symbol, name):
            self.expr_edit.insert(name + "(")

        # 单位面板
        unit_widget, self.unit_layout, self.unit_buttons = self._create_buttons_from_items(
            self.core.units, lambda item: item[3], handle_unit_click
        )
        scroll = QScrollArea()
        scroll.setWidget(unit_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        right_tabs.addTab(scroll, "单位")

        # 常数面板
        const_widget, self.const_layout, self.const_buttons = self._create_buttons_from_items(
            self.core.consts, lambda item: True, handle_const_click
        )
        scroll = QScrollArea()
        scroll.setWidget(const_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        right_tabs.addTab(scroll, "常数")

        # 函数面板
        func_data = [  # （名字，描述，符号）
            ("sin", "正弦函数", "sin"), ("cos", "余弦函数", "cos"), ("tan", "正切函数", "tan"),
            # ("csc", "余割函数(1/sin)", "csc"), ("sec", "正割函数(1/cos)", "sec"), ("cot", "余切函数(1/tan)", "cot"),
            ("asin", "反正弦", "asin"), ("acos", "反余弦", "acos"), ("atan", "反正切", "atan"),
            ("log", "log(真数, 底数)", "log"), ("lg", "常用对数", "lg"), ("ln", "自然对数", "ln"),
            ("abs", "绝对值", "|x|"),
        ]
        func_widget, self.func_layout, self.func_buttons = self._create_buttons_from_items(
            func_data, lambda item: True, handle_func_click
        )
        scroll = QScrollArea()
        scroll.setWidget(func_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        right_tabs.addTab(scroll, "函数")

        content_layout.addWidget(left_widget, 3)
        content_layout.addWidget(right_tabs, 2)
        main_layout.addLayout(content_layout)

        # 诊断/步骤信息区
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(300)
        main_layout.addWidget(self.info_text)

        # 历史记录按钮
        hist_btn = QPushButton("历史记录")
        hist_btn.setObjectName("opBtn")
        hist_btn.clicked.connect(self.show_history)
        main_layout.addWidget(hist_btn)

        self._create_menubar()

        self.resize(800, 750)

    @catch_exceptions("创建按钮面板时崩溃")
    def _create_buttons_from_items(self, items, filter_func, click_handler, cols=3):
        """
        从数据列表生成按钮面板
        :param items: 数据列表（名字，描述，符号）
        :param filter_func: 过滤函数，返回 True 表示显示
        :param click_handler: 点击处理函数，接收 (symbol, name)
        :param cols: 列数
        :return: (widget, layout, buttons)
        """
        widget = QWidget()
        layout = QGridLayout(widget)
        buttons = []
        row, col = 0, 0

        for item in items:
            if not filter_func(item):
                continue
            symbol = item[2]
            description = item[1]
            name = item[0]
            btn = QPushButton(symbol)
            btn.setObjectName("unitBtn")
            btn.setToolTip(description)
            btn.clicked.connect(lambda checked, s=symbol, n=name: click_handler(s, n))
            buttons.append(btn)
            layout.addWidget(btn, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        return widget, layout, buttons

    @catch_exceptions("创建菜单栏时崩溃")
    def _create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        help_menu = menubar.addMenu("帮助")
        welcome_action = QAction("欢迎", self)
        welcome_action.triggered.connect(self.show_welcome)
        help_menu.addAction(welcome_action)
        help_action = QAction("用户手册", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    @catch_exceptions("更新右侧面板按钮列数时崩溃")
    def update_button_layout(self):
        """根据窗口宽度动态更新按钮列数"""
        tab_widget = self.findChild(QTabWidget)
        if not tab_widget:
            return
        # 获取当前标签页的宽度
        tab_width = tab_widget.width() - 20
        # 根据宽度计算列数（每个按钮约60-70px）
        for i in range(1, 10):
            if tab_width < 100 * i + 50:
                new_cols = i
                break
        else:
            new_cols = 10
        # 更新所有面板
        if hasattr(self, 'unit_buttons') and self.unit_buttons:
            self._reflow_buttons(self.unit_layout, self.unit_buttons, new_cols)
        if hasattr(self, 'const_buttons') and self.const_buttons:
            self._reflow_buttons(self.const_layout, self.const_buttons, new_cols)
        if hasattr(self, 'func_buttons') and self.func_buttons:
            self._reflow_buttons(self.func_layout, self.func_buttons, new_cols)
        self.panel_cols = new_cols

    @catch_exceptions("重新排列右侧面板按钮时崩溃")
    def _reflow_buttons(self, layout, buttons, cols):
        """重新排列按钮到指定列数，并调整按钮大小保持圆形"""
        # 清空布局
        while layout.count():
            layout.takeAt(0)
        # 获取可用宽度
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            available_width = tab_widget.width() - 30  # 减去内边距
        else:
            available_width = 300
        # 计算按钮大小（保持正方形）
        spacing = 7
        if available_width > 1000:
            btn_size = (available_width - spacing * (cols - 1)) // cols - 20
            btn_size = max(40, btn_size)
            btn_size = min(100, btn_size)
        else:
            btn_size = 70
        row, col = 0, 0
        for btn in buttons:
            btn.setFixedSize(btn_size, btn_size)
            # 根据文本长度动态调整字体大小
            text_len = len(btn.text())
            if text_len >=10:
                font_size = max(10, btn_size // 6)
            elif text_len >= 8:
                font_size = max(10, btn_size // 5)
            elif text_len >= 6:
                font_size = max(10, btn_size // 4)  # 很长时更小
            elif text_len >= 4:
                font_size = max(12, btn_size // 3)
            else:
                font_size = max(14, btn_size // 3)
            btn.setStyleSheet(f"""
                QPushButton#unitBtn {{
                    border-radius: {btn_size // 2}px;
                    min-width: {btn_size}px;
                    min-height: {btn_size}px;
                    max-width: {btn_size}px;
                    max-height: {btn_size}px;
                    font-size: {font_size}px;
                }}
            """)
            layout.addWidget(btn, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    @catch_exceptions("处理按钮事件时崩溃")
    def on_button_clicked(self, checked=False):
        btn = self.sender()
        text = btn.text()
        match text:
            case '单位转换':
                # 切换转换模式状态，并改变按钮样式标记按下状态
                self.is_convert_mode = not self.is_convert_mode
                btn.setChecked(self.is_convert_mode)  # 保持按下/弹起状态
                if self.is_convert_mode:
                    current_result = self.result_label.text()
                    if current_result in ("结果", "错误"):
                        QMessageBox.warning(self, "提示", "请先完成计算再进行单位转换")
                        self.is_convert_mode = False
                        btn.setChecked(False)
            case '=':
                self.calculate()
            case 'C':
                self.expr_edit.clear()
                self.result_label.setText("结果")
                self.info_text.clear()
            case 'CE':
                self.expr_edit.clear()
            case '⌫':
                self.expr_edit.backspace()
            case '√':
                self.expr_edit.insert('√(')
            case "∧":
                self.expr_edit.insert('^')
            case t:
                self.expr_edit.insert(t)

    @catch_exceptions("处理计算时崩溃")
    def calculate(self):
        expr = self.expr_edit.text()
        if not expr.strip():
            return
        # self.result_label.setText("计算中...")
        QApplication.processEvents()
        result_str, error_msg = self.core.evaluate(expr)
        if error_msg:
            self.result_label.setText("错误")
            self.info_text.setText(error_msg)
        else:
            self.result_label.setText(result_str)
            self.info_text.clear()

    @catch_exceptions("处理历史记录时崩溃")
    def show_history(self, checked=False):
        """展示历史记录"""
        if not self.core.history:
            QMessageBox.information(self, "历史记录", "暂无历史记录")
            return
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("历史记录")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)
        # 文本显示区域
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 10))
        # 格式化历史文本（支持序号或直接显示）
        history_lines = []
        for idx, (expr, res) in enumerate(self.core.history, 1):
            history_lines.append(f"{idx}. {expr} = {res}")
        history_text = "\n".join(history_lines)
        text_edit.setText(history_text)
        layout.addWidget(text_edit)
        # 按钮栏
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空历史")
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)
        # 清空功能
        def clear_history():
            self.core.history.clear()
            text_edit.clear()
            QMessageBox.information(dialog, "提示", "历史记录已清空")
        clear_btn.clicked.connect(clear_history)
        dialog.exec_()

    @catch_exceptions("打开关于窗口时崩溃")
    def show_about(self, checked=False):
        """显示关于对话框"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("关于 DimCalculator")
        dialog.setFixedSize(420, 420)
        dialog.setStyleSheet("""
            QDialog { background-color: white; }
            QLabel { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
            QLabel#link { color: #0078d7; }
            QLabel#link:hover { text-decoration: underline; }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 30, 40, 30)

        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("datas/icon.ico").pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 软件名称
        title = QLabel("DimCalculator")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d7;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 版本号 + 作者
        try:
            with open("datas/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            version = config.get("version", "版本信息获取失败")
        except:
            version = "版本信息获取失败"
        version_label = QLabel(f"{version}\n作者：ljx-13")
        version_label.setStyleSheet("font-size: 16px; color: #666;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # 分隔线
        line = QLabel("─" * 30)
        line.setStyleSheet("color: #ddd; font-size: 12px;")
        line.setAlignment(Qt.AlignCenter)
        layout.addWidget(line)

        # 详细描述
        desc = QLabel(
            "智能量纲计算器\n"
            "面向高中物理教学，支持带单位的表达式运算\n"
        )
        desc.setStyleSheet("font-size: 13px; color: #444; line-height: 1.6;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # 发布页链接
        link_label = QLabel("""
            发布页:<br>
            <a href="https://github.com/ljx-13/DimCalculator/releases" style="color:#0078d7; text-decoration:none;">
            github
            </a><br>
            <a href="https://gitee.com/ljx-13/dim-calculator/releases" style="color:#0078d7; text-decoration:none;">
            gitee(推荐)
            </a>
        """)
        link_label.setOpenExternalLinks(True)
        link_label.setAlignment(Qt.AlignCenter)
        link_label.setTextFormat(Qt.RichText)
        layout.addWidget(link_label)

        # 许可证
        license_label = QLabel("MIT License")
        license_label.setStyleSheet("font-size: 12px; color: #888;")
        license_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_label)

        layout.addStretch()

        dialog.exec_()

    @catch_exceptions("打开用户手册时崩溃")
    def show_help(self, checked=False):
        """打开用户手册"""
        try:
            with open("docs/help.md", "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "提示", f"用户手册加载失败: {e}")
        else:
            dialog = QDialog(self)
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            dialog.setWindowTitle("用户手册")
            dialog.resize(700, 700)
            layout = QVBoxLayout(dialog)
            text_browser = QTextBrowser()
            text_browser.setReadOnly(True)
            text_browser.setOpenExternalLinks(True)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QTextBrowser {
                    background-color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 20px;
                    font-size: 18px;
                    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                    line-height: 1.8;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 8px;
                }
                QScrollBar::handle:vertical {
                    background: #d0d0d0;
                    border-radius: 4px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #b0b0b0;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
            text_browser.setMarkdown(content)
            layout.addWidget(text_browser)
            dialog.exec_()

    @catch_exceptions("打开欢迎窗口时崩溃")
    def show_welcome(self, checked=False):
        """打开欢迎窗口"""
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setWindowTitle("欢迎使用 DimCalculator")
        dialog.resize(500, 380)
        dialog.setStyleSheet("""
            QDialog {background-color: white;}
            QLabel {font-family: "Segoe UI", "Microsoft YaHei", sans-serif;}
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = QLabel("DimCalculator")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #0078d7;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 副标题
        subtitle = QLabel("智能量纲计算器")
        subtitle.setStyleSheet("font-size: 18px; color: #666;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # 分隔线
        line = QLabel("─" * 30)
        line.setStyleSheet("color: #ddd; font-size: 12px;")
        line.setAlignment(Qt.AlignCenter)
        layout.addWidget(line)

        # 功能介绍
        desc = QLabel(
            "支持带单位的表达式运算\n"
            "例如：5m + 20cm = 5.2m\n\n"
            "内置物理常数：_g, _c, _h ...\n"
            "支持数学函数：sin, cos, tan\n\n"
            "点击「帮助/用户手册」菜单可查看完整说明"
        )
        desc.setStyleSheet("font-size: 16px; color: #444; line-height: 1.8;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()

        # 按钮
        btn = QPushButton("开始使用")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 0;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)

        dialog.exec_()

    @catch_exceptions("检查首次启动时崩溃")
    def check_first_run(self):
        """第一次运行时弹出欢迎窗口"""
        try:
            with open("datas/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logging.warning(f"首次启动检查失败: {e}")
        else:
            if config.get("first_run", True):
                self.show_welcome()
                config["first_run"] = False
                with open("datas/config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)

    @catch_exceptions("重新计算窗口大小时崩溃")
    def resizeEvent(self, event):
        """窗口尺寸变化时触发"""
        super().resizeEvent(event)
        # 延迟执行，确保布局已完成调整
        QTimer.singleShot(10, self.update_button_layout)

    def closeEvent(self, event):
        event.accept()
