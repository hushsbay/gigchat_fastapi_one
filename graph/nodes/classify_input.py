import json
from typing import Any, Dict
from common_fastapi.ai.llm_openai import LLMClient
# CATEGORIES는 여기 말고 함수 내에서 지연 import (순환 import 방지)

llm = LLMClient()

#####################################################
def _safe_json_parse(text: str) -> Dict[str, Any]: # JSON 파싱 실패 시 빈 딕셔너리 반환
    try:
        return json.loads(text)
    except Exception:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except Exception:
            return {}

def _normalize(cond: Dict[str, Any]) -> Dict[str, Any]: # 조건 정규화 - 모든 키가 존재하도록 보장
    base = {
        "gender": None,
        "age": None,
        "place": None,
        "work_days": None,
        "start_time": None,
        "end_time": None,
        "hourly_wage": None,
        "category": None,
        "requirements": None,
    }
    base.update(cond or {})
    return base
#####################################################

def classify_input(state): # LLM 한 번 호출로 아래 2단계 작업 수행
    
    import main # 순환 import 방지를 위한 지연 import
    CATEGORIES = main.CATEGORIES # print(f'===== {CATEGORIES}')

    print(f'state.text===== {state.text}')
    
    prompt = f"""
    1. 다음 작업을 수행하세요.
       사용자 입력중에 아래 2. 중요 규칙과 관련 있다면 그건 알바/일자리를 찾기 위한 내용이라고 봐야 함.
       그래서, 사용자 입력이 아르바이트/알바/일자리와 관련되어 있다면, 일자리 조건(아래 2. 중요 규칙)을 추출해야 함
    2. 중요 규칙      
      1) 성별(gender) : "남성" 또는 "여성" 으로만 표시
      2) 나이(age) : 숫자 + '대'로 항상 표시해야 함
        - 예1) 32 또는 35세 또는 39살 : "30대"로 표시
        - 예2) 30대 : "30대" 그대로 표시
      3) 지역(place)
        - 전국 시,도,군,구 등 지역명이 들어 있으면 행정구역상 공식 명칭으로 추출
        - 전국의 유명 관광지, 알려진 hot place 등이 나오면 그곳이 속한 공식 행정구역명을 찾아 반환
        - 어느 지역에 거주한다, 살고 있다라고 하면 그건 알바를 구하는 의미일 수도 있음
        - 예1) 서울 강남 => "서울시 강남구"
        - 예2) 철산 => "경기도 광명시 철산동"
        - 예3) 수원 매탄동 => "경기도 수원시 영통구 매탄동"
        - 예4) 해운대 => "부산시 해운대구"
        - 예5) 제부도 => 경기도 안산시 제부도가 아닌 "경기도 안산시 서신면 제부리"로 나와야 함 (그게 어렵거나 정확치 않으면 "경기도 안산시"까지만 추출)
      4) 근무요일(work_days)은 요일 여러 개를 지정할 수 있음 (예: "월화수")
        - 주중은 "월화수목금", 주말은 "토일"을 의미
        - 주말과 월요일인 경우 "토일월"을 의미
      5) 근무시작시각(start_time)와 근무종료시각(end_time)
        - hh:mm이 표준
        - 예1) 근무 시작이 9시 : "09:00"
        - 예2) 근무 시작이 9시반 : "09:30"
        - 예3) 근무 종료가 18시 : "18:00"
        - 예4) 근무 종료가 18시반 : "18:30"
        - 예5) 오전 또는 오전 근무라고 하면 : start_time은 "09:00" end_time은 "14:00"으로 표시
        - 예6) 오후 또는 오후 근무라고 하면 : start_time은 "14:00" end_time은 "18:00"으로 표시
        - 예7) 09:00-18:00 또는 0900~1800 형식이라면 start_time은 09:00 end_time은 18:00으로 표시
        - 예8) 종일근무는 09:00-18:00로 보고 start_time은 09:00 end_time은 18:00으로 표시
      6) 시급(hourly_wage)은 알바 입장에서는 사실상 특정 시급 이상만 원하므로 최저 시급이며 아래와 같은 형식으로 저장
        - 숫자만 표시되도록 함
        - 숫자 다음의 화폐 단위(예: 원)는 제거하기
      7) 희망하는 알바/일자리의 업종/카테고리(category)는 아래에서 하나만 선택
        - {', '.join(CATEGORIES)}
        - 예1) 수영장 : 위 카테고리중 "문화/여가/생활"를 선택
        - 예2) 프로그래밍 : 위 카테고리중 "IT/인터넷"를 선택
      8) 추가 조건(requirements)
        - 만일 위 항목들이 아닌 사용자가 추가로 요구하는 알바/일자리와 관련 있는 내용이거나 자격증, 기존 일자리 경험이 있으면
          아래 응답형식 json중에 requirements 값에 넣어줘 (중요함)
        - 예1) 운전 면허증
        - 예2) 수영 강사 자격증, 경험 등
        - 예3) 바리스타 자격증, 경험 등
        - 참고로, 이 requirements값이 들어 있으면 별도 검색 버튼을 눌러 Vector data 검색으로 처리하고자 함
    ### 응답 형식 (반드시 이 JSON 형식으로만 응답)
    {{
      "job_related": true | false,
      "condition": {{
        "gender": string | null,
        "age": string | number | null,
        "place": string | null,
        "work_days": string | null,
        "start_time": string | null,
        "end_time": string | null,
        "hourly_wage": string | number | null,
        "category": string | null,
        "requirements": string | null,
      }}
    }}
    ### 예시 1) 아래 사용자 입력은 위 2. 중요 규칙에 있으므로 일자리 조건이라고 봐야 함
    **입력**: "강남에 거주하는 35세 남자입니다."
    **응답**:
    {{
      "job_related": true,
      "condition": {{
        "place": "서울특별시 강남구",
        "age": "30대",
        "gender": "남성"
      }}
    }}
    ### 예시 2)
    **입력**: "오늘 날씨 어때?"
    **응답**:
    {{
      "job_related": false,
      "condition": {{}}
    }}
    3. 사용자 입력: "{state.text}"
    """
    
    messages = [{"role": "user", "content": prompt}]
    raw_response = llm.chat(messages)
    print(f"[classify_input] LLM raw response: {raw_response}")
    parsed = _safe_json_parse(raw_response) # JSON 파싱
    state.job_related = parsed.get("job_related", False) # 일자리 관련 여부
    if not state.job_related:
        state.reply = "죄송합니다. 알바/일자리 검색과 관련된 질문만 주시면 감사하겠습니다."
        print(f"[classify_input] Not job-related")
        return state
    
    extracted = _normalize(parsed.get("condition", {})) # 조건 추출 및 병합
    merged = dict(state.condition or {})
    for k, v in extracted.items():
        if v not in (None, "", []):
            merged[k] = v
    state.condition = merged
    state.reply = "일자리 조건을 추가 또는 업데이트했습니다."
    
    print(f"[classify_input] Job-related=True, extracted: {extracted}")
    print(f"[classify_input] Merged condition: {merged}")
    
    return state
