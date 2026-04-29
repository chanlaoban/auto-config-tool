# 📋 AutoConfig Tool — 智能配置表格系统

企业级智能配置表格系统，面向系统集成商/设备供应商。根据客户需求（招标参数），结合厂家产品知识库，自动生成设备配置清单。对标 WPS 表格的交互体验，内嵌 AI 智能体实现配置自动化。

## ✨ 核心价值

- **⚡ 秒级配单**：人工翻阅产品手册配单需要数小时，AI 配单秒级完成
- **🧠 知识沉淀**：每次配单都是对 AI 的训练，越用越精准
- **🌐 分布式学习**：团队配单经验可共享，新人也能配出老手的水平

## 🏗️ 项目结构

```
auto-config-tool/
├── backend/          # FastAPI 后端
│   ├── main.py       # 入口文件
│   ├── config.py     # 配置文件
│   ├── database.py   # 数据库操作
│   ├── models/       # 数据模型
│   ├── routers/      # API 路由
│   └── services/     # 业务逻辑（AI、匹配、学习引擎）
├── frontend/         # 前端界面
├── scripts/          # 工具脚本
├── DESIGN.md         # 详细设计文档
├── start.bat         # Windows 启动脚本
└── start.sh          # Linux/Mac 启动脚本
```

## 🚀 快速启动

### 环境要求

- Python 3.10+
- Node.js (前端)
- pip / npm

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 一键启动

```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

## 🔧 核心功能

| 模式 | 说明 |
|:----|:----|
| 🎓 **学习模式** | 上传产品资料（Excel/PDF/Word），AI 自动学习产品体系和参数规格 |
| 🔍 **搜索模式** | 智能搜索知识库，快速定位产品和参数 |
| 🤖 **匹配模式** | 根据招标需求自动匹配最佳产品配置方案 |

## 📊 表格规范

表格包含 18 列（A-R），分为三大区域：

- **需求区** (A-E)：客户招标原始内容
- **配置区** (H-Q)：厂家的配置响应方案
- **差异区** (R)：需求与规格的不满足项标注

## 🛠️ 技术栈

- **后端**：FastAPI + SQLite + LangChain/AI
- **前端**：React/Vue (WPS-like 表格交互)
- **AI**：支持多种 LLM 接入，实现智能匹配与学习

## 📄 License

MIT
