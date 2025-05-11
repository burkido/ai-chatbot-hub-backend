"""
Rate limiter implementation for FastAPI.
"""

from typing import Dict, Tuple, Optional
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, 
        app,
        max_requests: int = 30,  # Default: 60 requests
        window_seconds: int = 60,  # Default: 1 minute window
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_records: Dict[str, list] = {}  # IP -> list of request timestamps

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for non-production environments unless explicitly enabled
        if settings.ENVIRONMENT != "production" and not settings.RATE_LIMITING_ENABLED:
            return await call_next(request)

        # Get client IP - consider using X-Forwarded-For if behind a proxy
        client_ip = request.client.host
        
        # Check if IP should be exempted (e.g., internal services)
        if self._is_exempt(client_ip, request.url.path):
            return await call_next(request)
        
        # Check if the client has exceeded the rate limit
        now = time.time()
        
        if client_ip not in self.request_records:
            self.request_records[client_ip] = []
        
        # Remove timestamps outside the current window
        self.request_records[client_ip] = [
            timestamp for timestamp in self.request_records[client_ip]
            if now - timestamp < self.window_seconds
        ]
        
        # Check if max requests is exceeded
        if len(self.request_records[client_ip]) >= self.max_requests:
            return Response(
                content={"detail": "Too many requests"},
                status_code=HTTP_429_TOO_MANY_REQUESTS,
            )
        
        # Add current request timestamp
        self.request_records[client_ip].append(now)
        
        # Process the request
        return await call_next(request)

    def _is_exempt(self, client_ip: str, path: str) -> bool:
        """Check if an IP or path is exempt from rate limiting."""
        # Example: Exclude internal IPs or health check endpoints
        if path.endswith("/health"):
            return True
        
        # Add whitelist IPs (e.g., your monitoring systems)
        whitelist_ips = getattr(settings, "RATE_LIMITING_WHITELIST", [])
        if client_ip in whitelist_ips:
            return True
            
        return False
