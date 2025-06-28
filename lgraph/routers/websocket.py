"""
WebSocket 실시간 통신 라우터
- JWT 토큰을 통한 WebSocket 인증
- 팟캐스트 작업 상태 실시간 업데이트
- 에이전트 진행 상황 실시간 알림
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import json
import logging
from typing import Optional

from database import get_db, User
from utils.websocket_manager import manager
from utils.auth_utils import verify_token
# WebSocket에서는 직접 토큰 인증을 구현

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)

async def get_user_from_websocket_token(token: str, db: Session) -> Optional[User]:
    """WebSocket 연결 시 JWT 토큰을 통한 사용자 인증"""
    try:
        payload = verify_token(token, "access")
        if payload is None:
            return None
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if username is None or user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id, User.username == username).first()
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception as e:
        logger.error(f"❌ WebSocket 토큰 인증 실패: {e}")
        return None

@router.websocket("/task-updates")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT 액세스 토큰"),
    db: Session = Depends(get_db)
):
    """
    팟캐스트 작업 상태 실시간 업데이트 WebSocket 연결
    
    Query Parameters:
        token: JWT 액세스 토큰 (Authorization 헤더 대신 쿼리 파라미터 사용)
    
    실시간 전송 메시지 타입:
    - connection_established: 연결 성공 확인
    - task_status_update: 작업 상태 변경 (PENDING -> PROCESSING -> COMPLETED/FAILED)
    - agent_progress_update: 개별 에이전트 실행 진행 상황
    - tts_progress_update: TTS 음성 생성 진행 상황
    """
    # 1. JWT 토큰을 통한 사용자 인증
    user = await get_user_from_websocket_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized: Invalid or expired token")
        return
    
    # 2. WebSocket 연결 수락 및 관리자에 등록
    try:
        await manager.connect(websocket, user)
        
        # 3. 연결 유지 및 메시지 처리 루프
        while True:
            try:
                # 클라이언트로부터 메시지 수신 (ping/pong, heartbeat 등)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # ping 메시지에 대한 pong 응답
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }))
                
                # 기타 클라이언트 요청 처리 (필요에 따라 확장)
                elif message.get("type") == "subscribe_task":
                    task_id = message.get("task_id")
                    if task_id:
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "task_id": task_id,
                            "message": f"Task {task_id} 업데이트 구독 시작"
                        }))
                
            except json.JSONDecodeError:
                logger.warning(f"⚠️ 잘못된 JSON 메시지 수신 - User ID: {user.id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except WebSocketDisconnect:
                logger.info(f"🔌 클라이언트 연결 종료 - User ID: {user.id}")
                break
            
            except Exception as e:
                logger.error(f"❌ WebSocket 메시지 처리 오류 - User ID: {user.id}, Error: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 정상 연결 해제 - User ID: {user.id}")
    except Exception as e:
        logger.error(f"❌ WebSocket 연결 오류 - User ID: {user.id}, Error: {e}")
    finally:
        # 4. 연결 해제 시 관리자에서 제거
        manager.disconnect(websocket)

@router.websocket("/admin/system-updates")
async def admin_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="관리자 JWT 액세스 토큰"),
    db: Session = Depends(get_db)
):
    """
    시스템 관리자용 실시간 모니터링 WebSocket 연결
    - 전체 시스템 상태 모니터링
    - 모든 사용자의 작업 진행 상황 실시간 확인
    """
    # 1. 관리자 권한 확인
    user = await get_user_from_websocket_token(token, db)
    if not user or user.role.value != "admin":
        await websocket.close(code=4003, reason="Forbidden: Admin access required")
        return
    
    try:
        await websocket.accept()
        logger.info(f"👑 관리자 WebSocket 연결됨 - Admin ID: {user.id}")
        
        # 시스템 상태 정보 전송
        await websocket.send_text(json.dumps({
            "type": "admin_connected",
            "message": "관리자 모니터링 WebSocket 연결됨",
            "connected_users": manager.get_connected_users_count(),
            "active_connections": manager.get_active_connections_count()
        }))
        
        # 연결 유지
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "get_system_status":
                await websocket.send_text(json.dumps({
                    "type": "system_status",
                    "connected_users": manager.get_connected_users_count(),
                    "active_connections": manager.get_active_connections_count()
                }))
    
    except WebSocketDisconnect:
        logger.info(f"🔌 관리자 WebSocket 정상 연결 해제 - Admin ID: {user.id}")
    except Exception as e:
        logger.error(f"❌ 관리자 WebSocket 연결 오류 - Admin ID: {user.id}, Error: {e}")

# WebSocket 상태 확인용 HTTP 엔드포인트
@router.get("/status")
async def websocket_status():
    """WebSocket 연결 상태 조회"""
    return {
        "connected_users": manager.get_connected_users_count(),
        "active_connections": manager.get_active_connections_count(),
        "status": "healthy"
    } 