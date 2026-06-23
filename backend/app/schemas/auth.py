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


class ExtensionCodeResponse(BaseModel):
    code: str
    expires_in: int


class ExtensionExchangeRequest(BaseModel):
    code: str


class ExtensionRefreshRequest(BaseModel):
    refresh_token: str


class ExtensionRevokeRequest(BaseModel):
    refresh_token: str


class ExtensionSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class AuthStatusResponse(BaseModel):
    connected: bool
    message: str


class UpdateMeRequest(BaseModel):
    nickname: str | None = None
    picture: str | None = None
