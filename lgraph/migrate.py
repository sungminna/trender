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
            "sqlalchemy.url = postgresql://lgraph_user:lgraph_password@localhost:5432/lgraph"
        )
        
        with open("alembic.ini", "w") as f:
            f.write(content)
        
        # env.py 설정
        env_content = '''from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config, pool
from alembic import context

# 현재 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import Base

config = context.config

# 환경 변수에서 DATABASE_URL 가져오기
database_url = os.getenv("DATABASE_URL")
if database_url:
    database_url = database_url.replace("asyncpg", "psycopg2")
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        
        with open("alembic/env.py", "w") as f:
            f.write(env_content)
        
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