#!/bin/bash
# AutoConfig Tool - 启动脚本 (WSL/Linux)
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "╔══════════════════════════════════════════╗"
echo "║     AutoConfig Tool · 启动中...          ║"
echo "╚══════════════════════════════════════════╝"

# Start backend server
cd "$DIR/backend"
source venv/bin/activate
echo "🔧 后端服务: http://localhost:8000"
echo "🌐 前端界面: http://localhost:8000/app"
echo "📖 API文档:  http://localhost:8000/docs"
echo ""
python main.py
