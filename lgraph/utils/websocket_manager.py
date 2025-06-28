"""
WebSocket 연결 관리자
- 사용자별 WebSocket 연결 관리
- 인증된 연결만 허용
- 실시간 작업 상태 업데이트 브로드캐스트
"""
import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from database import User
from schemas import TaskStatus
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # user_id: List[WebSocket] 매핑으로 사용자별 다중 연결 지원
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # websocket: user_id 매핑으로 빠른 역방향 조회
        self.connection_user_map: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user: User):
        """인증된 사용자의 WebSocket 연결 수락"""
        await websocket.accept()
        user_id = user.id
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        self.connection_user_map[websocket] = user_id
        
        logger.info(f"✅ WebSocket 연결됨 - User ID: {user_id}, 활성 연결 수: {len(self.active_connections[user_id])}")
        
        # 연결 확인 메시지 전송
        await self.send_personal_message({
            "type": "connection_established",
            "message": "WebSocket 연결이 성공적으로 설정되었습니다.",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self.connection_user_map:
            user_id = self.connection_user_map[websocket]
            
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                
                # 해당 사용자의 연결이 모두 해제되면 딕셔너리에서 제거
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            del self.connection_user_map[websocket]
            logger.info(f"❌ WebSocket 연결 해제됨 - User ID: {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """특정 사용자에게 메시지 전송 (모든 활성 연결에)"""
        if user_id in self.active_connections:
            disconnected_websockets = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"❌ 메시지 전송 실패 - User ID: {user_id}, Error: {e}")
                    disconnected_websockets.append(websocket)
            
            # 연결이 끊어진 WebSocket 정리
            for websocket in disconnected_websockets:
                self.disconnect(websocket)
    
    async def send_task_status_update(self, task_id: int, user_id: int, status: TaskStatus, 
                                    error_message: Optional[str] = None, 
                                    additional_data: Optional[dict] = None):
        """작업 상태 업데이트 메시지 전송"""
        message = {
            "type": "task_status_update",
            "task_id": task_id,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        if additional_data:
            message.update(additional_data)
        
        await self.send_personal_message(message, user_id)
        logger.info(f"📡 작업 상태 업데이트 전송 - Task ID: {task_id}, User ID: {user_id}, Status: {status.value}")
    
    async def send_agent_progress_update(self, task_id: int, user_id: int, 
                                       agent_name: str, agent_status: TaskStatus,
                                       progress_data: Optional[dict] = None):
        """에이전트 진행 상황 업데이트 메시지 전송"""
        message = {
            "type": "agent_progress_update",
            "task_id": task_id,
            "agent_name": agent_name,
            "agent_status": agent_status.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if progress_data:
            message.update(progress_data)
        
        await self.send_personal_message(message, user_id)
        logger.info(f"🤖 에이전트 진행 상황 전송 - Task ID: {task_id}, Agent: {agent_name}, Status: {agent_status.value}")
    
    async def send_tts_progress_update(self, task_id: int, user_id: int, 
                                     tts_status: str, progress_data: Optional[dict] = None):
        """TTS 진행 상황 업데이트 메시지 전송"""
        message = {
            "type": "tts_progress_update",
            "task_id": task_id,
            "tts_status": tts_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if progress_data:
            message.update(progress_data)
        
        await self.send_personal_message(message, user_id)
        logger.info(f"🎵 TTS 진행 상황 전송 - Task ID: {task_id}, TTS Status: {tts_status}")
    
    def get_active_connections_count(self) -> int:
        """전체 활성 연결 수 반환"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_connected_users_count(self) -> int:
        """연결된 사용자 수 반환"""
        return len(self.active_connections)
    
    def is_user_connected(self, user_id: int) -> bool:
        """특정 사용자의 연결 상태 확인"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

# 전역 연결 관리자 인스턴스
manager = ConnectionManager() 