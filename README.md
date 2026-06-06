# DimCalculator - 智能量纲计算器

**@ author: ljx-13**
**@ version: 0.1.2**

## 项目简介

**DimCalculator** 是一款为高中物理学习设计的智能量纲计算器。

在高中物理学习中，单位换算是很多同学的易错点。本软件支持直接输入带单位的表达式（如 `5*m + 20*cm`），自动进行单位换算和量纲检查，并给出清晰的计算结果。

该项目作为第40届青少年科技创新大赛的参赛作品创建，目前仍处于早期开发阶段，暂不提供发布版本，仅供学习和交流使用。

### 主要功能

(演示图片来自早期版本，请以实际界面为准)

- **全鼠标操作**：仿 Windows 11 计算器界面，无需键盘即可完成所有操作
- **带单位运算**：支持 `5m + 20cm` 等自然输入
![基本功能.png](images/%E5%9F%BA%E6%9C%AC%E5%8A%9F%E8%83%BD.png)
- **物理常数库**：内置重力加速度 `_g`、光速 `_c`、普朗克常数 `_h` 等常用物理常数
![物理常数.png](images/%E7%89%A9%E7%90%86%E5%B8%B8%E6%95%B0.png)
- **三角函数**：支持 sin、cos、tan，自动识别角度（deg）和弧度（rad）
![数学函数.png](images/%E6%95%B0%E5%AD%A6%E5%87%BD%E6%95%B0.png)
- **智能错误诊断**：对单位不匹配的情况给出具体修改建议
![错误分析.png](images/%E9%94%99%E8%AF%AF%E5%88%86%E6%9E%90.png)
- **历史记录**：自动保存计算历史，支持清空和复制
![历史记录保存.png](images/%E5%8E%86%E5%8F%B2%E8%AE%B0%E5%BD%95%E4%BF%9D%E5%AD%98.png)
- **上一次结果引用**：使用 `ans` 引用上一次计算结果

## 快速开始

### 环境要求

- Python 3.12 或更高版本
- Windows 10 及以上

### 运行步骤

```bash
git clone https://gitee.com/ljx-13/dim-calculator.git
cd DimCalculator
pip install -r requirements.txt
python main.py
```
