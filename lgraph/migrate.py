#!/usr/bin/env python3
"""
간단한 데이터베이스 마이그레이션 도구
"""

import subprocess
import sys
from pathlib import Path


def init_alembic():
    """Alembic을 초기화합니다."""
    print("🔧 Alembic 초기화 중...")
    
    try:
        # Alembic 초기화
        subprocess.run(["poetry", "run", "alembic", "init", "alembic"], check=True)
        
        # alembic.ini 설정
        with open("alembic.ini", "r") as f:
            content = f.read()
        
        content = content.replace(
            "sqlalchemy.url = driver://user:pass@localhost/dbname",
            "sqlalchemy.url = postgresql+psycopg2://lgraph_user:lgraph_password@localhost:5432/lgraph"
        )
        
        with open("alembic.ini", "w") as f:
            f.write(content)
        
        # env.py 설정 (Base import 및 target_metadata 자동 추가)
        env_path = Path("alembic/env.py")
        env_content = env_path.read_text()
        if "from database import Base" not in env_content:
            insert_code = (
                "import sys\n"
                "import os\n"
                "sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))\n"
                "from database import Base\n"
                "target_metadata = Base.metadata\n"
            )
            env_content = env_content.replace("target_metadata = None", insert_code)
            env_path.write_text(env_content)
        
        print("✅ Alembic 초기화 완료")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Alembic 초기화 실패: {e}")
        return False
    
    return True


def create_migration(message):
    """새 마이그레이션을 생성합니다."""
    print(f"📄 마이그레이션 생성 중: {message}")
    
    try:
        subprocess.run([
            "poetry", "run", "alembic", "revision", "--autogenerate", 
            "-m", message
        ], check=True)
        print("✅ 마이그레이션 생성 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 마이그레이션 생성 실패: {e}")
        return False


def apply_migrations():
    """마이그레이션을 적용합니다."""
    print("🔄 마이그레이션 적용 중...")
    
    try:
        subprocess.run(["poetry", "run", "alembic", "upgrade", "head"], check=True)
        print("✅ 마이그레이션 적용 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 마이그레이션 적용 실패: {e}")
        return False


def setup_and_migrate():
    """전체 설정 및 마이그레이션을 수행합니다."""
    
    # Alembic이 없으면 초기화
    if not Path("alembic").exists():
        if not init_alembic():
            return False
    
    # 초기 마이그레이션 생성
    if not create_migration("Initial migration"):
        return False
    
    # 마이그레이션 적용
    return apply_migrations()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="데이터베이스 마이그레이션 도구")
    parser.add_argument("command", 
                       choices=["init", "create", "apply", "setup"], 
                       help="실행할 명령")
    parser.add_argument("-m", "--message", 
                       default="Auto migration",
                       help="마이그레이션 메시지")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_alembic()
    elif args.command == "create":
        create_migration(args.message)
    elif args.command == "apply":
        apply_migrations()
    elif args.command == "setup":
        setup_and_migrate() 