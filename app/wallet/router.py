from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.auth.dependencies import get_current_user
from .service import wallet_service
from .schema import WalletRead
from .utils import from_cent
from app.users.model import User

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get(
    "/me",
    response_model=WalletRead,
    status_code=status.HTTP_200_OK
)
async def get_user_wallet(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    wallet = await wallet_service.get_wallet_by_user_id(session, user.id)

    wallet_data = wallet.model_dump()
    wallet_data["available_display"] = f"${from_cent(wallet.available)}"

    return WalletRead.model_validate(wallet_data)


@router.get("/create", status_code=status.HTTP_201_CREATED)
async def create_user_wallet(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    await wallet_service.create_wallet(session, user.id)
