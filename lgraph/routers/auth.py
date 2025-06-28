from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from database import get_db, User
from schemas import (
    UserCreate, UserResponse, UserLogin, Token, UserUpdate,
    ChangePasswordRequest, RefreshTokenRequest
)
from services.user_service import user_service
from utils.auth_dependencies import get_current_active_user, get_admin_user
from utils.auth_utils import verify_token, create_token_pair

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    사용자 회원가입
    
    - **email**: 유효한 이메일 주소 (고유해야 함)
    - **username**: 사용자명 (3-50자, 고유해야 함)
    - **password**: 비밀번호 (6-100자)
    - **full_name**: 전체 이름 (선택사항)
    """
    return user_service.create_user(db, user_create)


@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    사용자 로그인
    
    - **username**: 이메일 또는 사용자명
    - **password**: 비밀번호
    
    Returns:
        - **access_token**: API 요청에 사용할 토큰 (30분 유효)
        - **refresh_token**: 토큰 갱신용 토큰 (7일 유효)
    """
    token_data = user_service.login_user(db, login_data)
    return token_data


@router.post("/login/form", response_model=Token)
async def login_with_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 호환 로그인 (Swagger UI용)
    """
    login_data = UserLogin(username=form_data.username, password=form_data.password)
    token_data = user_service.login_user(db, login_data)
    return token_data


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Access Token 갱신
    
    - **refresh_token**: 유효한 refresh token
    
    Returns:
        새로운 access_token과 refresh_token 쌍
    """
    # Refresh token 검증
    payload = verify_token(refresh_request.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    username = payload.get("sub")
    
    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 존재 및 활성 상태 확인
    user = user_service.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 새 토큰 쌍 생성
    return create_token_pair(user.id, user.username)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    현재 로그인한 사용자의 프로필 정보 조회
    
    Headers:
        Authorization: Bearer {access_token}
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자의 프로필 정보 수정
    
    - **email**: 새 이메일 주소 (선택사항)
    - **username**: 새 사용자명 (선택사항)
    - **full_name**: 새 전체 이름 (선택사항)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    updated_user = user_service.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user


@router.post("/change-password")
async def change_password(
    password_request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    비밀번호 변경
    
    - **current_password**: 현재 비밀번호
    - **new_password**: 새 비밀번호 (6-100자)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    success = user_service.change_password(
        db, 
        current_user.id, 
        password_request.current_password, 
        password_request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return {"message": "Password changed successfully"}


@router.post("/deactivate")
async def deactivate_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    계정 비활성화 (현재 사용자)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    success = user_service.deactivate_user(db, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Account deactivated successfully"}


# 관리자 전용 엔드포인트
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    모든 사용자 목록 조회 (관리자 전용)
    
    Query Parameters:
        - **skip**: 건너뛸 레코드 수 (기본값: 0)
        - **limit**: 최대 반환 레코드 수 (기본값: 100)
    
    Headers:
        Authorization: Bearer {admin_access_token}
    """
    return user_service.get_all_users(db, skip, limit)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    특정 사용자 정보 조회 (관리자 전용)
    
    Path Parameters:
        - **user_id**: 사용자 ID
    
    Headers:
        Authorization: Bearer {admin_access_token}
    """
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/deactivate")
async def deactivate_user_by_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    특정 사용자 계정 비활성화 (관리자 전용)
    
    Path Parameters:
        - **user_id**: 사용자 ID
    
    Headers:
        Authorization: Bearer {admin_access_token}
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    success = user_service.deactivate_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": f"User {user_id} deactivated successfully"} 