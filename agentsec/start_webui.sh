#!/usr/bin/env bash
# agentsec-labs Web 靶场启动脚本（Linux / macOS 服务器）
# 用法：chmod +x start_webui.sh && ./start_webui.sh
# 依赖：Python 3.10+ 与本机 Ollama（默认 localhost:11434，可在 lab/config.py 修改）
cd "$(dirname "$0")"
echo "正在启动靶场..."
echo "启动后请用浏览器访问:  http://127.0.0.1:8765  （Ctrl+C 停止）"
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python
exec "$PYTHON" webui.py
