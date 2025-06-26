"""
MinIO 객체 스토리지 클라이언트 유틸리티

오디오 파일을 MinIO에 업로드하고 다운로드하는 기능을 제공합니다.
"""

import os
import io
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from datetime import datetime, timedelta


class MinIOClient:
    """MinIO 객체 스토리지 클라이언트"""
    
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "lgraph-audio")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        # MinIO 클라이언트 초기화
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # 버킷 초기화
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """버킷이 존재하지 않으면 생성합니다."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✅ MinIO 버킷 '{self.bucket_name}' 생성 완료")
            else:
                print(f"✅ MinIO 버킷 '{self.bucket_name}' 확인 완료")
        except S3Error as e:
            print(f"❌ MinIO 버킷 확인/생성 실패: {e}")
            raise
    
    def upload_file(self, object_name: str, file_path: str, content_type: str = "audio/wav") -> dict:
        """파일을 MinIO에 업로드합니다."""
        try:
            # 파일 크기 확인
            file_size = os.path.getsize(file_path)
            
            # 파일 업로드
            with open(file_path, 'rb') as file_data:
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=file_size,
                    content_type=content_type
                )
            
            print(f"✅ MinIO 업로드 완료: {object_name}")
            
            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "file_size": file_size,
                "content_type": content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"MinIO 업로드 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "object_name": object_name
            }
    
    def upload_bytes(self, object_name: str, data: bytes, content_type: str = "audio/wav") -> dict:
        """바이트 데이터를 MinIO에 업로드합니다."""
        try:
            # 바이트 데이터를 스트림으로 변환
            data_stream = io.BytesIO(data)
            file_size = len(data)
            
            # 데이터 업로드
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=file_size,
                content_type=content_type
            )
            
            print(f"✅ MinIO 바이트 업로드 완료: {object_name}")
            
            return {
                "success": True,
                "object_name": object_name,
                "bucket_name": self.bucket_name,
                "file_size": file_size,
                "content_type": content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"MinIO 바이트 업로드 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "object_name": object_name
            }
    
    def download_file(self, object_name: str, file_path: str) -> dict:
        """MinIO에서 파일을 다운로드합니다."""
        try:
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path
            )
            
            file_size = os.path.getsize(file_path)
            
            print(f"✅ MinIO 다운로드 완료: {object_name}")
            
            return {
                "success": True,
                "object_name": object_name,
                "file_path": file_path,
                "file_size": file_size,
                "downloaded_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"MinIO 다운로드 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "object_name": object_name
            }
    
    def get_object_stream(self, object_name: str):
        """MinIO에서 객체를 스트림으로 가져옵니다."""
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return response
        except Exception as e:
            print(f"❌ MinIO 스트림 가져오기 실패: {str(e)}")
            raise
    
    def get_object_info(self, object_name: str) -> Optional[dict]:
        """객체 정보를 가져옵니다."""
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            
            return {
                "object_name": object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified.isoformat(),
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
            
        except Exception as e:
            print(f"❌ MinIO 객체 정보 가져오기 실패: {str(e)}")
            return None
    
    def delete_object(self, object_name: str) -> dict:
        """객체를 삭제합니다."""
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            
            print(f"✅ MinIO 객체 삭제 완료: {object_name}")
            
            return {
                "success": True,
                "object_name": object_name,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"MinIO 객체 삭제 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "object_name": object_name
            }
    
    def generate_presigned_url(self, object_name: str, expires: timedelta = timedelta(hours=1)) -> Optional[str]:
        """객체에 대한 미리 서명된 URL을 생성합니다."""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            print(f"✅ Presigned URL 생성 완료: {object_name}")
            return url
        except Exception as e:
            print(f"❌ Presigned URL 생성 실패: {str(e)}")
            return None
    
    def list_objects(self, prefix: str = "") -> list:
        """버킷의 객체 목록을 가져옵니다."""
        try:
            objects = []
            for obj in self.client.list_objects(self.bucket_name, prefix=prefix):
                objects.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                })
            return objects
        except Exception as e:
            print(f"❌ MinIO 객체 목록 가져오기 실패: {str(e)}")
            return []


# 전역 인스턴스
minio_client = None

def get_minio_client() -> MinIOClient:
    """MinIO 클라이언트 인스턴스를 반환합니다."""
    global minio_client
    if minio_client is None:
        minio_client = MinIOClient()
    return minio_client


if __name__ == "__main__":
    # 테스트 코드
    client = get_minio_client()
    
    # 버킷 리스트 테스트
    objects = client.list_objects()
    print(f"버킷의 객체 수: {len(objects)}")
    
    for obj in objects:
        print(f"  - {obj['object_name']} ({obj['size']} bytes)") 