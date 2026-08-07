"""通过git获取树状项目结构"""

import subprocess
import os

os.chdir(os.path.dirname(os.path.dirname(__file__)))
files = subprocess.check_output(["git", "-c", "core.quotepath=false", "ls-files"], text=True, encoding="utf-8").strip().splitlines()

def build(files_) -> dict[str, dict | None]:
    """
    构建文件树
    :return: {目录名：子目录（字典）} 或 {文件名：None}
    """
    root = {}
    for f in files_:
        parts = f.split("/")
        node = root
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = None
    return root

def render(node, prefix=""):
    """渲染"""
    lines = []
    for i, (name, child) in enumerate(node.items()):
        lines.append(prefix + ("└── " if i == len(node) - 1 else "├── ") + (name if child is None else name + "/"))
        if child is not None:
            lines.extend(render(child, prefix + ("    " if i == len(node) - 1 else "│   ")))
    return lines

if __name__ == "__main__":
    print("DimCalculator/")
    for line in render(build(files), prefix="    "):
        print(line)
