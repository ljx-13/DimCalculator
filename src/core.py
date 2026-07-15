from typing import List, Tuple
from functools import lru_cache
import logging
import pint
import math
import json
import re

FUNC_NAMES = {'sin', 'cos', 'tan', 'log', 'lg', 'ln', 'abs', 'sqrt'}
SUPER_SCRIPT = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
                       '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻', }

ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
loger = logging.getLogger(__name__)

class DimCalculatorCore:
    """核心计算类，支持超时控制和错误诊断"""
    def __init__(self, units_file="datas/units.json", constants_file="datas/consts.json"):
        self.ureg = ureg
        self.__units = self._load_units(units_file)
        self.__consts = self._load_consts(constants_file)
        self.history = []
        """(exper, result_str)"""
        self.last_ans = "0"
        self.namespace = self._build_namespace()

    @property
    def units(self) -> List[Tuple[str, str, str, bool]]:
        """List[(英文名称, 显示名称, 符号, 是否常用)]"""
        return self.__units

    @property
    def consts(self) -> List[Tuple[str, str, str, str]]:
        """List[(英文名称, 显示名称, 符号, 值)]"""
        return self.__consts


    def processed(self, exper):
        """处理输入"""
        # 替换输入字符串中的部分字符
        exper = (exper.replace("×", "*").replace("××", "* *")
                 .replace("\\", "/")
                 .replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
                 .replace("√(", "sqrt(").replace("%", "/100")
                 .replace("ans", self.last_ans)#.replace("π", str(self.consts[0][3]))
                 )

        def replace_if_surrounded_by_math(exp, sym: str, name: str):
            """替换数学符号及数字中的exp"""
            allowed = set("0123456789+-*/^%!()[]{}×÷·: \t_")
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

        # 替换单位符号和常量
        for (name, dn, symbol, c) in self.units:
            exper = replace_if_surrounded_by_math(exper, symbol, name)
        for (name, dn, symbol, v) in self.consts:
            if name.startswith("_"):  # 物理常量
                exper = replace_if_surrounded_by_math(exper, "_" + symbol, name)
            else:  # 数学常量
                exper = replace_if_surrounded_by_math(exper, symbol, name)
        loger.debug("replaced: " + exper)

        def atomize_units(exp) -> str:
            """把单位原子化，如 5V/3A -> (5V)/(3A)，防止计算优先级错误"""
            # 原子化：数字 + 字母（可能带数字后缀，如 m2, m3）
            new = []
            i = 0
            n = len(exp)
            while i < n:
                ch = exp[i]
                if ch.isdigit() or ch == '.':
                    start = i
                    # 收集数字（包括科学计数法）
                    while i < n and (exp[i].isdigit() or exp[i] == '.'):
                        i += 1
                    if i < n and exp[i] in 'eE':
                        i += 1
                        if i < n and exp[i] in '+-':
                            i += 1
                        while i < n and exp[i].isdigit():
                            i += 1
                    num_part = exp[start:i]

                    # 检查后面是否跟单位
                    if i < n and (exp[i].isalpha() or exp[i] in "_"):
                        ident_start = i
                        # 检查函数调用
                        while i < n and (exp[i].isalpha() or exp[i] in '_/·'):
                            if exp[i] in '/·':
                                # 检查 / 后面是不是函数调用
                                j = i + 1
                                while j < n and exp[j].isalpha():
                                    j += 1
                                if j < n and exp[j] == '(':
                                    break  # /sin( 这种情况，停止收集
                                if i < n - 1 and exp[i + 1].isdigit():
                                    break  # /3A 这种情况，停止收集
                            # 前瞻：字母后面直接跟 (，也是函数调用
                            if i == ident_start:
                                j = i
                                while j < n and exp[j].isalpha():
                                    j += 1
                                if j < n and exp[j] == '(':
                                    break
                            i += 1
                        else:
                            while i < n and (exp[i].isalpha() or exp[i] in "_/·^+-"):
                                if exp[i] in "/·+-" and i < n-1 and (exp[i+1].isdigit() or exp[i+1] in "_+-"):
                                    break
                                i += 1
                            # 允许字母后面跟数字（如 m2, m3）
                            while i < n and (exp[i].isdigit() or exp[i] in "+-"):
                                i += 1
                        ident = exp[ident_start:i]

                        # 原子化
                        new.append('(' + num_part + ident + ')')
                    else:
                        new.append(num_part)
                else:
                    new.append(ch)
                    i += 1
            exp = ''.join(new)
            return exp

        exper = atomize_units(exper)
        loger.debug("atomized: " + exper)
        exper = (exper.replace("÷", "/").replace(":", "/")
                 .replace("^", "**").replace("·", "*"))  # 与复合单位中/区分

        def insert_mul(exp):
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
            loger.debug("tab *: " + exp)
            return exp
        exper = insert_mul(exper)

        # 补全右括号
        s9s0 = exper.count("(") - exper.count(")")
        if s9s0 > 0:
            exper += ")" * s9s0
        return exper

    @lru_cache(maxsize=128)  # 缓存计算结果
    def _safe_eval(self, exper: str) -> "pint.Quantity | int | float":
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
                result = self._to_preferred(result)
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
        # self.auto_preferred_units = []
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
                if not hasattr(self.ureg, name):
                    self.ureg.define(f"{name} = {definition} = {symbol}")
                    loger.debug("new_define_unit: " + name)
                units_list.append((name, display_name, symbol, common))
            # 导入合并单位
            preferred_unit_names = data.get("preferred_units", [])
            self.ureg.default_preferred_units = [self.ureg.Unit(name) for name in preferred_unit_names]
            self.preferred_units = preferred_unit_names
            # print(ureg.default_preferred_units)
            return units_list
        except FileNotFoundError:
            loger.error("FileNotFoundError: " + filename)
            return []
        except Exception as e:
            loger.error(type(e).__name__ + ": " + str(e))
            return []

    def _load_consts(self, filename) -> list:
        """导入常量，返回常量字典"""
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
            const_list = []
            for unit in data.get("consts", []):
                name = unit["name"]
                display_name = unit.get("display_name", name)
                symbol = unit["symbol"]
                value = unit["value"]
                const_list.append((name, display_name, symbol, value))
            return const_list
        except FileNotFoundError:
            loger.error("FileNotFoundError: " + filename)
            return []
        except Exception as e:
            loger.error(type(e).__name__ + ": " + str(e))
            return []

    def _build_namespace(self):
        namespace = {}
        # 所有注册的单位
        for name, dn, s, c in self.units:
            try:
                namespace[name] = getattr(self.ureg, name)
            except AttributeError:
                pass
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
        # 常数
        for name, _, _, value_str in self.consts:
            namespace[name] = ureg.parse_expression(value_str)
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
            if isinstance(x, pint.Quantity):
                return abs(x.magnitude)
            return abs(x)
        def log(x, base):
            """默认的log以e为底，为避免歧义去除该默认值"""
            return math.log(x, base)
        def sqrt(x):
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
        namespace['sqrt'] = sqrt
        namespace['abs'] = _abs
        namespace['log'] = log
        namespace['lg'] = math.log10
        namespace['ln'] = lambda x: math.log(x, math.e)
        return namespace

    def diagnose_error(self, error: Exception) -> str:  # todo: 角度弧度
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

    @staticmethod
    def _format_scientific(result: str) -> str:
        """把 1.234e+15 转成 1.234×10¹⁵，把 **10 转成上角标"""
        import re

        # 处理科学计数法
        result = re.sub(
            r'(\d+(?:\.\d+)?)[eE]\+?(-?\d+)',
            lambda m: f"{m.group(1)}×10{''.join(SUPER_SCRIPT.get(c, c) for c in m.group(2))}",
            result
        )
        # 处理 ** 指数：优先匹配小数，再匹配整数
        def replace_power(m):
            exp = m.group(1)
            if '.' in exp:
                return f"^{exp}"
            else:
                return ''.join(SUPER_SCRIPT.get(c, c) for c in exp)
        result = re.sub(r'\*\*(-?\d+(?:\.\d+)?)', replace_power, result)
        return result

    @staticmethod
    def _round_magnitude(value: float):
        """四舍五入，同时避免丢失极大极小值"""
        if isinstance(value, float):
            if 0 < abs(value) < 1e-10 or abs(value) > 1e10:
                return f"{value:.12g}".rstrip('0').rstrip('.')
            rounded = round(value, 12)
            if rounded.is_integer():
                return str(int(rounded))
            result = f"{rounded:.12g}"
            # 去除e-06中的前导0
            parts = result.split('e')
            if len(parts) == 2:
                exp = parts[1]
                if exp[0] in "+-":
                    if exp[1] == '0':
                        exp = exp[0] + exp[2:]
                else:
                    if exp[0] == '0':
                        exp = exp[0] + exp[2:]
                result = parts[0].rstrip('0').rstrip('.') + 'e' + exp
            return result
        return str(value)

    def _to_preferred(self, result: "pint.Quantity"):
        """将Quantity的单位转换到通用单位"""
        if isinstance(result, pint.Quantity):
            unit = str(result.units)
            # print(unit)
            if "liter" in unit:
                if result.magnitude >= 1000:
                    result = result.to('liter')
                return result
            try:
                result = result.to_preferred()
                loger.debug("auto to_preferred(): " + str(result))
            except Exception as e:
                loger.warning("failed auto to_preferred(): " + str(e))
            finally:
                if set(result.dimensionality.keys()) == {'[time]'}:  # fixme: Hz
                    mag = abs(result.magnitude)
                    if mag >= 3600:
                        result = result.to('h')
                    elif mag >= 60:
                        result = result.to('min')
                for u in self.preferred_units:
                    # if result == "49kg*m/s²/m²":
                    #     breakpoint()
                    #     print(u, result, result.check(u))
                    if result.check(u):
                        loger.warning("unauto to_preferred(): " + u)
                        result = result.to(u)
                return result
        else:
            raise TypeError

    def evaluate(self, original_exper: str) -> tuple[str | None, str | None]:
        """
        计算表达式
        :return: (结果字符串, 错误信息)
        """
        # raise SyntaxError
        loger.debug("\n========== DEBUG ==========")
        loger.debug("origin: " + original_exper)
        exper = self.processed(original_exper)
        loger.debug("final exper: " + exper)
        try:
            result = self._safe_eval(exper)
            loger.debug("original result: " + str(result))
            # 格式化输出
            if isinstance(result, pint.Quantity):
                # 紧凑格式：5m 而不是 5 meter
                try:
                    # 智能格式化数值
                    mag = result.magnitude
                    mag_str = self._round_magnitude(mag)
                    result_str = f"{mag_str}{result.units:~}".replace(" ", "")
                    loger.debug("format: " + result_str)
                except:
                    loger.warning("failed to format result: " + str(result))
                    result_str = str(result).replace(" ", "")
                # 把1/X改成X^-1的格式
                result_str = re.sub(r'1/([a-zA-Z_][a-zA-Z0-9_]*)', r'\1⁻¹', result_str)
            else:
                result_str = str(self._round_magnitude(result))
            result_str = result_str
            loger.debug("final result: " + result_str)
        except Exception as e:
            # 诊断错误
            diagnosis = self.diagnose_error(e)
            return None, diagnosis
        else:
            # 记录历史
            self.history.append((original_exper, result_str))
            self.last_ans = result_str
            return self._format_scientific(result_str).replace("deg", "°"), None  #todo: *·

    def convert_unit(self, target_unit: str):
        """
        将上一次计算结果转换为目标单位
        :return: (转换结果字符串, 错误信息)
        """
        try:
            # 解析 last_ans 为 pint.Quantity
            q = self.ureg.parse_expression(self.last_ans)
            # 转换为目标单位
            converted = q.to(target_unit)
            # 格式化输出
            result_str = f"{self._round_magnitude(converted.magnitude)}{converted.units:~}".replace(" ", "")
            return self._format_scientific(result_str).replace("deg", "°").replace("*", "·"), None
        except pint.DimensionalityError:
            return None, f"❌ 单位不匹配：无法将 {self.last_ans} 转换为 {target_unit}"
        except pint.UndefinedUnitError:
            return None, f"❌ 未定义的单位：'{target_unit}'"
        except Exception as e:
            return None, f"转换失败: {e}"
