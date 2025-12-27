import google.generativeai as genai
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Use Gemini models
        self.model = "gemini-2.5-flash"  # Fast, latest generation model
        self.embedding_model = "models/text-embedding-004"  # For embeddings
        
        logger.info(f"LLM Service initialized with Gemini (model: {self.model}, embedding: {self.embedding_model})")

    def generate_response(self, prompt: str, context: str = ""):
        """Generate a response using Gemini"""
        try:
            full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def get_embedding(self, text: str):
        """Generate embeddings using Gemini"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_answer(self, query: str, context: str) -> str:
        """Generate answer for RAG pipeline with query and context"""
        return self.generate_response(query, context)
    
    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Batch generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

llm_service = LLMService()

# Backward compatibility function for worker pool
def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts (sync wrapper)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(llm_service.generate_embeddings(texts))
