from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from database import Base


class KnowledgeBase(Base):
    """知识库 - 存储产品目录文件信息"""
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    name = Column(String(200), nullable=False, comment="知识库名称")
    description = Column(Text, default="", comment="知识库描述")
    file_path = Column(String(500), default="", comment="原始文件路径")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间")

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name='{self.name}')>"


class KnowledgeItem(Base):
    """知识条目 - 单个产品信息"""
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, comment="所属知识库ID")
    category = Column(String(100), default="", comment="产品分类")
    product_name = Column(String(200), nullable=False, comment="产品名称")
    brand = Column(String(100), default="", comment="品牌")
    model = Column(String(200), default="", comment="产品型号")
    internal_code = Column(String(100), default="", comment="厂家内部型号/编码")
    specs_json = Column(Text, default="{}", comment="产品规格参数（JSON格式）")
    price = Column(Float, default=0.0, comment="产品单价")
    unit = Column(String(20), default="", comment="单位")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间")

    def __repr__(self):
        return f"<KnowledgeItem(id={self.id}, name='{self.product_name}', brand='{self.brand}')>"


class Sheet(Base):
    """表格 - 用户的配置表格数据"""
    __tablename__ = "sheets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    name = Column(String(200), nullable=False, comment="表格名称")
    data_json = Column(Text, default="[]", comment="表格数据（JSON格式，18列数组）")
    mode = Column(String(20), default="manual", comment="模式: learning/semi-auto/full-auto/manual")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间",
    )

    def __repr__(self):
        return f"<Sheet(id={self.id}, name='{self.name}', mode='{self.mode}')>"


class Memory(Base):
    """记忆 - 用户的学习记忆/匹配规则"""
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    name = Column(String(200), nullable=False, comment="记忆名称")
    matching_rules_json = Column(Text, default="[]", comment="匹配规则（JSON格式）")
    parameter_mappings_json = Column(Text, default="{}", comment="参数映射（JSON格式）")
    preferences_json = Column(Text, default="{}", comment="用户偏好（JSON格式）")
    version = Column(Integer, default=1, comment="版本号")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间")

    def __repr__(self):
        return f"<Memory(id={self.id}, name='{self.name}', version={self.version})>"


class LearningLog(Base):
    """学习日志 - 记录用户每次匹配操作和反馈"""
    __tablename__ = "learning_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=True, comment="关联表格ID")
    action = Column(String(50), nullable=False, comment="操作类型: match/correct/confirm/reject")
    input_data = Column(Text, default="{}", comment="输入数据（JSON）")
    output_data = Column(Text, default="{}", comment="输出数据（JSON）")
    feedback = Column(String(20), default="", comment="用户反馈: positive/negative/corrected")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间")

    def __repr__(self):
        return f"<LearningLog(id={self.id}, action='{self.action}', feedback='{self.feedback}')>"
