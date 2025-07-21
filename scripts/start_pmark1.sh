#!/bin/bash

# PMark2 시스템 시작 스크립트
# 사용법: ./scripts/start_pmark1.sh

echo "🚀 PMark2 AI Assistant 시스템 시작 중..."

# 프로젝트 루트 디렉토리로 이동
cd /Users/YMARX/Dropbox/2025_ECMiner/C_P02_SKAI/03_진행/PMark2-Dev

# 기존 프로세스 종료
echo "🛑 기존 프로세스 정리 중..."
pkill -f "python run.py" 2>/dev/null
pkill -f "python start_frontend.py" 2>/dev/null
sleep 2

# 백엔드 서버 시작
echo "🔧 백엔드 서버 시작 중..."
cd backend
source venv/bin/activate
python run.py &
BACKEND_PID=$!
cd ..

# 백엔드 서버 시작 대기
echo "⏳ 백엔드 서버 시작 대기 중..."
sleep 10

# 백엔드 상태 확인
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ 백엔드 서버 시작 완료"
else
    echo "❌ 백엔드 서버 시작 실패"
    exit 1
fi

# 프론트엔드 서버 시작
echo "🌐 프론트엔드 서버 시작 중..."
python start_frontend.py &
FRONTEND_PID=$!

# 프론트엔드 서버 시작 대기
echo "⏳ 프론트엔드 서버 시작 대기 중..."
sleep 5

# 프론트엔드 상태 확인
if curl -s http://localhost:3001 > /dev/null; then
    echo "✅ 프론트엔드 서버 시작 완료"
else
    echo "❌ 프론트엔드 서버 시작 실패"
    exit 1
fi

echo ""
echo "🎉 PMark2 AI Assistant 시스템 시작 완료!"
echo ""
echo "📱 접속 정보:"
echo "   • 웹 브라우저: http://localhost:3001"
echo "   • 백엔드 API: http://localhost:8001"
echo "   • API 문서: http://localhost:8001/docs"
echo ""
echo "🛑 종료하려면: ./scripts/stop_pmark1.sh"
echo ""

# 프로세스 ID 저장
echo $BACKEND_PID > /tmp/pmark1_backend.pid
echo $FRONTEND_PID > /tmp/pmark1_frontend.pid

# 프로세스 모니터링
echo "📊 시스템 모니터링 중... (Ctrl+C로 종료)"
trap 'echo ""; echo "🛑 시스템 종료 중..."; ./scripts/stop_pmark1.sh; exit 0' INT

while true; do
    sleep 10
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ 백엔드 서버가 종료되었습니다."
        break
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ 프론트엔드 서버가 종료되었습니다."
        break
    fi
done 