from fastapi import Request
import os
from pathlib import Path
from typing import List
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from functools import lru_cache

DEFAULT_TZ = os.getenv("DEFAULT_TIMEZONE", "Asia/Seoul")

def _get_zone(tz_name: str | None):
    name = tz_name or DEFAULT_TZ
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc

def format_datetime(dt: datetime | None, tz_name: str | None = None) -> str | None:
    """
    Convert a datetime (possibly naive) to target timezone and return
    formatted string "YYYY-MM-DD HH:MM:SS.ffffff".
    If dt is None return None. If dt is not a datetime, return str(dt).
    """
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return str(dt)
    # treat naive datetimes as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    target = _get_zone(tz_name)
    try:
        converted = dt.astimezone(target)
        return converted.strftime("%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        try:
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return str(dt)

# lru_cache()를 쓰면 프로세스가 살아있는 동안 (개발 중 uvicorn --reload로 재시작되면 새로 로드됨) 파일을 반복해서 읽지 않음
# 캐시 동작: lru_cache()는 간단하고 성능 좋지만, 개발 중 ACL 파일을 수정하면 캐시가 즉시 갱신되지 않음
# 개발용으로는 lru_cache 대신 매요청 읽기를 하거나, 변경 시 get_server_keys.cache_clear()를 호출하는 엔드포인트(관리용)를 만들 수 있음
# 만약 server.acl을 자주 수정하고 캐시 무효화 없이 즉시 반영하고 싶다면 lru_cache를 제거하거나, 파일의 최종 수정시간을 체크해서 필요 시 다시 읽도록 구현
@lru_cache() # lru_cache로 캐시하여 매요청 파일 I/O를 피함
def get_server_keys() -> List[str]:
    ACL_FILE = os.path.join(Path(__file__).resolve().parents[1], "server.acl")
    try:
        text = Path(ACL_FILE).read_text(encoding="utf-8")
        keys = [ln.strip() for ln in text.splitlines() if ln.strip()]
    except Exception:
        keys = []
    return keys
        
def chk_server_Key(serverkeyArr: list[str], request: Request) -> str:
    server_key = request.headers.get("server_key")
    if server_key not in serverkeyArr:
        return f'허용된 서버키가 아닙니다: {server_key}'
    return ''
