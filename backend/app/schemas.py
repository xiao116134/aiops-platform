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
    email: str = ''
    phone: str = ''


class LoginResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserInfo


class RefreshTokenResponse(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UpdateProfileRequest(BaseModel):
    email: str = Field(min_length=3, max_length=128)
    phone: str = Field(min_length=11, max_length=11, pattern=r'^1\d{10}$')


class MessageResponse(BaseModel):
    message: str


class AvatarUploadResponse(BaseModel):
    message: str
    avatar_url: str


class AlertItem(BaseModel):
    id: str
    level: str
    status: str
    service: str
    title: str
    assignee: str
    time: str


class AlertsListResponse(BaseModel):
    items: list[AlertItem]
    services: list[str]
    total: int


class AlertTimelineEvent(BaseModel):
    time: str
    event: str


class AlertActionRecord(BaseModel):
    time: str
    operator: str
    action: str


class AlertDetailResponse(AlertItem):
    impact: str
    timeline: list[AlertTimelineEvent]
    actions: list[AlertActionRecord]


class AssignAlertRequest(BaseModel):
    assignee: str = Field(min_length=1, max_length=64)
