#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import shutil

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ask(prompt, default="y"):
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "n", ""):
            return answer if answer else default
        print("请输入 y 或 n")


def confirm(prompt):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if ask(prompt):
                return func(*args, **kwargs)
            else:
                print("跳过\n")
                return None

        return wrapper

    return decorator


def run_cmd(cmd):
    return subprocess.run(cmd, shell=True)


def get_version():
    try:
        with open("datas/config.json", "r", encoding="utf-8") as f:
            return json.load(f).get("version", "").strip()
    except:
        return ""


def print_header():
    print("\n" + "=" * 40)
    print("   DimCalculator 发布脚本")
    print("=" * 40 + "\n")


@confirm("[1/4] 确认版本号")
def step_version():
    version = get_version()
    if not version:
        version = input("未找到版本号，请输入: ").strip()
    print(f"版本: {version}")
    return version


@confirm("[2/4] 确认提交信息并提交")
def step_commit(version):
    msg = input("提交信息 (留空=更新版本): ").strip()
    if not msg:
        msg = f"更新版本 {version}"
    print(f"信息: {msg}")
    run_cmd('git add .')
    run_cmd(f'git tag -a "{version}" -m "{msg}"')
    run_cmd(f'git commit -m "{msg}"')
    return version


@confirm("[3/4] 确认打包")
def step_pack():
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    cmd = (
        'pyinstaller --onedir --windowed '
        '--icon=datas/icon.ico --name DimCalculator '
        '--add-data ".venv/Lib/site-packages/PyQt5/Qt5/plugins;PyQt5/Qt5/plugins" '
        'main.py'
    )
    if run_cmd(cmd).returncode:
        print("打包失败！")
        sys.exit(1)
    dist_dir = "dist/DimCalculator"
    if os.path.exists(dist_dir):
        os.makedirs(f"{dist_dir}/log", exist_ok=True)
        for folder in ("src", "datas"):
            if os.path.exists(folder):
                shutil.copytree(folder, f"{dist_dir}/{folder}", dirs_exist_ok=True)


@confirm("[4/4] 确认推送")
def step_push():
    run_cmd('git push origin main')
    run_cmd('git push gitee main')


def main():
    print_header()
    version = get_version()
    if version:
        print(f"当前版本: {version}")
    else:
        version = input("请输入版本号: ").strip()

    step_version()
    step_commit(version)
    step_pack()
    step_push()

    print("\n" + "=" * 40)
    print("   ✓ 发布完成！")
    print("=" * 40)
    print(f"   版本: {version}")
    print(f"   文件: dist/DimCalculator/DimCalculator.exe")
    print("=" * 40)
    input("\n按 Enter 退出...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")