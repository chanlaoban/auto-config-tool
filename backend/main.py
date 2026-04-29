"""
AutoConfig Tool - 企业级自动配置工具后端

FastAPI应用入口 - 包含所有路由、中间件、启动事件
"""
import sys
import os
from pathlib import Path

# 确保backend目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from database import init_db
from config import COLUMNS_18

# 导入路由
from routers import auth, sheets, ai, memory

# 前端文件路径（相对于main.py的上一级目录）
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# 创建FastAPI应用实例
app = FastAPI(
    title="AutoConfig Tool API",
    description="企业级自动配置工具后端API - 支持学习/半自动/全自动三种模式",
    version="1.0.0",
)

# ========== CORS配置 ==========
# 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 全局异常处理 ==========

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器 - 统一错误格式"""
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": f"服务器内部错误: {str(exc)}"},
    )


# ========== 注册路由 ==========

app.include_router(auth.router)
app.include_router(sheets.router)
app.include_router(ai.router)
app.include_router(memory.router)


# ========== 前端静态文件 ==========

# Serve the main frontend page
@app.get("/app", response_class=FileResponse)
async def serve_app():
    """返回前端应用主页"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=404,
        content={"success": False, "data": None, "error": "前端文件未找到"},
    )


# Redirect root to /app (frontend) for browser access
@app.get("/")
async def root():
    """根路径 - 返回API状态或重定向到前端"""
    from fastapi.responses import RedirectResponse
    # Check if request accepts HTML (browser) vs JSON (API client)
    # For simplicity, always redirect to frontend
    return RedirectResponse(url="/app")


# ========== 启动事件 ==========

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    try:
        init_db()
        print("✓ 数据库初始化成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")


# ========== 主入口 ==========

if __name__ == "__main__":
    import uvicorn
    print("╔══════════════════════════════════════════╗")
    print("║    AutoConfig Tool API Server v1.0       ║")
    print("╠══════════════════════════════════════════╣")
    print("║  前端:   http://localhost:8000/app        ║")
    print("║  API:    http://localhost:8000/api/...    ║")
    print("║  文档:   http://localhost:8000/docs       ║")
    print("╚══════════════════════════════════════════╝")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
