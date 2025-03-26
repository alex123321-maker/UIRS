from fastapi import APIRouter

from src.api.v1 import auth, user,recipe,ingredient,tag

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(recipe.router, prefix="/recipe", tags=["recipe"])
api_router.include_router(tag.router, prefix="/tag", tags=["tag"])
api_router.include_router(ingredient.router, prefix="/ingredient", tags=["ingredient"])

