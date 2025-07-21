#!/usr/bin/env python3
"""
PMark2 Backend Server Runner
FastAPI를 이용한 백엔드 서버 실행 스크립트
"""

import uvicorn
import socket
import sys
import os
from contextlib import closing

def find_free_port(start_port=8001, max_attempts=10):
    """사용 가능한 포트를 찾는 함수"""
    # 먼저 설정된 포트를 시도
    from app.config import Config
    preferred_port = Config.BACKEND_PORT
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', preferred_port))
            return preferred_port
    except OSError:
        pass
    
    # 설정된 포트가 사용 중이면 다른 포트 시도
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return None

def get_local_ip():
    """로컬 IP 주소를 가져오는 함수"""
    try:
        # 임시 소켓을 만들어서 로컬 IP 확인
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "localhost"

def main():
    port = find_free_port()
    if not port:
        print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
        sys.exit(1)
    
    local_ip = get_local_ip()
    
    print(f"🚀 PMark2 Backend Server Starting...")
    print(f"🌐 Server running on:")
    print(f"   • Local:    http://localhost:{port}")
    print(f"   • Network:  http://{local_ip}:{port}")
    print(f"📡 Other computers can access: http://{local_ip}:{port}")
    print(f"🛑 Press Ctrl+C to stop the server")
    
    try:
        # 0.0.0.0으로 바인딩하여 네트워크 접속 허용
        uvicorn.run(
            "main:app",
            host="0.0.0.0",  # 모든 인터페이스에서 접속 허용
            port=port,
            reload=True,
            reload_dirs=[os.getcwd()]
        )
    except KeyboardInterrupt:
        print("\n✨ Backend server stopped.")
    except Exception as e:
        print(f"❌ Error starting backend server: {e}")

if __name__ == "__main__":
    main() 