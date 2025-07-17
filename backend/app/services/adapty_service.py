"""
Adapty subscription service for checking user subscription status.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class AdaptyService:
    """Service class for interacting with Adapty API"""
    
    def __init__(self):
        self.api_key = "secret_live_MFRorBEe.r4gMB8CwyoUcMaEzQohfoVZauxSpfn2s"
        self.base_url = "https://api.adapty.io/api/v2/server-side-api"
        self.headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def check_subscription_status(self, customer_user_id: str) -> Dict[str, Any]:
        """
        Check user subscription status from Adapty
        
        Args:
            customer_user_id: The customer user ID to check subscription for
            
        Returns:
            Dict containing subscription status information
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Add customer user ID to headers as required by Adapty
                request_headers = {
                    **self.headers,
                    "adapty-customer-user-id": customer_user_id
                }
                
                # Make request to Adapty API to get user profile/subscription status
                response = await client.get(
                    f"{self.base_url}/profile/",
                    headers=request_headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "data": data,
                        "is_premium": self._extract_premium_status(data)
                    }
                elif response.status_code == 404:
                    # Profile not found - user likely doesn't have Adapty profile yet
                    logger.warning(f"Adapty profile not found for user: {customer_user_id}")
                    return {
                        "success": True,  # This is not an error, just no subscription
                        "data": None,
                        "is_premium": False,
                        "message": "No Adapty profile found for user"
                    }
                else:
                    logger.error(f"Adapty API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}: {response.text}",
                        "is_premium": False
                    }
                    
        except httpx.TimeoutException:
            logger.error("Adapty API request timed out")
            return {
                "success": False,
                "error": "Request timed out",
                "is_premium": False
            }
        except Exception as e:
            logger.error(f"Error checking Adapty subscription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "is_premium": False
            }
    
    def _extract_premium_status(self, adapty_response: Dict[str, Any]) -> bool:
        """
        Extract premium status from Adapty response data
        
        Args:
            adapty_response: Raw response data from Adapty API
            
        Returns:
            Boolean indicating if user has active premium subscription
        """
        try:
            # Extract the data object from response
            data = adapty_response.get("data", {})
            
            # Check for active access levels (premium access)
            access_levels = data.get("access_levels", [])
            if access_levels:
                for access_level in access_levels:
                    # Check if access level is active and not expired
                    expires_at = access_level.get("expires_at")
                    if expires_at is None:  # Lifetime access
                        return True
                    
                    # Check if subscription is not cancelled and not expired
                    try:
                        # Simple ISO format parsing (Adapty uses ISO 8601)
                        expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        if expires_date > datetime.now(expires_date.tzinfo):
                            # Also check if not cancelled
                            renewal_cancelled_at = access_level.get("renewal_cancelled_at")
                            if renewal_cancelled_at is None:
                                return True
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse expires_at date: {expires_at}, error: {e}")
                        continue
            
            # Check for active subscriptions as fallback
            subscriptions = data.get("subscriptions", [])
            if subscriptions:
                for subscription in subscriptions:
                    expires_at = subscription.get("expires_at")
                    if expires_at is None:  # Lifetime subscription
                        return True
                    
                    # Check if subscription is not expired and not cancelled
                    try:
                        # Simple ISO format parsing (Adapty uses ISO 8601)
                        expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        if expires_date > datetime.now(expires_date.tzinfo):
                            renewal_cancelled_at = subscription.get("renewal_cancelled_at")
                            if renewal_cancelled_at is None:
                                return True
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse expires_at date: {expires_at}, error: {e}")
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error extracting premium status: {str(e)}")
            return False

# Create a singleton instance
adapty_service = AdaptyService()
