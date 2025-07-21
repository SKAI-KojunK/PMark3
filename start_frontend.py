#!/usr/bin/env python3
"""
PMark2 Frontend Server - Multi-user Support
"""

import http.server
import socketserver
import os
import socket
import threading
from urllib.parse import urlparse

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        print(f"🔗 Request from {self.client_address[0]}: {path}")  # 사용자 IP 포함 디버깅
        
        # Route handling
        if path == '/' or path == '/chatbot':
            # Serve the new chatbot interface
            self.serve_chatbot()
        elif path == '/old' or path == '/prototype':
            # Serve the old prototype interface
            self.serve_file('frontend-prototype.html')
        else:
            # Default file serving
            super().do_GET()
    
    def serve_chatbot(self):
        """새로운 챗봇 인터페이스를 서빙합니다."""
        filename = 'chatbot.html'
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # HTML content as bytes
                content_bytes = content.encode('utf-8')
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content_bytes))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(content_bytes)
                print(f"✅ Served {filename} to {self.client_address[0]}")
            else:
                self.send_error(404, f"File {filename} not found")
                print(f"❌ File {filename} not found for {self.client_address[0]}")
        except Exception as e:
            self.send_error(500, f"Error serving file: {str(e)}")
            print(f"❌ Error serving {filename} to {self.client_address[0]}: {str(e)}")
    
    def serve_file(self, filename):
        """지정된 파일을 서빙합니다."""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                content_bytes = content.encode('utf-8')
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content_bytes))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(content_bytes)
                print(f"✅ Served {filename} to {self.client_address[0]}")
            else:
                self.send_error(404, f"File {filename} not found")
                print(f"❌ File {filename} not found for {self.client_address[0]}")
        except Exception as e:
            self.send_error(500, f"Error serving file: {str(e)}")
            print(f"❌ Error serving {filename} to {self.client_address[0]}: {str(e)}")

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """멀티스레드를 지원하는 TCP 서버"""
    allow_reuse_address = True
    daemon_threads = True  # 메인 스레드 종료 시 자동으로 워커 스레드도 종료

def find_free_port(start_port=3000, max_attempts=10):
    """사용 가능한 포트를 찾습니다."""
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
    # 3001번 포트를 우선적으로 사용
    port = 3001
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
    except OSError:
        print(f"❌ 포트 {port}가 이미 사용 중입니다. 다른 포트를 시도합니다.")
        port = find_free_port(3002)
        if not port:
            print("❌ 사용 가능한 포트를 찾을 수 없습니다.")
            return
    
    local_ip = get_local_ip()
    
    print(f"🚀 PMark2 Frontend Server Starting...")
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"🌐 Server running on:")
    print(f"   • Local:    http://localhost:{port}")
    print(f"   • Network:  http://{local_ip}:{port}")
    print(f"📡 Other computers can access:")
    print(f"   • Chatbot:     http://{local_ip}:{port}/")
    print(f"   • Prototype:   http://{local_ip}:{port}/old")
    print(f"👥 Multi-user support: ✅ ENABLED")
    print(f"🛑 Press Ctrl+C to stop the server")
    
    # 파일 존재 확인
    if os.path.exists('chatbot.html'):
        print("✅ chatbot.html found")
    else:
        print("❌ chatbot.html not found")
    
    try:
        # ThreadingTCPServer로 다중 사용자 지원
        with ThreadingTCPServer(("0.0.0.0", port), CustomHTTPRequestHandler) as httpd:
            print(f"🔥 Server ready for multiple concurrent users!")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✨ Frontend server stopped.")
    except Exception as e:
        print(f"❌ Error starting frontend server: {e}")

if __name__ == "__main__":
    main() 