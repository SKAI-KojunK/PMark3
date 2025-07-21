#!/usr/bin/env python3
"""
PMark2.5 테스트 환경 초기 설정 스크립트
필요한 디렉토리와 파일을 생성하고 환경을 준비합니다.
"""

import os
import shutil
import sys

def create_directory_structure():
    """테스트 환경 디렉토리 구조를 생성합니다."""
    directories = [
        "backend/app",
        "backend/app/api",
        "backend/app/agents",
        "backend/app/logic",
        "backend/data",
        "frontend",
        "data"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 디렉토리 생성: {directory}")

def copy_backend_files():
    """기존 백엔드 파일들을 테스트 환경으로 복사합니다."""
    source_dir = "../backend"
    target_dir = "backend"
    
    if not os.path.exists(source_dir):
        print(f"❌ 소스 디렉토리를 찾을 수 없습니다: {source_dir}")
        return False
    
    # 복사할 파일들
    files_to_copy = [
        "requirements.txt",
        "main.py",
        "app/__init__.py",
        "app/config.py",
        "app/database.py",
        "app/models.py",
        "app/api/__init__.py",
        "app/api/chat.py",
        "app/api/work_details.py",
        "app/agents/__init__.py",
        "app/agents/parser.py",
        "app/logic/__init__.py",
        "app/logic/normalizer.py",
        "app/logic/recommender.py"
    ]
    
    for file_path in files_to_copy:
        source_file = os.path.join(source_dir, file_path)
        target_file = os.path.join(target_dir, file_path)
        
        if os.path.exists(source_file):
            # 타겟 디렉토리 생성
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            # 파일 복사
            shutil.copy2(source_file, target_file)
            print(f"📄 파일 복사: {file_path}")
        else:
            print(f"⚠️ 파일을 찾을 수 없습니다: {source_file}")
    
    return True

def create_test_chatbot_html():
    """테스트용 챗봇 HTML 파일을 생성합니다."""
    source_file = "../chatbot.html"
    target_file = "test_chatbot.html"
    
    if os.path.exists(source_file):
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 백엔드 URL을 테스트 환경으로 변경
        content = content.replace('http://localhost:8001', 'http://localhost:8002')
        content = content.replace('http://127.0.0.1:8001', 'http://127.0.0.1:8002')
        
        # 테스트 환경 표시 추가
        content = content.replace('<title>PMark2 AI Assistant</title>', 
                                '<title>PMark2.5 AI Assistant (TEST)</title>')
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📄 테스트용 챗봇 HTML 생성: {target_file}")
        return True
    else:
        print(f"⚠️ 원본 챗봇 HTML을 찾을 수 없습니다: {source_file}")
        return False

def create_env_file():
    """테스트 환경용 .env 파일을 생성합니다."""
    env_content = """# PMark2.5 테스트 환경 설정

# 포트 설정 (기존과 충돌 방지)
TEST_BACKEND_PORT=8010
TEST_FRONTEND_PORT=3010

# 데이터베이스 설정
TEST_DATABASE_URL=sqlite:///./data/test_notifications.db
TEST_SQLITE_DB_PATH=./data/test_notifications.db
TEST_VECTOR_DB_PATH=./data/test_vector_db

# LLM 설정
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

# 파일 경로 설정
NOTIFICATION_HISTORY_FILE=../[Noti이력].xlsx
STATUS_CODE_FILE=../[현상코드].xlsx
EQUIPMENT_TYPE_FILE=../설비유형 자료_20250522.xlsx

# 기타 설정
DEBUG=True
MAX_RECOMMENDATIONS=15
MIN_RECOMMENDATIONS=1
MAX_SQL_RETRY=5
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""
    
    with open(".env", 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("📄 테스트 환경 .env 파일 생성")

def create_init_files():
    """__init__.py 파일들을 생성합니다."""
    init_dirs = [
        "backend/app",
        "backend/app/api",
        "backend/app/agents",
        "backend/app/logic"
    ]
    
    for directory in init_dirs:
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# PMark2.5 Test Environment\n")
            print(f"📄 __init__.py 생성: {init_file}")

def main():
    print("🚀 PMark2.5 테스트 환경 초기 설정 시작...")
    
    # 현재 디렉토리를 test_env로 변경
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_env_dir = os.path.dirname(script_dir)
    os.chdir(test_env_dir)
    
    print(f"📁 작업 디렉토리: {os.getcwd()}")
    
    # 1. 디렉토리 구조 생성
    print("\n1️⃣ 디렉토리 구조 생성 중...")
    create_directory_structure()
    
    # 2. 백엔드 파일 복사
    print("\n2️⃣ 백엔드 파일 복사 중...")
    if not copy_backend_files():
        print("❌ 백엔드 파일 복사 실패")
        return
    
    # 3. 테스트용 챗봇 HTML 생성
    print("\n3️⃣ 테스트용 챗봇 HTML 생성 중...")
    create_test_chatbot_html()
    
    # 4. 환경 설정 파일 생성
    print("\n4️⃣ 환경 설정 파일 생성 중...")
    create_env_file()
    
    # 5. __init__.py 파일 생성
    print("\n5️⃣ __init__.py 파일 생성 중...")
    create_init_files()
    
    print("\n✅ 테스트 환경 초기 설정 완료!")
    print("\n📋 다음 단계:")
    print("1. cd test_env")
    print("2. python scripts/start_test_backend.py")
    print("3. 새 터미널에서: python scripts/start_test_frontend.py")
    print("4. 브라우저에서 http://localhost:3002 접속")

if __name__ == "__main__":
    main() 