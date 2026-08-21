from fastapi import APIRouter, Depends
from .schema import UserResponse
from .model import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_authenticated_user(user: User = Depends(get_current_user)):
    return user
