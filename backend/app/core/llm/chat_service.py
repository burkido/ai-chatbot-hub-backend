from typing import Dict, Any, List, Tuple, Optional

from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage

from app.models.schemas.chat import ChatMessage
from app.core.llm.providers import DEFAULT_SIMILARITY_THRESHOLD
from app.core.llm.assistant_config import get_assistant_config, ASSISTANT_TYPE_DOCTOR
from app.core.translation import TranslationService

# Store singleton instances - key format: f"{provider_name}:{assistant_type}"
_CHAT_SERVICE_INSTANCES = {}

class ChatService:
    """Service for handling chat functionality"""
    
    def __init__(self, llm_provider, assistant_type: str = ASSISTANT_TYPE_DOCTOR):
        """
        Initialize the chat service
        
        Args:
            llm_provider: The LLM provider to use
            assistant_type: The type of assistant to use (defaults to doctor)
        """
        self.llm_provider = llm_provider
        self.assistant_type = assistant_type.lower()
        self.assistant_config = get_assistant_config(self.assistant_type)
        self.translation_service = TranslationService()
    
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
        """
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
            # This ensures our Doctor Assistant role can't be overridden
            elif msg.role != "system":
                raise ValueError(f"Unknown role: {msg.role}")
        
        # Use search_message for vector search if provided, otherwise use new_message
        search_query = search_message if search_message is not None else new_message
        
        # Get augmented prompt with relevant medical context and sources
        augmented_prompt, sources = self._augment_prompt(search_query, namespace, topic, vectorstore)
        
        # Include context in the user's message if sources are available
        if sources and "Contexts:" in augmented_prompt:
            parts = augmented_prompt.split("Contexts:")
            if len(parts) > 1:
                context_part = parts[1].split("Query:")[0].strip()
                # Include context directly in the user's message
                user_message_with_context = f"""Based on the following medical information:

                {context_part}

                Please answer my question: {new_message}"""
                langchain_messages.append(HumanMessage(content=user_message_with_context))
        else:
            # No context available, just add the user's message
            langchain_messages.append(HumanMessage(content=new_message))

        print(f"Chat messages prepared for LLM: {langchain_messages}")

        # Get the assistant's response
        response = chat_model(langchain_messages)
        
        return response.content, sources
    
    def generate_title(self, message: str) -> str:
        """
        Generate a title for a chat conversation
        
        Args:
            message: The initial message to generate a title for
            
        Returns:
            A generated title
        """
        chat_model = self.llm_provider.get_chat_model()
        prompt = HumanMessage(content=f"Create a very brief title (4 words max) for this message: '{message}'")
        response = chat_model([prompt])
        return response.content.strip()
    
    def _get_system_prompt(self) -> str:
        """
        Return the system prompt for the configured assistant type
        
        Returns:
            System prompt text based on the assistant type
        """
        return self.assistant_config["system_prompt"]
    
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
        """
        # Get top results from knowledge base
        results = vectorstore.similarity_search_with_score(
            query=query,
            k=3,
            filter={"topic": {"$eq": topic}} if topic else None,
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
            
            # Just provide the context and query, role enforcement is handled separately
            augmented_prompt = f"""Contexts:
            {source_knowledge}

            Query: {query}"""
        else:
            # No results found - let the model know it should use general knowledge
            augmented_prompt = f"""No specific information found in the medical database for this query.

            Query: {query}"""
        
        return augmented_prompt, sources

# Factory function to get a ChatService instance
def get_chat_service_instance(
    provider_name: str = "openai", 
    assistant_type: str = ASSISTANT_TYPE_DOCTOR, 
    **kwargs
) -> ChatService:
    """
    Factory function to get a ChatService with the specified provider and assistant type
    
    This implementation follows the singleton pattern, ensuring that only one
    instance of ChatService exists for each provider+assistant type throughout 
    the application's lifetime.
    
    Args:
        provider_name: Name of the provider to use
        assistant_type: Type of assistant to use
        **kwargs: Additional arguments to pass to the provider constructor
        
    Returns:
        A singleton instance of ChatService with the specified provider and assistant type
    """
    from app.core.llm.providers import get_llm_provider
    
    # Create a composite key for the instance cache
    instance_key = f"{provider_name}:{assistant_type.lower()}"
    
    # If a chat service instance for this provider and assistant type already exists, return it
    if instance_key in _CHAT_SERVICE_INSTANCES:
        return _CHAT_SERVICE_INSTANCES[instance_key]
    
    # Otherwise, create a new instance with the appropriate provider and assistant type
    llm_provider = get_llm_provider(provider_name, **kwargs)
    chat_service = ChatService(llm_provider, assistant_type=assistant_type)
    _CHAT_SERVICE_INSTANCES[instance_key] = chat_service
    return chat_service
