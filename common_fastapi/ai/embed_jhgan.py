from sentence_transformers import SentenceTransformer

class EmbedderKo:

    def __init__(self, model_name="jhgan/ko-sroberta-multitask"):
        self.model_name = model_name
        print(f"[EmbedderKo] 모델 로딩 중: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            print(f"[EmbedderKo] 모델 로딩 완료: {model_name}")
        except Exception as e:
            print(f"❌ 모델 로딩 실패: {e}")
            raise

    def create_embedding(self, text: str):
        # 문자열 하나를 벡터로 변환
        # Args => text: 임베딩할 텍스트
        # Return => list: 임베딩 벡터 (768차원)
        try: # sentence-transformers는 numpy array를 반환하므로 list로 변환
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            return []
