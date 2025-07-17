#!/usr/bin/env python3
"""
Test script for Adapty integration
"""

import sys
import os
import asyncio

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.adapty_service import adapty_service

async def test_adapty_service():
    """Test the Adapty service with a sample user ID"""
    test_user_id = "test-user-12345"
    
    print(f"Testing Adapty service with user ID: {test_user_id}")
    print("-" * 50)
    
    try:
        result = await adapty_service.check_subscription_status(test_user_id)
        
        print("Result:")
        print(f"  Success: {result['success']}")
        print(f"  Is Premium: {result['is_premium']}")
        
        if result.get('error'):
            print(f"  Error: {result['error']}")
        
        if result.get('message'):
            print(f"  Message: {result['message']}")
        
        if result.get('data'):
            print(f"  Data: {result['data']}")
        
    except Exception as e:
        print(f"Error testing service: {e}")

if __name__ == "__main__":
    asyncio.run(test_adapty_service())
