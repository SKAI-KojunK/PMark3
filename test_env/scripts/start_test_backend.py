#!/usr/bin/env python3
"""
PMark2.5 테스트 환경 백엔드 시작 스크립트
포트 8002를 사용하여 기존 프로젝트와 충돌하지 않습니다.
"""

import os
import sys
import subprocess
import socket
import time

def check_port_available(port):
    """포트가 사용 가능한지 확인"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            return True
    except OSError:
        return False

def find_free_port(start_port=8002, max_attempts=10):
    """사용 가능한 포트를 찾습니다."""
    for port in range(start_port, start_port + max_attempts):
        if check_port_available(port):
            return port
    return None

def main():
    print("🚀 PMark2.5 테스트 환경 백엔드 시작 중...")
    
    # 현재 디렉토리를 test_env로 변경
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_env_dir = os.path.dirname(script_dir)
    os.chdir(test_env_dir)
    
    print(f"📁 작업 디렉토리: {os.getcwd()}")
    
    # 포트 확인 (기존과 충돌 방지) - 8010부터 순차적으로 확인
    target_port = None
    for port in range(8010, 8031):  # 8010~8030 범위에서 검색
        if check_port_available(port):
            target_port = port
            print(f"✅ 포트 {target_port}를 사용합니다.")
            break
        else:
            print(f"⚠️ 포트 {port}가 이미 사용 중입니다.")
    
    if target_port is None:
        print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
        return
    
    # 환경 변수 설정
    env = os.environ.copy()
    env["TEST_BACKEND_PORT"] = str(target_port)
    env["TEST_FRONTEND_PORT"] = "3010"
    env["TEST_DATABASE_URL"] = f"sqlite:///./data/test_notifications.db"
    env["TEST_SQLITE_DB_PATH"] = "./data/test_notifications.db"
    env["TEST_VECTOR_DB_PATH"] = "./data/test_vector_db"
    
    # 엑셀 파일 경로 설정 (프로젝트 루트 기준)
    project_root = os.path.dirname(test_env_dir)
    env["NOTIFICATION_HISTORY_FILE"] = os.path.join(project_root, "[Noti이력].xlsx")
    env["STATUS_CODE_FILE"] = os.path.join(project_root, "[현상코드].xlsx")
    env["EQUIPMENT_TYPE_FILE"] = os.path.join(project_root, "설비유형 자료_20250522.xlsx")
    
    print(f"🔧 포트: {target_port}")
    print(f"🗄️ 데이터베이스: {env['TEST_SQLITE_DB_PATH']}")
    print(f"🔍 벡터 DB: {env['TEST_VECTOR_DB_PATH']}")
    
    # 백엔드 디렉토리로 이동
    backend_dir = os.path.join(test_env_dir, "backend")
    if not os.path.exists(backend_dir):
        print(f"❌ 백엔드 디렉토리를 찾을 수 없습니다: {backend_dir}")
        return
    
    os.chdir(backend_dir)
    print(f"📁 백엔드 디렉토리: {os.getcwd()}")
    
    # requirements.txt 확인
    if not os.path.exists("requirements.txt"):
        print("📝 requirements.txt를 복사합니다...")
        # 상위 디렉토리의 requirements.txt를 복사
        original_requirements = os.path.join(test_env_dir, "..", "backend", "requirements.txt")
        if os.path.exists(original_requirements):
            import shutil
            shutil.copy2(original_requirements, "requirements.txt")
            print("✅ requirements.txt 복사 완료")
        else:
            print("⚠️ requirements.txt를 찾을 수 없습니다.")
    
    # 데이터 디렉토리 생성
    data_dir = os.path.join(test_env_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    print(f"📁 데이터 디렉토리 생성: {data_dir}")
    
    try:
        print("🔥 테스트 백엔드 서버 시작...")
        print(f"🌐 접속 주소: http://localhost:{target_port}")
        print(f"📊 API 문서: http://localhost:{target_port}/docs")
        print("🛑 종료하려면 Ctrl+C를 누르세요")
        
        # uvicorn으로 서버 시작
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", str(target_port),
            "--reload"
        ], env=env)
        
    except KeyboardInterrupt:
        print("\n✨ 테스트 백엔드 서버가 종료되었습니다.")
    except Exception as e:
        print(f"❌ 서버 시작 중 오류 발생: {e}")

if __name__ == "__main__":
    main() 