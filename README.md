# DimCalculator - 智能量纲计算器

**@ author: ljx-13**

## 项目简介

**DimCalculator** 是一款为高中物理学习设计的智能量纲计算器。

在高中物理学习中，单位换算是很多同学的易错点。本软件支持直接输入带单位的表达式（如 `5m + 20cm`），自动进行单位换算和量纲检查，并给出清晰的计算结果。

（本软件尚处于测试阶段，尚不稳定）

### 主要功能

(演示图片来自早期版本，请以实际界面为准)

- **全鼠标操作**：仿 Windows 11 计算器界面，无需键盘即可完成所有操作
- **带单位运算**：支持 `5m + 20cm` 等自然输入
![基本功能.png](docs/images/%E5%9F%BA%E6%9C%AC%E5%8A%9F%E8%83%BD.png)
- **物理常数库**：内置重力加速度 `_g`、光速 `_c`、普朗克常数 `_h` 等常用物理常数
![物理常数.png](docs/images/%E7%89%A9%E7%90%86%E5%B8%B8%E6%95%B0.png)
- **三角函数**：支持 sin、cos、tan，自动识别角度（deg）和弧度（rad）
![数学函数.png](docs/images/%E6%95%B0%E5%AD%A6%E5%87%BD%E6%95%B0.png)
- **智能错误诊断**：对单位不匹配的情况给出具体修改建议
![错误分析.png](docs/images/%E9%94%99%E8%AF%AF%E5%88%86%E6%9E%90.png)
- **历史记录**：自动保存计算历史，支持清空和复制
![历史记录保存.png](docs/images/%E5%8E%86%E5%8F%B2%E8%AE%B0%E5%BD%95%E4%BF%9D%E5%AD%98.png)
- **上一次结果引用**：使用 `ans` 引用上一次计算结果

## 快速开始

### 发布页

- https://github.com/ljx-13/DimCalculator/releases
- https://gitee.com/ljx-13/dim-calculator/releases （国内推荐）

### 环境要求

- Windows 10 及以上
- Linux/macOS 可从源码运行，但未充分测试
- Android/IOS 暂不支持

### 从源码运行

部分开发中的功能可能尚未提供发行版，您可以从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/ljx-13/DimCalculator.git
cd DimCalculator

# 2. 创建并激活虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行主程序
python main.py

# 5. 如需运行测试
python tools/test.py

# 6. 如需打包为exe
pyinstaller --onedir --windowed --icon=datas/icon.ico --name DimCalculator --add-data ".venv/Lib/site-packages/PyQt5/Qt5/plugins;PyQt5/Qt5/plugins" main.py
```

## 项目结构

```text
DimCalculator/
   ├── .gitignore
   ├── LICENSE
   ├── README.md
   ├── datas/  # 数据文件
   │   ├── config.json  # 配置文件
   │   ├── consts.json  # 常量
   │   ├── icon.ico
   │   └── units.json  # 单位
   ├── docs/
   │   ├── help.md  # 帮助文档
   │   └── images/  # 演示图片
   ├── fixme.txt  # 待修复bug及开发计划
   ├── main.py
   ├── requirements.txt
   ├── src/  # 源代码
   │   ├── __init__.py
   │   ├── core.py  # 计算引擎
   │   └── gui.py  # 桌面端界面
   ├── tools/
   │   ├── publish.py  # 更新版本打包发布（自用）
   │   ├── reset.py  # 重置设置
   │   ├── test.py  # 测试
   │   └── tree.py  # 获取项目结构
   └── ui/
       ├── settings.ui  # 设置界面
       └── style.qss  # 样式表
```
