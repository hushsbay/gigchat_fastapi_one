from fastapi import FastAPI, status # https://fastapi.tiangolo.com/reference/status/
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import sys
from dotenv import load_dotenv  # 프로젝트별 .env 로드용
from contextlib import asynccontextmanager
from common_fastapi.shared.logger import logger
from common_fastapi.shared.constant import Const
from common_fastapi.shared.db import init_db_pool, close_db_pool, get_db_connection  # 공통 DB 모듈
from common_fastapi.shared.config import validate_env  # 공통 환경 변수 검증

from route.chat import router as chat_router
from route.admin import router as admin_router

origins = ["http://localhost:3000", "http://localhost:8082"]
load_dotenv() # 프로젝트별 환경 변수 로드 (LOG_PATH 등)
# API_KEY, DB_URL은 common_fastapi/.env 사용하고 LOG_PATH는 gigchat_fastapi/.env 사용

pool = None  # 하위 호환을 위한 module-level 변수
CATEGORIES = []  # DB에서 로드할 카테고리 목록 (kind='01', depth=1)
@asynccontextmanager
async def lifespan(app: FastAPI): # Application lifespan: 생성시 DB풀 만들고 종료시 닫음
    global pool, CATEGORIES
    validate_env() # 공통 환경 변수 검증 (API_KEY, DB_URL)
    pool = await init_db_pool() # common_fastapi의 DB 풀 초기화
    app.state.pool = pool
    
    try: # 카테고리 목록 로드
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                "SELECT nm FROM public.category WHERE kind = '01' AND depth = 1 ORDER BY seq"
            )
            CATEGORIES = [row['nm'] for row in rows] # logger.info(f"✅ 카테고리 로드 완료: {len(CATEGORIES)}개")
    except Exception as e:
        logger.exception(f"❌ 카테고리 로드 실패: {e}")
        CATEGORIES = []  # 실패 시 빈 배열
    
    try:
        yield # 애플리케이션 실행
    finally:
        try:
            await close_db_pool()  # common_fastapi의 close 함수 사용
        except Exception:
            logger.exception("Error closing DB pool on shutdown")

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

print(f"sys.executable={sys.executable}")
print(f"sys.version={sys.version.splitlines()[0]}")

app.include_router(chat_router, prefix="/chat")
app.include_router(admin_router, prefix="/admin")

# 예를 들어, localhost:8000/gigwork/doc_query/docid 라우팅인데 localhost:8000/gigwork/doc_query 만으로 요청시
# fastapi가 { "detail": "Not Found" }으로 응답하는데 아래 @app.exception_handler(Exception)로 걸리지 않고 있음
# 이 부분은 클라이언트에서 응답핸들링 공통 모듈을 작성하기로 함 
# - 그 경우 1) 아래 { "detail": { "code": Const.CODE_NOT_OK, "msg": str(ex) } }과 2) code,msg 없는 경우 둘 다 커버하기
    
# CORS 미들웨어가 이미 설정되어 있지만, 전역 예외 핸들러가 별도의 응답을 반환할 때는 명시적으로 CORS 헤더를 포함해 주는 것이 안전
# 더 좋은 방법은 예외 핸들러가 직접 CORS 처리를 하느니 CORS 미들웨어가 항상 응답 헤더를 붙이도록 설정하거나, 
# 예외 핸들러에서 app.middleware('http') 같은 공통 로직을 통해 헤더를 보장하는 구조를 향후 고려
@app.exception_handler(Exception) # FastAPIHTTPException)
async def custom_http_exception_handler(request: Request, ex: Exception): # FastAPIHTTPException):
    logger.exception("Unhandled exception : %s", ex)
    # Browser may block access to response body if CORS headers are missing
    # Ensure we echo the Origin header (if present) so the browser can read the response
    origin = request.headers.get("origin")
    cors_headers = {}
    if origin:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse( # Return a JSON body with details. Use ex.__str__() so messages propagate
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={ "detail": { "code": Const.CODE_NOT_OK, "msg": str(ex) } },
        headers=cors_headers
    )
