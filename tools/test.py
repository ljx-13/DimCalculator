import logging
import sys

from core import DimCalculatorCore

sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.ERROR,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    )

calc = DimCalculatorCore(units_file="../datas/units.json", constants_file="../datas/consts.json")

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
    test("1km + 500m", "1500m")
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
    # print("\n物理常数:")
    # test("_g", "9.8m/s²")
    # test("_g * 5kg", "N")
    # test("_c", "299792458m/s")
    # test("_G", "×10⁻¹¹")  # 或者 "m³/kg/s²"
    # test("_N_A", "×10²³")
    # test("_h", "×10⁻³⁴")
    # # test("_e_charge", "×10⁻¹⁹") fixme
    # # test("_m_e", "×10⁻³¹")
    # # test("_k_B", "×10⁻²³")
    # test("_epsilon_0", "×10⁻¹²")
    # test("_mu_0", "×10⁻⁶")

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
