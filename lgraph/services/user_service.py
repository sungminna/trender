from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException, status

from database import User, UserRole
from schemas import UserCreate, UserUpdate, UserLogin, UserResponse
from utils.auth_utils import verify_password, get_password_hash, create_token_pair


class UserService:
    """사용자 관련 비즈니스 로직 처리"""
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> UserResponse:
        """
        새 사용자 생성
        
        Args:
            db: 데이터베이스 세션
            user_create: 사용자 생성 정보
        
        Returns:
            UserResponse: 생성된 사용자 정보
            
        Raises:
            HTTPException: 중복된 이메일/사용자명이 있는 경우
        """
        # 중복 검사
        existing_user = db.query(User).filter(
            or_(User.email == user_create.email, User.username == user_create.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_create.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # 비밀번호 해싱
        hashed_password = get_password_hash(user_create.password)
        
        # 사용자 생성
        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            role=UserRole.USER
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return UserResponse.model_validate(db_user)
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        """
        사용자 인증
        
        Args:
            db: 데이터베이스 세션
            login_data: 로그인 정보
        
        Returns:
            Optional[User]: 인증된 사용자 또는 None
        """
        # 이메일 또는 사용자명으로 검색
        user = db.query(User).filter(
            or_(User.email == login_data.username, User.username == login_data.username)
        ).first()
        
        if not user:
            return None
        
        if not verify_password(login_data.password, user.hashed_password):
            return None
        
        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        ID로 사용자 조회
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
        
        Returns:
            Optional[User]: 사용자 또는 None
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        이메일로 사용자 조회
        
        Args:
            db: 데이터베이스 세션
            email: 이메일 주소
        
        Returns:
            Optional[User]: 사용자 또는 None
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        사용자명으로 사용자 조회
        
        Args:
            db: 데이터베이스 세션
            username: 사용자명
        
        Returns:
            Optional[User]: 사용자 또는 None
        """
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[UserResponse]:
        """
        사용자 정보 업데이트
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            user_update: 업데이트할 정보
        
        Returns:
            Optional[UserResponse]: 업데이트된 사용자 정보 또는 None
            
        Raises:
            HTTPException: 중복된 이메일/사용자명이 있는 경우
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # 중복 검사 (현재 사용자 제외)
        if user_update.email or user_update.username:
            existing_user = db.query(User).filter(
                User.id != user_id,
                or_(
                    User.email == user_update.email if user_update.email else False,
                    User.username == user_update.username if user_update.username else False
                )
            ).first()
            
            if existing_user:
                if existing_user.email == user_update.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
        
        # 업데이트 적용
        if user_update.email is not None:
            user.email = user_update.email
        if user_update.username is not None:
            user.username = user_update.username
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        
        db.commit()
        db.refresh(user)
        
        return UserResponse.model_validate(user)
    
    @staticmethod
    def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """
        비밀번호 변경
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            current_password: 현재 비밀번호
            new_password: 새 비밀번호
        
        Returns:
            bool: 변경 성공 여부
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # 현재 비밀번호 확인
        if not verify_password(current_password, user.hashed_password):
            return False
        
        # 새 비밀번호 해싱 및 저장
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        return True
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """
        사용자 비활성화
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
        
        Returns:
            bool: 비활성화 성공 여부
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        
        return True
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        모든 사용자 목록 조회 (관리자용)
        
        Args:
            db: 데이터베이스 세션
            skip: 건너뛸 레코드 수
            limit: 최대 반환 레코드 수
        
        Returns:
            List[UserResponse]: 사용자 목록
        """
        users = db.query(User).offset(skip).limit(limit).all()
        return [UserResponse.model_validate(user) for user in users]
    
    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> dict:
        """
        사용자 로그인 처리
        
        Args:
            db: 데이터베이스 세션
            login_data: 로그인 정보
        
        Returns:
            dict: 토큰 정보
            
        Raises:
            HTTPException: 인증 실패 시
        """
        user = UserService.authenticate_user(db, login_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return create_token_pair(user.id, user.username)


# 인스턴스 생성
user_service = UserService() 