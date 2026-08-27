from typing import List, Tuple
from functools import lru_cache
import logging
import pint
import math
import json
import re

DEBUG_LEVEL = {logging.DEBUG: "DEBUG", logging.INFO: "INFO", logging.WARNING: "WARNING", logging.ERROR: "ERROR", logging.CRITICAL: "CRITICAL"}
SUPER_SCRIPT = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
                       '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻', }

ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
loger = logging.getLogger(__name__)

class DimCalculatorCore:
    """核心计算类，支持超时控制和错误诊断"""
    def __init__(self, units_file="datas/units.json", constants_file="datas/consts.json", precision=12):
        """
        :param precision: 命名空间中常量精度
        """
        self.calculate_error: Exception | None = None
        self.log_text = ""
        self.ureg = ureg
        self.__units = self._load_units(units_file)
        self.__consts = self._load_consts(constants_file)
        self.precision = precision
        self.history = []
        """(exper, result_str)"""
        self.last_ans: str = "0"
        self.namespace = self._build_namespace()

    @property
    def units(self) -> List[Tuple[str, str, str, bool]]:
        """List[(英文名称, 显示名称, 符号, 是否常用)]"""
        return self.__units

    @property
    def consts(self) -> List[Tuple[str, str, str, str, bool]]:
        """List[(英文名称, 显示名称, 符号, 值, 是否常用)]"""
        return self.__consts

    def _log(self, *args, level=logging.DEBUG):
        """记录日志"""
        s = "".join(map(str, args))
        loger.log(level, s)
        self.log_text += f"--{DEBUG_LEVEL[level]}-- {s}\n"

    def processed(self, exper):
        """处理输入"""
        # 替换输入字符串中的部分字符
        exper = (exper.replace(" ", "")
                 .replace("×", "*").replace("××", "* *").replace("⋅", "·")
                 .replace("\\", "/")
                 .replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
                 .replace("√(", "sqrt(").replace("%", "/100")
                 .replace("ans", self.last_ans)#.replace("π", str(self.consts[0][3]))
            )
        # 上标数字转普通格式（连续上标整体替换）
        # 匹配连续上标字符（如 ²³ → 23）
        map_ = {k: v for v, k in SUPER_SCRIPT.items()}
        exper = re.sub(
            r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+',
            lambda m: '^' + ''.join(map_[c_] for c_ in m.group()),
            exper
        )
        # exper = re.sub(
        #     r'(?<![eE])([a-zA-Z_]+)(\d+)',
        #     lambda m: f"{m.group(1)}^{m.group(2)}",
        #     exper
        # )
        # 替换单位符号和常量
        for (name, dn, symbol, c) in self.units:
            if '/' not in symbol:
                exper = self._replace_if_surrounded_by_math(exper, symbol, name)
        for (name, dn, symbol, v, c) in self.consts:
            if name.startswith("_"):  # 物理常量
                exper = self._replace_if_surrounded_by_math(exper, "_" + symbol, name)
            else:  # 数学常量
                exper = self._replace_if_surrounded_by_math(exper, symbol, name)
        self._log("replaced: ", exper)

        exper = self._atomize_units(exper)
        self._log("atomized: ", exper)
        exper = (exper.replace("÷", "/").replace(":", "/")
                 .replace("^", "**").replace("·", "*"))  # 与复合单位中/和*区分

        exper = self._insert_mul(exper)
        self._log("insert *: ", exper)

        # 补全右括号
        s9s0 = exper.count("(") - exper.count(")")
        if s9s0 > 0:
            exper += ")" * s9s0
        return exper

    @staticmethod
    def _replace_if_surrounded_by_math(exp, sym: str, name: str):
        """在exp中sym两边都是数字或数学符号时，把exp中的sym替换成name"""
        allowed = set("0123456789+-*/^%!()[]{}×÷·: \t_")  # todo: ~
        result = []
        i = 0
        n = len(exp)
        sym_len = len(sym)
        while i < n:
            pos = exp.find(sym, i)
            if pos == -1:
                result.append(exp[i:])
                break
            before_char = exp[pos - 1] if pos > 0 else '^'
            after_char = exp[pos + sym_len] if pos + sym_len < n else '$'
            before_ok = (pos == 0) or (before_char in allowed)
            after_ok = (pos + sym_len == n) or (after_char in allowed)
            if before_ok and after_ok:
                result.append(exp[i:pos])
                result.append(name)
            else:
                result.append(exp[i:pos + sym_len])
            i = pos + sym_len
        return ''.join(result)

    @staticmethod
    def _atomize_units(exp) -> str:
        """
        把单位原子化，防止计算优先级错误。
        将数字与其紧邻的单位用括号包裹，确保单位不被错误解析为变量或运算符。如:

        - 5V/3A -> (5V)/(3A)
        - 5kg/mol -> (5kg/mol)
        - 5m/sin(60°) -> (5m)/sin(60°)
        - 5mol^-1 -> (5mol^-1)
        - 6.62607015e^-34J·s -> (6.62607015e^-34J·s)
        支持的单位写法:

        - 基本单位: m, kg, mol, J, V, A 等
        - 复合单位: kg/mol, J/(kg·K)
        - 指数: m^2, m², mol^-1, mol^0.5
        - 中间点: J·s, N⋅m
        """
        is_digit_or_dot = lambda x: x.isdigit() or x == '.'  # 检测是否为函数或小数点
        new = []
        i = 0
        n = len(exp)
        while i < n:
            ch = exp[i]
            if is_digit_or_dot(ch):
                start = i
                # 收集数字部分（整数或小数）
                while i < n and is_digit_or_dot(exp[i]):
                    i += 1
                # 注：不再支持 e/E 科学计数法（如 3e+2），因为在该应用场景中 e 代表自然常数或元电荷
                # 处理 ^ 指数（如 10^-34，）
                if i < n and exp[i] == '^':
                    i += 1
                    if i < n and exp[i] in '+-':
                        i += 1
                    while i < n and exp[i].isdigit():  # todo: 循环指数
                        i += 1
                num_part = exp[start:i]
                # 检查数字后面是否紧跟单位/常数（字母或下划线开头）
                if i < n and (exp[i].isalpha() or exp[i] in "_"):
                    ident_start = i
                    # 收集单位部分，支持括号嵌套（如 J/(kg·K)）
                    paren_depth = 0
                    while i < n:
                        c = exp[i]
                        if c == '(':
                            paren_depth += 1
                            i += 1
                        elif c == ')':
                            paren_depth -= 1
                            if paren_depth < 0:
                                break  # 多余的右括号（不属于当前单位），停止
                            i += 1
                            if paren_depth == 0:
                                break  # 配对的右括号，括号内容收集完毕
                        elif c.isalpha() or c == '_' or c.isdigit():
                            i += 1
                        elif c in '/·':
                            # 遇到 / 或 · 且后面是数字时停止（如 /3A 中的 /3）。此时当前单位结束，后面的数字+单位由下一轮处理
                            if i + 1 < n and exp[i + 1].isdigit():
                                break
                            i += 1
                        elif c == '^':
                            # 收集指数部分（如 ^-1, ^2）
                            i += 1
                            if i < n and exp[i] in '+-':
                                i += 1
                            while i < n and is_digit_or_dot(exp[i]):
                                i += 1
                        else:
                            # 遇到其他字符（运算符、函数括号等），单位结束
                            break
                    ident = exp[ident_start:i]
                    if ident:
                        # 将数字+单位整体用括号包裹
                        new.append('(' + num_part + ident + ')')
                    else:
                        new.append(num_part)
                else:
                    new.append(num_part)
            else:
                # 非数字字符直接保留
                new.append(ch)
                i += 1
        return ''.join(new)

    @staticmethod
    def _insert_mul(exp):
        """补全省略的乘号"""
        result = []
        i = 0
        n = len(exp)
        while i < n:
            if exp[i].isdigit() or exp[i] == '.':
                # 收集数字部分
                start = i
                while i < n and (exp[i].isdigit() or exp[i] == '.'):
                    i += 1
                num_part = exp[start:i]
                if i < n and (exp[i].isalpha() or exp[i] == "_"):
                    if i < n - 1 and exp[i] in "eE" and (exp[i + 1].isdigit() or exp[i + 1] in "+-"):  # 检查科学计数法
                        result.append(num_part)
                    else:
                        result.append(num_part + '*')
                        # print(exper[i])
                else:
                    result.append(num_part)
            elif exp[i] == ')':
                # 右括号后紧跟左括号，插入乘号
                result.append(exp[i])
                i += 1
                if i < n and (exp[i] == '(' or exp[i].isalpha() or exp[i].isdigit()):
                    result.append('*')
            else:
                result.append(exp[i])
                i += 1
        exp = "".join(result)
        return exp

    @staticmethod
    def _round_quantity_str(value_str: str, precision: int) -> str:
        """按有效数字四舍五入quantity格式字符串中的数值部分"""
        import re
        # 匹配开头的数值（含科学计数法）
        # ^ 从字符串开头匹配
        # ([\d.]+(?:e[+-]?\d+)?) 捕获组：
        #   [\d.]+     匹配数字和小数点（如 9.80665 或 299792458）
        #   (?:        非捕获组，用于组合
        #       e          匹配字母 e（科学计数法标志）
        #       [+-]?      可选的正号或负号
        #       \d+        一个或多个数字（指数部分）
        #   )?         整个科学计数法部分可选
        match = re.match(r'^([\d.]+(?:e[+-]?\d+)?)', value_str)
        if not match:
            return value_str
        num_str = match.group(1)
        unit_part = value_str[len(num_str):]
        num = float(num_str)
        # 使用 .g 格式：根据 precision 位有效数字
        formatted = f"{num:.{precision}g}"
        return formatted + unit_part

    @lru_cache(maxsize=128)  # 缓存计算结果
    def _safe_eval(self, exper: str) -> pint.Quantity | int | float:
        """
        安全计算表达式，支持单位和数学函数。
        :return: pint.Quantity或数值。
        """
        # 表达式安全检查（长度）
        if len(exper) > 200:
            raise ValueError("表达式过长（超过200字符）")
        # 使用受限的 eval
        try:
            result = eval(exper, self.namespace)
            # print(exper, type(result), self.namespace)
            if isinstance(result, pint.Quantity):
                result = result
            return result
        except pint.DimensionalityError:
            raise
        except NameError:
            raise
        except SyntaxError:
            raise
        except Exception as e:
            raise ValueError(f"表达式错误: {e}")

    def _load_units(self, filename) -> list:
        """导入单位，自动注册，返回中文名。"""
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
            units_list = []
            for unit in data.get("units", []):
                name = unit["name"]
                symbol = unit["symbol"]
                definition = unit["definition"]
                display_name = unit["display_name"]
                common = unit["common"]
                # 注册单位
                if not ("/"  in symbol or "·" in symbol or "⋅" in symbol):
                    if not hasattr(self.ureg, name):
                        self.ureg.define(f"{name} = {definition} = {symbol}")  # fixme: cm3 -> centi m3
                        self._log("new_define_unit: ", name)
                units_list.append((name, display_name, symbol, common))
            # 导入合并单位
            preferred_unit_names = data.get("preferred_units", [])
            self.ureg.default_preferred_units = [self.ureg.Unit(name) for name in preferred_unit_names]
            self.preferred_units = preferred_unit_names
            # print(ureg.default_preferred_units)
            return units_list
        except FileNotFoundError:
            self._log("FileNotFoundError: ", filename, level=logging.ERROR)
            return []
        except Exception as e:
            self._log(type(e).__name__, ": ", str(e), level=logging.ERROR)
            return []

    # noinspection PyMethodMayBeStatic
    def _load_consts(self, filename: str) -> list:
        """导入常量，返回常量字典"""
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
            const_list = []
            for const in data.get("consts", []):
                name = const["name"]
                display_name = const.get("display_name", name)
                symbol = const["symbol"]
                value = const["value"]
                common = const["common"]
                const_list.append((name, display_name, symbol, value, common))
            return const_list
        except FileNotFoundError:
            self._log("FileNotFoundError: ", filename, level=logging.ERROR)
            return []
        except Exception as e:
            self._log(type(e).__name__, ": ", str(e), level=logging.ERROR)
            return []

    def _build_namespace(self):
        """为运算创建命名空间"""
        namespace = {}
        # 所有注册的单位
        for name, dn, s, c in self.units:
            if not ("/" in s or "·" in s or "⋅" in s):
                namespace[name] = getattr(self.ureg, name)
        # 基本单位（保障）
        basic_units = {
            'm': self.ureg.m, 'kg': self.ureg.kg, 's': self.ureg.s, 'A': self.ureg.A,
            'K': self.ureg.K, 'mol': self.ureg.mol, 'cd': self.ureg.cd, 'g': self.ureg.g,
            'cm': self.ureg.cm, 'km': self.ureg.km, 'mm': self.ureg.mm,
            'N': self.ureg.N, 'J': self.ureg.J, 'W': self.ureg.W, 'Pa': self.ureg.Pa,
            'V': self.ureg.V, 'ohm': self.ureg.ohm, 'Hz': self.ureg.Hz,
            'rad': self.ureg.radian, 'deg': self.ureg.degree,
        }
        namespace.update(basic_units)
        # 让 pint 自动识别这些前缀组合，并加入 namespace
        si_prefixes = ['n', 'µ', 'm', 'c', 'd', 'da', 'h', 'k', 'M', 'G', 'T', 'p', 'f']
        base_names = ['s', 'g', 'm', 'A', 'V', 'W', 'N', 'Pa', 'J', 'Hz', 'mol', 'lm', 'lx']
        for prefix in si_prefixes:
            for base in base_names:
                name = prefix + base
                # 如果已经在 namespace 中，跳过（避免覆盖已有定义）
                if name not in namespace:
                    try:
                        # 用 parse_expression 让 pint 自动解析前缀组合
                        # 比如 "ns" -> nanosecond, "µm" -> micrometer
                        namespace[name] = self.ureg.parse_expression(name)
                    except Exception as e:
                        self._log("failed to set prefixes:", type(e).__name__, ": ", str(e), level=logging.WARNING)
        # 常数
        for name, _, _, value_str, _ in self.consts:
            namespace[name] = ureg.parse_expression(self._round_quantity_str(value_str, self.precision))
        # 数学常数和函数
        def trigonometric(f, x):
            """三角函数"""
            input_x = x
            if isinstance(x, pint.Quantity):
                if x.units == ureg.degree:
                    x = x.to(ureg.radian).magnitude
                elif x.units == ureg.radian:
                    x = x.magnitude
                else:
                    raise TypeError(f"三角函数要求角度（deg/rad），但输入了 {x.units}")
            result = f(x)
            # 防止tan(pi/2)等定义域之外的情况
            if abs(result) > 1e15:
                raise ValueError(f"tan({input_x}) 无定义：正切函数在 π/2 + kπ 处趋于无穷")
            return round(result, 12)
        def _abs(x):
            """绝对值"""
            if isinstance(x, pint.Quantity):
                return abs(x.magnitude)
            return abs(x)
        def log(x, base_):
            """取对数"""
            # 如果带单位，检查是否无量纲
            if isinstance(x, pint.Quantity):
                if not x.dimensionless:
                    raise ValueError(f"对数log()的参数必须无量纲，但输入了 {x.units}")
                x = x.magnitude
            # 现在 x 是纯数字
            return math.log(x, base_)
        def sqrt(x):  # todo: free sqrt
            """开方"""
            if isinstance(x, pint.Quantity):
                return math.sqrt(x.magnitude) * x.units ** 0.5
            elif isinstance(x, pint.Unit):
                return x ** 0.5
            return math.sqrt(x)

        namespace['pi'] = math.pi
        namespace['e'] = math.e
        namespace['sin'] = lambda x: trigonometric(math.sin, x)
        namespace['cos'] = lambda x: trigonometric(math.cos, x)
        namespace['tan'] = lambda x: trigonometric(math.tan, x)
        namespace['cot'] = lambda x: trigonometric(lambda v: 1 / math.tan(v), x)
        namespace['sec'] = lambda x: trigonometric(lambda v: 1 / math.cos(v), x)
        namespace['csc'] = lambda x: trigonometric(lambda v: 1 / math.sin(v), x)
        namespace['asin'] = lambda x: trigonometric(math.asin, x)
        namespace['acos'] = lambda x: trigonometric(math.acos, x)
        namespace['atan'] = lambda x: trigonometric(math.atan, x)
        namespace['sqrt'] = sqrt
        namespace['abs'] = _abs
        namespace['log'] = log
        namespace['lg'] = lambda x: log(x, 10)
        namespace['ln'] = lambda x: log(x, math.e)
        namespace['mod'] = lambda a, b: a % b
        namespace['factorial'] = math.factorial
        namespace['sinh'] = math.sinh
        namespace['cosh'] = math.cosh
        namespace['tanh'] = math.tanh
        return namespace

    def update_namespace(self):
        logging.info(f"update namespace: precision={self.precision}")
        self.namespace = self._build_namespace()
        self._safe_eval.cache_clear()

    @staticmethod
    def diagnose_error(error: Exception) -> str:  # todo: 角度弧度
        """根据错误类型生成教学提示，支持量纲分析、未定义名称、语法错误等"""
        err_type = type(error).__name__
        err_msg = str(error)
        # print(err_type, err_msg.lower())
        # 1. 量纲不匹配（DimensionalityError）
        if hasattr(error, 'units1') and hasattr(error, 'units2'):
            u1 = str(error.units1).lower()
            u2 = str(error.units2).lower()

            # 辅助函数：判断单位是否属于某物理量
            def is_length(u):
                return 'meter' in u or u in ('m', 'cm', 'km', 'mm')

            def is_time(u):
                return 'second' in u or u in ('s', 'min', 'h')

            def is_mass(u):
                return 'kilogram' in u or u in ('kg', 'g', 'mg')

            def is_energy(u):
                return 'joule' in u or u in ('j', 'joule')

            def is_power(u):
                return 'watt' in u or u in ('w', 'watt')

            def is_voltage(u):
                return 'volt' in u or u in ('v', 'volt')

            def is_current(u):
                return 'ampere' in u or u in ('a', 'ampere')

            if (is_length(u1) and is_time(u2)) or (is_length(u2) and is_time(u1)):
                return (
                    f"❌ 单位错误：长度（米）和时间（秒）不能直接相加或相减。\n"
                    f"💡 提示：您是否想计算速度？请尝试 长度 / 时间，例如 `10*m / 5*s`。"
                )
            elif (is_mass(u1) and is_length(u2)) or (is_mass(u2) and is_length(u1)):
                return (
                    f"❌ 单位错误：质量（千克）和长度（米）不能直接运算。\n"
                    f"💡 提示：您是否想计算力？力 = 质量 × 加速度，例如 `10*kg * 9.8*m/s^2`。"
                )
            elif (is_energy(u1) and is_time(u2)) or (is_energy(u2) and is_time(u1)):
                return (
                    f"❌ 单位错误：能量（焦耳）和时间（秒）不能直接相加。\n"
                    f"💡 提示：功率 = 能量 / 时间，单位是瓦特（W），例如 `100*J / 10*s`。"
                )
            elif (is_voltage(u1) and is_current(u2)) or (is_voltage(u2) and is_current(u1)):
                return (
                    f"❌ 单位错误：电压（伏特）和电流（安培）不能直接相加。\n"
                    f"💡 提示：电阻 = 电压 / 电流，单位是欧姆（Ω），例如 `10*V / 2*A`。"
                )
            else:
                return (
                    f"❌ 单位不匹配：`{error.units1}` 与 `{error.units2}` 不属于同一物理量纲。\n"
                    f"💡 提示：请检查表达式中的单位是否一致。例如长度只能与长度相加，速度不能与时间相加等。"
                )

        # 2. 未定义的名称（NameError 或 UndefinedUnitError）
        if isinstance(error, NameError) or ('UndefinedUnitError' in err_type):
            import re
            match = re.search(r"'([^']+)'", err_msg)
            if match:
                undefined = match.group(1)
                suggestions = {
                    'm': '米（正确写法：m）',
                    'kg': '千克（正确写法：kg）',
                    's': '秒（正确写法：s）',
                    'N': '牛顿（正确写法：N）',
                    'J': '焦耳（正确写法：J）',
                    'W': '瓦特（正确写法：W）',
                    'Pa': '帕斯卡（正确写法：Pa）',
                    'V': '伏特（正确写法：V）',
                    'A': '安培（正确写法：A）',
                    'Ω': '欧姆（正确写法：ohm 或 Ω）',
                    'C': '库仑（正确写法：C）',
                    'F': '法拉（正确写法：F）',
                    'H': '亨利（正确写法：H）',
                    'T': '特斯拉（正确写法：T）',
                    'Hz': '赫兹（正确写法：Hz）',
                    'rad': '弧度（正确写法：rad）',
                    'deg': '度（正确写法：deg）',
                    '_g': '重力加速度（正确写法：_g，或点击常数面板的 g 按钮）',
                    '_c': '光速（正确写法：_c）',
                    'pi': '圆周率（正确写法：pi，或使用 π 符号）',
                    'e': '自然常数（正确写法：e）',
                }
                if undefined in suggestions:
                    return f"❌ 未定义的名称：`{undefined}`\n💡 提示：{suggestions[undefined]}"
                else:
                    return (
                        f"❌ 未定义的名称：`{undefined}`\n"
                        f"💡 提示：请检查是否使用了正确的单位（m, kg, s, N, J...）或物理常数（_g, _c, _pi...）。"
                    )
            else:
                return f"❌ 计算错误：{err_msg}\n💡 提示：请检查是否使用了未定义的变量或单位。"

        # 3. 语法错误（SyntaxError）
        if isinstance(error, SyntaxError):
            return (
                f"❌ 表达式语法错误：{err_msg}\n"
                f"💡 提示：请检查括号是否匹配、运算符是否正确（例如不要连续两个运算符 `++`），或是否使用了不支持的字符。"
            )

        # 4. 其他异常（如 ZeroDivisionError, OverflowError 等）
        if isinstance(error, ZeroDivisionError):
            return "❌ 除零错误：表达式分母为零。\n💡 提示：请检查除数是否可能为零。"
        if isinstance(error, OverflowError):
            return "❌ 数值溢出：计算结果过大或过小。\n💡 提示：请简化表达式或使用科学计数法。"

        # 5. 默认提示
        return f"❌ 计算错误：{err_msg}\n💡 提示：请检查表达式语法、单位是否正确，或简化表达式后重试。"

    def _format_scientific(self, result: str) -> str:
        """把 1.234e+15 转成 1.234×10¹⁵，把 **10 转成上角标"""
        # 处理科学计数法
        # \d+(?:\.\d+)?)    捕获组1：数字，可有小数
        # [eE]    字母e或E
        # \+?    可选的正号 + 或没有
        # (-?\d+)    捕获组2：指数，可带负号
        result = re.sub(
            r'(\d+(?:\.\d+)?)[eE]\+?(-?\d+)',
            lambda m: f"{m.group(1)}×10{''.join(SUPER_SCRIPT.get(c, c) for c in m.group(2))}",  # type: ignore
            result
        )
        # 处理 ** 指数：优先匹配小数，再匹配整数
        # \*\*    两个乘号（转义）
        # (-?\d+(?:\.\d+)?)    捕获组：数字，可有符号和小数
        def replace_power(m):
            exp = m.group(1)
            if '.' in exp:
                return f"^{exp}"
            else:
                return ''.join(SUPER_SCRIPT.get(c, c) for c in exp)  # type: ignore
        result = (re.sub(r'\*\*(-?\d+(?:\.\d+)?)', replace_power, result))
        result = result.replace("**", "^").replace("*", "⋅")
        self._log("format scientific: ", result)
        return result

    @staticmethod
    def _round_magnitude(value: float):
        """四舍五入，同时避免丢失极大极小值"""
        if isinstance(value, pint.Quantity):
            value = value.magnitude
        if isinstance(value, int) and abs(value) > 1e308:
            return str(value)  # 防止超出浮点范围
        if isinstance(value, (int, float)):
            result = f"{value:.12g}"  # 12位有效数字
            if float(result).is_integer():
                if abs(value) <= 12:
                    return str(int(float(result)))  # int不支持科学计数法，用float做桥接
            # 去除e-06中的前导0
            parts = result.split('e')
            if len(parts) == 2:
                exp = parts[1]
                if exp[0] in "+-":
                    if exp[1] == '0':
                        exp = exp[0] + exp[2:]
                else:
                    if exp[0] == '0':
                        exp = exp[1:]
                result = parts[0].rstrip('0').rstrip('.') + 'e' + exp
            return result
        return str(value)

    def _to_preferred(self, result: "pint.Quantity") -> pint.Quantity | int | float:
        """将Quantity的单位转换到通用单位"""  # todo: 转至标准单位，转至基本单位
        if isinstance(result, pint.Quantity):
            # 如果是无量纲，直接返回数值
            self._log(f"original dimensionality: ", result.dimensionality)
            if result.dimensionless:
                if not result.units in ("rad", "r", "deg", "degree"):
                    return result.to_base_units().magnitude
                # else:
                #     return result
            try:
                result = result.to_preferred()
            except Exception as e:
                self._log(f"failed auto to_preferred(): {result}  # {e}", level=logging.WARNING)
            else:
                self._log("auto to_preferred(): ", result)
            finally:
                def get_result_and_mag(obj):
                    result_ = result.to(obj)
                    return result_, abs(result_.magnitude)
                for u in self.preferred_units:
                    if result.check(u):
                        self._log("nonauto to_preferred(): ", u, level=logging.WARNING)
                        result = result.to(u)
                if result.check("Hz"):
                    if "r" not in str(result.units):
                        result = result.to("Hz")
                    else:
                        result, mag = get_result_and_mag("r/s")
                        if mag < 1:
                            result = result.to('r/min')
                elif result.check("s"):
                    if result.units not in ("millisecond", "minute", "day"):
                        result, mag = get_result_and_mag("s")
                        if mag >= 24 * 3600 and mag % 27 == 0:
                            result = result.to("day")
                        elif mag >= 3600 and mag % 9 == 0:
                            result = result.to('h')
                        elif 1e-6 <= mag < 0.1:
                            result = result.to('ms')
                elif result.check("kg"):
                    if result.units not in ("u","unified_atomic_mass_unit"):
                        result, mag = get_result_and_mag("kg")
                        if mag >= 1000:
                            result = result.to('t')
                        elif 1e-3 <= mag < 0.1:
                            result = result.to('g')
                        elif 1e-6 <= mag < 1e-3:
                            result = result.to('mg')
                        elif 1e-30 <= mag < 1e-20:
                            result = result.to('u')
                elif result.check("m"):
                    if result.units not in ("mile", "ft", "ly"):
                        result, mag = get_result_and_mag("m")
                        if mag >= 9.4607304725808e15:
                            result = result.to('ly')
                        elif mag >= 1000:
                            result = result.to('km')
                        elif 1e-2 <= mag < 0.1:
                            result = result.to('cm')
                        elif 1e-3 <= mag < 1e-2:
                            result = result.to('mm')
                        elif 1e-6 <= mag < 1e-3:
                            result = result.to('um')
                        elif 1e-9 <= mag < 1e-6:
                            result = result.to('nm')
                elif result.check("m**2"):
                    result, mag = get_result_and_mag("m**2")
                    if mag >= 1e6:
                        result = result.to('km**2')
                    elif 1e-4 <= mag < 1e-2:
                        result = result.to('cm**2')
                    elif 1e-6 <= mag < 1e-4:
                        result = result.to('mm**2')
                elif result.check("m**3"):
                    if "liter" in str(result.units):
                        result, mag = get_result_and_mag("L")
                        if 1e-6 <= mag < 1:
                            result = result.to('mL')
                        elif mag < 1e-6:
                            result = result.to("m**3")
                    else:
                        result, mag = get_result_and_mag("m**3")
                        if mag >= 1e9:
                            result = result.to('km**3')
                        elif 1e-6 <= mag < 1e-3:
                            result = result.to('cm**3')
                        elif 1e-9 <= mag < 1e-6:
                            result = result.to('mm**3')
                elif result.check("m/s"):
                    if "k" not in str(result.units):
                        result = result.to("m/s")
                elif result.check("Pa"):
                    result, mag = get_result_and_mag("Pa")
                    if mag >= 101325:
                        result = result.to('atm')
                    elif mag >= 1000:
                        result = result.to('kPa')
                elif result.check("A"):
                    result, mag = get_result_and_mag("A")
                    if mag < 0.1:
                        result = result.to('mA')
                elif result.check("V"):
                    result, mag = get_result_and_mag("V")
                    if mag < 0.1:
                        result = result.to('mV')
                elif result.check("W"):
                    result, mag = get_result_and_mag("W")
                    if mag >= 1000:
                        result = result.to('kW')
                elif result.check("g/cm**3"):
                    result, mag = get_result_and_mag("g/cm**3")
                    if mag <= 0.001:
                        result = result.to('kg/m**3')
                elif result.check("g/mol"):
                    result, mag = get_result_and_mag("g/mol")
                    if mag >= 1000:
                        result = result.to('kg/mol')
                elif result.check("J"):
                    if result.units not in ("eV", "cal", "kWh"):
                        result, mag = get_result_and_mag("J")
                        if mag >= 3.6e6:
                            result = result.to('kWh')
                        elif mag <= 1e-15:
                            result = result.to('eV')
                # if "e" not in str(result.magnitude) and "." in str(result.magnitude):
                #     if "." in str(origin.magnitude):
                #         if len(str(result.magnitude).split('.')[1]) > 10 > len(str(origin.magnitude).split('.')[1]):
                #             # 化简完为不整齐小数，使用原结果
                #             result = origin
                #     else:
                #         result = origin
                return result
        else:
            raise TypeError

    def evaluate(self, original_exper: str) -> tuple[str, None] | tuple[None, str]:
        """
        计算表达式
        :return: (结果字符串, 错误信息)
        """
        # raise SyntaxError
        self.log_text = ""
        self.calculate_error = None
        loger.debug("========== DEBUG ==========")
        self._log("origin: ", original_exper)
        exper = self.processed(original_exper)
        self._log("final exper: ", exper)
        try:
            result = self._safe_eval(exper)
            self._log("original result: ", result)
            # 格式化输出
            if isinstance(result, pint.Quantity):
                # 紧凑格式：5m 而不是 5 meter
                try:
                    # 智能格式化数值
                    result = self._to_preferred(result)
                    self._log("to preferred: ", result)
                    if isinstance(result, pint.Quantity):
                        mag = result.magnitude
                    else:
                        mag = result
                    mag_str = self._round_magnitude(mag)
                    result_str = f"{mag_str}{result.units:~}".replace(" ", "")
                    self._log("format: ", result_str)
                except Exception as e:
                    self._log(f"failed to format result:  {str(result)}  # {str(e)}", level=logging.WARNING)
                    result_str = str(result).replace(" ", "")
                # 把1/X改成X^-1的格式
                result_str = re.sub(r'1/([a-zA-Z_][a-zA-Z0-9_]*)', r'\1⁻¹', result_str)
            else:
                result_str = str(self._round_magnitude(result))
            result_str = result_str.replace("deg", "°").replace("°C", "℃").replace("°F", "℉")
            self._log("final result: ", result_str)
        except Exception as e:
            # 诊断错误
            self.calculate_error = e
            diagnosis = self.diagnose_error(e)
            return None, diagnosis
        else:
            # 记录历史
            self.history.append((original_exper, result_str))
            if len(self.history) > 200:
                self.history.pop(0)
            self.last_ans = result_str
            return self._format_scientific(result_str), None

    def convert_unit(self, target_unit: str):
        """
        将上一次计算结果转换为目标单位
        :return: (转换结果字符串, 错误信息)
        """
        try:
            # 解析 last_ans 为 pint.Quantity
            q = self.ureg.parse_expression(self.last_ans)  # todo: eval
            # 转换为目标单位
            converted = q.to(target_unit)
            # 格式化输出
            result_str = f"{self._round_magnitude(converted.magnitude)}{converted.units:~}".replace(" ", "")
            result_str = self._format_scientific(result_str).replace("deg", "°").replace("°C", "℃").replace("°F", "℉")
            return result_str, None
        except pint.DimensionalityError:
            return None, f"❌ 单位不匹配：无法将 {self.last_ans} 转换为 {target_unit}"
        except pint.UndefinedUnitError:
            return None, f"❌ 未定义的单位：'{target_unit}'"
        except Exception as e:
            return None, f"转换失败: {e}"
