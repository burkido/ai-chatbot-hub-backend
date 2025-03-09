from fastapi import APIRouter

from app.api.routes import auth, items, users, chat, documents, redeem, utils, assetlinks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(redeem.router, prefix="/redeem-code", tags=["redeem"])
api_router.include_router(assetlinks.router, prefix="", tags=["assetlink"])