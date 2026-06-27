@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    DimCalculator 发布脚本
echo ========================================
echo.

:: 读取版本号
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
set /p confirm="[1/4] 版本号已更新？(y/n): "
if /i not "%confirm%"=="y" pause & exit /b 0

:: 提交信息
echo.
set /p commit_msg="[2/4] 提交信息（留空=更新版本）: "
if "%commit_msg%"=="" set commit_msg=更新版本
echo 提交信息: %commit_msg%
echo.
set /p confirm="确认提交？(y/n): "
if /i not "%confirm%"=="y" echo 已取消 & exit /b 0

:: Git 提交并打标签
echo.
echo 正在提交...
git add .
git tag -a "%VERSION%" -m "%commit_msg%" 2>nul
git commit -m "%commit_msg%"
if errorlevel 1 (echo [警告] 提交失败或无变更) else echo 提交成功

:: 确认打包
echo.
set /p confirm="[3/4] 确认开始打包？(y/n): "
if /i not "%confirm%"=="y" goto skip_pack

:: 删除旧 dist
echo.
echo 删除旧 dist...
if exist dist rmdir /s /q dist & echo dist 已删除

:: 打包
echo.
echo 正在打包，请稍候...
pyinstaller --onedir --windowed --icon=datas/icon.ico --name DimCalculator --add-data ".venv/Lib/site-packages/PyQt5/Qt5/plugins;PyQt5/Qt5/plugins" main.py
if errorlevel 1 (echo [错误] 打包失败！ & pause & exit /b 1)

:: 准备运行环境（log + 资源文件）
echo.
echo 正在准备运行环境...
if exist "dist\DimCalculator" (
    mkdir "dist\DimCalculator\log" 2>nul && echo log 文件夹已创建
    if exist "src" xcopy /E /I /Y "src" "dist\DimCalculator\src" >nul & echo 已复制 src
    if exist "datas" xcopy /E /I /Y "datas" "dist\DimCalculator\datas" >nul & echo 已复制 datas
)

:skip_pack

:: 推送到远程
echo.
set /p confirm="[4/4] 是否推送到远程？(y/n): "
if /i not "%confirm%"=="y" echo 跳过推送 & exit /b 0

echo 正在推送到 GitHub...
git push origin main
if errorlevel 1 (echo [警告] GitHub 推送失败) else echo GitHub 推送成功

echo 正在推送到 Gitee...
git push gitee main
if errorlevel 1 (echo [警告] Gitee 推送失败) else echo Gitee 推送成功

echo.
echo ========================================
echo    ✓ 发布完成！
echo ========================================
echo    版本: %VERSION%
echo    文件: dist\DimCalculator\DimCalculator.exe
echo ========================================
pause
