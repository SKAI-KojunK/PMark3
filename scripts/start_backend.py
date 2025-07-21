#!/usr/bin/env python3
"""
PMark1 Backend Server Starter
포트 충돌 방지 및 여러 사용자 접속 지원
"""

import os
import sys
import subprocess
import signal
import time
import socket
from pathlib import Path

def find_free_port(start_port=8001, max_attempts=10):
    """사용 가능한 포트를 찾는 함수"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return None

def kill_existing_processes():
    """기존 PMark1 백엔드 프로세스 종료"""
    try:
        # macOS/Linux에서 PMark1 관련 프로세스 찾기 및 종료
        result = subprocess.run(['pkill', '-f', 'python.*run.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 기존 백엔드 프로세스 종료됨")
        time.sleep(2)  # 프로세스 종료 대기
    except Exception as e:
        print(f"⚠️  프로세스 종료 중 오류: {e}")

def get_local_ip():
    """로컬 IP 주소를 가져오는 함수"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "localhost"

def main():
    # 프로젝트 루트 디렉토리로 이동
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    
    if not backend_dir.exists():
        print("❌ Backend 디렉토리를 찾을 수 없습니다.")
        sys.exit(1)
    
    os.chdir(backend_dir)
    
    # 기존 프로세스 종료
    kill_existing_processes()
    
    # 가상환경 활성화 확인
    venv_path = backend_dir / "venv"
    if not venv_path.exists():
        print("❌ 가상환경을 찾을 수 없습니다. 먼저 setup_dev.sh를 실행하세요.")
        sys.exit(1)
    
    # 환경 변수 설정
    env = os.environ.copy()
    env['BACKEND_PORT'] = '8001'
    env['FRONTEND_PORT'] = '3001'
    
    # 포트 확인
    port = find_free_port(8001)
    if not port:
        print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
        sys.exit(1)
    
    local_ip = get_local_ip()
    
    print(f"🚀 PMark1 Backend Server Starting...")
    print(f"📁 Working Directory: {backend_dir}")
    print(f"🌐 Server running on:")
    print(f"   • Local:    http://localhost:{port}")
    print(f"   • Network:  http://{local_ip}:{port}")
    print(f"📡 Other computers can access: http://{local_ip}:{port}")
    print(f"🛑 Press Ctrl+C to stop the server")
    
    try:
        # 가상환경 활성화 후 서버 시작
        if os.name == 'nt':  # Windows
            activate_script = venv_path / "Scripts" / "activate.bat"
            cmd = f'"{activate_script}" && python run.py'
        else:  # macOS/Linux
            activate_script = venv_path / "bin" / "activate"
            cmd = f'source "{activate_script}" && python run.py'
        
        # 서버 프로세스 시작
        process = subprocess.Popen(
            cmd,
            shell=True,
            env=env,
            cwd=backend_dir
        )
        
        # 프로세스 종료 대기
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped by user.")
        if process:
            process.terminate()
    except Exception as e:
        print(f"❌ Error starting backend server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 