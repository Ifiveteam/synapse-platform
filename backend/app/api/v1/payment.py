from __future__ import annotations

import base64
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user_dep
from app.core.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/payment", tags=["payment"])

TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"


def _secret_key() -> str:
    return os.getenv("TOSS_SECRET_KEY", "")


def _auth_header() -> str:
    encoded = base64.b64encode(f"{_secret_key()}:".encode()).decode()
    return f"Basic {encoded}"


class ConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int


@router.post("/cancel", response_model=UserResponse)
async def cancel_subscription(
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    user.plan = "free"
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/confirm", response_model=UserResponse)
async def confirm_payment(
    body: ConfirmRequest,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            TOSS_CONFIRM_URL,
            json={
                "paymentKey": body.paymentKey,
                "orderId": body.orderId,
                "amount": body.amount,
            },
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
            },
        )

    if res.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"토스 결제 승인 실패: {res.text}",
        )

    user.plan = "pro"
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)
