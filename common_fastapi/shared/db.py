# DB 연결 풀 중앙 관리 : 모든 프로젝트는 이 모듈의 pool 사용
import asyncpg
from pgvector.asyncpg import register_vector
from contextlib import asynccontextmanager
from common_fastapi.shared.config import DB_URL
from common_fastapi.shared.logger import logger

_pool = None # 전역 DB 풀

# 아래 create_pool(...)에 init=register_vector를 전달하도록 수정
# 이로써 풀에서 생성되는 모든 커넥션에 pgvector 타입 코덱이 등록되어 간헐적인 "expected str, got list" 오류를 방지
# 안전을 위해 풀 생성 직후 단일 커넥션에 대해 호출하던 await register_vector(conn)도 그대로 남겨둠 (무해하며 충돌 없음)
async def init_db_pool(database_url: str = None, min_size: int = 1, max_size: int = 10): # DB 연결 풀 초기화
    global _pool    
    db_url = database_url or DB_URL
    if not db_url:
        raise ValueError("❌ DB_URL이 설정되지 않았습니다")
    _pool = await asyncpg.create_pool(db_url, min_size=min_size, max_size=max_size, command_timeout=60, init=register_vector) # pgvector 등록
    async with _pool.acquire() as conn: # 첫 연결 테스트
        await register_vector(conn)
    # logger.info(f"✅ DB 연결 풀 초기화 완료 (min={min_size}, max={max_size})")
    return _pool

async def close_db_pool(): # DB 연결 풀 종료
    global _pool
    if _pool:
        await _pool.close()
        # logger.info("✅ DB 연결 풀 종료")
        _pool = None

def get_pool(): # 현재 DB 풀 반환
    if _pool is None:
        raise RuntimeError("❌ DB 풀이 초기화되지 않았습니다. init_db_pool()을 먼저 호출하세요")
    return _pool

@asynccontextmanager
async def get_db_connection(): # DB 연결 가져오기 (컨텍스트 매니저)
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
