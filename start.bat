@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════════╗
echo ║     AutoConfig Tool · 启动中...          ║
echo ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0backend"
call venv\Scripts\activate.bat
echo 🔧 后端服务: http://localhost:8000
echo 🌐 前端界面: http://localhost:8000/app
echo 📖 API文档:  http://localhost:8000/docs
echo.
python main.py
pause
