#!/bin/bash

# PMark2 시스템 상태 확인 스크립트
# 사용법: ./scripts/status_pmark1.sh

echo "📊 PMark2 AI Assistant 시스템 상태 확인 중..."
echo ""

# 프로젝트 루트 디렉토리로 이동
cd /Users/YMARX/Dropbox/2025_ECMiner/C_P02_SKAI/03_진행/PMark2-Dev

# 백엔드 서버 상태 확인
echo "🔧 백엔드 서버 (포트 8001):"
if lsof -i :8001 > /dev/null 2>&1; then
    echo "   ✅ 실행 중"
    BACKEND_PID=$(lsof -ti :8001 | head -1)
    echo "   📋 PID: $BACKEND_PID"
    
    # API 응답 테스트
    if curl -s http://localhost:8001/health > /dev/null; then
        echo "   🌐 API 응답: 정상"
    else
        echo "   ⚠️  API 응답: 오류"
    fi
else
    echo "   ❌ 중지됨"
fi

echo ""

# 프론트엔드 서버 상태 확인
echo "🌐 프론트엔드 서버 (포트 3001):"
if lsof -i :3001 > /dev/null 2>&1; then
    echo "   ✅ 실행 중"
    FRONTEND_PID=$(lsof -ti :3001 | head -1)
    echo "   📋 PID: $FRONTEND_PID"
    
    # 웹 페이지 응답 테스트
    if curl -s http://localhost:3001 > /dev/null; then
        echo "   🌐 웹 페이지 응답: 정상"
    else
        echo "   ⚠️  웹 페이지 응답: 오류"
    fi
else
    echo "   ❌ 중지됨"
fi

echo ""

# 데이터베이스 상태 확인
echo "🗄️  데이터베이스:"
if [ -f "backend/data/sample_notifications.db" ]; then
    echo "   ✅ 데이터베이스 파일 존재"
    DB_SIZE=$(ls -lh backend/data/sample_notifications.db | awk '{print $5}')
    echo "   📊 크기: $DB_SIZE"
else
    echo "   ❌ 데이터베이스 파일 없음"
fi

echo ""

# 가상환경 상태 확인
echo "🐍 Python 가상환경:"
if [ -d "backend/venv" ]; then
    echo "   ✅ 가상환경 디렉토리 존재"
    if [ -f "backend/venv/bin/activate" ]; then
        echo "   ✅ 가상환경 활성화 스크립트 존재"
    else
        echo "   ❌ 가상환경 활성화 스크립트 없음"
    fi
else
    echo "   ❌ 가상환경 디렉토리 없음"
fi

echo ""

# 환경 변수 확인
echo "🔧 환경 설정:"
if [ -f "backend/.env" ]; then
    echo "   ✅ 백엔드 .env 파일 존재"
    if grep -q "OPENAI_API_KEY" backend/.env; then
        API_KEY_STATUS=$(grep "OPENAI_API_KEY" backend/.env | cut -d'=' -f2)
        if [ "$API_KEY_STATUS" = "your-openai-api-key-here" ]; then
            echo "   ⚠️  OpenAI API 키: 설정되지 않음"
        else
            echo "   ✅ OpenAI API 키: 설정됨"
        fi
    else
        echo "   ❌ OpenAI API 키: 없음"
    fi
else
    echo "   ❌ 백엔드 .env 파일 없음"
fi

if [ -f "frontend/.env" ]; then
    echo "   ✅ 프론트엔드 .env 파일 존재"
else
    echo "   ❌ 프론트엔드 .env 파일 없음"
fi

echo ""

# 전체 시스템 상태 요약
echo "📋 시스템 상태 요약:"
BACKEND_RUNNING=$(lsof -i :8001 > /dev/null 2>&1 && echo "1" || echo "0")
FRONTEND_RUNNING=$(lsof -i :3001 > /dev/null 2>&1 && echo "1" || echo "0")

if [ "$BACKEND_RUNNING" = "1" ] && [ "$FRONTEND_RUNNING" = "1" ]; then
    echo "   🟢 전체 시스템: 정상 실행 중"
    echo "   🌐 접속 URL: http://localhost:3001"
elif [ "$BACKEND_RUNNING" = "1" ]; then
    echo "   🟡 부분 실행: 백엔드만 실행 중"
elif [ "$FRONTEND_RUNNING" = "1" ]; then
    echo "   🟡 부분 실행: 프론트엔드만 실행 중"
else
    echo "   🔴 시스템 중지됨"
fi

echo ""
echo "💡 명령어 도움말:"
echo "   시작: ./scripts/start_pmark1.sh"
echo "   종료: ./scripts/stop_pmark1.sh"
echo "   상태: ./scripts/status_pmark1.sh" 