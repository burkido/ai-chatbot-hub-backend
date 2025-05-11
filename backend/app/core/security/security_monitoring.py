"""
Security logging and monitoring middleware.
"""

import time
import logging
import re
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings

# Create a dedicated security logger
security_logger = logging.getLogger("app.security")
if not security_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    security_logger.addHandler(handler)
    security_logger.setLevel(logging.INFO)


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware that monitors requests for suspicious activity.
    """
    
    # Patterns that might indicate SQL injection
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(\;))",
        r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
        r"(union.*select)",
        r"(concat\(.*\))",
    ]
    
    # Patterns that might indicate XSS attempts
    XSS_PATTERNS = [
        r"<script.*>",
        r"javascript:",
        r"on\w+\s*=",
        r"data:text/html",
    ]
    
    # Patterns for path traversal attempts 
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.\/)+",
        r"(\.\.\\)+",
        r"%2e%2e%2f",
    ]
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.patterns = {
            "sql_injection": [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS],
            "xss": [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS],
            "path_traversal": [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS],
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        suspicious = False
        
        # Extract relevant request data for analysis
        client_ip = request.client.host
        path = request.url.path
        query_string = request.url.query
        user_agent = request.headers.get("user-agent", "")
        
        # Check path and query string for suspicious patterns
        content_to_check = f"{path}?{query_string}"
        
        for attack_type, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(content_to_check):
                    suspicious = True
                    security_logger.warning(
                        f"Potential {attack_type} attempt: "
                        f"IP={client_ip}, Path={path}, Query={query_string}"
                    )
        
        # Process the request
        response = await call_next(request)
        
        # Log request details if suspicious or if it's a high-risk endpoint
        if suspicious or any(sensitive in path for sensitive in ["/auth", "/login", "/admin"]):
            duration = time.time() - start_time
            status_code = response.status_code
            
            # Log at appropriate level based on status code
            if status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
            
            security_logger.log(
                log_level,
                f"Request: IP={client_ip}, "
                f"Path={path}, "
                f"Status={status_code}, "
                f"Duration={duration:.4f}s, "
                f"User-Agent={user_agent}"
            )
            
            # For production, you could add integration with security monitoring services here
            if settings.ENVIRONMENT == "production" and status_code in [401, 403, 429]:
                # This could trigger an alert or be sent to a SIEM system
                pass
        
        return response
