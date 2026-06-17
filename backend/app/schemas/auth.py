"""Auth API Pydantic 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    picture: str | None

    model_config = {"from_attributes": True}


class DevLoginResponse(BaseModel):
    access_token: str
    user: UserResponse


class RefreshResponse(BaseModel):
    access_token: str
    user: UserResponse


class AuthStatusResponse(BaseModel):
    connected: bool
    message: str
