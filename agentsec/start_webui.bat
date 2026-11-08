@echo off
chcp 65001 >nul
title 靶场 Web 靶场
rem %~dp0 = 本 bat 所在目录（相对定位，项目搬到任何位置/机器都能启动）
cd /d "%~dp0"
echo 正在启动靶场...
echo 启动后请用浏览器访问:  http://127.0.0.1:8765
echo 关闭此窗口即停止服务。
start "" http://127.0.0.1:8765
python webui.py
pause
