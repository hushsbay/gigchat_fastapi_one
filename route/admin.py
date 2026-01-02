from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from common_fastapi.shared.db import get_db_connection
from common_fastapi.shared.logger import logger
from common_fastapi.ai.embed_jhgan import EmbedderKo
from common_fastapi.ai.embed_openai import _client_embed
import time

router = APIRouter()

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


@router.post("/update_embeddings768")
async def update_embeddings768() -> Dict[str, Any]:
    """
    jobs1 테이블의 embedding768 필드를 업데이트
    - company + title + description + qualifications 를 결합하여 임베딩
    - jhgan/ko-sroberta-multitask 모델 사용 (768차원)
    """
    try:
        start_time = time.time()
        embedder = get_embedder_768()
        
        total = 0
        updated = 0
        failed = 0
        failed_ids = []
        
        async with get_db_connection() as conn:
            # embedding768이 NULL인 레코드 조회 : WHERE embedding768 IS NULL 일단 빼고 전체 업데이트
            rows = await conn.fetch("""
                SELECT id, company, title, description, qualifications
                FROM public.jobs1
                
                ORDER BY id
            """)
            
            total = len(rows)
            logger.info(f"[768 Embeddings] 처리할 레코드: {total}개")
            
            for row in rows:
                try:
                    # 임베딩할 텍스트 생성
                    text_parts = []
                    if row['company']:
                        text_parts.append(row['company'])
                    if row['title']:
                        text_parts.append(row['title'])
                    if row['description']:
                        text_parts.append(row['description'])
                    if row['qualifications']:
                        text_parts.append(row['qualifications'])
                    
                    text = ' '.join(text_parts)
                    
                    if not text.strip():
                        logger.warning(f"[768 Embeddings] Job ID {row['id']}: 임베딩할 텍스트 없음")
                        failed += 1
                        failed_ids.append(row['id'])
                        continue
                    
                    # 임베딩 생성
                    embedding = embedder.create_embedding(text)
                    
                    if not embedding:
                        logger.error(f"[768 Embeddings] Job ID {row['id']}: 임베딩 생성 실패")
                        failed += 1
                        failed_ids.append(row['id'])
                        continue
                    
                    # DB 업데이트
                    await conn.execute("""
                        UPDATE public.jobs1
                        SET embedding768 = $1::vector
                        WHERE id = $2
                    """, embedding, row['id'])
                    
                    updated += 1
                    
                    if updated % 10 == 0:
                        logger.info(f"[768 Embeddings] 진행 중... {updated}/{total}")
                
                except Exception as e:
                    logger.exception(f"[768 Embeddings] Job ID {row['id']} 처리 실패: {e}")
                    failed += 1
                    failed_ids.append(row['id'])
        
        duration = time.time() - start_time
        
        logger.info(f"[768 Embeddings] 완료 - 총: {total}, 성공: {updated}, 실패: {failed}, 소요시간: {duration:.1f}초")
        
        return {
            "success": True,
            "total": total,
            "updated": updated,
            "failed": failed,
            "failed_ids": failed_ids,
            "duration": duration
        }
    
    except Exception as e:
        logger.exception(f"[768 Embeddings] 전체 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/update_embeddings1536")
async def update_embeddings1536() -> Dict[str, Any]:
    """
    jobs1 테이블의 embedding1536 필드를 업데이트
    - company + title + description + qualifications 를 결합하여 임베딩
    - OpenAI text-embedding-3-small 모델 사용 (1536차원)
    """
    try:
        if not _client_embed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API Key가 설정되지 않았습니다"
            )
        
        start_time = time.time()
        
        total = 0
        updated = 0
        failed = 0
        failed_ids = []
        
        async with get_db_connection() as conn:
            # embedding1536이 NULL인 레코드 조회 : WHERE embedding1536 IS NULL 일단 빼고 전체 업데이트
            rows = await conn.fetch("""
                SELECT id, company, title, description, qualifications
                FROM public.jobs1
                
                ORDER BY id
            """)
            
            total = len(rows)
            logger.info(f"[1536 Embeddings] 처리할 레코드: {total}개")
            
            for row in rows:
                try:
                    # 임베딩할 텍스트 생성
                    text_parts = []
                    if row['company']:
                        text_parts.append(row['company'])
                    if row['title']:
                        text_parts.append(row['title'])
                    if row['description']:
                        text_parts.append(row['description'])
                    if row['qualifications']:
                        text_parts.append(row['qualifications'])
                    
                    text = ' '.join(text_parts)
                    
                    if not text.strip():
                        logger.warning(f"[1536 Embeddings] Job ID {row['id']}: 임베딩할 텍스트 없음")
                        failed += 1
                        failed_ids.append(row['id'])
                        continue
                    
                    # OpenAI 임베딩 생성
                    response = _client_embed.embeddings.create(
                        model="text-embedding-3-small",
                        input=text
                    )
                    
                    embedding = response.data[0].embedding
                    
                    if not embedding:
                        logger.error(f"[1536 Embeddings] Job ID {row['id']}: 임베딩 생성 실패")
                        failed += 1
                        failed_ids.append(row['id'])
                        continue
                    
                    # DB 업데이트
                    await conn.execute("""
                        UPDATE public.jobs1
                        SET embedding1536 = $1::vector
                        WHERE id = $2
                    """, embedding, row['id'])
                    
                    updated += 1
                    
                    if updated % 10 == 0:
                        logger.info(f"[1536 Embeddings] 진행 중... {updated}/{total}")
                
                except Exception as e:
                    logger.exception(f"[1536 Embeddings] Job ID {row['id']} 처리 실패: {e}")
                    failed += 1
                    failed_ids.append(row['id'])
        
        duration = time.time() - start_time
        
        logger.info(f"[1536 Embeddings] 완료 - 총: {total}, 성공: {updated}, 실패: {failed}, 소요시간: {duration:.1f}초")
        
        return {
            "success": True,
            "total": total,
            "updated": updated,
            "failed": failed,
            "failed_ids": failed_ids,
            "duration": duration
        }
    
    except Exception as e:
        logger.exception(f"[1536 Embeddings] 전체 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
