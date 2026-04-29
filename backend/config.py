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

# AI API配置
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
AI_API_BASE = os.getenv("AI_API_BASE", "https://api.openai.com/v1")

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
