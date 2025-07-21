from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import re
from app.database import DatabaseManager
from app.logic.scenario_analyzer import ScenarioAnalyzer

router = APIRouter()

class AutocompleteRequest(BaseModel):
    input_text: str
    scenario_type: Optional[str] = None  # "scenario1" or "scenario2"

class AutocompleteResponse(BaseModel):
    suggestions: List[str]
    scenario_type: Optional[str]
    confidence: float

class ScenarioAnalysisRequest(BaseModel):
    input_text: str

class ScenarioAnalysisResponse(BaseModel):
    scenario_type: str  # "scenario1" or "scenario2"
    confidence: float
    reasoning: str

@router.post("/analyze-scenario", response_model=ScenarioAnalysisResponse)
async def analyze_scenario(request: ScenarioAnalysisRequest):
    """사용자 입력을 분석하여 시나리오 1 또는 2로 분류"""
    try:
        analyzer = ScenarioAnalyzer()
        result = analyzer.analyze_scenario(request.input_text)
        
        return ScenarioAnalysisResponse(
            scenario_type=result["scenario_type"],
            confidence=result["confidence"],
            reasoning=result["reasoning"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시나리오 분석 중 오류: {str(e)}")

@router.post("/autocomplete", response_model=AutocompleteResponse)
async def get_autocomplete_suggestions(request: AutocompleteRequest):
    """사용자 입력에 대한 자동완성 추천 제공"""
    try:
        if not request.input_text.strip():
            return AutocompleteResponse(suggestions=[], scenario_type=None, confidence=0.0)
        
        # 시나리오 타입이 지정되지 않은 경우 자동 분석
        if not request.scenario_type:
            analyzer = ScenarioAnalyzer()
            analysis = analyzer.analyze_scenario(request.input_text)
            scenario_type = analysis["scenario_type"]
            confidence = analysis["confidence"]
        else:
            scenario_type = request.scenario_type
            confidence = 1.0
        
        # 시나리오별 자동완성 추천
        if scenario_type == "scenario1":
            suggestions = get_scenario1_suggestions(request.input_text)
        elif scenario_type == "scenario2":
            suggestions = get_scenario2_suggestions(request.input_text)
        else:
            # 두 시나리오 모두에서 추천
            suggestions = get_combined_suggestions(request.input_text)
        
        return AutocompleteResponse(
            suggestions=suggestions[:7],  # 최대 7개 추천
            scenario_type=scenario_type,
            confidence=confidence
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자동완성 생성 중 오류: {str(e)}")

def get_scenario1_suggestions(input_text: str) -> List[str]:
    """시나리오 1용 자동완성 추천 (설비유형 기반)"""
    suggestions = []
    
    try:
        # 설비유형 자료에서 추천
        db = DatabaseManager()
        equipment_data = db.get_equipment_type_data()
        
        if not equipment_data:
            return suggestions
        
        input_lower = input_text.lower().strip()
        input_words = input_lower.split()  # 입력 텍스트를 단어로 분리
        
        for row in equipment_data:
            equipment_type = row.get('type_name', '')  # 설비유형 컬럼
            equipment_code = row.get('type_code', '')  # 설비유형 코드 컬럼
            
            if not equipment_type or not equipment_code:
                continue
            
            equipment_type_lower = equipment_type.lower()
            equipment_code_lower = equipment_code.lower()
            
            # 1. 설비유형 코드 매칭 (2글자 이상 일치) - 참조는 코드, 추천은 설비유형
            if len(input_lower) >= 2 and input_lower in equipment_code_lower:
                suggestions.append(equipment_type)
            
            # 2. 설비유형의 영문 단어 매칭 (한 단어 이상 일치)
            equipment_words = equipment_type_lower.split()
            for word in equipment_words:
                # 영문 단어만 매칭 (한글 제외)
                if re.match(r'^[a-zA-Z]+$', word) and len(word) >= 2:
                    # 입력의 각 단어와 매칭
                    for input_word in input_words:
                        if len(input_word) >= 2 and (input_word in word or word.startswith(input_word)):
                            suggestions.append(equipment_type)
                            break
                    if equipment_type in suggestions:
                        break
            
            # 3. 전체 입력 텍스트와 설비유형 매칭
            if len(input_lower) >= 2:
                # 입력 텍스트의 일부가 설비유형에 포함되는지 확인
                for input_word in input_words:
                    if len(input_word) >= 2 and input_word in equipment_type_lower:
                        suggestions.append(equipment_type)
                        break
        
        # 중복 제거 및 유사도 순 정렬
        suggestions = list(set(suggestions))
        suggestions.sort(key=lambda x: calculate_similarity(input_text, x), reverse=True)
        
    except Exception as e:
        print(f"시나리오 1 자동완성 오류: {e}")
    
    return suggestions

def get_scenario2_suggestions(input_text: str) -> List[str]:
    """시나리오 2용 자동완성 추천 (작업대상 기반)"""
    suggestions = []
    
    try:
        # Noti이력에서 작업대상 추천
        db = DatabaseManager()
        notification_data = db.get_notification_history_data()
        
        if not notification_data:
            return suggestions
        
        input_lower = input_text.lower().strip()
        input_words = input_lower.split()  # 입력 텍스트를 단어로 분리
        
        for row in notification_data:
            item_no = row.get('itemno', '')  # 작업대상 컬럼
            
            if not item_no:
                continue
            
            item_no_lower = item_no.lower()
            
            # 숫자로 시작하는 경우 (4개 이상 일치)
            if re.match(r'^\d', input_text):
                if len(input_text) >= 4:
                    # 숫자 부분 추출
                    input_numbers = re.findall(r'\d+', input_text)
                    item_numbers = re.findall(r'\d+', item_no)
                    
                    for input_num in input_numbers:
                        for item_num in item_numbers:
                            if input_num in item_num or item_num in input_num:
                                suggestions.append(item_no)
                                break
                        if item_no in suggestions:
                            break
            
            # 영문 코드로 시작하는 경우 (2글자 이상 일치)
            elif re.match(r'^[A-Za-z]', input_text):
                if len(input_lower) >= 2:
                    # 영문 부분 추출
                    input_alpha = re.findall(r'[A-Za-z]+', input_text)
                    item_alpha = re.findall(r'[A-Za-z]+', item_no)
                    
                    for input_alpha_part in input_alpha:
                        for item_alpha_part in item_alpha:
                            if input_alpha_part.lower() in item_alpha_part.lower() or \
                               item_alpha_part.lower() in input_alpha_part.lower():
                                suggestions.append(item_no)
                                break
                        if item_no in suggestions:
                            break
            
            # 일반적인 부분 문자열 매칭 (2글자 이상)
            if len(input_lower) >= 2 and input_lower in item_no_lower:
                suggestions.append(item_no)
            
            # 4. 입력 텍스트의 각 단어와 매칭
            for input_word in input_words:
                if len(input_word) >= 2 and input_word in item_no_lower:
                    suggestions.append(item_no)
                    break
        
        # 중복 제거 및 유사도 순 정렬
        suggestions = list(set(suggestions))
        suggestions.sort(key=lambda x: calculate_similarity(input_text, x), reverse=True)
        
    except Exception as e:
        print(f"시나리오 2 자동완성 오류: {e}")
    
    return suggestions

def get_combined_suggestions(input_text: str) -> List[str]:
    """두 시나리오 모두에서 추천 (유사도가 높은 것 우선)"""
    scenario1_suggestions = get_scenario1_suggestions(input_text)
    scenario2_suggestions = get_scenario2_suggestions(input_text)
    
    # 모든 추천을 합치고 유사도 순으로 정렬
    all_suggestions = scenario1_suggestions + scenario2_suggestions
    all_suggestions = list(set(all_suggestions))  # 중복 제거
    
    # 유사도 순으로 정렬
    all_suggestions.sort(key=lambda x: calculate_similarity(input_text, x), reverse=True)
    
    return all_suggestions

def calculate_similarity(input_text: str, suggestion: str) -> float:
    """입력 텍스트와 추천 항목 간의 유사도 계산"""
    if not input_text or not suggestion:
        return 0.0
    
    input_lower = input_text.lower()
    suggestion_lower = suggestion.lower()
    input_words = input_lower.split()
    
    # 정확한 일치
    if input_lower == suggestion_lower:
        return 1.0
    
    # 시작 부분 일치
    if suggestion_lower.startswith(input_lower):
        return 0.9
    
    # 포함 관계
    if input_lower in suggestion_lower:
        return 0.8
    
    # 단어 단위 매칭 (더 높은 우선순위)
    matched_words = 0
    for input_word in input_words:
        if len(input_word) >= 2 and input_word in suggestion_lower:
            matched_words += 1
    
    if matched_words > 0:
        word_similarity = matched_words / len(input_words)
        return 0.7 + (word_similarity * 0.2)  # 0.7 ~ 0.9 범위
    
    # 부분 일치 (공통 문자 수)
    common_chars = sum(1 for c in input_lower if c in suggestion_lower)
    if common_chars > 0:
        return min(0.6, common_chars / len(input_lower))
    
    return 0.0 