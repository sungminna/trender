from datetime import datetime, timedelta
from typing import Optional, Union
from passlib.context import CryptContext
from jose import JWTError, jwt
from config import settings

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT Access Token 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """JWT Refresh Token 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    토큰 검증
    
    Args:
        token: JWT 토큰
        token_type: 토큰 타입 ("access" 또는 "refresh")
    
    Returns:
        토큰 payload 또는 None (유효하지 않은 경우)
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_from_token(token: str) -> Optional[dict]:
    """
    토큰에서 사용자 정보 추출
    
    Args:
        token: JWT access token
    
    Returns:
        사용자 정보 dict 또는 None
    """
    payload = verify_token(token, "access")
    if payload is None:
        return None
    
    user_id: int = payload.get("user_id")
    username: str = payload.get("sub")
    
    if user_id is None or username is None:
        return None
        
    return {"user_id": user_id, "username": username}


def create_token_pair(user_id: int, username: str) -> dict:
    """
    Access Token과 Refresh Token 쌍 생성
    
    Args:
        user_id: 사용자 ID
        username: 사용자명
    
    Returns:
        토큰 쌍 dict
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": username, "user_id": user_id},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": username, "user_id": user_id}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    } 