from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserInfo(BaseModel):
    username: str
    role: str
    avatar_url: str = ''


class LoginResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserInfo


class RefreshTokenResponse(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class MessageResponse(BaseModel):
    message: str


class AvatarUploadResponse(BaseModel):
    message: str
    avatar_url: str
