"""更新版本，打包发布（自用）"""

import os
import json
import subprocess
import shutil

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ask(prompt):
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "n", ""):
            return True if answer == "y" else False
        print("请输入 y 或 n")


def confirm(prompt, exit_=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if ask(prompt):
                return func(*args, **kwargs)
            else:
                if exit_:
                    exit(0)
                print("跳过\n")
                return None

        return wrapper

    return decorator


def run_cmd(cmd):
    return subprocess.run(cmd, shell=True)

def test():
    from test import run_all_tests
    run_all_tests()
    print("\n测试通过\n\n")

def reset():
    from reset import reset
    reset()
    print("已恢复出厂设置")

@confirm("[1/4] 确认版本号", exit_=True)
def step_version(version):
    if not version:
        version = input("未找到版本号，请输入: ").strip()
    print(f"版本: {version}")
    return version


@confirm("[2/4] 确认更新版本（请确认已经提交完毕）")
def step_commit(version):
    # msg = input("版本信息信息 (留空=更新版本): ").strip()
    # if not msg:
    #     msg = f"更新版本 {version}"
    # print(f"信息: {msg}")
    # run_cmd('git add .')
    # run_cmd(f'git commit -m "{msg}"')
    run_cmd(f'git tag -a "{version}"')
    return version


@confirm("[3/4] 确认打包")
def step_pack():
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    cmd = 'pyinstaller DimCalculator.spec'
    if run_cmd(cmd).returncode:
        print("打包失败！")
    dist_dir = "dist/DimCalculator"
    if os.path.exists(dist_dir):
        os.makedirs(f"{dist_dir}/log", exist_ok=True)
        for folder in ("datas", "docs/"):
            if os.path.exists(folder):
                shutil.copytree(folder, f"{dist_dir}/{folder}", dirs_exist_ok=True)


@confirm("[4/4] 确认推送")
def step_push():
    run_cmd('git push origin main --follow-tags')
    run_cmd('git push gitee main --follow-tags')


def main():
    test()
    reset()
    with open("datas/config.json", "r", encoding="utf-8") as f:
        version =  json.load(f).get("version", "").strip()
    print(version)
    step_version(version)
    step_commit(version)
    step_pack()
    step_push()


if __name__ == "__main__":
    main()
    input("按回车退出...")
