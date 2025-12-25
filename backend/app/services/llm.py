import ollama
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        self.model = settings.OLLAMA_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL

    def generate_response(self, prompt: str, context: str = ""):
        full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
        response = self.client.chat(model=self.model, messages=[
            {'role': 'user', 'content': full_prompt},
        ])
        return response['message']['content']

    def get_embedding(self, text: str):
        response = self.client.embeddings(model=self.embedding_model, prompt=text)
        return response['embedding']

llm_service = LLMService()
