import os
import threading
from typing import Any, Optional, Dict
import logging

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Configure logger
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_INDEX_NAME = "assistant-ai"
DEFAULT_SIMILARITY_THRESHOLD = 0.51
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_TEMPERATURE = 0.7

# Store singleton instances with thread safety
_PROVIDER_INSTANCES: Dict[str, Any] = {}
_provider_lock = threading.Lock()

class LLMProvider:
    """Base class for LLM providers"""
    
    def get_chat_model(self) -> Any:
        """
        Return chat model implementation
        
        Returns:
            Chat model instance
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement get_chat_model")
    
    def get_embedding_model(self) -> Any:
        """
        Return embedding model implementation
        
        Returns:
            Embedding model instance
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement get_embedding_model")
    
    def get_vectorstore(self, index_name: str = DEFAULT_INDEX_NAME) -> Any:
        """
        Return vector store implementation
        
        Args:
            index_name: Name of the vector store index
            
        Returns:
            Vector store instance
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement get_vectorstore")


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        chat_model_name: str = DEFAULT_CHAT_MODEL,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        temperature: float = DEFAULT_TEMPERATURE
    ):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            chat_model_name: Name of the chat model to use
            embedding_model_name: Name of the embedding model to use
            temperature: Temperature setting for the chat model
            
        Raises:
            ValueError: If API key is not provided or invalid
        """
        try:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key is required")
            
            self.chat_model_name = chat_model_name
            self.embedding_model_name = embedding_model_name
            self.temperature = temperature
            
            # Validate temperature range
            if not 0.0 <= temperature <= 2.0:
                raise ValueError("Temperature must be between 0.0 and 2.0")
            
            logger.info(f"OpenAI provider initialized with model: {chat_model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {str(e)}")
            raise
    
    def get_chat_model(self) -> ChatOpenAI:
        """
        Return OpenAI chat model implementation
        
        Returns:
            Configured ChatOpenAI instance
            
        Raises:
            Exception: If chat model creation fails
        """
        try:
            model = ChatOpenAI(
                openai_api_key=self.api_key,
                temperature=self.temperature,
                model=self.chat_model_name
            )
            logger.debug(f"Created chat model: {self.chat_model_name}")
            return model
        except Exception as e:
            logger.error(f"Failed to create chat model: {str(e)}")
            raise Exception(f"Chat model initialization failed: {str(e)}")
    
    def get_embedding_model(self) -> OpenAIEmbeddings:
        """
        Return OpenAI embedding model implementation
        
        Returns:
            Configured OpenAIEmbeddings instance
            
        Raises:
            Exception: If embedding model creation fails
        """
        try:
            model = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                model=self.embedding_model_name
            )
            logger.debug(f"Created embedding model: {self.embedding_model_name}")
            return model
        except Exception as e:
            logger.error(f"Failed to create embedding model: {str(e)}")
            raise Exception(f"Embedding model initialization failed: {str(e)}")
    
    def get_vectorstore(self, index_name: str = DEFAULT_INDEX_NAME) -> PineconeVectorStore:
        """
        Return PineconeVectorStore with OpenAI embeddings
        
        Args:
            index_name: Name of the Pinecone index
            
        Returns:
            Configured PineconeVectorStore instance
            
        Raises:
            Exception: If vector store creation fails
        """
        try:
            if not index_name:
                raise ValueError("Index name cannot be empty")
            
            embedding_model = self.get_embedding_model()
            vectorstore = PineconeVectorStore(
                index_name=index_name,
                embedding=embedding_model
            )
            logger.debug(f"Created vector store with index: {index_name}")
            return vectorstore
        except Exception as e:
            logger.error(f"Failed to create vector store: {str(e)}")
            raise Exception(f"Vector store initialization failed: {str(e)}")


# Factory function to get the appropriate LLM provider
def get_llm_provider(provider_name: str = "openai", **kwargs) -> LLMProvider:
    """
    Factory function to get the appropriate LLM provider
    
    This implementation follows the singleton pattern with thread safety,
    ensuring that only one instance of each provider type exists throughout 
    the application's lifetime.
    
    Args:
        provider_name: Name of the provider to use
        **kwargs: Additional arguments to pass to the provider constructor
    
    Returns:
        A singleton instance of LLMProvider
    
    Raises:
        ValueError: If the provider is not supported or invalid parameters
        Exception: If provider initialization fails
    """
    try:
        if not provider_name:
            raise ValueError("Provider name cannot be empty")
        
        provider_key = provider_name.lower()
        
        # Thread-safe singleton pattern
        with _provider_lock:
            # If a provider instance with this name already exists, return it
            if provider_key in _PROVIDER_INSTANCES:
                logger.debug(f"Returning existing provider instance: {provider_key}")
                return _PROVIDER_INSTANCES[provider_key]
            
            # Otherwise, create a new instance
            logger.info(f"Creating new provider instance: {provider_key}")
            
            if provider_key == "openai":
                provider = OpenAIProvider(**kwargs)
                _PROVIDER_INSTANCES[provider_key] = provider
                logger.info(f"OpenAI provider created and cached")
                return provider
            
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
            
    except ValueError as e:
        logger.error(f"Invalid provider configuration: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to get LLM provider: {str(e)}")
        raise


def clear_provider_cache() -> None:
    """
    Clear the provider instance cache
    
    This function is useful for testing or when you need to force
    recreation of provider instances.
    """
    global _PROVIDER_INSTANCES
    with _provider_lock:
        logger.info(f"Clearing {len(_PROVIDER_INSTANCES)} cached provider instances")
        _PROVIDER_INSTANCES.clear()


def get_cached_provider_count() -> int:
    """
    Get the number of cached provider instances
    
    Returns:
        Number of cached instances
    """
    return len(_PROVIDER_INSTANCES)


def get_supported_providers() -> list[str]:
    """
    Get list of supported provider names
    
    Returns:
        List of supported provider names
    """
    return ["openai"]
