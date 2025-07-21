#!/usr/bin/env python3
"""
PMark2.5 데이터베이스 초기화 스크립트

이 스크립트는 PMark2.5의 데이터베이스를 초기화하고 Excel 파일에서 데이터를 로드합니다.
"""

import sys
import os

# 현재 스크립트 경로에서 backend 디렉토리를 Python path에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
test_env_dir = os.path.dirname(script_dir)
backend_dir = os.path.join(test_env_dir, 'backend')
sys.path.insert(0, backend_dir)

from app.database import db_manager
from app.config import Config

def main():
    """데이터베이스 초기화 및 데이터 로드"""
    print("🔄 PMark2.5 데이터베이스 초기화 시작...")
    
    try:
        # 데이터베이스 초기화 (테이블 생성)
        print("📋 데이터베이스 테이블 생성...")
        db_manager._initialize_database()
        
        # Excel 데이터 로드
        print("📊 Excel 데이터 로드 중...")
        print(f"  - 작업요청 이력: {Config.NOTIFICATION_HISTORY_FILE}")
        print(f"  - 현상코드: {Config.STATUS_CODE_FILE}")
        print(f"  - 설비유형: {Config.EQUIPMENT_TYPE_FILE}")
        
        db_manager.load_excel_data()
        
        # 데이터 로드 확인
        print("\n📈 데이터 로드 결과:")
        
        # 작업요청 이력 확인
        history_data = db_manager.get_notification_history_data()
        print(f"  - 작업요청 이력: {len(history_data)} 건")
        
        # 설비유형 확인
        equipment_data = db_manager.get_equipment_type_data()
        print(f"  - 설비유형: {len(equipment_data)} 건")
        
        # 현상코드 확인
        status_data = db_manager.get_status_codes()
        print(f"  - 현상코드: {len(status_data)} 건")
        
        print("\n✅ 데이터베이스 초기화 완료!")
        
        # 샘플 자동완성 테스트
        print("\n🧪 자동완성 테스트:")
        if equipment_data:
            print(f"  - 설비유형 샘플: {equipment_data[0] if equipment_data else 'None'}")
        
        if history_data:
            print(f"  - 작업요청 샘플: {history_data[0]['itemno'] if history_data else 'None'}")
            
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 