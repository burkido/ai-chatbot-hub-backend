#!/usr/bin/env python3
"""
Test script to verify conversational improvements for the Doctor Assistant
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.llm.assistant_config import get_assistant_config, ASSISTANT_TYPE_DOCTOR, clear_chat_service_cache

def test_assistant_config():
    """Test the updated doctor assistant configuration"""
    print("Testing updated Doctor Assistant configuration...")
    
    # Clear any cached instances to use the new config
    try:
        from app.core.llm.chat_service import clear_chat_service_cache
        clear_chat_service_cache()
    except ImportError:
        print("Note: Could not clear chat service cache")
    
    # Get the updated configuration
    config = get_assistant_config(ASSISTANT_TYPE_DOCTOR)
    
    print(f"Assistant Name: {config['name']}")
    print(f"Temperature: {config['temperature']}")
    print("\nSystem Prompt:")
    print("-" * 50)
    print(config['system_prompt'])
    print("-" * 50)
    
    # Check if the prompt allows for conversational elements
    prompt = config['system_prompt'].lower()
    conversational_keywords = [
        'casual conversation', 'greetings', 'small talk', 
        'friendly', 'conversational', 'approachable'
    ]
    
    found_keywords = []
    for keyword in conversational_keywords:
        if keyword in prompt:
            found_keywords.append(keyword)
    
    print(f"\nConversational elements found: {found_keywords}")
    
    if found_keywords:
        print("✅ Configuration updated successfully! The assistant should now be more conversational.")
    else:
        print("❌ Configuration may not have been updated properly.")

if __name__ == "__main__":
    test_assistant_config()
