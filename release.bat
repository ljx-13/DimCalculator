@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    DimCalculator 发布脚本
echo ========================================
echo.

:: 步骤1：确认 VERSION 已更新
for /f "tokens=2 delims=:," %%i in ('findstr /i /c:"\"version\"" datas\config.json') do (
    set VERSION=%%~i
    set VERSION=!VERSION: =!
    set VERSION=!VERSION:"=!
    set VERSION=!VERSION:}=!
)
if not defined VERSION (
    echo [警告] config.json 中未找到 version 字段
    set /p VERSION="请输入版本号: "
)

echo 当前版本: %VERSION%
echo.
set /p confirm="[1/5] 版本号已更新？(y/n): "
if /i not "%confirm%"=="y" (
    pause
    exit /b 0
)

:: 步骤2：获取提交信息
echo.
set /p commit_msg="[2/5] 提交信息（留空=更新版本）: "
if "%commit_msg%"=="" set commit_msg=更新版本
echo 提交信息: %commit_msg%
echo.
set /p confirm="确认提交？(y/n): "
if /i not "%confirm%"=="y" (
    echo 已取消
    exit /b 0
    pause
)

:: 步骤3：Git 提交
echo.
echo [3/5] 正在提交...
git add .
git tag -a %version% -m "%commit_msg%"
git commit -m "%commit_msg%"
if errorlevel 1 (
    echo [警告] 提交失败或无变更
) else (
    echo 提交成功
)

:: 步骤6：确认打包
echo.
set /p confirm="[4/5] 确认开始打包？(y/n): "
if /i not "%confirm%"=="y" (
    echo 已取消打包
    exit /b 0
    pause
)

:: 步骤5：删除旧 dist
echo.
echo [5/6] 删除旧 dist...
if exist dist (
    rmdir /s /q dist
    echo dist 已删除
)

:: 步骤7：打包
echo.
echo 正在打包，请稍候...
pyinstaller --onedir --windowed --icon=../datas/icon.ico --name DimCalculator --add-data ".venv/Lib/site-packages/PyQt5/Qt5/plugins;PyQt5/Qt5/plugins" main.py

if errorlevel 1 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)

:: ===== 新增：在打包好的程序路径下创建 log 文件夹 =====
echo.
echo 正在创建 log 文件夹...
if exist "dist\DimCalculator" (
    mkdir "dist\DimCalculator\log" 2>nul
    echo log 文件夹已创建在 dist\DimCalculator\log
) else (
    echo [警告] 找不到 dist\DimCalculator 目录，请手动创建 log 文件夹
)

:: 步骤4：推送到 GitHub
echo.
set /p confirm="[5/5] 是否推送到远程？(y/n): "
if /i not "%confirm%"=="y" (
    echo 跳过推送
    exit /b 0
)

echo 正在推送到 GitHub...
git push origin main
if errorlevel 1 (
    echo [警告] GitHub 推送失败
) else (
    echo GitHub 推送成功
)

echo 正在推送到 Gitee...
git push gitee main
if errorlevel 1 (
    echo [警告] Gitee 推送失败
) else (
    echo Gitee 推送成功
)

:skip_push



echo.
echo ========================================
echo    ✓ 发布完成！
echo ========================================
echo    版本: %VERSION%
echo    文件: dist\DimCalculator.exe
echo ========================================
pause