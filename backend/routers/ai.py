import json
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from database import get_db
from models.knowledge import Sheet, LearningLog, KnowledgeBase, KnowledgeItem, Memory
from routers.auth import get_current_user
from models.user import User
from services.ai_agent import AIClient
from services.matching_engine import MatchingEngine
from services.learning_engine import LearningEngine

router = APIRouter(prefix="/api/ai", tags=["AI智能匹配"])


# ========== Pydantic Schemas ==========

class AIQueryRequest(BaseModel):
    """AI查询请求"""
    prompt: str
    knowledge_base_id: Optional[int] = None
    context: Optional[str] = ""


class MatchRequest(BaseModel):
    """单行匹配请求"""
    demand_row: dict  # 需求行数据（至少包含B, C列）
    knowledge_base_id: Optional[int] = None
    sheet_id: Optional[int] = None


class AutoConfigureRequest(BaseModel):
    """全表自动配置请求"""
    sheet_id: int
    knowledge_base_id: Optional[int] = None
    mode: str = "full-auto"  # full-auto 或 semi-auto


class LearnRequest(BaseModel):
    """学习请求 - 用户手动映射"""
    sheet_id: int
    row_index: int
    demand_data: dict  # 需求数据
    product_data: dict  # 用户选择的产品数据
    feedback: str = "corrected"  # positive / negative / corrected


# ========== 工具函数 ==========

def create_ai_client(user: User = None) -> AIClient:
    """创建AI客户端，优先使用用户自定义配置"""
    if user and user.api_key:
        return AIClient(
            api_key=user.api_key,
            api_base=user.api_base,
            model=user.api_model,
        )
    return AIClient()


def load_knowledge_items(knowledge_base_id: int, db: Session) -> list:
    """从知识库加载产品条目"""
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.knowledge_base_id == knowledge_base_id
    ).all()
    return [
        {
            "id": item.id,
            "category": item.category,
            "product_name": item.product_name,
            "brand": item.brand,
            "model": item.model,
            "internal_code": item.internal_code,
            "specs_json": item.specs_json,
            "price": item.price,
            "unit": item.unit,
        }
        for item in items
    ]


# ========== 路由 ==========

@router.post("/query")
async def ai_query(
    req: AIQueryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """通用AI查询 - 带知识库上下文"""
    # 加载知识库上下文
    context = req.context or ""
    if req.knowledge_base_id:
        items = load_knowledge_items(req.knowledge_base_id, db)
        if items:
            context += "\n\n可用产品列表:\n"
            for item in items[:50]:  # 限制上下文长度
                context += f"- {item['product_name']} ({item['brand']} {item['model']})\n"

    # 调用AI（使用用户自定义配置）
    ai = create_ai_client(user)
    try:
        result = ai.query(req.prompt, context)
        return {"success": True, "data": {"response": result}, "error": ""}
    except Exception as e:
        return {"success": False, "data": None, "error": f"AI查询失败: {str(e)}"}


@router.post("/match")
async def match_product(
    req: MatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    匹配需求到产品 - 针对单行需求，返回建议的产品信息
    
    输入: 需求行数据（B=设备名称, C=招标/需求参数, D=单位, E=数量）
    输出: 匹配到的产品信息（H-R列）
    """
    demand_text = f"{req.demand_row.get('B', '')} {req.demand_row.get('C', '')}"
    knowledge_items = []

    # 加载知识库
    if req.knowledge_base_id:
        knowledge_items = load_knowledge_items(req.knowledge_base_id, db)
    else:
        # 尝试从用户的所有知识库加载
        all_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.user_id == user.id).all()
        for kb in all_kbs:
            items = load_knowledge_items(kb.id, db)
            knowledge_items.extend(items)

    # 尝试AI匹配（使用用户自定义配置）
    ai = create_ai_client(user)
    try:
        result = ai.match_demand_to_product(demand_text, knowledge_items)
        if result:
            return {"success": True, "data": result, "error": ""}
    except Exception:
        pass  # AI失败，回退到规则匹配

    # 规则匹配回退
    engine = MatchingEngine()
    match_result = engine.find_best_match(demand_text, knowledge_items)
    
    if match_result:
        # 计算数量和价格
        quantity = req.demand_row.get("E", "1")
        try:
            qty = float(quantity) if quantity else 1
        except (ValueError, TypeError):
            qty = 1
        
        price_info = engine.calculate_price(qty, match_result.get("price", 0))
        
        product_row = {
            "H": match_result.get("product_name", ""),
            "I": match_result.get("specs_json", ""),
            "J": match_result.get("brand", ""),
            "K": match_result.get("model", ""),
            "L": match_result.get("internal_code", ""),
            "M": str(int(qty)),
            "N": match_result.get("unit", ""),
            "O": str(match_result.get("price", 0)),
            "P": str(price_info.get("total", 0)),
            "Q": "",
            "R": "",
        }
        return {"success": True, "data": product_row, "error": ""}

    return {"success": False, "data": None, "error": "未找到匹配产品"}


@router.post("/auto-configure")
async def auto_configure(
    req: AutoConfigureRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    全表自动配置 - 处理所有行，为每条需求匹配最佳产品
    
    处理流程：
    1. 读取表格所有行
    2. 逐行匹配需求到产品
    3. 填充H-Q列（产品信息）
    4. 标记R列（不满足参数）
    """
    # 获取表格
    sheet = db.query(Sheet).filter(Sheet.id == req.sheet_id, Sheet.user_id == user.id).first()
    if not sheet:
        return {"success": False, "data": None, "error": "表格不存在或无权限访问"}

    try:
        rows = json.loads(sheet.data_json) if sheet.data_json else []
    except json.JSONDecodeError:
        return {"success": False, "data": None, "error": "表格数据格式错误"}

    if not rows:
        return {"success": False, "data": None, "error": "表格为空，没有需要处理的数据"}

    # 加载知识库
    knowledge_items = []
    if req.knowledge_base_id:
        knowledge_items = load_knowledge_items(req.knowledge_base_id, db)
    else:
        all_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.user_id == user.id).all()
        for kb in all_kbs:
            items = load_knowledge_items(kb.id, db)
            knowledge_items.extend(items)

    # 加载记忆（学习规则）
    memories = db.query(Memory).filter(Memory.user_id == user.id).order_by(Memory.version.desc()).all()
    memory = memories[0] if memories else None

    ai = create_ai_client(user)
    engine = MatchingEngine()
    learning = LearningEngine()

    # 如果开启了学习模式，加载学习规则
    if req.mode in ("learning", "semi-auto") and memory:
        try:
            learning.load_memory(
                json.loads(memory.matching_rules_json or "[]"),
                json.loads(memory.parameter_mappings_json or "{}"),
                json.loads(memory.preferences_json or "{}"),
            )
        except json.JSONDecodeError:
            pass

    updated_rows = []
    matched_count = 0
    unmatched_count = 0

    for row_idx, row in enumerate(rows):
        demand_text = f"{row.get('B', '')} {row.get('C', '')}"
        quantity_str = row.get("E", "1")
        try:
            qty = float(quantity_str) if quantity_str else 1
        except (ValueError, TypeError):
            qty = 1

        # 初始化产品列
        product_row = {
            "H": "", "I": "", "J": "", "K": "", "L": "",
            "M": "", "N": "", "O": "", "P": "", "Q": "", "R": "",
        }

        matched_product = None

        # 1. 尝试AI匹配（全自动和半自动模式）
        if req.mode in ("full-auto", "semi-auto"):
            try:
                ai_result = ai.auto_configure(demand_text, knowledge_items)
                if ai_result and ai_result.get("H"):
                    matched_product = ai_result
            except Exception:
                pass

        # 2. AI失败或学习模式：尝试规则匹配
        if not matched_product:
            # 检查是否有学习规则
            rule_match = None
            if req.mode == "learning" and memory:
                rule_match = learning.find_matching_rule(demand_text)

            if rule_match:
                matched_product = rule_match
            else:
                # 使用匹配引擎
                result = engine.find_best_match(demand_text, knowledge_items)
                if result:
                    price_info = engine.calculate_price(qty, result.get("price", 0))
                    matched_product = {
                        "H": result.get("product_name", ""),
                        "I": result.get("specs_json", ""),
                        "J": result.get("brand", ""),
                        "K": result.get("model", ""),
                        "L": result.get("internal_code", ""),
                        "M": str(int(qty)),
                        "N": result.get("unit", ""),
                        "O": str(result.get("price", 0)),
                        "P": str(price_info.get("total", 0)),
                        "Q": "",
                        "R": "",
                    }

        if matched_product:
            product_row.update(matched_product)
            # 比较规格，找出不满足的参数
            try:
                demand_spec = row.get("C", "")
                product_spec = matched_product.get("I", "")
                non_match = engine.compare_specs(demand_spec, product_spec)
                if non_match:
                    product_row["R"] = "; ".join(non_match[:5])  # 最多显示5条
            except Exception:
                pass
            matched_count += 1
        else:
            unmatched_count += 1

        # 合并需求列和产品列
        updated_row = {**row, **product_row}
        updated_rows.append(updated_row)

        # 记录学习日志（全自动模式下）
        if req.mode == "full-auto":
            log = LearningLog(
                user_id=user.id,
                sheet_id=sheet.id,
                action="auto_match",
                input_data=json.dumps({"row_index": row_idx, "demand": demand_text}, ensure_ascii=False),
                output_data=json.dumps(product_row, ensure_ascii=False),
                feedback="",
            )
            db.add(log)

    # 更新表格数据
    sheet.data_json = json.dumps(updated_rows, ensure_ascii=False)
    sheet.mode = req.mode
    sheet.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "data": {
            "total_rows": len(rows),
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
            "rows": updated_rows,
        },
        "error": "",
    }


@router.post("/learn")
async def learn_from_example(
    req: LearnRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    学习样本 - 用户手动映射需求到产品后的反馈学习
    
    将用户的手动修正记录为学习样本，更新匹配规则
    """
    # 记录学习日志
    log = LearningLog(
        user_id=user.id,
        sheet_id=req.sheet_id,
        action="manual_mapping",
        input_data=json.dumps(req.demand_data, ensure_ascii=False),
        output_data=json.dumps(req.product_data, ensure_ascii=False),
        feedback=req.feedback,
    )
    db.add(log)

    # 更新记忆（学习规则）
    learning = LearningEngine()
    updated_rules = learning.learn_from_example(req.demand_data, req.product_data)

    # 查找或创建记忆
    memory = db.query(Memory).filter(
        Memory.user_id == user.id,
    ).order_by(Memory.version.desc()).first()

    if memory:
        # 更新现有记忆
        try:
            existing_rules = json.loads(memory.matching_rules_json) if memory.matching_rules_json else []
        except json.JSONDecodeError:
            existing_rules = []
        
        # 合并规则
        for new_rule in updated_rules:
            # 检查是否已存在相似规则
            exists = any(
                r.get("keyword", "").lower() == new_rule.get("keyword", "").lower()
                for r in existing_rules
            )
            if not exists:
                existing_rules.append(new_rule)

        memory.matching_rules_json = json.dumps(existing_rules, ensure_ascii=False)
        memory.version += 1
    else:
        # 创建新记忆
        memory = Memory(
            user_id=user.id,
            name=f"自动记忆 v1",
            matching_rules_json=json.dumps(updated_rules, ensure_ascii=False),
            parameter_mappings_json="{}",
            preferences_json="{}",
            version=1,
        )
        db.add(memory)

    db.commit()
    db.refresh(memory)

    return {
        "success": True,
        "data": {
            "memory_id": memory.id,
            "version": memory.version,
            "rules_count": len(updated_rules),
            "message": "学习成功，已更新匹配规则",
        },
        "error": "",
    }
