#!/bin/bash

# PMark2 시스템 종료 스크립트
# 사용법: ./scripts/stop_pmark2.sh

echo "🛑 PMark2 AI Assistant 시스템 종료 중..."

# 프로젝트 루트 디렉토리로 이동
cd /Users/YMARX/Dropbox/2025_ECMiner/C_P02_SKAI/03_진행/PMark2-Dev

# 저장된 프로세스 ID 확인
if [ -f /tmp/pmark2_backend.pid ]; then
    BACKEND_PID=$(cat /tmp/pmark2_backend.pid)
    echo "🔧 백엔드 서버 종료 중 (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    rm -f /tmp/pmark2_backend.pid
fi

if [ -f /tmp/pmark2_frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/pmark2_frontend.pid)
    echo "🌐 프론트엔드 서버 종료 중 (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null
    rm -f /tmp/pmark2_frontend.pid
fi

# 프로세스 이름으로 추가 종료
echo "🧹 남은 프로세스 정리 중..."
pkill -f "python run.py" 2>/dev/null
pkill -f "python start_frontend.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null

# 포트 사용 확인
echo "🔍 포트 사용 상태 확인 중..."
if lsof -i :8001 > /dev/null 2>&1; then
    echo "⚠️  포트 8001이 여전히 사용 중입니다."
    lsof -i :8001
fi

if lsof -i :3001 > /dev/null 2>&1; then
    echo "⚠️  포트 3001이 여전히 사용 중입니다."
    lsof -i :3001
fi

# 잠시 대기
sleep 2

# 최종 확인
if ! lsof -i :8001 > /dev/null 2>&1 && ! lsof -i :3001 > /dev/null 2>&1; then
    echo "✅ PMark2 시스템 종료 완료!"
    echo "📊 모든 포트가 해제되었습니다."
else
    echo "⚠️  일부 포트가 여전히 사용 중일 수 있습니다."
    echo "🔍 수동으로 확인하려면:"
    echo "   lsof -i :8001"
    echo "   lsof -i :3001"
fi 