from fastapi import APIRouter, status, Depends
from app.users.schema import UserCreate
from app.database import get_session, AsyncSession

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    print("REGISTER NEW USER")


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(session: AsyncSession = Depends(get_session)):
    print("LOGIN NEW USER")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def login_user(session: AsyncSession = Depends(get_session)):
    print("LOGOUT NEW USER")
