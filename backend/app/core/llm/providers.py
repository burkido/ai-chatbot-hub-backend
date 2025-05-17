import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Configuration
DEFAULT_INDEX_NAME = "assistant-ai"
DEFAULT_SIMILARITY_THRESHOLD = 0.51

# Store singleton instances
_PROVIDER_INSTANCES = {}

class LLMProvider:
    """Base class for LLM providers"""
    
    def get_chat_model(self) -> Any:
        """Return chat model implementation"""
        raise NotImplementedError
    
    def get_embedding_model(self) -> Any:
        """Return embedding model implementation"""
        raise NotImplementedError
    
    def get_vectorstore(self, index_name: str = DEFAULT_INDEX_NAME) -> Any:
        """Return vector store implementation"""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        chat_model_name: str = "gpt-4o-mini",
        embedding_model_name: str = "text-embedding-3-small",
        temperature: float = 0.7
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.chat_model_name = chat_model_name
        self.embedding_model_name = embedding_model_name
        self.temperature = temperature
    
    def get_chat_model(self) -> ChatOpenAI:
        """Return OpenAI chat model implementation"""
        return ChatOpenAI(
            openai_api_key=self.api_key,
            temperature=self.temperature,
            model=self.chat_model_name
        )
    
    def get_embedding_model(self) -> OpenAIEmbeddings:
        """Return OpenAI embedding model implementation"""
        return OpenAIEmbeddings(
            openai_api_key=self.api_key,
            model=self.embedding_model_name
        )
    
    def get_vectorstore(self, index_name: str = DEFAULT_INDEX_NAME) -> PineconeVectorStore:
        """Return PineconeVectorStore with OpenAI embeddings"""
        embedding_model = self.get_embedding_model()
        return PineconeVectorStore(
            index_name=index_name,
            embedding=embedding_model
        )


# Factory function to get the appropriate LLM provider
def get_llm_provider(provider_name: str = "openai", **kwargs) -> LLMProvider:
    """
    Factory function to get the appropriate LLM provider
    
    This implementation follows the singleton pattern, ensuring that only one
    instance of each provider type exists throughout the application's lifetime.
    
    Args:
        provider_name: Name of the provider to use
        **kwargs: Additional arguments to pass to the provider constructor
    
    Returns:
        A singleton instance of LLMProvider
    
    Raises:
        ValueError: If the provider is not supported
    """
    provider_key = provider_name.lower()
    
    # If a provider instance with this name already exists, return it
    if provider_key in _PROVIDER_INSTANCES:
        return _PROVIDER_INSTANCES[provider_key]
    
    # Otherwise, create a new instance
    if provider_key == "openai":
        provider = OpenAIProvider(**kwargs)
        _PROVIDER_INSTANCES[provider_key] = provider
        return provider
    
    raise ValueError(f"Unsupported LLM provider: {provider_name}")
