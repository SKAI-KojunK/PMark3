"""
PMark1 AI Assistant - 데이터베이스 관리 모듈

이 파일은 SQLite 데이터베이스와의 상호작용을 담당합니다.
설비관리 시스템의 알림 데이터를 검색하고, LLM 정규화 엔진을 활용하여 유사한 작업을 찾습니다.

주요 담당자: 백엔드 개발자, 데이터베이스 관리자
수정 시 주의사항:
- DB 스키마 변경 시 기존 데이터 마이그레이션 필요
- LLM 정규화 엔진과 연동되어 정확한 용어 매칭 제공
- 성능 최적화를 위해 인덱스 설정 권장
"""

import sqlite3
import pandas as pd
import os
from typing import List, Dict, Any, Optional
from .config import Config
from .logic.normalizer import normalizer
import logging

class DatabaseManager:
    """
    데이터베이스 관리 클래스
    
    사용처:
    - recommender.py: RecommendationEngine에서 유사 작업 검색
    - chat.py: 직접 호출하여 데이터 검증
    
    연계 파일:
    - models.py: Recommendation 모델 사용
    - logic/normalizer.py: LLM 정규화 엔진 사용
    - config.py: 데이터베이스 경로 설정
    
    담당자 수정 가이드:
    - DB 스키마 변경 시 create_tables() 메서드 수정
    - 새로운 검색 조건 추가 시 search_similar_notifications() 수정
    - 성능 최적화를 위해 인덱스 추가 고려
    """
    
    def __init__(self):
        """
        데이터베이스 매니저 초기화
        
        설정:
        - 데이터베이스 연결 설정
        - 테이블 생성 (없는 경우)
        - 로깅 설정
        """
        self.db_path = Config.SQLITE_DB_PATH
        self.conn = None
        self.logger = logging.getLogger(__name__)
        self._ensure_data_directory()
        self._initialize_database()
    
    def _ensure_data_directory(self):
        """데이터 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _initialize_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.logger.info(f"DB 파일 경로: {self.db_path}, 존재 여부: {os.path.exists(self.db_path)}")
        
        # 작업요청 이력 테이블 생성
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                itemno TEXT NOT NULL,
                process TEXT,
                location TEXT,
                equipType TEXT,
                statusCode TEXT,
                work_title TEXT,
                work_details TEXT,
                priority TEXT DEFAULT '일반작업',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 현상코드 테이블 생성
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS status_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                description TEXT,
                category TEXT
            )
        ''')
        
        # 설비유형 테이블 생성
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS equipment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_code TEXT NOT NULL,
                type_name TEXT,
                category TEXT
            )
        ''')
        
        # 인덱스 생성 (검색 성능 향상)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_equipType ON notification_history(equipType)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_location ON notification_history(location)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_statusCode ON notification_history(statusCode)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_process ON notification_history(process)")
        
        self.conn.commit()
        self.logger.info("데이터베이스 초기화 완료")
    
    def load_excel_data(self):
        """Excel 파일에서 데이터 로드"""
        try:
            # 파일 경로를 절대경로로 변환
            notification_file = os.path.abspath(Config.NOTIFICATION_HISTORY_FILE)
            status_file = os.path.abspath(Config.STATUS_CODE_FILE)
            equipment_file = os.path.abspath(Config.EQUIPMENT_TYPE_FILE)
            
            # 파일 경로 로깅
            self.logger.info(f"엑셀 파일 경로 확인:")
            self.logger.info(f"  - 작업요청 이력: {notification_file} (존재: {os.path.exists(notification_file)})")
            self.logger.info(f"  - 현상코드: {status_file} (존재: {os.path.exists(status_file)})")
            self.logger.info(f"  - 설비유형: {equipment_file} (존재: {os.path.exists(equipment_file)})")

            # 작업요청 이력 로드
            if os.path.exists(notification_file):
                df_history = pd.read_excel(notification_file)
                # 컬럼명 strip 처리
                df_history.columns = [c.strip() for c in df_history.columns]
                self.logger.info(f"작업요청 이력 파일 로드: {len(df_history)} 건, 컬럼: {df_history.columns.tolist()}")
                
                # 컬럼명 매핑 (실제 Excel 파일 구조에 맞춤)
                column_mapping = {
                    '작업대상': 'itemno',
                    'Plant': 'process', 
                    'Location': 'location',
                    '설비유형': 'equipType',
                    '현상코드': 'statusCode',  # 실제 컬럼명에 맞춤 (공백 없음)
                    '작업명': 'work_title',
                    '우선 순위': 'priority'
                }
                df_history = df_history.rename(columns=column_mapping)
                self.logger.info(f"컬럼명 매핑 후: {df_history.columns.tolist()}")
                required_columns = ['itemno', 'process', 'location', 'equipType', 'statusCode', 'work_title', 'priority']
                for col in required_columns:
                    if col not in df_history.columns:
                        self.logger.error(f"작업요청 이력 파일에 필수 컬럼이 없습니다: {col}")
                        raise RuntimeError(f"작업요청 이력 파일에 필수 컬럼이 없습니다: {col}")
                df_history['work_details'] = df_history.get('work_title', '')
                df_history['created_at'] = pd.Timestamp.now()
                df_history = df_history[required_columns + ['work_details', 'created_at']]
                df_history.to_sql('notification_history', self.conn, if_exists='replace', index=False)
                self.conn.commit()
                self.logger.info(f"작업요청 이력 로드 완료: {len(df_history)} 건")
            else:
                self.logger.error(f"작업요청 이력 파일을 찾을 수 없습니다: {notification_file}")
                raise RuntimeError(f"작업요청 이력 파일을 찾을 수 없습니다: {notification_file}")
            
            # 현상코드 로드
            if os.path.exists(status_file):
                df_status = pd.read_excel(status_file)
                df_status.columns = [c.strip() for c in df_status.columns]
                self.logger.info(f"현상코드 파일 로드: {len(df_status)} 건, 컬럼: {df_status.columns.tolist()}")
                if '현상코드' in df_status.columns:
                    df_status = df_status[['현상코드']].copy()
                    df_status.columns = ['code']
                    df_status['description'] = df_status['code']
                    df_status['category'] = '일반'
                df_status.to_sql('status_codes', self.conn, if_exists='replace', index=False)
                self.conn.commit()
                self.logger.info(f"현상코드 로드 완료: {len(df_status)} 건")
            else:
                self.logger.error(f"현상코드 파일을 찾을 수 없습니다: {status_file}")
                raise RuntimeError(f"현상코드 파일을 찾을 수 없습니다: {status_file}")
            
            # 설비유형 로드 (두 번째 시트 사용)
            if os.path.exists(equipment_file):
                # 두 번째 시트 '설비유형' 읽기
                df_equip = pd.read_excel(equipment_file, sheet_name='설비유형')
                df_equip.columns = [c.strip() for c in df_equip.columns]
                self.logger.info(f"설비유형 파일 로드 (두 번째 시트): {len(df_equip)} 건, 컬럼: {df_equip.columns.tolist()}")
                
                if len(df_equip.columns) >= 4:
                    # 헤더 제거 (첫 번째 행이 헤더)
                    if df_equip.iloc[0, 1] == '설비유형 대분류':
                        df_equip = df_equip.iloc[1:].reset_index(drop=True)
                    
                    # 컬럼명 매핑 수정: D컬럼(4번째)을 type_name으로 사용
                    # A: id, B: category, C: temp, D: type_name (D컬럼 전체 값)
                    df_equip.columns = ['id', 'category', 'temp', 'type_name']
                    # type_name(D컬럼)을 type_code로도 사용하여 D컬럼 전체 값이 반환되도록 함
                    df_equip['type_code'] = df_equip['type_name']
                    df_equip = df_equip[['type_code', 'type_name', 'category']].copy()
                    
                    # 빈 값 제거
                    df_equip = df_equip.dropna(subset=['type_code', 'type_name'])
                    
                    df_equip.to_sql('equipment_types', self.conn, if_exists='replace', index=False)
                    self.conn.commit()
                    self.logger.info(f"설비유형 로드 완료: {len(df_equip)} 건")
                else:
                    self.logger.error("설비유형 파일의 컬럼 구조가 예상과 다릅니다.")
                    raise RuntimeError("설비유형 파일의 컬럼 구조가 예상과 다릅니다.")
            else:
                self.logger.error(f"설비유형 파일을 찾을 수 없습니다: {equipment_file}")
                raise RuntimeError(f"설비유형 파일을 찾을 수 없습니다: {equipment_file}")
            
        except Exception as e:
            self.logger.error(f"Excel 데이터 로드 중 오류: {e}")
            raise
    
    def _create_sample_data(self):
        """샘플 데이터 생성 (Excel 파일이 없을 경우)"""
        # 샘플 작업요청 이력
        sample_history = [
            ("44043-CA1-6\"-P", "RFCC", "No.1 PE", "Pressure Vessel", "고장", "압력용기 누설 점검", "압력용기 연결부위 누설 확인 및 수리", "일반작업"),
            ("Y-MV1035", "석유제품배합/저장", "Motor Operated Valve", "Motor Operated Valve", "작동불량", "모터밸브 작동불량 점검", "모터밸브 작동상태 확인 및 수리", "긴급작업"),
            ("SW-CV1307-02", "합성수지 포장", "1창고 #7Line", "Conveyor", "고장", "컨베이어 러버벨트 교체", "컨베이어 러버벨트 마모 확인 및 교체", "우선작업"),
            ("RFCC-001", "RFCC", "No.1 PE", "Heat Exchanger", "누설", "열교환기 누설 점검", "열교환기 튜브 누설 확인 및 수리", "일반작업"),
            ("MV-2024-001", "석유제품배합/저장", "Storage Tank", "Valve", "고장", "저장탱크 밸브 교체", "저장탱크 출구 밸브 교체", "긴급작업")
        ]
        
        for itemno, process, location, equipType, statusCode, work_title, work_details, priority in sample_history:
            self.conn.execute('''
                INSERT INTO notification_history 
                (itemno, process, location, equipType, statusCode, work_title, work_details, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (itemno, process, location, equipType, statusCode, work_title, work_details, priority))
        
        # 샘플 현상코드
        sample_status_codes = [
            ("고장", "설비 고장", "설비"),
            ("누설", "유체 누설", "누설"),
            ("작동불량", "정상 작동하지 않음", "작동"),
            ("소음", "비정상 소음 발생", "소음"),
            ("진동", "과도한 진동", "진동"),
            ("온도상승", "비정상 온도 상승", "온도"),
            ("압력상승", "비정상 압력 상승", "압력")
        ]
        
        for code, description, category in sample_status_codes:
            self.conn.execute('''
                INSERT INTO status_codes (code, description, category)
                VALUES (?, ?, ?)
            ''', (code, description, category))
        
        # 샘플 설비유형
        sample_equipment_types = [
            ("PV", "Pressure Vessel", "용기"),
            ("HE", "Heat Exchanger", "열교환기"),
            ("MV", "Motor Operated Valve", "밸브"),
            ("CV", "Control Valve", "제어밸브"),
            ("PU", "Pump", "펌프"),
            ("CO", "Conveyor", "컨베이어"),
            ("DR", "Drum", "드럼"),
            ("TK", "Tank", "탱크")
        ]
        
        for type_code, type_name, category in sample_equipment_types:
            self.conn.execute('''
                INSERT INTO equipment_types (type_code, type_name, category)
                VALUES (?, ?, ?)
            ''', (type_code, type_name, category))
        
        self.conn.commit()
        self.logger.info("샘플 데이터 생성 완료")
    
    def search_similar_notifications(self, equip_type: str = None, location: str = None, 
                                   status_code: str = None, priority: str = None, limit: int = 15) -> List[Dict[str, Any]]:
        """유사한 작업요청 이력 검색 (위치 기반 검색 강화 + SQL 에러 처리)"""
        
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 입력값 정규화 (위치 우선 정규화)
                normalized_location = self.normalize_term(location, "location") if location else None
                normalized_equip_type = self.normalize_term(equip_type, "equipment") if equip_type else None
                normalized_status_code = self.normalize_term(status_code, "status") if status_code else None
                normalized_priority = self.normalize_term(priority, "priority") if priority else None
                
                query = '''
                    SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
                    FROM notification_history
                    WHERE 1=1
                '''
                params = []
                
                # 위치 기반 검색 강화 (위치가 입력된 경우 우선 검색)
                if normalized_location:
                    # 위치와 공정명 모두에서 검색하되, 위치 매칭에 더 높은 가중치
                    query += " AND (location LIKE ? OR process LIKE ?)"
                    params.extend([f"%{normalized_location}%", f"%{normalized_location}%"])
                
                if normalized_equip_type:
                    query += " AND equipType LIKE ?"
                    params.append(f"%{normalized_equip_type}%")
                
                if normalized_status_code:
                    query += " AND statusCode LIKE ?"
                    params.append(f"%{normalized_status_code}%")
                
                # 우선순위는 선택적 검색 조건
                if normalized_priority:
                    query += " AND priority LIKE ?"
                    params.append(f"%{normalized_priority}%")
                
                # 위치가 입력된 경우 위치 기반 정렬 우선
                if normalized_location:
                    query += " ORDER BY CASE WHEN location LIKE ? THEN 1 ELSE 2 END, created_at DESC LIMIT ?"
                    params.extend([f"%{normalized_location}%", limit])
                else:
                    query += " ORDER BY created_at DESC LIMIT ?"
                    params.append(limit)
                
                cursor = self.conn.execute(query, params)
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    # 실제 유사도 점수는 추천 엔진에서 계산되므로 임시 점수 제거
                    results.append(result)
                
                # 결과 수에 따른 처리
                if len(results) == 0:
                    self.logger.warning("검색 결과가 없습니다. 기본 검색으로 fallback")
                    return self._fallback_search(limit)
                elif 1 <= len(results) <= 5:
                    self.logger.info(f"검색 결과: {len(results)}건 (1-5건 범위)")
                    return results
                elif 6 <= len(results) <= 15:
                    self.logger.info(f"검색 결과: {len(results)}건 (6-15건 범위)")
                    return results[:5]  # 5개씩 묶어서 반환
                else:
                    self.logger.info(f"검색 결과: {len(results)}건 (15건 초과)")
                    return results[:5]  # 상위 5개만 반환
                
            except sqlite3.Error as e:
                retry_count += 1
                self.logger.error(f"SQL 에러 (시도 {retry_count}/{max_retries}): {e}")
                
                if retry_count >= max_retries:
                    self.logger.error("최대 재시도 횟수 초과. 기본 검색으로 fallback")
                    return self._fallback_search(limit)
                else:
                    # 간단한 쿼리로 재시도
                    try:
                        return self._simple_search(limit)
                    except Exception as fallback_error:
                        self.logger.error(f"Fallback 검색도 실패: {fallback_error}")
                        return []
        
        return []
    
    def _fallback_search(self, limit: int) -> List[Dict[str, Any]]:
        """기본 검색 (SQL 에러 시 fallback)"""
        try:
            query = '''
                SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
                FROM notification_history
                ORDER BY created_at DESC
                LIMIT ?
            '''
            cursor = self.conn.execute(query, [limit])
            columns = [description[0] for description in cursor.description]
            
            results = []
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                results.append(result)
            
            return results
        except Exception as e:
            self.logger.error(f"Fallback 검색 실패: {e}")
            return []
    
    def _simple_search(self, limit: int) -> List[Dict[str, Any]]:
        """간단한 검색 (복잡한 쿼리 실패 시)"""
        try:
            query = '''
                SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
                FROM notification_history
                LIMIT ?
            '''
            cursor = self.conn.execute(query, [limit])
            columns = [description[0] for description in cursor.description]
            
            results = []
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                results.append(result)
            
            return results
        except Exception as e:
            self.logger.error(f"간단한 검색 실패: {e}")
            return []
    
    def normalize_term(self, term: str, category: str) -> str:
        """LLM을 사용하여 용어를 표준 용어로 정규화"""
        if not term:
            return term
        
        # LLM 정규화 수행
        normalized_term, confidence = normalizer.normalize_term(term, category)
        
        # 신뢰도가 낮은 경우 원본 반환 (임계값을 높여서 더 보수적으로 정규화)
        if confidence < 0.8:
            return term
        
        return normalized_term
    
    def search_by_itemno(self, itemno: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        ITEMNO로 유사한 작업대상 검색
        
        Args:
            itemno: 검색할 작업대상 번호
            limit: 반환할 최대 결과 수
            
        Returns:
            유사한 작업대상 목록
            
        검색 전략:
        1. 정확한 매칭 우선
        2. 부분 매칭 (포함 관계)
        3. 유사한 패턴 매칭
        """
        # 다단계 검색 전략
        results = []
        
        # 1단계: 정확한 매칭
        query_exact = '''
            SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
            FROM notification_history
            WHERE itemno = ?
            ORDER BY created_at DESC
        '''
        cursor = self.conn.execute(query_exact, [itemno])
        columns = [description[0] for description in cursor.description]
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            results.append(result)
        
        # 2단계: 부분 매칭 (정확한 매칭이 없거나 부족한 경우)
        if len(results) < limit:
            query_partial = '''
                SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
                FROM notification_history
                WHERE itemno LIKE ? AND itemno != ?
                ORDER BY 
                    CASE 
                        WHEN itemno LIKE ? THEN 1  -- 시작 부분 매칭
                        WHEN itemno LIKE ? THEN 2  -- 끝 부분 매칭
                        ELSE 3                     -- 중간 부분 매칭
                    END,
                    created_at DESC
                LIMIT ?
            '''
            remaining_limit = limit - len(results)
            cursor = self.conn.execute(query_partial, [
                f"%{itemno}%", itemno,  # 부분 매칭, 정확한 매칭 제외
                f"{itemno}%",           # 시작 부분 매칭
                f"%{itemno}",           # 끝 부분 매칭
                remaining_limit
            ])
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                results.append(result)
        
        # 3단계: 패턴 유사성 검색 (예: 숫자 패턴, 문자 패턴 등)
        if len(results) < limit:
            # ITEMNO 패턴 분석
            import re
            
            # 숫자 패턴 추출
            numbers = re.findall(r'\d+', itemno)
            letters = re.findall(r'[A-Za-z]+', itemno)
            
            if numbers or letters:
                query_pattern = '''
                    SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
                    FROM notification_history
                    WHERE itemno NOT LIKE ?
                '''
                params = [f"%{itemno}%"]  # 이미 검색된 부분 매칭 제외
                
                # 숫자 패턴 매칭
                if numbers:
                    for num in numbers:
                        query_pattern += " AND itemno LIKE ?"
                        params.append(f"%{num}%")
                
                # 문자 패턴 매칭
                if letters:
                    for letter in letters:
                        query_pattern += " AND itemno LIKE ?"
                        params.append(f"%{letter}%")
                
                query_pattern += " ORDER BY created_at DESC LIMIT ?"
                remaining_limit = limit - len(results)
                params.append(remaining_limit)
                
                cursor = self.conn.execute(query_pattern, params)
                
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    results.append(result)
        
        return results[:limit]
    
    def get_status_codes(self) -> List[Dict[str, Any]]:
        """현상코드 목록 조회"""
        cursor = self.conn.execute("SELECT code, description, category FROM status_codes")
        return [{"code": row[0], "description": row[1], "category": row[2]} for row in cursor.fetchall()]
    
    def get_equipment_types(self) -> List[Dict[str, Any]]:
        """설비유형 목록 조회"""
        cursor = self.conn.execute("SELECT type_code, type_name, category FROM equipment_types")
        return [{"type_code": row[0], "type_name": row[1], "category": row[2]} for row in cursor.fetchall()]
    
    def get_equipment_type_data(self) -> List[Dict[str, Any]]:
        """설비유형 자료 조회 (자동완성용)"""
        try:
            cursor = self.conn.execute("SELECT * FROM equipment_types")
            return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"설비유형 자료 조회 오류: {e}")
            return []
    
    def get_notification_history_data(self) -> List[Dict[str, Any]]:
        """작업요청 이력 자료 조회 (자동완성용)"""
        try:
            cursor = self.conn.execute("SELECT * FROM notification_history")
            return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"작업요청 이력 자료 조회 오류: {e}")
            return []
    
    def get_notification_by_itemno(self, itemno: str) -> Optional[Dict[str, Any]]:
        """ITEMNO로 특정 알림 조회"""
        try:
            cursor = self.conn.execute('''
                SELECT itemno, process, location, equipType, statusCode, work_title, work_details, priority
                FROM notification_history
                WHERE itemno = ?
            ''', [itemno])
            
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            self.logger.error(f"ITEMNO 알림 조회 오류: {e}")
            return None
    
    def save_work_order(self, work_order_data: Dict[str, Any]) -> bool:
        """
        작업요청을 데이터베이스에 저장
        
        Args:
            work_order_data: 저장할 작업요청 데이터
            
        Returns:
            저장 성공 여부
            
        담당자 수정 가이드:
        - 외부 시스템 연동 로직 추가 필요
        - 트랜잭션 처리 및 롤백 로직 구현 필요
        - 감사 로그(Audit Log) 추가 권장
        """
        try:
            # 작업요청 테이블이 없으면 생성
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS work_orders (
                    itemno TEXT PRIMARY KEY,
                    work_title TEXT NOT NULL,
                    work_details TEXT NOT NULL,
                    process TEXT,
                    location TEXT,
                    equipType TEXT,
                    statusCode TEXT,
                    priority TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 작업요청 저장
            self.conn.execute('''
                INSERT INTO work_orders 
                (itemno, work_title, work_details, process, location, equipType, statusCode, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                work_order_data['itemno'],
                work_order_data['work_title'],
                work_order_data['work_details'],
                work_order_data['process'],
                work_order_data['location'],
                work_order_data['equipType'],
                work_order_data['statusCode'],
                work_order_data['priority'],
                work_order_data['created_at']
            ))
            
            self.conn.commit()
            self.logger.info(f"작업요청 저장 완료: ITEMNO={work_order_data['itemno']}")
            return True
            
        except Exception as e:
            self.logger.error(f"작업요청 저장 오류: {e}")
            return False
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager() 