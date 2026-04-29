from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="哈希后的密码")
    
    # AI API 配置
    api_key = Column(String(500), default="", comment="用户自定义API Key")
    api_base = Column(String(500), default="https://api.openai.com/v1", comment="API Base URL")
    api_model = Column(String(100), default="gpt-3.5-turbo", comment="AI模型名称")
    
    # 用户信息
    display_name = Column(String(100), default="", comment="显示名称")
    avatar_url = Column(String(500), default="", comment="头像URL")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间",
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
