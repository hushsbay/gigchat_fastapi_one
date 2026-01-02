from openai import OpenAI
from common_fastapi.shared.config import OPENAI_API_KEY

class LLMClient:

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("❌ OPENAI_API_KEY가 공통 프로젝트 .env에 없습니다.")
        self.api_key = OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)

    def chat(self, messages: list, model="gpt-4o-mini"):
        try:
            response = self.client.chat.completions.create(model=model, messages=messages, temperature=0)
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM(OPENAI) 호출 오류: {e}")
            return None
