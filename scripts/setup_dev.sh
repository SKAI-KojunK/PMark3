#!/bin/bash

# PMark2-Dev 개발 환경 설정 스크립트

set -e

echo "🚀 PMark2-Dev 개발 환경 설정을 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Python 버전 확인
check_python() {
    log_info "Python 버전을 확인합니다..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python $PYTHON_VERSION 발견"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        log_success "Python $PYTHON_VERSION 발견"
        PYTHON_CMD="python"
    else
        log_error "Python이 설치되어 있지 않습니다. Python 3.8+를 설치해주세요."
        exit 1
    fi
}

# Node.js 버전 확인
check_node() {
    log_info "Node.js 버전을 확인합니다..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_success "Node.js $NODE_VERSION 발견"
    else
        log_warning "Node.js가 설치되어 있지 않습니다. React 개발을 위해 설치를 권장합니다."
    fi
}

# 가상환경 설정
setup_venv() {
    log_info "Python 가상환경을 설정합니다..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        log_success "가상환경 생성 완료"
    else
        log_info "기존 가상환경 발견"
    fi
    
    # 가상환경 활성화
    source venv/bin/activate
    log_success "가상환경 활성화 완료"
}

# Python 의존성 설치
install_python_deps() {
    log_info "Python 의존성을 설치합니다..."
    
    # pip 업그레이드
    pip install --upgrade pip
    
    # 기본 의존성 설치
    pip install -r backend/requirements.txt
    
    log_success "Python 의존성 설치 완료"
}

# Node.js 의존성 설치
install_node_deps() {
    if command -v node &> /dev/null; then
        log_info "Node.js 의존성을 설치합니다..."
        
        cd frontend
        npm install
        cd ..
        
        log_success "Node.js 의존성 설치 완료"
    else
        log_warning "Node.js가 설치되어 있지 않아 프론트엔드 의존성을 건너뜁니다."
    fi
}

# 환경 변수 파일 설정
setup_env() {
    log_info "환경 변수 파일을 설정합니다..."
    
    if [ ! -f "backend/.env" ]; then
        if [ -f "backend/.env.example" ]; then
            cp backend/.env.example backend/.env
            log_warning "backend/.env 파일이 생성되었습니다. OpenAI API 키를 설정해주세요."
        else
            log_warning "backend/.env.example 파일이 없습니다. 수동으로 .env 파일을 생성해주세요."
        fi
    else
        log_info "기존 .env 파일 발견"
    fi
}

# 로그 디렉토리 생성
create_dirs() {
    log_info "필요한 디렉토리를 생성합니다..."
    
    mkdir -p backend/logs
    mkdir -p docs
    mkdir -p scripts
    
    log_success "디렉토리 생성 완료"
}

# 권한 설정
set_permissions() {
    log_info "스크립트 권한을 설정합니다..."
    
    chmod +x start_frontend.py
    chmod +x backend/run.py
    chmod +x scripts/*.sh
    
    log_success "권한 설정 완료"
}

# 개발 도구 설치
install_dev_tools() {
    log_info "개발 도구를 설치합니다..."
    
    # Python 개발 도구
    pip install black isort flake8 pylint mypy
    
    log_success "개발 도구 설치 완료"
}

# 설정 완료 메시지
show_completion() {
    echo ""
    log_success "PMark2-Dev 개발 환경 설정이 완료되었습니다!"
    echo ""
    echo "다음 단계를 진행하세요:"
    echo ""
    echo "1. OpenAI API 키 설정:"
    echo "   nano backend/.env"
    echo ""
    echo "2. 백엔드 서버 시작 (개발 모드):"
    echo "   cd backend && python run.py --dev"
    echo ""
    echo "3. 프론트엔드 서버 시작 (개발 모드):"
    echo "   python start_frontend.py --dev"
    echo ""
    echo "4. 테스트 실행:"
    echo "   cd backend && python -m pytest"
    echo ""
    echo "📚 자세한 내용은 README.md를 참조하세요."
}

# 메인 실행
main() {
    echo "=========================================="
    echo "  PMark2-Dev 개발 환경 설정"
    echo "=========================================="
    echo ""
    
    check_python
    check_node
    setup_venv
    install_python_deps
    install_node_deps
    setup_env
    create_dirs
    set_permissions
    install_dev_tools
    show_completion
}

# 스크립트 실행
main "$@"
