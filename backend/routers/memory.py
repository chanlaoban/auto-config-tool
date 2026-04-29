import json
import os
import uuid
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from database import get_db
from config import UPLOAD_DIR
from models.knowledge import Memory, LearningLog
from routers.auth import get_user_from_token

router = APIRouter(prefix="/api/memory", tags=["记忆管理"])


# ========== 工具函数 ==========

def get_token_from_header(authorization: str) -> str:
    """从Authorization header提取token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少Bearer token")
    return authorization.replace("Bearer ", "")


# ========== 路由 ==========

@router.get("")
def list_memories(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有记忆列表"""
    token = get_token_from_header(authorization)
    user = get_user_from_token(token, db)

    memories = db.query(Memory).filter(
        Memory.user_id == user.id,
    ).order_by(Memory.version.desc()).all()

    result = []
    for m in memories:
        result.append({
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "created_at": m.created_at.isoformat() if m.created_at else "",
            "rules_count": len(json.loads(m.matching_rules_json)) if m.matching_rules_json else 0,
        })

    return {"success": True, "data": result, "error": ""}


@router.post("/export")
def export_memory(
    memory_id: Optional[int] = None,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """
    导出记忆为 .mem 文件（JSON格式）
    如果指定memory_id则导出指定记忆，否则导出最新版本
    """
    token = get_token_from_header(authorization)
    user = get_user_from_token(token, db)

    if memory_id:
        memory = db.query(Memory).filter(
            Memory.id == memory_id,
            Memory.user_id == user.id,
        ).first()
    else:
        memory = db.query(Memory).filter(
            Memory.user_id == user.id,
        ).order_by(Memory.version.desc()).first()

    if not memory:
        return {"success": False, "data": None, "error": "未找到记忆数据"}

    # 构建.mem文件内容
    mem_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user.id,
        "username": user.username,
        "memory": {
            "id": memory.id,
            "name": memory.name,
            "version": memory.version,
            "matching_rules": json.loads(memory.matching_rules_json) if memory.matching_rules_json else [],
            "parameter_mappings": json.loads(memory.parameter_mappings_json) if memory.parameter_mappings_json else {},
            "preferences": json.loads(memory.preferences_json) if memory.preferences_json else {},
            "created_at": memory.created_at.isoformat() if memory.created_at else "",
        },
    }

    # 写入临时文件
    export_filename = f"memory_{user.id}_{memory.id}_{uuid.uuid4().hex[:8]}.mem"
    export_path = os.path.join(UPLOAD_DIR, export_filename)
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(mem_data, f, ensure_ascii=False, indent=2)

    return FileResponse(
        path=export_path,
        filename=f"{memory.name}.mem",
        media_type="application/json",
    )


@router.post("/import")
async def import_memory(
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """
    导入 .mem 记忆文件
    解析并合并到用户的现有记忆中
    """
    token = get_token_from_header(authorization)
    user = get_user_from_token(token, db)

    # 验证文件扩展名
    if not file.filename.endswith(".mem"):
        return {"success": False, "data": None, "error": "仅支持 .mem 文件格式"}

    # 读取上传文件
    content = await file.read()
    try:
        mem_data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"success": False, "data": None, "error": f"文件格式错误: {str(e)}"}

    # 验证.mem文件结构
    if "memory" not in mem_data:
        return {"success": False, "data": None, "error": "无效的.mem文件格式"}

    imported_memory = mem_data["memory"]

    # 获取用户最新记忆
    existing = db.query(Memory).filter(
        Memory.user_id == user.id,
    ).order_by(Memory.version.desc()).first()

    if existing:
        # 合并到现有记忆
        try:
            existing_rules = json.loads(existing.matching_rules_json) if existing.matching_rules_json else []
        except json.JSONDecodeError:
            existing_rules = []

        imported_rules = imported_memory.get("matching_rules", [])

        # 合并规则（去重）
        existing_keywords = {r.get("keyword", "").lower() for r in existing_rules if r.get("keyword")}
        new_rules_count = 0
        for rule in imported_rules:
            keyword = rule.get("keyword", "").lower()
            if keyword and keyword not in existing_keywords:
                existing_rules.append(rule)
                existing_keywords.add(keyword)
                new_rules_count += 1

        existing.matching_rules_json = json.dumps(existing_rules, ensure_ascii=False)
        existing.name = f"{existing.name} + 导入记忆"
        existing.version += 1

        # 合并参数映射
        try:
            existing_mappings = json.loads(existing.parameter_mappings_json) if existing.parameter_mappings_json else {}
        except json.JSONDecodeError:
            existing_mappings = {}
        imported_mappings = imported_memory.get("parameter_mappings", {})
        existing_mappings.update(imported_mappings)
        existing.parameter_mappings_json = json.dumps(existing_mappings, ensure_ascii=False)

        db.commit()
        db.refresh(existing)

        return {
            "success": True,
            "data": {
                "memory_id": existing.id,
                "version": existing.version,
                "new_rules": new_rules_count,
                "message": f"成功导入 {new_rules_count} 条新规则",
            },
            "error": "",
        }
    else:
        # 创建新记忆
        new_memory = Memory(
            user_id=user.id,
            name=imported_memory.get("name", "导入的记忆"),
            matching_rules_json=json.dumps(imported_memory.get("matching_rules", []), ensure_ascii=False),
            parameter_mappings_json=json.dumps(imported_memory.get("parameter_mappings", {}), ensure_ascii=False),
            preferences_json=json.dumps(imported_memory.get("preferences", {}), ensure_ascii=False),
            version=1,
        )
        db.add(new_memory)
        db.commit()
        db.refresh(new_memory)

        return {
            "success": True,
            "data": {
                "memory_id": new_memory.id,
                "version": 1,
                "new_rules": len(imported_memory.get("matching_rules", [])),
                "message": "成功创建新记忆",
            },
            "error": "",
        }


@router.post("/sync")
def sync_memory(
    memory_id: Optional[int] = None,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """
    同步记忆到云端存储
    
    目前实现为本地存储（备份到文件），可扩展为真正的云同步
    """
    token = get_token_from_header(authorization)
    user = get_user_from_token(token, db)

    if memory_id:
        memory = db.query(Memory).filter(
            Memory.id == memory_id,
            Memory.user_id == user.id,
        ).first()
    else:
        memory = db.query(Memory).filter(
            Memory.user_id == user.id,
        ).order_by(Memory.version.desc()).first()

    if not memory:
        return {"success": False, "data": None, "error": "未找到记忆数据"}

    # 备份到本地文件（模拟云同步）
    sync_data = {
        "user_id": user.id,
        "username": user.username,
        "memory_id": memory.id,
        "name": memory.name,
        "version": memory.version,
        "matching_rules": json.loads(memory.matching_rules_json) if memory.matching_rules_json else [],
        "parameter_mappings": json.loads(memory.parameter_mappings_json) if memory.parameter_mappings_json else {},
        "preferences": json.loads(memory.preferences_json) if memory.preferences_json else {},
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }

    # 写入同步备份
    sync_filename = f"sync_backup_user_{user.id}_{uuid.uuid4().hex[:8]}.json"
    sync_path = os.path.join(UPLOAD_DIR, sync_filename)
    with open(sync_path, "w", encoding="utf-8") as f:
        json.dump(sync_data, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "data": {
            "memory_id": memory.id,
            "version": memory.version,
            "synced_at": sync_data["synced_at"],
            "backup_file": sync_filename,
            "message": "记忆同步成功（本地备份）",
        },
        "error": "",
    }
