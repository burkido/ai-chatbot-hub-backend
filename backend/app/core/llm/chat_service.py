from typing import Dict, Any, List, Tuple, Optional
import logging

from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage

from app.models.schemas.chat import ChatMessage
from app.core.llm.providers import DEFAULT_SIMILARITY_THRESHOLD
from app.core.llm.assistant_config import get_assistant_config, ASSISTANT_TYPE_DOCTOR
from app.core.translation import TranslationService, TranslationError

# Configure logger
logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_MAX_SOURCES = 3
DEFAULT_MAX_CONTEXT_LENGTH = 4000
DEFAULT_TITLE_MAX_WORDS = 4

class ChatService:
    """Service for handling chat functionality"""
    
    def __init__(self, llm_provider, assistant_type: str = ASSISTANT_TYPE_DOCTOR):
        """
        Initialize the chat service
        
        Args:
            llm_provider: The LLM provider to use
            assistant_type: The type of assistant to use (defaults to doctor)
        """
        try:
            self.llm_provider = llm_provider
            self.assistant_type = assistant_type.lower()
            self.assistant_config = get_assistant_config(self.assistant_type)
            self.translation_service = TranslationService()
            logger.info(f"ChatService initialized with assistant type: {self.assistant_type}")
        except Exception as e:
            logger.error(f"Failed to initialize ChatService: {str(e)}")
            raise
    
    def chat(
        self,
        new_message: str,
        namespace: str,
        topic: str,
        history: List[ChatMessage],
        language: str = "en",
        search_message: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a chat message with LLM provider
        
        Args:
            new_message: The new message from the user (in their language)
            namespace: The namespace for vector search
            topic: The topic for vector search filtering
            history: The chat history
            language: The language code for the response (defaults to English)
            search_message: Optional translated message for vector search (defaults to new_message)
            
        Returns:
            Tuple containing response content and sources
            
        Raises:
            ValueError: If invalid inputs are provided
            Exception: If chat processing fails
        """
        try:
            # Validate inputs
            if not new_message or not new_message.strip():
                raise ValueError("Message cannot be empty")
            
            if not namespace:
                raise ValueError("Namespace is required")
                
            # Get required services
            chat_model = self.llm_provider.get_chat_model()
            vectorstore = self.llm_provider.get_vectorstore()

            langchain_messages = []
            
            # Get the system prompt based on the assistant type
            system_prompt = self._get_system_prompt()
            
            # Always add the system message first to ensure role enforcement
            langchain_messages.append(SystemMessage(content=system_prompt))
            
            # Process history messages - but skip any existing system messages to prevent conflicts
            for msg in history:
                if msg.role == "user":
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    langchain_messages.append(AIMessage(content=msg.content))
                # We intentionally skip system messages from history
                # This ensures our Assistant role can't be overridden
                elif msg.role != "system":
                    logger.warning(f"Unknown message role in history: {msg.role}")
            
            # Use search_message for vector search if provided, otherwise use new_message
            search_query = search_message if search_message is not None else new_message
            
            # Get augmented prompt with relevant context and sources
            try:
                augmented_prompt, sources = self._augment_prompt(search_query, namespace, topic, vectorstore)
            except Exception as e:
                logger.error(f"Failed to augment prompt: {str(e)}")
                # Continue without augmentation if it fails
                sources = []
                augmented_prompt = f"Query: {search_query}"
            
            # Include context in the user's message if sources are available
            if sources and "Contexts:" in augmented_prompt:
                parts = augmented_prompt.split("Contexts:")
                if len(parts) > 1:
                    context_part = parts[1].split("Query:")[0].strip()
                    # Truncate context if too long
                    if len(context_part) > DEFAULT_MAX_CONTEXT_LENGTH:
                        context_part = context_part[:DEFAULT_MAX_CONTEXT_LENGTH] + "..."
                    
                    user_message_with_context = f"""Based on the following medical information:

                        {context_part}

                        Please answer my question: {new_message}"""

                    langchain_messages.append(HumanMessage(content=user_message_with_context))
            else:
                # No context available, just add the user's message
                langchain_messages.append(HumanMessage(content=new_message))

            logger.debug(f"Prepared {len(langchain_messages)} messages for LLM")

            # Get the assistant's response
            response = chat_model(langchain_messages)
            
            logger.info(f"Chat processed successfully, returned {len(sources)} sources")
            return response.content, sources
            
        except ValueError as e:
            logger.error(f"Validation error in chat: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat processing: {str(e)}")
            raise Exception(f"Chat processing failed: {str(e)}")
    
    def generate_title(self, message: str) -> str:
        """
        Generate a title for a chat conversation
        
        Args:
            message: The initial message to generate a title for
            
        Returns:
            A generated title
            
        Raises:
            Exception: If title generation fails
        """
        try:
            if not message or not message.strip():
                return "New Conversation"
                
            chat_model = self.llm_provider.get_chat_model()
            prompt = HumanMessage(
                content=f"Create a very brief title ({DEFAULT_TITLE_MAX_WORDS} words max) for this message: '{message[:200]}'"
            )
            response = chat_model([prompt])
            title = response.content.strip()
            
            # Validate title length and fallback if needed
            if len(title.split()) > DEFAULT_TITLE_MAX_WORDS:
                words = title.split()[:DEFAULT_TITLE_MAX_WORDS]
                title = " ".join(words)
            
            logger.debug(f"Generated title: {title}")
            return title if title else "New Conversation"
            
        except Exception as e:
            logger.error(f"Title generation failed: {str(e)}")
            return "New Conversation"
    
    def _get_system_prompt(self) -> str:
        """
        Return the system prompt for the configured assistant type
        
        Returns:
            System prompt text based on the assistant type
            
        Raises:
            ValueError: If assistant config is invalid
        """
        try:
            if not self.assistant_config or "system_prompt" not in self.assistant_config:
                raise ValueError(f"Invalid assistant configuration for type: {self.assistant_type}")
            return self.assistant_config["system_prompt"]
        except Exception as e:
            logger.error(f"Failed to get system prompt: {str(e)}")
            raise ValueError(f"System prompt configuration error: {str(e)}")
    
    def _augment_prompt(
        self,
        query: str,
        namespace: str,
        topic: str,
        vectorstore,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Augment user query with relevant information from the vector database
        
        Args:
            query: The user query
            namespace: The namespace for vector search
            topic: The topic for vector search filtering
            vectorstore: The vector store to search in
            similarity_threshold: Minimum similarity threshold for including results
            
        Returns:
            Tuple containing augmented prompt and sources
            
        Raises:
            Exception: If vector search fails
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            # Get top results from knowledge base
            search_filter = {"topic": {"$eq": topic}} if topic else None
            
            results = vectorstore.similarity_search_with_score(
                query=query,
                k=DEFAULT_MAX_SOURCES,
                filter=search_filter,
                namespace=namespace
            )

            # Extract sources information - only from documents with sufficient score
            sources = []
            filtered_results = []
            
            for doc, score in results:
                if score >= similarity_threshold:
                    # Convert score to percentage (scores are typically between 0-1)
                    similarity_percentage = round(score * 100, 2)
                    source_info = {
                        "authors": doc.metadata.get("authors", "Unknown"),
                        "book_title": doc.metadata.get("book_title", "Untitled"),
                        "source": doc.metadata.get("source", ""),
                        "score": score,
                        "similarity_percentage": similarity_percentage
                    }
                    sources.append(source_info)
                    filtered_results.append((doc, score))
            
            # Format the prompt differently based on whether we found sources
            if filtered_results:
                source_knowledge = "\n".join([doc.page_content for doc, _ in filtered_results])
                
                augmented_prompt = f"""Contexts:
                    {source_knowledge}

                    Query: {query}"""
            else:
                    # No results found - let the model know it should use general knowledge
                    augmented_prompt = f"""No specific information found in the knowledge database for this query. Answer with your best knowledge and expertise.

                    Query: {query}"""
            
            logger.debug(f"Augmented prompt with {len(sources)} sources (threshold: {similarity_threshold})")
            return augmented_prompt, sources
            
        except Exception as e:
            logger.error(f"Failed to augment prompt: {str(e)}")
            # Return basic prompt without augmentation
            return f"Query: {query}", []

# Factory function to get a ChatService instance
def get_chat_service_instance(
    provider_name: str = "openai", 
    assistant_type: str = ASSISTANT_TYPE_DOCTOR, 
    **kwargs
) -> ChatService:
    """
    Factory function to create a ChatService with the specified provider and assistant type
    
    This implementation creates a new ChatService instance each time it's called.
    Caching is handled at the dependency injection level using @lru_cache.
    
    Args:
        provider_name: Name of the provider to use
        assistant_type: Type of assistant to use
        **kwargs: Additional arguments to pass to the provider constructor
        
    Returns:
        A new instance of ChatService with the specified provider and assistant type
        
    Raises:
        ValueError: If invalid provider or assistant type is specified
        Exception: If ChatService initialization fails
    """
    try:
        from app.core.llm.providers import get_llm_provider
        
        # Validate inputs
        if not provider_name:
            raise ValueError("Provider name cannot be empty")
        if not assistant_type:
            raise ValueError("Assistant type cannot be empty")
        
        # Create a new instance with the appropriate provider and assistant type
        logger.info(f"Creating new ChatService instance: {provider_name}:{assistant_type.lower()}")
        llm_provider = get_llm_provider(provider_name, **kwargs)
        chat_service = ChatService(llm_provider, assistant_type=assistant_type)
        
        logger.info(f"ChatService instance created: {provider_name}:{assistant_type.lower()}")
        return chat_service
        
    except Exception as e:
        logger.error(f"Failed to get ChatService instance: {str(e)}")
        raise
