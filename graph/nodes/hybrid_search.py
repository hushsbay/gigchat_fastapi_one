from common_fastapi.shared.db import get_db_connection
from common_fastapi.shared.logger import logger
from common_fastapi.ai.embed_jhgan import EmbedderKo
from common_fastapi.ai.embed_openai import _client_embed
from .search_conditions import validate_time_conditions, build_where_conditions

# 768차원 임베딩 모델 (jhgan/ko-sroberta-multitask)
embedder_768 = None
# 1536차원 임베딩 모델 (OpenAI text-embedding-3-small)
# _client_embed는 common_fastapi에서 가져옴

def get_embedder_768():
    """768차원 임베딩 모델 싱글톤"""
    global embedder_768
    if embedder_768 is None:
        embedder_768 = EmbedderKo()
    return embedder_768


async def hybrid_search(state):
    """
    하이브리드 검색: 일반 SQL 검색 + 벡터 유사도 검색
    - requirements 필드를 벡터 임베딩하여 유사도 검색
    - sql_search의 WHERE 조건을 재사용하고, 벡터 검색 조건을 추가
    """
    logger.info(f"[hybrid_search] 시작")
    
    condition = state.condition
    requirements = condition.get("requirements")
    
    # requirements가 없으면 일반 SQL 검색과 동일
    if not requirements or not requirements.strip():
        logger.warning("[hybrid_search] requirements 없음 - 일반 SQL 검색으로 대체")
        state.result = []
        state.reply = "추가 조건(requirements)이 없어 하이브리드 검색을 수행할 수 없습니다."
        return state
    
    # start_time과 end_time 검증
    is_valid, error_msg = validate_time_conditions(condition)
    if not is_valid:
        logger.error(f"[hybrid_search] {error_msg}")
        state.result = []
        state.reply = error_msg
        return state
    
    # 임베딩 모델 선택
    embedding_model = state.embeddingModel or "jhgan"
    similarity_threshold = state.similarityThreshold or 0.4
    
    logger.info(f"[hybrid_search] embedding_model: {embedding_model}, threshold: {similarity_threshold}")
    
    # requirements 임베딩 생성
    try:
        if embedding_model == "jhgan":
            embedder = get_embedder_768()
            requirements_embedding = embedder.create_embedding(requirements)
            embedding_field = "embedding768"
            logger.info(f"[hybrid_search] 768차원 임베딩 생성 완료")
        elif embedding_model == "openai":
            if not _client_embed:
                raise Exception("OpenAI API Key가 설정되지 않았습니다")
            response = _client_embed.embeddings.create(
                model="text-embedding-3-small",
                input=requirements
            )
            requirements_embedding = response.data[0].embedding
            embedding_field = "embedding1536"
            logger.info(f"[hybrid_search] 1536차원 임베딩 생성 완료")
        else:
            raise Exception(f"지원하지 않는 임베딩 모델: {embedding_model}")
        
        if not requirements_embedding:
            raise Exception("임베딩 생성 실패")
    
    except Exception as e:
        logger.exception(f"[hybrid_search] 임베딩 생성 오류: {e}")
        state.result = []
        state.reply = f"벡터 임베딩 생성 중 오류가 발생했습니다: {str(e)}"
        return state
    
    # SQL 쿼리 기본 구조
    query = """
        SELECT id, company, title, location, hourly_wage, work_days, start_time, end_time,
               category, gender, age, description, deadline, status,
               1 - ({embedding_field} <=> $1::vector) AS similarity
          FROM public.jobs1
         WHERE status = 'ACTIVE'
    """.replace("{embedding_field}", embedding_field)
    
    # 첫 번째 파라미터는 임베딩 벡터
    # 공통 WHERE 조건 생성 (초기 param_count는 1, 임베딩 벡터가 $1이므로)
    where_clause, condition_params, param_count = build_where_conditions(condition, initial_param_count=1)
    query += where_clause
    
    # 파라미터 리스트: 임베딩 벡터 + 조건 파라미터
    params = [requirements_embedding] + condition_params
    
    # 9. 벡터 유사도 조건 (임계값)
    query += f" AND (1 - ({embedding_field} <=> $1::vector)) >= {similarity_threshold}"
    
    # 유사도 높은 순, 최신 등록순 정렬, 최대 50개 제한
    query += " ORDER BY similarity DESC, created_at DESC LIMIT 50"
    
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
                    "status": row["status"],
                    "similarity": float(row["similarity"])
                })
            
            logger.info(f"[hybrid_search] 검색 완료 - {len(results)}개 결과")
            
            # 상태 업데이트
            state.result = results
            
            # 응답 메시지 생성
            if len(results) > 0:
                state.reply = f"하이브리드 검색 결과: {len(results)}개의 일자리를 찾았습니다."
            else:
                state.reply = "조건에 맞는 일자리를 찾지 못했습니다. 조건을 완화해보시겠어요?"
            
            return state
            
    except Exception as e:
        logger.exception(f"[hybrid_search] 오류 발생: {e}")
        state.result = []
        state.reply = "하이브리드 검색 중 오류가 발생했습니다."
        return state

