# =========================
# 7. app/services/embedding.py
# =========================
from typing import List, Union
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logging import app_logger
from app.core.exceptions import EmbeddingError

class EmbeddingService:
    """Service for generating embeddings (supports local and cloud)"""
    
    def __init__(self):
        self.model = None
        self.use_cloud = settings.USE_CLOUD_EMBEDDINGS
        
        if not self.use_cloud:
            self._init_local_model()
    
    def _init_local_model(self):
        """Initialize local sentence transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(settings.LOCAL_EMBEDDING_MODEL)
            app_logger.info(f"Loaded local embedding model: {settings.LOCAL_EMBEDDING_MODEL}")
        except Exception as e:
            app_logger.error(f"Failed to load local model: {str(e)}")
            raise EmbeddingError(f"Failed to initialize embedding model: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def embed_text_cloud(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            import openai
            openai.api_key = settings.OPENAI_API_KEY
            
            response = await openai.Embedding.acreate(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            app_logger.debug(f"Generated {len(embeddings)} embeddings via OpenAI")
            return embeddings
            
        except Exception as e:
            app_logger.error(f"OpenAI embedding failed: {str(e)}")
            raise EmbeddingError(f"Cloud embedding failed: {str(e)}")
    
    def embed_text_local(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings locally"""
        try:
            if not self.model:
                self._init_local_model()
            
            embeddings = self.model.encode(texts, show_progress_bar=False)
            app_logger.debug(f"Generated {len(embeddings)} embeddings locally")
            return embeddings
            
        except Exception as e:
            app_logger.error(f"Local embedding failed: {str(e)}")
            raise EmbeddingError(f"Local embedding failed: {str(e)}")
    
    async def embed_text(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Main embedding method (chooses cloud or local)"""
        if isinstance(texts, str):
            texts = [texts]
        
        if self.use_cloud and settings.OPENAI_API_KEY:
            embeddings = await self.embed_text_cloud(texts)
            return np.array(embeddings)
        else:
            return self.embed_text_local(texts)
    
    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query"""
        embeddings = await self.embed_text([query])
        return embeddings[0]

# Singleton instance
embedding_service = EmbeddingService()
embed_text = embedding_service.embed_text
embed_query = embedding_service.embed_query