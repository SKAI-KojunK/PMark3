#!/usr/bin/env python3
"""
PMark2.5 테스트 환경 종료 스크립트
실행 중인 테스트 환경 프로세스를 안전하게 종료합니다.
"""

import os
import subprocess
import signal
import psutil
import time

def find_processes_by_port(port):
    """특정 포트를 사용하는 프로세스를 찾습니다."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port == port:
                    processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def kill_process(proc):
    """프로세스를 안전하게 종료합니다."""
    try:
        print(f"🛑 프로세스 종료 중: PID {proc.pid} ({proc.name()})")
        proc.terminate()
        
        # 5초 대기 후 강제 종료
        try:
            proc.wait(timeout=5)
            print(f"✅ 프로세스 {proc.pid} 정상 종료")
        except psutil.TimeoutExpired:
            print(f"⚠️ 프로세스 {proc.pid} 강제 종료")
            proc.kill()
            
    except psutil.NoSuchProcess:
        print(f"ℹ️ 프로세스 {proc.pid} 이미 종료됨")
    except Exception as e:
        print(f"❌ 프로세스 {proc.pid} 종료 중 오류: {e}")

def main():
    print("🛑 PMark2.5 테스트 환경 종료 중...")
    
    # 테스트 환경 포트들 (기존과 충돌 방지)
    test_ports = [8010, 3010]  # 백엔드, 프론트엔드 (기본값)
    
    # 추가로 8011~8030, 3011~3030 범위의 포트도 확인
    for backend_port in range(8011, 8031):
        test_ports.append(backend_port)
    for frontend_port in range(3011, 3031):
        test_ports.append(frontend_port)
    
    for port in test_ports:
        processes = find_processes_by_port(port)
        if processes:
            print(f"🔍 포트 {port}에서 {len(processes)}개 프로세스 발견")
            for proc in processes:
                kill_process(proc)
        else:
            print(f"ℹ️ 포트 {port}에서 실행 중인 프로세스 없음")
    
    # 추가로 Python 프로세스 중 테스트 관련 프로세스 찾기
    print("🔍 테스트 관련 Python 프로세스 확인 중...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else ''
            if (proc.name() == 'python' or proc.name() == 'python3') and \
               ('test' in cmdline.lower() or '8010' in cmdline or '3010' in cmdline or 
                any(f'80{port}' in cmdline for port in range(11, 31)) or
                any(f'30{port}' in cmdline for port in range(11, 31))):
                print(f"🔍 테스트 관련 프로세스 발견: PID {proc.pid}")
                print(f"   명령어: {cmdline}")
                response = input("이 프로세스를 종료하시겠습니까? (y/N): ")
                if response.lower() in ['y', 'yes']:
                    kill_process(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    print("✨ 테스트 환경 종료 완료")
    print("💡 모든 프로세스가 종료되었습니다.")

if __name__ == "__main__":
    main() 