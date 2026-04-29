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
    created_at: datetime

    class Config:
        from_attributes = True


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


def get_current_user(token: str = Depends(lambda: None), db: Session = Depends(get_db)) -> User:
    """从JWT令牌中获取当前用户（从Authorization header）"""
    # 这个函数需要从请求中提取token，但FastAPI Depends方式不同
    # 我们在路由中手动处理，这里留作备用
    raise HTTPException(status_code=401, detail="请使用Authorization header传递token")


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
def get_me(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    """获取当前用户信息（从Authorization header解析token）"""
    if not authorization.startswith("Bearer "):
        return {"success": False, "data": None, "error": "缺少Bearer token"}

    token = authorization.replace("Bearer ", "")
    try:
        user = get_user_from_token(token, db)
        return {"success": True, "data": UserResponse.model_validate(user).model_dump(), "error": ""}
    except HTTPException as e:
        return {"success": False, "data": None, "error": e.detail}
    except Exception as e:
        return {"success": False, "data": None, "error": f"Token验证失败: {str(e)}"}
