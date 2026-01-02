import json, re, os
from typing import List, Optional, Tuple, Any
from openai import OpenAI # type: ignore

# 벡터(Vector)는 형식/구조, 임베딩(Embedding)은 목적/의미
# 벡터 = 수치들의 배열로 표현된 데이터 구조
# 임베딩 = 데이터(텍스트,이미지 등)를 의미를 보존하면서 숫자 벡터로 변환한 것 : list[float]

_client_embed = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

def _coerce_to_list(emb: Any) -> Optional[List[float]]: # 리스트로 강제 형 변환
    # emb => list[float]. 성공시 list[float] 반환, 실패(if cannot coerce)시 None
    if emb is None:
        return None
    if isinstance(emb, (list, tuple)): # already list/tuple of numbers
        try:
            return [float(x) for x in emb]
        except Exception:
            return None
    if isinstance(emb, str): # JSON string containing a list
        try:
            obj = json.loads(emb)
            if isinstance(obj, (list, tuple)):
                return [float(x) for x in obj]
        except Exception:
            pass
        s = emb.strip() # fallback: simple bracketed number parsing without eval
        if s.startswith('[') and s.endswith(']'):
            inner = s[1:-1].strip() # 문자열 s 첫번째/마지막 제외한 나머지 부분의 양쪽 끝 공백 제거
            if inner == "":
                return []
            parts = re.split(r'\s*,\s*', inner) # r'\s*,\s*' => 0개 이상의 공백 문자, 그 뒤에 오는 쉼표, 그 뒤에 오는 0개 이상의 공백 문자와 일치하는 부분을 찾음
            try: # 위는 inner 문자열을 양쪽에 공백이 있거나 없는 쉼표를 기준으로 분리하여 공백이 제거된 깔끔한 항목들의 리스트를 생성
                return [float(p) for p in parts]
            except Exception:
                return None
    # numpy arrays (optional)
    try:
        import numpy as np  # type: ignore
        if isinstance(emb, np.ndarray):
            return emb.astype(float).tolist()
    except Exception:
        pass
    return None

def prepare_embedding_param(embedding: Any) -> Tuple[bool, Any]: # DB SQL문에 사용하기 위한 준비임
    # Returns (use_inline, value)
    # - use_inline(False): value is list[float] and should be passed as bound parameter ($n)
    # - use_inline(True): value is escaped JSON literal string (e.g. '[0.1,0.2,...]') to inline into SQL and cast to vector
    lst = _coerce_to_list(embedding)
    if lst is not None:
        return False, lst
    try: # fallback: attempt to produce a safely escaped JSON literal string
        literal = json.dumps(embedding)
        literal = literal.replace("'", "''")
        return True, literal
    except Exception:
        raise ValueError("Cannot prepare openai embedding parameter: unsupported format")
    
def get_embedding(text: str) -> List[float]: # Generate embedding for given text using OpenAI client
    if _client_embed is None:
        raise RuntimeError("OpenAI API key not configured for embeddings (OPENAI_API_KEY missing)")
    response = _client_embed.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding
