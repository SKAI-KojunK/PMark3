#!/usr/bin/env python3
"""
PMark2.5 테스트 환경 프론트엔드 서버

이 스크립트는 PMark2.5의 고급 기능을 테스트하기 위한 프론트엔드 서버를 실행합니다.
백엔드와 포트 동기화를 위한 정보 제공 API도 포함되어 있습니다.

담당자: 프론트엔드 개발자
수정 시 주의사항:
- 백엔드 포트 감지 로직 확인
- CORS 설정 유지
- 정적 파일 서빙 경로 확인
"""

import os
import sys
import http.server
import socketserver
import json
import socket
from urllib.parse import urlparse, parse_qs

# 현재 스크립트 위치에서 프로젝트 루트 찾기
current_dir = os.path.dirname(os.path.abspath(__file__))
test_env_dir = os.path.dirname(current_dir)  # test_env
project_root = os.path.dirname(test_env_dir)  # PMark2-Dev

# Python 경로에 추가
sys.path.insert(0, test_env_dir)

def find_available_port(start_port=3010, max_attempts=10):
    """사용 가능한 포트 찾기"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def detect_backend_port():
    """실행 중인 백엔드 포트 감지"""
    test_ports = [8010, 8011, 8012, 8013, 8014, 8015]
    
    for port in test_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5) # 타임아웃을 짧게 조정
                # 'localhost' 대신 '127.0.0.1'을 사용하여 감지 안정성 향상
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    print(f"🔍 [TEST] Backend detected on port {port}")
                    return port
        except:
            continue
    
    print("⚠️ [TEST] No backend detected, using default port 8013")
    return 8013

class TestFrontendHandler(http.server.SimpleHTTPRequestHandler):
    """테스트 환경용 프론트엔드 핸들러"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=test_env_dir, **kwargs)
    
    def do_GET(self):
        """GET 요청 처리"""
        path = urlparse(self.path).path
        
        # 백엔드 정보 API
        if path == '/api/backend-info':
            self.handle_backend_info()
            return
        
        # 루트 경로 - test_chatbot.html 서빙
        if path == '/' or path == '/index.html':
            self.serve_test_chatbot()
            return
        
        # 기존 프로토타입 접근
        if path == '/old' or path == '/prototype':
            self.serve_old_chatbot()
            return
        
        # 기본 파일 서빙
        super().do_GET()
    
    def handle_backend_info(self):
        """백엔드 정보 제공 API"""
        try:
            backend_port = detect_backend_port()
            
            response_data = {
                "backendPort": backend_port,
                "backendUrl": f"http://localhost:{backend_port}",
                "apiBase": f"http://localhost:{backend_port}/api/v1",
                "version": "2.5.0",
                "features": ["session_management", "multiturn_conversation", "accumulated_context"]
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            
            print(f"✅ [TEST] Served backend info (port {backend_port}) to {self.client_address[0]}")
            
        except Exception as e:
            print(f"❌ [TEST] Backend info error: {e}")
            self.send_error(500, "Backend info retrieval failed")
    
    def serve_test_chatbot(self):
        """PMark2.5 테스트 채팅봇 서빙"""
        try:
            chatbot_path = os.path.join(test_env_dir, 'test_chatbot.html')
            
            if os.path.exists(chatbot_path):
                with open(chatbot_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(content.encode('utf-8'))
                print(f"✅ [TEST] Served test_chatbot.html to {self.client_address[0]}")
            else:
                self.send_error(404, "test_chatbot.html not found")
                print(f"❌ [TEST] test_chatbot.html not found: {chatbot_path}")
                
        except Exception as e:
            print(f"❌ [TEST] Error serving test_chatbot.html: {e}")
            self.send_error(500, "Internal server error")
    
    def serve_old_chatbot(self):
        """기존 프로토타입 채팅봇 서빙"""
        try:
            # 프로젝트 루트의 chatbot.html 서빙
            chatbot_path = os.path.join(project_root, 'chatbot.html')
            
            if os.path.exists(chatbot_path):
                with open(chatbot_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(content.encode('utf-8'))
                print(f"✅ [TEST] Served old chatbot.html to {self.client_address[0]}")
            else:
                self.send_error(404, "chatbot.html not found")
                
        except Exception as e:
            print(f"❌ [TEST] Error serving old chatbot.html: {e}")
            self.send_error(500, "Internal server error")
    
    def do_OPTIONS(self):
        """CORS preflight 요청 처리"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """로그 메시지 커스터마이징"""
        client_ip = self.client_address[0]
        path = args[1] if len(args) > 1 else "unknown"
        
        # 요청 로깅
        print(f"🔗 [TEST] Request from {client_ip}: {path}")

def main():
    """메인 실행 함수"""
    # 포트 설정
    preferred_port = 3010
    port = find_available_port(preferred_port)
    
    if port != preferred_port:
        print(f"❌ 포트 {preferred_port}가 이미 사용 중입니다. 다른 포트를 시도합니다.")
    
    if not port:
        print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
        return
    
    # 서버 정보 출력
    print("🚀 PMark2.5 테스트 환경 프론트엔드 서버 시작 중...")
    print(f"📁 현재 디렉토리: {test_env_dir}")
    print(f"🌐 서버 실행 중:")
    print(f"   • Local:    http://localhost:{port}")
    
    # 네트워크 IP 감지
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"   • Network:  http://{local_ip}:{port}")
        print(f"📡 다른 컴퓨터에서 접속 가능:")
        print(f"   • 테스트 챗봇:     http://{local_ip}:{port}/")
        print(f"   • 프로토타입:   http://{local_ip}:{port}/old")
    except:
        print("   • Network:  IP 감지 실패")
    
    print("👥 멀티 사용자 지원: ✅ ENABLED")
    print("🔧 테스트 환경: ✅ ENABLED")
    print("�� 서버 종료하려면 Ctrl+C를 누르세요")
    
    # test_chatbot.html 존재 확인
    chatbot_path = os.path.join(test_env_dir, 'test_chatbot.html')
    if os.path.exists(chatbot_path):
        print("✅ test_chatbot.html 발견")
    else:
        print("⚠️ test_chatbot.html 없음 - 기본 파일 서빙만 가능")
    
    print("🔥 테스트 환경 서버가 여러 동시 사용자를 위해 준비되었습니다!")
    
    # 서버 시작
    try:
        with socketserver.TCPServer(("", port), TestFrontendHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 서버가 종료되었습니다.")
    except Exception as e:
        print(f"❌ 서버 오류: {e}")

if __name__ == "__main__":
    main() 