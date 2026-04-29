import os
from pathlib import Path

# 数据库配置 - SQLite
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autoconfig.db")

# JWT认证配置
SECRET_KEY = os.getenv("SECRET_KEY", "autoconfig-tool-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24小时

# 文件上传目录
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/")
# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# AI API配置（全局默认值，用户可在前端覆盖）
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
AI_API_BASE = os.getenv("AI_API_BASE", "https://api.openai.com/v1")

# 支持的AI模型列表
SUPPORTED_MODELS = {
    "openai": {
        "name": "OpenAI",
        "base": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o（推荐）"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini（快速）"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base": "https://api.deepseek.com/v1",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3（推荐）"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1（深度推理）"},
        ],
    },
    "siliconflow": {
        "name": "SiliconFlow (硅基流动)",
        "base": "https://api.siliconflow.cn/v1",
        "models": [
            {"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen2.5-72B"},
            {"id": "Qwen/Qwen2-72B-Instruct", "name": "Qwen2-72B"},
            {"id": "Pro/Qwen/Qwen2.5-72B-Instruct", "name": "Qwen2.5-72B Pro"},
            {"id": "THUDM/glm-4-9b-chat", "name": "GLM-4-9B"},
        ],
    },
    "moonshot": {
        "name": "Moonshot (月之暗面)",
        "base": "https://api.moonshot.cn/v1",
        "models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot v1 8K"},
            {"id": "moonshot-v1-32k", "name": "Moonshot v1 32K"},
            {"id": "moonshot-v1-128k", "name": "Moonshot v1 128K"},
        ],
    },
    "baidu": {
        "name": "百度千帆",
        "base": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "models": [
            {"id": "ERNIE-4.0-8K", "name": "ERNIE 4.0"},
            {"id": "ERNIE-3.5-8K", "name": "ERNIE 3.5"},
        ],
    },
    "aliyun": {
        "name": "阿里通义千问",
        "base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            {"id": "qwen-turbo", "name": "Qwen Turbo"},
            {"id": "qwen-plus", "name": "Qwen Plus（推荐）"},
            {"id": "qwen-max", "name": "Qwen Max"},
        ],
    },
    "zhipu": {
        "name": "智谱AI",
        "base": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            {"id": "glm-4-plus", "name": "GLM-4 Plus"},
            {"id": "glm-4-air", "name": "GLM-4 Air"},
        ],
    },
    "ollama": {
        "name": "本地 Ollama",
        "base": "http://localhost:11434/v1",
        "models": [
            {"id": "llama3", "name": "Llama 3"},
            {"id": "qwen2.5", "name": "Qwen 2.5"},
            {"id": "deepseek-r1", "name": "DeepSeek R1"},
            {"id": "mistral", "name": "Mistral"},
        ],
    },
}

# 18列定义 (A-R)
COLUMNS_18 = {
    "A": "序号",
    "B": "设备名称",
    "C": "招标/需求参数",
    "D": "单位",
    "E": "数量",
    "F": "",  # 空列
    "G": "",  # 空列
    "H": "产品名称",
    "I": "产品规格",
    "J": "品牌",
    "K": "产品型号",
    "L": "厂家内部型号",
    "M": "数量",
    "N": "单位",
    "O": "产品单价",
    "P": "总价",
    "Q": "备注",
    "R": "不满足参数",
}

COLUMN_LETTERS = list("ABCDEFGHIJKLMNOPQR")

# A-E 为需求侧，H-R 为产品匹配侧
DEMAND_COLUMNS = ["A", "B", "C", "D", "E"]
PRODUCT_COLUMNS = ["H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R"]
