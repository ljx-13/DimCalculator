import traceback
from functools import wraps
import logging

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMainWindow, QLineEdit, QLabel, QHBoxLayout, QGridLayout, QPushButton, \
    QTabWidget, QTextEdit, QMessageBox, QApplication, QDialog
# from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

from core import DimCalculatorCore

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
                QMessageBox.critical(None, "程序崩溃", msg + "错误日志已保存至 DimCalculator.log")
                return None
        return wrapper
    return decorator

class DimCalculatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.core = DimCalculatorCore()
        self.is_convert_mode = False  # 标记是否处于单位转换模式
        self.initUI()

    @catch_exceptions("初始化窗口时崩溃\n")
    def initUI(self):  # todo: 欢迎
        self.setWindowTitle("DimCalculator - 智能量纲计算器")
        self.setMinimumSize(700, 700)
        # raise SyntaxError
        self.setMaximumWidth(1000)
        self.setBaseSize(700, 700)
        self.setWindowIcon(QIcon("icon.ico"))
        self.setStyleSheet("""
            QMainWindow { background-color: #f3f3f3; }
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
            QPushButton#funcBtn, QPushButton#unitBtn { background-color: #f9f9f9; font-size: 20px; }
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

        # 结果显示
        self.result_label = QLabel("结果")
        self.result_label.setObjectName("resultLabel")
        self.result_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.result_label)

        # 主内容区域（左右分栏）
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # 左侧：数字与运算符网格
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

        # 右侧面板（单位、常数、函数）
        right_tabs = QTabWidget()
        right_tabs.setTabPosition(QTabWidget.North)

        # 单位面板
        unit_widget = QWidget()
        unit_layout = QGridLayout(unit_widget)
        row, col = 0, 0
        if not self.core.units:
            label = QLabel("单位配置文件导入错误\n请检查 units.json")
            label.setAlignment(Qt.AlignCenter)
            right_tabs.addTab(label, "单位")
        else:
            for name, display_name, symbol, common in self.core.units:
                if common:
                    btn = QPushButton(symbol)
                    btn.setObjectName("unitBtn")
                    btn.setToolTip(display_name)  # 悬停显示内部符号
                    btn.clicked.connect(lambda checked, s=symbol: self.handle_unit_click(s))
                    unit_layout.addWidget(btn, row, col)
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1
            # 添加滚动区域
            from PyQt5.QtWidgets import QScrollArea
            scroll = QScrollArea()
            scroll.setWidget(unit_widget)
            scroll.setWidgetResizable(True)
            scroll.setMinimumWidth(250)
            right_tabs.addTab(scroll, "单位")

        # 常数面板
        const_widget = QWidget()
        unit_layout = QGridLayout(const_widget)
        row, col = 0, 0
        if not self.core.consts:
            label = QLabel("常数配置文件导入错误\n请检查 consts.json")
            label.setAlignment(Qt.AlignCenter)
            right_tabs.addTab(label, "常数")
        else:
            for name, display_name, symbol, value in self.core.consts:
                btn = QPushButton(symbol)
                btn.setObjectName("unitBtn")
                btn.setToolTip(display_name)  # 悬停显示内部符号
                btn.clicked.connect(
                    lambda checked, s=symbol, n=name:
                    self.expr_edit.insert("_" + s) if n not in ("pi", "e") else self.expr_edit.insert(s)
                )
                unit_layout.addWidget(btn, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
            # 添加滚动区域
            from PyQt5.QtWidgets import QScrollArea
            scroll = QScrollArea()
            scroll.setWidget(const_widget)
            scroll.setWidgetResizable(True)
            scroll.setMinimumWidth(250)
            right_tabs.addTab(scroll, "常数")

        # 函数面板
        func_widget = QWidget()
        func_layout = QGridLayout(func_widget)
        functions = {"sin": "正弦函数", "cos": "余弦函数", "tan": "正切函数",
                     "log": "log(真数, 底数)", "lg": "常用对数", "ln": "自然对数",
                     "abs": "绝对值"}
        row, col = 0, 0
        for func, tip in functions.items():
            btn = QPushButton(func)
            btn.setObjectName("funcBtn")
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, f=func: self.expr_edit.insert(f + "("))
            func_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        right_tabs.addTab(func_widget, "函数")

        content_layout.addLayout(left_grid, 3)
        content_layout.addWidget(right_tabs, 1)
        main_layout.addLayout(content_layout)

        # 诊断/步骤信息区
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(120)
        main_layout.addWidget(self.info_text)

        # 历史记录按钮
        hist_btn = QPushButton("历史记录")
        hist_btn.setObjectName("opBtn")
        hist_btn.clicked.connect(self.show_history)
        main_layout.addWidget(hist_btn)

        self.resize(700, 700)

    @catch_exceptions("处理单位输入时崩溃\n")
    def handle_unit_click(self, symbol):
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

    @catch_exceptions("处理按钮事件时崩溃\n")
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

    @catch_exceptions("处理计算时崩溃\n")
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

    @catch_exceptions("处理历史记录时崩溃\n")
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

    def closeEvent(self, event):
        event.accept()
