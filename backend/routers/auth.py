from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_db
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from models.user import User

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ========== Pydantic Schemas ==========

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: str


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    display_name: str = ""
    avatar_url: str = ""
    api_key: str = ""
    api_base: str = ""
    api_model: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """更新个人资料请求"""
    display_name: Optional[str] = None
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


class UpdateApiSettingsRequest(BaseModel):
    """更新AI API配置请求"""
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_model: Optional[str] = None


# ========== 工具函数 ==========

def hash_password(password: str) -> str:
    """对密码进行哈希处理（bcrypt限制72字节，提前截断）"""
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_from_token(token: str, db: Session) -> User:
    """从token解析并获取用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    """从Authorization header获取当前用户"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少Bearer token")
    token = authorization.replace("Bearer ", "")
    return get_user_from_token(token, db)


# ========== 路由 ==========

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册 - 创建新账号"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == req.username).first()
    if existing_user:
        return {"success": False, "data": None, "error": "用户名已存在"}

    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == req.email).first()
    if existing_email:
        return {"success": False, "data": None, "error": "邮箱已被注册"}

    # 创建新用户
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        display_name=req.username,
        api_base="https://api.openai.com/v1",
        api_model="gpt-3.5-turbo",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"success": True, "data": UserResponse.model_validate(user).model_dump(), "error": ""}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录 - 返回JWT令牌"""
    # 查找用户
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        return {"success": False, "data": None, "error": "用户名或密码错误"}

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(),
        },
        "error": "",
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {"success": True, "data": UserResponse.model_validate(user).model_dump(), "error": ""}


@router.put("/profile")
def update_profile(req: UpdateProfileRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新个人资料"""
    if req.display_name is not None:
        user.display_name = req.display_name
    if req.email is not None:
        # 检查邮箱是否被其他用户使用
        existing = db.query(User).filter(User.email == req.email, User.id != user.id).first()
        if existing:
            return {"success": False, "data": None, "error": "邮箱已被其他账号使用"}
        user.email = req.email
    
    db.commit()
    db.refresh(user)
    return {"success": True, "data": UserResponse.model_validate(user).model_dump(), "error": ""}


@router.put("/password")
def change_password(req: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改密码"""
    if not verify_password(req.old_password, user.hashed_password):
        return {"success": False, "data": None, "error": "原密码错误"}
    
    if len(req.new_password) < 6:
        return {"success": False, "data": None, "error": "新密码长度不少于6位"}
    
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"success": True, "data": {"message": "密码修改成功"}, "error": ""}


@router.get("/api-settings")
def get_api_settings(user: User = Depends(get_current_user)):
    """获取AI API配置"""
    return {
        "success": True,
        "data": {
            "api_key": user.api_key or "",
            "api_base": user.api_base or "https://api.openai.com/v1",
            "api_model": user.api_model or "gpt-3.5-turbo",
        },
        "error": "",
    }


@router.put("/api-settings")
def update_api_settings(req: UpdateApiSettingsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新AI API配置"""
    if req.api_key is not None:
        user.api_key = req.api_key
    if req.api_base is not None:
        user.api_base = req.api_base
    if req.api_model is not None:
        user.api_model = req.api_model
    
    db.commit()
    return {
        "success": True,
        "data": {
            "api_key": user.api_key or "",
            "api_base": user.api_base or "https://api.openai.com/v1",
            "api_model": user.api_model or "gpt-3.5-turbo",
        },
        "error": "",
    }
