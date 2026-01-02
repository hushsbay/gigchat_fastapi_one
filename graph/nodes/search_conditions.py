"""
공통 검색 조건 처리 모듈
sql_search와 hybrid_search에서 공통으로 사용하는 WHERE 조건 생성 로직
"""
import re
from typing import Dict, List, Tuple, Any

def normalize_region(region_name: str) -> str:
    """
    특별시/광역시/특별자치시/특별자치도 등을 간소화
    예) 서울특별시 -> 서울시, 광주광역시 -> 광주시
    예) 제주특별자치도 -> 제주도, 세종특별자치시 -> 세종시
    """
    region_name = region_name.replace("특별자치도", "도")
    region_name = region_name.replace("특별자치시", "시")
    region_name = region_name.replace("특별시", "시")
    region_name = region_name.replace("광역시", "시")
    return region_name


def validate_time_conditions(condition: Dict[str, Any]) -> Tuple[bool, str]:
    """
    start_time과 end_time 검증
    Returns: (is_valid, error_message)
    """
    has_start = condition.get("start_time") not in (None, "")
    has_end = condition.get("end_time") not in (None, "")
    
    if has_start != has_end:  # XOR: 둘 중 하나만 있으면
        return False, "근무 시작시각과 종료시각은 둘 다 입력하거나 둘 다 비워야 합니다."
    
    return True, ""


def build_where_conditions(
    condition: Dict[str, Any],
    initial_param_count: int = 0
) -> Tuple[str, List[Any], int]:
    """
    검색 조건에 따라 WHERE 절과 파라미터를 생성
    requirements 조건은 제외 (벡터 검색용)
    
    Args:
        condition: 검색 조건 딕셔너리
        initial_param_count: 시작 파라미터 번호 (기본값 0)
    
    Returns:
        (where_clause, params, param_count)
        - where_clause: SQL WHERE 절 문자열
        - params: 바인딩할 파라미터 리스트
        - param_count: 최종 파라미터 개수
    """
    where_parts = []
    params = []
    param_count = initial_param_count
    
    # 1. gender 조건: 남성인 경우 gender in ('무관', '남성')
    if condition.get("gender"):
        param_count += 1
        where_parts.append(f" AND gender IN ('무관', ${param_count})")
        params.append(condition["gender"])
    
    # 2. age 조건: varchar 배열 필드에서 '20대' 같은 값 찾기
    if condition.get("age"):
        age_value = condition["age"]
        
        # age가 숫자인 경우 연령대 계산 (예: 25 -> "20대", 32 -> "30대")
        if isinstance(age_value, (int, float)):
            age_range = f"{int(age_value) // 10 * 10}대"
        elif isinstance(age_value, str):
            age_range = age_value
        else:
            age_range = str(age_value)
        
        param_count += 1
        where_parts.append(f" AND ${param_count}::varchar = ANY(age)")
        params.append(age_range)
    
    # 3. place 조건: 시/군까지만 매칭 (제주도는 제주도까지만)
    if condition.get("place"):
        place = condition["place"]
        place = normalize_region(place)
        
        if place.startswith("제주"):
            region_pattern = "제주"
        else:
            match = re.match(r'^(.+[시군도])(?:\s|$)', place)
            if match:
                region_pattern = match.group(1)
            else:
                region_pattern = place
        
        param_count += 1
        where_parts.append(f"""
            AND REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(location, '특별자치도', '도', 'g'),
                        '특별자치시', '시', 'g'),
                    '특별시', '시', 'g'),
                '광역시', '시', 'g'
            ) LIKE ${param_count} || '%'
        """)
        params.append(region_pattern)
    
    # 4. work_days 조건: DB에 저장된 모든 요일이 검색 조건에 포함되어야 함
    # 예) DB에 "월화수" 저장 시, 검색 조건이 "월"만 있으면 X, "월화수" 또는 "월화수목"이면 O
    if condition.get("work_days"):
        work_days = condition["work_days"]
        if isinstance(work_days, str):
            if "," in work_days:
                days_list = [day.strip() for day in work_days.split(",")]
            else:
                days_list = [work_days[i:i+1] for i in range(0, len(work_days), 1)]
            
            param_count += 1
            where_parts.append(f" AND ${param_count}::varchar[] @> work_days")
            params.append(days_list)
    
    # 5-6. start_time, end_time 조건: 전후 1시간 범위
    has_start = condition.get("start_time") not in (None, "")
    has_end = condition.get("end_time") not in (None, "")
    
    if has_start and has_end:
        start_time = condition["start_time"]
        end_time = condition["end_time"]
        
        param_count += 1
        start_param = param_count
        param_count += 1
        end_param = param_count
        
        where_parts.append(f"""
            AND start_time::time BETWEEN (${start_param}::text::time - interval '1 hour')
                                     AND (${start_param}::text::time + interval '1 hour')
            AND end_time::time BETWEEN (${end_param}::text::time - interval '1 hour')
                                   AND (${end_param}::text::time + interval '1 hour')
        """)
        params.append(start_time)
        params.append(end_time)
    
    # 7. hourly_wage 조건: 최소 시급 이상
    if condition.get("hourly_wage"):
        wage = condition["hourly_wage"]
        if isinstance(wage, str):
            wage = int(''.join(filter(str.isdigit, wage)))
        
        param_count += 1
        where_parts.append(f" AND hourly_wage >= ${param_count}")
        params.append(int(wage))
    
    # 8. category 조건
    if condition.get("category"):
        param_count += 1
        where_parts.append(f" AND category = ${param_count}")
        params.append(condition["category"])
    
    where_clause = ''.join(where_parts)
    return where_clause, params, param_count
