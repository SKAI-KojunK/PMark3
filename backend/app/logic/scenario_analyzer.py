import re
from typing import Dict, Any
from app.config import Config

class ScenarioAnalyzer:
    """자동완성용 시나리오 분석기 - 입력 패턴에 따라 추천 방식을 결정"""
    
    def __init__(self):
        # 자동완성 시나리오 1: 설비유형 기반 추천이 필요한 키워드들
        self.scenario1_keywords = [
            "압력", "베젤", "베셀", "vessel", "pressure",
            "밸브", "valve", "모터", "motor", "펌프", "pump",
            "탱크", "tank", "저장", "storage", "컨베이어", "conveyor",
            "열교환", "heat", "exchanger", "필터", "filter",
            "압축", "compressor", "팬", "fan", "블로워", "blower",
            "드럼", "drum", "반응", "reactor", "분석", "analyzer"
        ]
        
        # 자동완성 시나리오 2: ITEMNO 기반 추천이 필요한 패턴들
        self.scenario2_patterns = [
            r'^[A-Z]-',          # Y-MV1035 같은 패턴
            r'^[A-Z]{2,4}-',     # PE-SE1304B 같은 패턴
            r'^\d{4,}',          # 4자리 이상 숫자로 시작
            r'^[A-Z]{2,4}\d',    # 영문+숫자 조합
        ]
    
    def analyze_scenario(self, input_text: str) -> Dict[str, Any]:
        """자동완성을 위한 시나리오 분석 - 입력 패턴에 따라 추천 방식 결정"""
        if not input_text or not input_text.strip():
            return {
                "scenario_type": "scenario1",  # 기본값
                "confidence": 0.0,
                "reasoning": "입력이 없어 기본 시나리오 1을 적용합니다."
            }
        
        input_text = input_text.strip()
        
        # 시나리오 2 패턴 확인 (ITEMNO 자동완성)
        if self._is_itemno_pattern(input_text):
            return {
                "scenario_type": "scenario2",
                "confidence": 0.9,
                "reasoning": "ITEMNO 패턴으로 작업대상 자동완성을 제공합니다."
            }
        
        # 시나리오 1 키워드 확인 (설비유형 자동완성)
        if self._is_equipment_keyword(input_text):
            return {
                "scenario_type": "scenario1",
                "confidence": 0.8,
                "reasoning": "설비유형 관련 키워드로 설비유형 자동완성을 제공합니다."
            }
        
        # 기본값: 시나리오 1 (설비유형 기반)
        return {
            "scenario_type": "scenario1",
            "confidence": 0.5,
            "reasoning": "기본 시나리오 1로 설비유형 자동완성을 제공합니다."
        }
    
    def _is_itemno_pattern(self, input_text: str) -> bool:
        """ITEMNO 패턴인지 확인 (자동완성용)"""
        # 패턴 매칭
        for pattern in self.scenario2_patterns:
            if re.match(pattern, input_text, re.IGNORECASE):
                return True
        
        # 숫자로 시작하는 경우 (4자리 이상)
        if re.match(r'^\d{4,}', input_text):
            return True
        
        # 하이픈이 포함된 패턴 (ITEMNO 특성)
        if '-' in input_text and re.match(r'^[A-Z0-9\-"]+$', input_text):
            return True
        
        return False
    
    def _is_equipment_keyword(self, input_text: str) -> bool:
        """설비유형 관련 키워드인지 확인"""
        input_lower = input_text.lower()
        
        # 직접 키워드 매칭
        for keyword in self.scenario1_keywords:
            if keyword in input_lower:
                return True
        
        # 한글 설비 관련 키워드
        equipment_patterns = [
            r'.*설비.*', r'.*장비.*', r'.*기계.*', r'.*시설.*'
        ]
        
        for pattern in equipment_patterns:
            if re.search(pattern, input_lower):
                return True
        
        return False
    
    def _calculate_scenario2_score(self, input_text: str) -> float:
        """시나리오 2 점수 계산 (하위 호환성을 위해 유지)"""
        if self._is_itemno_pattern(input_text):
            return 3.0
        return 0.0
    
    def _calculate_scenario1_score(self, input_text: str) -> float:
        """시나리오 1 점수 계산 (하위 호환성을 위해 유지)"""
        if self._is_equipment_keyword(input_text):
            return 2.0
        return 1.0  # 기본값
    
    def _get_scenario2_reasoning(self, input_text: str) -> str:
        """시나리오 2 판단 근거 생성"""
        return "ITEMNO 패턴으로 작업대상 자동완성을 제공합니다."
    
    def _get_scenario1_reasoning(self, input_text: str) -> str:
        """시나리오 1 판단 근거 생성"""
        return "설비유형 관련 키워드로 설비유형 자동완성을 제공합니다."
    
    def is_scenario2_pattern(self, input_text: str) -> bool:
        """시나리오 2 패턴인지 빠르게 확인 (하위 호환성)"""
        return self._is_itemno_pattern(input_text) 