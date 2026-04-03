# =========================
# 9. app/services/rag_pipeline.py
# =========================
import openai
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import app_logger
from app.core.exceptions import DocumentIntelligenceException
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.models.document import QueryLog

class RAGPipeline:
    """Advanced RAG pipeline with improved prompting and streaming"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.system_prompt = """You are an expert AI assistant specialized in answering questions based on provided documents. 
        Follow these guidelines:
        1. Answer based ONLY on the provided context
        2. If the answer cannot be found in the context, say "I cannot find this information in the provided documents"
        3. Cite specific parts of the context when relevant
        4. Be concise but thorough
        5. If asked for opinions, state that you can only provide information from the documents
        
        Context from documents:
        {context}
        
        Question: {query}
        
        Answer:"""
    
    async def retrieve_context(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        document_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context from vector store"""
        query_embedding = await embedding_service.embed_query(query)
        
        similar_chunks = await vector_store.similarity_search(
            db=db,
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=document_ids
        )
        
        return similar_chunks
    
    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into context string"""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            source = f"[Source: {chunk['document_name']}, Relevance: {chunk['similarity_score']:.2f}]"
            context_parts.append(f"{source}\n{chunk['text']}\n")
        
        return "\n".join(context_parts)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_answer(
        self,
        query: str,
        context: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Generate answer using OpenAI"""
        try:
            prompt = self.system_prompt.format(context=context, query=query)
            
            response = await openai.ChatCompletion.acreate(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful document intelligence assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return {
                "answer": answer,
                "tokens_used": tokens_used,
                "model": settings.OPENAI_MODEL
            }
            
        except Exception as e:
            app_logger.error(f"OpenAI API error: {str(e)}")
            raise DocumentIntelligenceException(f"Failed to generate answer: {str(e)}")
    
    async def answer_query(
        self,
        db: Session,
        query: str,
        top_k: int = None,
        temperature: float = None,
        max_tokens: int = None,
        document_ids: List[int] = None
    ) -> Dict[str, Any]:
        """Complete RAG pipeline"""
        start_time = datetime.utcnow()
        
        # Use settings if not provided
        top_k = top_k or settings.RAG_TOP_K
        temperature = temperature or settings.RAG_TEMPERATURE
        max_tokens = max_tokens or settings.RAG_MAX_TOKENS
        
        try:
            # 1. Retrieve relevant context
            similar_chunks = await self.retrieve_context(db, query, top_k, document_ids)
            
            if not similar_chunks:
                answer = "No relevant information found in the documents."
                context = ""
                tokens_used = 0
            else:
                # 2. Format context
                context = self.format_context(similar_chunks)
                
                # 3. Generate answer
                result = await self.generate_answer(query, context, temperature, max_tokens)
                answer = result["answer"]
                tokens_used = result["tokens_used"]
            
            # 4. Log query
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            query_log = QueryLog(
                query_text=query,
                response_text=answer,
                context_chunks=str([c["id"] for c in similar_chunks]),
                response_time_ms=response_time,
                tokens_used=tokens_used,
                model_used=settings.OPENAI_MODEL
            )
            db.add(query_log)
            db.commit()
            
            return {
                "query": query,
                "answer": answer,
                "sources": similar_chunks,
                "total_tokens": tokens_used,
                "response_time_ms": response_time,
                "model_used": settings.OPENAI_MODEL
            }
            
        except Exception as e:
            app_logger.error(f"RAG pipeline failed: {str(e)}")
            raise
    
    async def stream_answer(
        self,
        db: Session,
        query: str,
        top_k: int = None,
        temperature: float = None,
        max_tokens: int = None,
        document_ids: List[int] = None
    ) -> AsyncGenerator[str, None]:
        """Stream answer token by token"""
        start_time = datetime.utcnow()
        
        top_k = top_k or settings.RAG_TOP_K
        temperature = temperature or settings.RAG_TEMPERATURE
        max_tokens = max_tokens or settings.RAG_MAX_TOKENS
        
        try:
            # Retrieve context first
            similar_chunks = await self.retrieve_context(db, query, top_k, document_ids)
            
            if not similar_chunks:
                yield '{"type": "answer", "content": "No relevant information found in the documents."}\n'
                yield '{"type": "done", "content": ""}\n'
                return
            
            # Send source information first
            for chunk in similar_chunks:
                yield f'{{"type": "source", "content": "{chunk["document_name"]}", "metadata": {{"similarity": {chunk["similarity_score"]:.2f}}}}}\n'
            
            # Format context
            context = self.format_context(similar_chunks)
            prompt = self.system_prompt.format(context=context, query=query)
            
            # Stream the answer
            response = await openai.ChatCompletion.acreate(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful document intelligence assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            full_answer = []
            async for chunk in response:
                if chunk.choices[0].delta.get("content"):
                    content = chunk.choices[0].delta.content
                    full_answer.append(content)
                    yield f'{{"type": "answer", "content": "{content}"}}\n'
            
            # Log the complete query
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            query_log = QueryLog(
                query_text=query,
                response_text="".join(full_answer),
                context_chunks=str([c["id"] for c in similar_chunks]),
                response_time_ms=response_time,
                model_used=settings.OPENAI_MODEL
            )
            db.add(query_log)
            db.commit()
            
            yield '{"type": "done", "content": ""}\n'
            
        except Exception as e:
            app_logger.error(f"Streaming RAG failed: {str(e)}")
            yield f'{{"type": "error", "content": "{str(e)}"}}\n'

# Singleton instance
rag_pipeline = RAGPipeline()
answer_query = rag_pipeline.answer_query
stream_answer = rag_pipeline.stream_answer