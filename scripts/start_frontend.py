#!/usr/bin/env python3
"""
PMark1 AI Assistant 프론트엔드 시작 스크립트
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """CORS를 지원하는 HTTP 요청 핸들러"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def start_http_server(port=3001):
    """HTTP 서버 시작"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    print(f"🌐 프론트엔드 서버가 http://localhost:{port}에서 시작되었습니다.")
    httpd.serve_forever()

def main():
    """프론트엔드 서버 시작"""
    
    # 프로젝트 루트 디렉토리로 이동
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 PMark1 AI Assistant 프론트엔드 서버 시작 중...")
    
    # chatbot.html 파일 확인
    html_file = project_root / "chatbot.html"
    if not html_file.exists():
        print("❌ chatbot.html 파일을 찾을 수 없습니다.")
        return
    
    # 포트 설정
    port = 3001
    
    # HTTP 서버 시작 (별도 스레드)
    server_thread = threading.Thread(target=start_http_server, args=(port,), daemon=True)
    server_thread.start()
    
    # 잠시 대기 후 브라우저 열기
    time.sleep(2)
    
    print(f"🌐 브라우저에서 http://localhost:{port}/chatbot.html을 열어주세요.")
    print("   또는 자동으로 브라우저가 열립니다.")
    print("   종료하려면 Ctrl+C를 누르세요.")
    
    try:
        # 브라우저 자동 열기
        webbrowser.open(f"http://localhost:{port}/chatbot.html")
        
        # 메인 스레드 대기
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 프론트엔드 서버가 종료되었습니다.")
    except Exception as e:
        print(f"❌ 프론트엔드 서버 시작 실패: {e}")

if __name__ == "__main__":
    main() 