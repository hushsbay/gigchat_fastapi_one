from common_fastapi.shared.db import get_db_connection
from common_fastapi.shared.logger import logger
from .search_conditions import validate_time_conditions, build_where_conditions

async def sql_search(state):
    """
    일반 SQL 검색 (requirements 제외)
    jobseeker의 조건과 employer의 jobs 테이블 데이터를 매칭
    """
    logger.info(f"[sql_search] 시작")
    
    condition = state.condition
    
    # start_time과 end_time 검증
    is_valid, error_msg = validate_time_conditions(condition)
    if not is_valid:
        logger.error(f"[sql_search] {error_msg}")
        state.result = []
        state.reply = error_msg
        return state
    
    # SQL 쿼리 기본 구조
    query = """
        SELECT id, company, title, location, hourly_wage, work_days, start_time, end_time,
               category, gender, age, description, deadline, status
          FROM public.jobs1
         WHERE status = 'ACTIVE'
    """
    
    # 공통 WHERE 조건 생성
    where_clause, params, param_count = build_where_conditions(condition, initial_param_count=0)
    query += where_clause
    
    # 공통 WHERE 조건 생성
    where_clause, params, param_count = build_where_conditions(condition, initial_param_count=0)
    query += where_clause
    
    # 최신 등록순 정렬, 최대 50개 제한
    query += " ORDER BY created_at DESC LIMIT 50"
    
    try:
        async with get_db_connection() as conn:
            rows = await conn.fetch(query, *params)
            
            # 결과를 딕셔너리 리스트로 변환
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "company": row["company"],
                    "title": row["title"],
                    "location": row["location"],
                    "hourly_wage": row["hourly_wage"],
                    "work_days": row["work_days"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "category": row["category"],
                    "gender": row["gender"],
                    "age": row["age"],
                    "description": row["description"],
                    "deadline": row["deadline"].isoformat() if row["deadline"] else None,
                    "status": row["status"]
                })
            
            logger.info(f"[sql_search] 검색 완료 - {len(results)}개 결과")
            
            # 상태 업데이트
            state.result = results
            
            # 응답 메시지 생성
            if len(results) > 0:
                state.reply = f"조건에 맞는 일자리 {len(results)}개를 찾았습니다."
            else:
                state.reply = "조건에 맞는 일자리를 찾지 못했습니다. 조건을 완화해보시겠어요?"
            
            return state
            
    except Exception as e:
        logger.exception(f"[sql_search] 오류 발생: {e}")
        state.result = []
        state.reply = "일자리 검색 중 오류가 발생했습니다."
        return state
