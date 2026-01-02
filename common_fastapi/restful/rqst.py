from pydantic import BaseModel
from typing import Any, Dict, Optional

class ChatRequest(BaseModel): # 챗봇에서 요청하는 검색 조건 채우기 또는 실제 검색용 공통 Request
    userid: Optional[str] = None
    text: str
    condition: Optional[Dict[str, Any]] = {}
    search: bool = False
    embeddingModel: str = 'jhgan'
    similarityThreshold: float = 0.3