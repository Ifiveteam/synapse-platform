"""Auth API Pydantic 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    picture: str | None
    plan: str

    model_config = {"from_attributes": True}


class DevLoginResponse(BaseModel):
    # access_token은 응답 바디에 안 담는다 — HttpOnly 쿠키로만 전달돼 JS가 읽을 수 없다.
    user: UserResponse


class RefreshResponse(BaseModel):
    # access_token은 응답 바디에 안 담는다 — HttpOnly 쿠키로만 전달돼 JS가 읽을 수 없다.
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


class DriveConnectRequest(BaseModel):
    """GIS 코드 클라이언트(popup)가 받은 authorization code."""

    code: str


class DriveConnectResponse(BaseModel):
    """Picker 렌더에 쓸 drive.file access token (단기)."""

    access_token: str


class YoutubeConnectRequest(BaseModel):
    """GIS 코드 클라이언트(popup)가 받은 youtube 스코프 authorization code."""

    code: str


class YoutubeConnectResponse(BaseModel):
    connected: bool = True


class DriveFolderRequest(BaseModel):
    folder_id: str
    folder_name: str | None = None


class DriveConnectionResponse(BaseModel):
    connected: bool
    folder_name: str | None = None


class GoogleConfigResponse(BaseModel):
    """프론트 Picker용 공개 설정 (빌드에 안 박고 런타임 제공)."""

    client_id: str
    picker_api_key: str
