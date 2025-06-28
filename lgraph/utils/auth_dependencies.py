from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, User
from utils.auth_utils import get_user_from_token

# HTTP Bearer 토큰 스키마
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 정보 반환
    
    Args:
        credentials: HTTP Bearer 토큰
        db: 데이터베이스 세션
    
    Returns:
        User: 인증된 사용자 객체
        
    Raises:
        HTTPException: 인증 실패 시
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    user_data = get_user_from_token(token)
    
    if user_data is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    현재 활성화된 사용자 반환
    
    Args:
        current_user: 현재 사용자
    
    Returns:
        User: 활성화된 사용자 객체
        
    Raises:
        HTTPException: 비활성화된 사용자인 경우
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    관리자 권한이 있는 사용자 반환
    
    Args:
        current_user: 현재 사용자
    
    Returns:
        User: 관리자 사용자 객체
        
    Raises:
        HTTPException: 관리자 권한이 없는 경우
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    선택적 사용자 인증 (토큰이 없어도 허용)
    
    Args:
        credentials: HTTP Bearer 토큰 (선택적)
        db: 데이터베이스 세션
    
    Returns:
        Optional[User]: 인증된 사용자 또는 None
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    user_data = get_user_from_token(token)
    
    if user_data is None:
        return None
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if user is None or not user.is_active:
        return None
    
    return user 