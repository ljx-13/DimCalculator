import json
import traceback
from functools import wraps
import logging

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMainWindow, QLineEdit, QLabel, QHBoxLayout, QGridLayout, QPushButton, \
    QTabWidget, QTextEdit, QMessageBox, QApplication, QDialog, QAction, QScrollArea
# from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QSize

from .core import DimCalculatorCore

func_data = [  # （名字，描述，符号，是否常用）
    ("sin", "正弦", "sin", True), ("cos", "余弦", "cos", True), ("tan", "正切", "tan", True),
    ("cot", "余切 (1/tan)", "cot", False), ("sec", "正割 (1/cos)", "sec", False), ("csc", "余割 (1/sin)", "csc", False),
    ("asin", "反正弦 (sin⁻¹)", "asin", True), ("acos", "反余弦 (cos⁻¹)", "acos", True), ("atan", "反正切 (tan⁻¹)", "atan", True),
    ("log", "对数 log(真数, 底数)", "log", True), ("lg", "常用对数", "lg", True), ("ln", "自然对数", "ln", True),
    ("abs", "绝对值", "|x|", True), ("mod", "取余", "取余", True), ("factorial", "阶乘", "n!", False),
    ("sinh", "双曲正弦", "sinh", False), ("cosh", "双曲余弦", "cosh", False), ("tanh", "双曲正切", "tanh", False),
]
get_std_icon = QApplication.style().standardIcon

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
        self.is_convert_mode = False
        self.unit_buttons = []
        self.const_buttons = []
        self.func_buttons = []
        self.panel_cols = 3  # 右侧面板共用列数
        self.precisionMode = 5
        self.precisionSet = 12
        self.precision = 12
        self.show_unusual = False
        self.debug = False
        self.if_log2info = False
        self.load_settings()
        self.core = DimCalculatorCore(precision=self.precision)
        self.initUI()

    @catch_exceptions("初始化窗口时崩溃")
    def initUI(self):  # todo: init外定义
        self.setUpdatesEnabled(False)
        self.setWindowTitle("DimCalculator - 智能量纲计算器")
        self.setMinimumSize(800, 750)
        # self.setMaximumWidth(1250)
        self.setWindowIcon(QIcon("datas/icon/light.ico"))
        # 加载样式表
        try:
            with open("ui/style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            logging.warning(f"样式表加载失败: {e}")

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
            ('C', 1, 0, True, '清除'), ('∧', 1, 1, True, '幂运算'), ('√', 1, 2, True, '平方根'), ('÷', 1, 3, True, ''),
            ('7', 2, 0, False, ''), ('8', 2, 1, False, ''), ('9', 2, 2, False, ''), ('×', 2, 3, True, ''),
            ('4', 3, 0, False, ''), ('5', 3, 1, False, ''), ('6', 3, 2, False, ''), ('-', 3, 3, True, ''),
            ('1', 4, 0, False, ''), ('2', 4, 1, False, ''), ('3', 4, 2, False, ''), ('+', 4, 3, True, ''),
            ('ans', 5, 0, True, '插入上一次计算结果'), ('0', 5, 1, False, ''), ('.', 5, 2, False, ''), ('=', 5, 3, True, ''),
        ]
        for text, row, col, is_op, tip in buttons:
            btn = QPushButton(text)
            btn.setProperty("insert_text", text)
            btn.setObjectName("numBtn")
            btn.setToolTip(tip)
            if text == "单位转换":
                btn.setCheckable(True)
            if is_op:
                btn.setObjectName("opBtn")
            if text == '=':
                btn.setStyleSheet("background-color: #0078d7; color: white;")
            elif text == "√":
                btn.setIcon(QIcon("datas/icon/sqrt.png"))
                btn.setText("")
                btn.setIconSize(QSize(30, 30))
            btn.clicked.connect(self.on_button_clicked)
            left_grid.addWidget(btn, row, col)
        left_widget.setLayout(left_grid)
        left_widget.setMaximumWidth(600)
        left_widget.setMaximumHeight(800)

        # 右侧面板（单位、常数、函数）
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.North)
        self.update_right_buttons()
        content_layout.addWidget(left_widget, 3)
        content_layout.addWidget(self.right_tabs, 2)
        main_layout.addLayout(content_layout)

        # 诊断/步骤信息区
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(300)
        main_layout.addWidget(self.info_text)
        if self.if_log2info:
            self.info_text.setText(self.core.log_text)

        # 菜单栏和状态栏
        self._create_menubar()

        self.precision_label = QLabel()
        self.precision_label.setStyleSheet("color: #333")
        self.statusBar().addWidget(self.precision_label)

        self.debug_label = QLabel()
        self.debug_label.setText("调试模式已打开")
        self.debug_label.setStyleSheet("color: #333;")
        self.debug_label.setVisible(False)  # 默认隐藏
        self.statusBar().addPermanentWidget(self.debug_label)  # 右对齐

        self.update_status_label()

        self.resize(800, 750)
        self.setUpdatesEnabled(True)

    @staticmethod
    def _create_buttons_from_items(items, filter_func, click_handler, cols=3):
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
        menubar = self.menuBar()

        setting_menu = menubar.addMenu("设置")
        setting = QAction("设置", self)
        setting.triggered.connect(self.show_settings)
        setting.setIcon(QIcon("datas/icon/setting.png"))
        setting_menu.addAction(setting)

        memory_menu = menubar.addMenu("记忆")
        history = QAction("历史记录", self)
        history.triggered.connect(self.show_history)
        memory_menu.addAction(history)

        help_menu = menubar.addMenu("帮助")
        welcome = QAction("欢迎", self)
        welcome.triggered.connect(self.show_welcome)
        help_menu.addAction(welcome)
        help_ = QAction("用户手册", self)
        help_.triggered.connect(self.show_help)
        help_.setIcon(get_std_icon(QApplication.style().SP_TitleBarContextHelpButton))
        help_menu.addAction(help_)
        about = QAction("关于", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)
        feedback = QAction("反馈", self)
        feedback.triggered.connect(self.show_feedback)
        help_menu.addAction(feedback)

    @catch_exceptions("更新右侧面板按钮时崩溃")
    def update_right_buttons(self):
        """重新放置右侧按钮"""
        self.right_tabs.clear()

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
                        for b in self.findChildren(QPushButton):
                            if b.text() == "单位转换":
                                b.setChecked(False)
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
            self.core.units, lambda item: True if self.show_unusual else item[3], handle_unit_click, self.panel_cols
        )
        scroll = QScrollArea()
        scroll.setWidget(unit_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        self.right_tabs.addTab(scroll, "单位")

        # 常数面板
        const_widget, self.const_layout, self.const_buttons = self._create_buttons_from_items(
            self.core.consts, lambda item: True if self.show_unusual else item[4], handle_const_click, self.panel_cols
        )
        scroll = QScrollArea()
        scroll.setWidget(const_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        self.right_tabs.addTab(scroll, "常数")

        # 函数面板
        func_widget, self.func_layout, self.func_buttons = self._create_buttons_from_items(
            func_data, lambda item: True if self.show_unusual else item[3], handle_func_click, self.panel_cols
        )
        scroll = QScrollArea()
        scroll.setWidget(func_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        self.right_tabs.addTab(scroll, "函数")

        self.update_rbutton_layout()

    def update_status_label(self):
        self.precision_label.setText(f"   常数精度: {self.precision} 位有效数字")
        self.debug_label.setVisible(self.debug)

    @catch_exceptions("更新右侧面板按钮列数时崩溃")
    def update_rbutton_layout(self):
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
        self.right_tabs.setUpdatesEnabled(False)
        if hasattr(self, 'unit_buttons') and self.unit_buttons:
            self._reflow_right_buttons(self.unit_layout, self.unit_buttons, new_cols)
        if hasattr(self, 'const_buttons') and self.const_buttons:
            self._reflow_right_buttons(self.const_layout, self.const_buttons, new_cols)
        if hasattr(self, 'func_buttons') and self.func_buttons:
            self._reflow_right_buttons(self.func_layout, self.func_buttons, new_cols)
        self.right_tabs.setUpdatesEnabled(True)
        self.panel_cols = new_cols

    @catch_exceptions("重新排列右侧面板按钮时崩溃")
    def _reflow_right_buttons(self, layout, buttons, cols):
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
        text = btn.property("insert_text")
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
            if self.if_log2info:
                self.info_text.setText(self.core.log_text + "\n" + error_msg)
            else:
                self.info_text.setText(error_msg)
        else:
            self.result_label.setText(result_str)
            if self.if_log2info:
                self.info_text.setText(self.core.log_text)
            else:
                self.info_text.clear()

    @catch_exceptions("处理历史记录时崩溃")
    def show_history(self, checked=False):
        if not self.core.history:
            QMessageBox.information(self, "历史记录", "暂无历史记录")
            return

        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore
        dialog.setWindowTitle("历史记录")
        dialog.resize(700, 500)

        layout = QVBoxLayout(dialog)

        # 表格
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["序号", "表达式", "结果"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px 10px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #ddd;
            }
            QTableWidget::item:selected {
                background-color: #cce4ff;
            }
        """)

        table.setRowCount(len(self.core.history))
        for idx, (expr, res) in enumerate(self.core.history):
            table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            table.setItem(idx, 1, QTableWidgetItem(expr))
            table.setItem(idx, 2, QTableWidgetItem(res))
            # 居中对齐序号和结果
            table.item(idx, 0).setTextAlignment(Qt.AlignCenter)
            table.item(idx, 2).setTextAlignment(Qt.AlignCenter)

        layout.addWidget(table)

        # 底部按钮
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空历史")
        clear_btn.setStyleSheet("color: red;")
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)

        def clear_history():
            yes = QMessageBox.question(dialog, "确认", "是否清空历史记录？", QMessageBox.Yes | QMessageBox.No)
            if yes == QMessageBox.No:
                return
            self.core.history.clear()
            table.clearContents()
            table.setRowCount(0)

        clear_btn.clicked.connect(clear_history)

        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec_()

    @catch_exceptions("打开关于窗口时崩溃")
    def show_about(self, checked=False):
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore
        dialog.setWindowTitle("关于 DimCalculator")
        dialog.setFixedSize(420, 400)
        dialog.setStyleSheet("""
            QDialog { background-color: white; }
            QLabel#link { color: #0078d7; }
            QLabel#link:hover { text-decoration: underline; }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 30, 40, 30)

        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("datas/icon/light.ico").pixmap(64, 64))
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
        version_label = QLabel(f"{version}  |  作者：ljx-13")
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
            "面向高中物理教学\n"
            "支持带单位的表达式运算\n"
        )
        desc.setStyleSheet("font-size: 13px; color: #444; line-height: 1.6;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # 发布页链接
        link_label = QLabel("""
            发布页:<br>
            <a href="https://github.com/ljx-13/DimCalculator/releases" style="color:#0078d7; text-decoration:none;">
            github
            </a>&nbsp;&nbsp;&nbsp;
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
        from PyQt5.QtWidgets import QTextBrowser
        try:
            with open("docs/help.md", "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "提示", f"用户手册加载失败: {e}")
        else:
            dialog = QDialog(self)
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore
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

    @catch_exceptions("打开反馈窗口时崩溃")
    def show_feedback(self, checked=False):
        from PyQt5.QtWidgets import QTextEdit, QPushButton, QHBoxLayout

        def get_version():
            try:
                with open("datas/config.json", "r", encoding="utf-8") as f:
                    return json.load(f).get("version", "未知版本")
            except:
                return "获取失败"
        def get_system_info():
            import platform
            return f"{platform.system()} {platform.release()}"
        def copy_info():
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(info))
            QMessageBox.information(dialog, "已复制", "调试信息已复制到剪贴板")
        def open_github():
            import webbrowser
            webbrowser.open("https://github.com/ljx-13/DimCalculator/issues/new")
        def open_log_folder():
            import os
            import subprocess
            log_dir = os.path.abspath("log")
            if os.path.exists(log_dir):
                subprocess.Popen(f'explorer "{log_dir}"')
        def get_err():
            import traceback
            e = self.core.calculate_error
            if e:
                return "".join(traceback.format_exception(type(e), e, e.__traceback__))
            else:
                return "(暂无异常)"

        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore
        dialog.setWindowTitle("反馈与调试信息")
        dialog.resize(600, 500)
        layout = QVBoxLayout(dialog)
        # 提示
        tip = QLabel("如果当前计算结果异常，请复制下方信息发送给开发者")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        # 文本框
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-size: 12px;")
        # 构建调试信息
        info = [
            f"版本 {get_version()}",
            f"系统: {get_system_info()}",
            f"精度: {self.precision} 位有效数字",
            "\n--- 当前计算日志 ---",
            self.core.log_text if self.core.log_text else "(暂无日志)",
            "\n--- 当前错误日志 ---",
            get_err()
            ]
        text_edit.setText("\n".join(info))
        layout.addWidget(text_edit)
        # 按钮
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("复制信息")
        issue_btn = QPushButton("打开 Github Issues")
        close_btn = QPushButton("关闭")
        folder_btn = QPushButton("打开日志文件夹")
        folder_btn.setIcon(get_std_icon(QApplication.style().SP_DirIcon))

        copy_btn.clicked.connect(copy_info)
        issue_btn.clicked.connect(open_github)
        folder_btn.clicked.connect(open_log_folder)
        close_btn.clicked.connect(dialog.accept)

        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(folder_btn)
        btn_layout.addWidget(issue_btn)

        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec_()

    @catch_exceptions("打开欢迎窗口时崩溃")
    def show_welcome(self, checked=False):
        dialog = QDialog(self)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore
        dialog.setWindowTitle("欢迎使用 DimCalculator")
        dialog.resize(500, 380)
        dialog.setStyleSheet("QDialog {background-color: white;}")

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
                min-width: 120px;
                min-height: 45px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)

        dialog.exec_()

    @catch_exceptions("打开设置页面时崩溃")
    def show_settings(self, checked=False):
        dialog = QDialog(self)
        from PyQt5.uic import loadUi  # type: ignore
        loadUi("ui/settings.ui", dialog)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore
        # 初始化
        precision_combo = dialog.precisionCombo
        precision_spin = dialog.precisionSet
        update_precision_state = lambda index: precision_spin.setEnabled(index == 5)  # 自定义项索引为5
        precision_combo.currentIndexChanged.connect(update_precision_state)
        precision_combo.setCurrentIndex(self.precisionMode)
        precision_spin.setValue(self.precisionSet)
        update_precision_state(self.precisionMode)
        dialog.checkUnusual.setChecked(self.show_unusual)
        dialog.startDebug.setChecked(self.debug)
        dialog.output2infoArea.setChecked(self.if_log2info)

        initial_precisionMode = self.precisionMode
        initial_precisionSet = self.precisionSet
        initial_unusual = dialog.checkUnusual.isChecked()
        initial_debug = dialog.startDebug.isChecked()
        initial_log = dialog.output2infoArea.isChecked()

        @catch_exceptions("重置设置选项时崩溃")
        def reset():
            yes = QMessageBox.question(dialog, "确认", "是否恢复出厂设置？", QMessageBox.Yes | QMessageBox.No)
            if yes == QMessageBox.No:
                return
            dialog.precisionCombo.setCurrentIndex(5)
            precision_spin.setValue(12)
            precision_spin.setEnabled(False)
            dialog.checkUnusual.setChecked(False)
            dialog.startDebug.setChecked(False)
            dialog.output2infoArea.setChecked(False)

        @catch_exceptions("保存设置选项时崩溃")
        def save():
            self.precisionMode = precision_combo.currentIndex()
            self.precisionSet = precision_spin.value()
            precision = self.precisionSet if self.precisionMode == 5 else [1, 2, 4, 6, 12][self.precisionMode]
            if self.precision != precision:
                self.core.precision = self.precision = precision
                self.core.update_namespace()
            show_unusual = dialog.checkUnusual.isChecked()
            if self.show_unusual != show_unusual:
                self.show_unusual = show_unusual
                self.update_right_buttons()
            debug = dialog.startDebug.isChecked()
            if self.debug != debug:
                self.debug = debug
                if debug:
                    logging.getLogger().setLevel(logging.DEBUG)
                    QMessageBox.information(dialog, "调试模式", "调试模式已开启\n日志将输出到 log/DimCalculator.log")
                else:
                    logging.getLogger().setLevel(logging.ERROR)
            log2info = dialog.output2infoArea.isChecked()
            self.if_log2info = log2info
            self.update_status_label()
            if self.dump_settings():
                dialog.accept()

        def cancel():
            has_changed = (
                    precision_combo.currentIndex() != initial_precisionMode or
                    precision_spin.value() != initial_precisionSet or
                    dialog.checkUnusual.isChecked() != initial_unusual or
                    dialog.startDebug.isChecked() != initial_debug or
                    dialog.output2infoArea.isChecked() != initial_log
            )
            if has_changed:
                reply = QMessageBox.question(dialog, "确认取消", "有未保存的更改，是否保存？", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    save()
                    return
            dialog.reject()

        dialog.ok.clicked.connect(lambda: save())
        dialog.cancel.clicked.connect(lambda: cancel())
        dialog.reset.clicked.connect(lambda: reset())

        # dialog.ok.setIcon(get_std_icon(QApplication.style().SP_DialogOkButton))
        # dialog.cancel.setIcon(get_std_icon(QApplication.style().SP_DialogCancelButton))

        dialog.exec_()

    @catch_exceptions("读取设置时崩溃")
    def load_settings(self):
        try:
            with open("datas/config.json", "r", encoding="utf-8") as f:  # todo
                config = json.load(f)
                self.precisionMode = config.get("precisionMode", 5)
                self.precisionSet = config.get("precisionSet", 12)
                self.precision = config.get("precision", 12)
                self.show_unusual = config.get("showUnusual", False)
                self.debug = config.get("debug", False)
                self.if_log2info = config.get("log2info", False)
        except Exception as e:
            QMessageBox.warning(None, "警告", f"读取设置时发生意外错误：\n{e}")
            logging.error(f"failed load settings: {e}")


    @catch_exceptions("保存设置时崩溃")
    def dump_settings(self) -> bool:
        try:
            with open("datas/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            config["precision"] = self.precision
            config["precisionMode"] = self.precisionMode
            config["precisionSet"] = self.precisionSet
            config["showUnusual"] = self.show_unusual
            config["debug"] = self.debug
            config["log2info"] = self.if_log2info
            with open("datas/config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            # raise Exception("test")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"保存设置时发生意外错误：\n{e}")
            logging.error(f"failed dump settings: {e}")
            return False
        else:
            return True

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
        QTimer.singleShot(10, self.update_rbutton_layout)

    def closeEvent(self, event):
        event.accept()
