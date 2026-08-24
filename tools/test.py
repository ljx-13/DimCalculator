"""测试"""

import logging
import os
import sys

from core import DimCalculatorCore

os.chdir(os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.ERROR,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    )

calc = DimCalculatorCore(units_file="datas/units.json", constants_file="datas/consts.json")

def test(expr, expected_contains=None, should_error=False, verbose=True):
    """简单的测试函数"""
    result, error = calc.evaluate(expr)

    if should_error:
        assert error is not None, f"期望报错，但没有: {expr}"
        if verbose:
            print(f"{expr} → 正确报错: {error[:50]}...")
        return True
    else:
        assert error is None, f"报错了: {error}"
        if expected_contains:
            assert expected_contains in result, f"期望包含 '{expected_contains}'，得到 '{result}'"
        if verbose:
            print(f"{expr} → {result}")
        return True


def run_all_tests():
    print("=" * 60)
    print("DimCalculator 测试开始")
    print("=" * 60)

    # ========== 1. 基础算术 ==========
    print("\n基础算术运算:")
    test("1+1", "2")
    test("10-3", "7")
    test("2*6", "12")
    test("15/3", "5")
    test("2^10", "1024")
    test("(3+5)*2", "16")

    # ========== 2. 长度单位 ==========
    print("\n长度单位:")
    test("5m + 20cm", "5.2m")
    test("1km + 500m", "1.5km")
    test("100cm", "1m")
    test("1000mm", "1m")
    test("1km / 2", "500m")

    # ========== 3. 质量单位 ==========
    print("\n质量单位:")
    test("1kg + 500g", "1.5kg")
    test("1000g", "1kg")
    test("2kg * 3", "6kg")

    # ========== 4. 时间单位 ==========
    print("\n时间单位:")
    test("3600s", "1h")
    test("3601s", "3601s")
    test("1h + 30min", "1.5h")
    test("72h", "3d")

    # ========== 5. 单位原子化 ==========
    print("\n单位原子化:")
    test("9.8m/s^2", "9.8m/s²")
    test("3m÷5m⋅s^-1", "0.6s")
    test("5sin(60°)", "4.33012701892")
    test("5m÷5mm/min", "60000s")
    test("5V/2A", "2.5Ω")
    test("(123m+45cm)kg", "123.45kg⋅m")

    # ========== 6. 导出单位 ==========
    print("\n导出单位 (N, J, W, Pa, V, Ω):")
    test("10kg * _g", "N")
    test("100N * 2m", "J")
    test("100J / 10s", "W")
    test("100N / 2m2", "Pa")
    test("10V / 2A", "Ω")
    test("2A * 5Ω", "10V")
    test("10V * 2A", "20W")
    test("10÷2s", "5Hz")
    test("5km/m", "5000")

    # ========== 7. 物理常数 ==========
    print("\n物理常数:")
    test("_g", "9.80665m/s²")
    test("_g * 5kg", "N")
    test("_c", "299792458m/s")
    test("_G", "×10⁻¹¹")  # 或者 "m³/kg/s²"
    test("_N_A", "×10²³")
    test("_h", "×10⁻³⁴")
    # test("_e_charge", "×10⁻¹⁹") fixme
    # test("_m_e", "×10⁻³¹")
    # test("_k_B", "×10⁻²³")
    test("_epsilon_0", "×10⁻¹²")
    test("_mu_0", "×10⁻⁶")

    # ========== 8. 数学常数 ==========
    print("\n数学常数:")
    test("pi", "3.14159")
    test("e", "2.71828")
    test("2*pi", "6.28318")

    # ========== 9. 三角函数 ==========
    print("\n三角函数 (角度/弧度):")
    test("sin(30*deg)", "0.5")
    test("cos(60*deg)", "0.5")
    test("tan(45*deg)", "1")
    test("sin(pi/2)", "1")
    test("cos(0)", "1")
    test("tan(pi/4)", "1")
    test("sin(pi)", "0")

    # ========== 10. 数学函数 ==========
    print("\n数学函数:")
    test("sqrt(144)", "12")
    test("sqrt(2)", "1.41421")
    test("abs(-5)", "5")
    test("abs(5)", "5")
    test("log(100, 10)", "2")
    test("lg(100)", "2")
    test("ln(e)", "1")

    # ========== 11. 常用体积单位 ==========
    print("\n体积单位:")
    test("1mL", "1ml")
    test("1000mL", "1l")

    # ========== 12. 温度 ==========
    print("\n温度:")
    test("25℃", "25℃")
    # test("273.15*K", "-0°C")
    # 温差
    test("100℃ - 20℃", "80Δ℃")
    test("5*20℃", "100℃")

    # ========== 13. ans / last_ans ==========
    print("\n上一次结果 (ans):")
    test("10m")
    test("ans * 2", "20m")
    test("ans + 5m", "25m")

    # ========== 14. 幂运算 ==========
    print("\n幂运算:")
    test("2^3", "8")
    test("10^2", "100")
    test("(2m)^3", "8m³")
    test("2m^3", "2m³")
    test("5m^0.5+6cm^0.5", "5.6m^0.5")

    # ========== 15. 括号 ==========
    print("\n括号:")
    test("(3+5)*(2+4)", "48")
    test("(10m)/(2s)", "5m/s")

    # ========== 16. 科学计数法 ==========
    # print("\n科学计数法:")
    # test("1e3", "1000")
    # test("1e-3", "001")
    # test("1e3m", "1000m")

    # 17. 四舍五入
    print("\n四舍五入")
    # 普通浮点数
    test("1.0", "1")
    test("1.5", "1.5")
    test("0.9999999999999999", "1")
    # 极大值
    test("1.0×10^20", "1×10²⁰")
    test("1.234567890123×10^15", "1.23456789012×10¹⁵")
    test("6.0×10^23", "6×10²³")
    test("1.5×10^30", "1.5×10³⁰")
    # 极小值
    test("6.017254718654654×10^-10", "6.01725471865×10⁻¹⁰")
    test("1.234567890123×10^-8", "1.23456789012×10⁻⁸")
    test("9.999999999999×10^-15", "1×10⁻¹⁴")
    test("1.0×10^-20", "1×10⁻²⁰")
    # 舍入
    test("1.2345678901234", "1.23456789012")
    test("9.8765432109876", "9.87654321099")
    test("0.00012345678901234", "0.000123456789012")

    # ========== 单位化简（自动转换） ==========
    print("\n单位化简（数值大小自动转换）:")

    # 长度
    test("1500m", "1.5km")
    test("0.05m", "5cm")
    test("0.005m", "5mm")
    test("0.0005m", "500µm")
    test("0.00005m", "50µm")
    test("5*10^-8m", "50nm")
    test("500m", "500m")
    test("1km", "1km")
    test("1mile", "1mi")  # todo: mile

    # 质量
    test("1500kg", "1.5t")
    test("0.05kg", "50g")
    test("0.005kg", "5g")
    test("5*10^-6kg", "5mg")
    test("0.5kg", "0.5kg")
    test("1u", "1u")

    # 时间
    test("7200s", "2h")
    test("3660s", "3660s")
    test("86400s", "1d")
    test("180s", "180s")
    test("60s", "60s")
    test("2min", "2min")
    test("0.05s", "50ms")

    # 面积
    test("2*10^6m2", "2km²")
    test("2*10^5m2", "200000m²")
    test("0.0005m2", "5cm²")

    # 体积
    test("2*10^9m3", "2km³")
    test("500mL", "500ml")

    # 速度
    test("5m/s", "5m/s")
    test("36km/h", "36km/h")

    # 转速
    test("5r/s", "5r/s")
    test("0.05r/s", "3r/min")
    test("0.01r/s", "0.6r/min")

    # 压强
    test("500Pa", "500Pa")
    test("1000Pa", "1kPa")
    test("101325Pa", "1atm")
    test("202650Pa", "2atm")
    test("50kPa", "50kPa")
    test("1atm", "1atm")

    # 电流
    test("0.5A", "0.5A")
    test("0.05A", "50mA")
    test("0.005A", "5mA")

    # 电压
    test("0.5V", "0.5V")
    test("0.05V", "50mV")
    test("0.005V", "5mV")

    # 功率
    test("500W", "500W")
    test("1000W", "1kW")
    test("1500W", "1.5kW")

    # 密度
    # test("1g/cm3", "1g/cm³") fixme
    # test("0.0005g/cm3", "0.5kg/m³")
    # test("0.001g/cm3", "1kg/m³")

    # 摩尔质量
    test("500g/mol", "500g/mol")
    test("1000g/mol", "1kg/mol")
    test("1500g/mol", "1.5kg/mol")

    # 能量
    test("500J", "500J")
    test("3600000J", "1kWh")
    test("5400000J", "1.5kWh")
    test("1*10^-16J", "624.150907446eV")
    test("1*10^-18J", "6.24150907446eV")

    # ========== 17. 错误诊断 ==========
    print("\n错误诊断:")
    test("5m + 10s", should_error=True)
    test("10kg + 5m", should_error=True)
    test("5xyz", should_error=True)
    test("sqrt(-1)", should_error=True)
    test("log(0)", should_error=True)
    test("asin(2)", should_error=True)
    test("10/0", should_error=True)

    # ========== 18. 混合表达式 ==========
    print("\n混合表达式:")
    test("sqrt(100m^2)", "10m")
    test("_g * 10kg * 2m", "196.133J")
    test("100W * 5s", "500J")
    test("sin(30deg) + cos(60deg)", "1")
    # test("(10*kg * 9.8*m/s**2) / (2*m**2)", "49Pa")

    # ========== 19. 单位转换 ==========
    print("\n单位转换 (convert_unit):")
    calc.evaluate("10m")
    result, error = calc.convert_unit("cm")
    if error is None:
        print(f"10m → cm: {result}")
    else:
        print(f"单位转换测试跳过: {error}", file=sys.stderr)

    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
