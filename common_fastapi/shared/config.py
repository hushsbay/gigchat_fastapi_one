# 환경 변수 중앙 관리 : API_KEY, DB URL 등 공통 설정은 common_fastapi/.env에서 로드
# 각 프로젝트별 설정(LOG_PATH 등)은 프로젝트의 .env에서 로드
import os
from pathlib import Path
from dotenv import load_dotenv

# common_fastapi 프로젝트의 .env 파일 로드 (API 키, DB URL 등 공통 설정)
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)

# 공통 환경 변수 (common_fastapi/.env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL")

# 프로젝트별 환경 변수 (각 프로젝트의 .env에서 읽음)
# LOG_PATH, DEFAULT_TIMEZONE 등은 각 프로젝트에서 load_dotenv() 후 os.getenv()로 사용
def get_env(key: str, default=None): # 환경 변수 가져오기
    return os.getenv(key, default)

def validate_env(): # 검증 (공통 환경 변수만) : 필수 공통 환경 변수 검증
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not DB_URL:
        missing.append("DB_URL")
    if missing:
        raise ValueError(f"❌ 필수 환경 변수가 없습니다: {', '.join(missing)}")
    # print("✅ 공통 환경 변수 로드 완료 (OPENAI_API_KEY, DB_URL)")
