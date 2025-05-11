import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from app.api.main import api_router
from app.core.config import settings
from app.core.i18n import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

# Create security scheme for Swagger UI to allow bearer token input
security_scheme = HTTPBearer(auto_error=False)

# Disable Swagger UI and documentation in production for security
if settings.ENVIRONMENT == "production":
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=None,  # Disable OpenAPI schema in production
        docs_url=None,     # Disable Swagger UI
        redoc_url=None,    # Disable ReDoc
        generate_unique_id_function=custom_generate_unique_id,
    )
else:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        generate_unique_id_function=custom_generate_unique_id,
    )

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add security middleware (always enabled, with stricter settings in production)
from app.core.security.security_headers import SecurityHeadersMiddleware
from app.core.security.security_monitoring import SecurityMonitoringMiddleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SecurityMonitoringMiddleware)

# Add rate limiting middleware in production
# Import only if needed to avoid errors if the file doesn't exist yet
if settings.ENVIRONMENT == "production":
    try:
        from app.core.security.rate_limiter import RateLimitMiddleware
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=60,  # Max 60 requests
            window_seconds=60  # Per minute
        )
    except ImportError:
        import warnings
        warnings.warn("Rate limiting middleware not available, but required in production.")

# Custom OpenAPI schema to include Accept-Language header parameter
def custom_openapi():
    # In production, we don't expose OpenAPI schema, so no need to generate it
    if settings.ENVIRONMENT == "production":
        return {}
    
    # For non-production environments, generate the schema as usual
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="International API with language support",
        routes=app.routes,
    )
    
    # Add global Accept-Language parameter
    language_description = (
        f"Preferred language for responses. "
        f"Supported: {', '.join(SUPPORTED_LANGUAGES)}. "
        f"Default: {DEFAULT_LANGUAGE}."
    )
    
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["parameters"] = openapi_schema["components"].get("parameters", {})
    openapi_schema["components"]["parameters"]["Accept-Language"] = {
        "name": "Accept-Language",
        "in": "header",
        "required": False,
        "schema": {
            "title": "Accept-Language",
            "type": "string",
            "default": DEFAULT_LANGUAGE,
            "enum": list(SUPPORTED_LANGUAGES),
        },
        "description": language_description,
    }
    
    # Add Bearer token security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Apply language parameter to all paths and add security
    if "paths" in openapi_schema:
        for path_key, path in openapi_schema["paths"].items():
            for operation in path.values():
                if "parameters" not in operation:
                    operation["parameters"] = []
                
                operation["parameters"].append({
                    "$ref": "#/components/parameters/Accept-Language"
                })
                
                # Add security requirement to all operations except login endpoints
                if not path_key.endswith("/login") and not path_key.endswith("/open-api"):
                    operation["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set the custom OpenAPI schema
app.openapi = custom_openapi

app.include_router(api_router, prefix=settings.API_V1_STR)
