from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import (
    ALERT_STATUS_ACKED,
    ALERT_STATUS_CLOSED,
    ALERT_STATUS_OPEN,
    ALERT_STATUS_SILENCED,
    add_alert_action,
    assign_alert as assign_alert_db,
    get_alert_detail as get_alert_detail_db,
    get_user,
    init_db,
    list_alerts as list_alerts_db,
    touch_last_login,
    transition_alert_status,
    update_avatar,
    update_password,
    update_profile,
)
from .schemas import (
    AlertDetailResponse,
    AlertsListResponse,
    AssignAlertRequest,
    AvatarUploadResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UpdateProfileRequest,
    UserInfo,
)
from .security import create_access_token, create_refresh_token, decode_token

app = FastAPI(
    title=settings.app_name,
    description='AiOps 平台后端 API 文档（认证、用户、告警中心）。',
    version='1.0.0',
    openapi_tags=[
        {'name': 'system', 'description': '系统状态与健康检查'},
        {'name': 'auth', 'description': '登录与 token 刷新'},
        {'name': 'user', 'description': '当前用户、密码与头像'},
        {'name': 'alerts', 'description': '告警中心列表、详情与处置动作'},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1)(:\d+)?/?$',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / 'uploads' / 'avatars'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount('/uploads', StaticFiles(directory=BASE_DIR / 'uploads'), name='uploads')

@app.on_event('startup')
def on_startup() -> None:
    init_db()


def format_dt(value) -> str:
    if value is None:
        return ''
    try:
        return value.isoformat()
    except AttributeError:
        return str(value)


def build_user_info(user_record: dict) -> UserInfo:
    return UserInfo(
        username=user_record['username'],
        role=user_record['role'],
        avatar_url=user_record['avatar_url'] or '',
        email=user_record.get('email') or '',
        phone=user_record.get('phone') or '',
        created_at=format_dt(user_record.get('created_at')),
        last_login_at=format_dt(user_record.get('last_login_at')),
    )


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='缺少或无效的 Authorization 头')

    token = authorization.split(' ', 1)[1]
    payload = decode_token(token)
    if payload.get('type') != 'access':
        raise HTTPException(status_code=401, detail='访问 token 无效')

    username = payload.get('sub')
    role = payload.get('role')
    if not username or not role:
        raise HTTPException(status_code=401, detail='Token 内容无效')

    return {'username': username, 'role': role}


@app.get(
    '/health',
    tags=['system'],
    summary='健康检查',
    response_description='服务存活状态',
)
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post(
    '/api/login',
    response_model=LoginResponse,
    tags=['auth'],
    summary='账号登录',
    response_description='返回 access token、refresh token 与用户信息',
    responses={401: {'description': '用户名或密码错误'}},
)
def login(payload: LoginRequest) -> LoginResponse:
    user = get_user(payload.username)
    if user is None or user['password'] != payload.password:
        raise HTTPException(status_code=401, detail='用户名或密码错误')

    touch_last_login(user['username'])
    user = get_user(payload.username)
    token = create_access_token(user['username'], user['role'])
    refresh_token = create_refresh_token(user['username'], user['role'])
    return LoginResponse(token=token, refresh_token=refresh_token, user=build_user_info(user))


@app.post(
    '/api/refresh-token',
    response_model=RefreshTokenResponse,
    tags=['auth'],
    summary='刷新 Access Token',
    response_description='返回新的 access token',
    responses={401: {'description': 'refresh token 无效或过期'}},
)
def refresh_token(payload: RefreshTokenRequest) -> RefreshTokenResponse:
    token_payload = decode_token(payload.refresh_token)
    if token_payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='refresh token 无效')

    username = token_payload.get('sub')
    role = token_payload.get('role')
    if not username or not role:
        raise HTTPException(status_code=401, detail='refresh token 内容无效')

    token = create_access_token(username, role)
    return RefreshTokenResponse(token=token)


@app.get(
    '/api/me',
    response_model=UserInfo,
    tags=['user'],
    summary='获取当前用户',
    response_description='返回当前登录用户信息',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '用户不存在'}},
)
def me(user: dict = Depends(get_current_user)) -> UserInfo:
    user_record = get_user(user['username'])
    if user_record is None:
        raise HTTPException(status_code=404, detail='用户不存在')
    return build_user_info(user_record)


@app.post(
    '/api/change-password',
    response_model=MessageResponse,
    tags=['user'],
    summary='修改密码',
    response_description='返回修改结果',
    responses={
        400: {'description': '旧密码错误 / 新旧密码相同'},
        401: {'description': '未登录或 token 无效'},
        404: {'description': '用户不存在'},
    },
)
def change_password(payload: ChangePasswordRequest, user: dict = Depends(get_current_user)) -> MessageResponse:
    user_record = get_user(user['username'])
    if user_record is None:
        raise HTTPException(status_code=404, detail='用户不存在')

    if user_record['password'] != payload.old_password:
        raise HTTPException(status_code=400, detail='旧密码错误')

    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail='新密码不能与旧密码相同')

    update_password(user['username'], payload.new_password)
    return MessageResponse(message='密码修改成功')


@app.post(
    '/api/profile',
    response_model=MessageResponse,
    tags=['user'],
    summary='更新用户信息',
    response_description='返回用户信息更新结果',
    responses={400: {'description': '邮箱或手机号格式不合法 / 已被占用'}, 401: {'description': '未登录或 token 无效'}, 404: {'description': '用户不存在'}},
)
def update_user_profile(payload: UpdateProfileRequest, user: dict = Depends(get_current_user)) -> MessageResponse:
    user_record = get_user(user['username'])
    if user_record is None:
        raise HTTPException(status_code=404, detail='用户不存在')

    email = payload.email.strip()
    phone = payload.phone.strip()
    if '@' not in email:
        raise HTTPException(status_code=400, detail='邮箱格式不正确')
    if not phone.isdigit() or len(phone) != 11 or not phone.startswith('1'):
        raise HTTPException(status_code=400, detail='手机号需为 11 位大陆手机号')

    ok, reason = update_profile(user['username'], email, phone, user['username'])
    if not ok:
        if reason == 'not_found':
            raise HTTPException(status_code=404, detail='用户不存在')
        if reason == 'duplicate':
            raise HTTPException(status_code=400, detail='邮箱或手机号已被占用')
        raise HTTPException(status_code=400, detail='用户信息更新失败')

    return MessageResponse(message='用户信息更新成功')


@app.post(
    '/api/upload-avatar',
    response_model=AvatarUploadResponse,
    tags=['user'],
    summary='上传头像',
    response_description='返回头像访问地址',
    responses={400: {'description': '图片类型或大小不合法'}, 401: {'description': '未登录或 token 无效'}},
)
async def upload_avatar(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> AvatarUploadResponse:
    if file.content_type not in {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}:
        raise HTTPException(status_code=400, detail='仅支持 png/jpg/webp 图片')

    ext = Path(file.filename or '').suffix.lower() or '.png'
    if ext not in {'.png', '.jpg', '.jpeg', '.webp'}:
        ext = '.png'

    filename = f"{user['username']}-{uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / filename

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='头像大小不能超过 2MB')

    save_path.write_bytes(content)
    avatar_url = f"http://localhost:8000/uploads/avatars/{filename}"
    update_avatar(user['username'], avatar_url)

    return AvatarUploadResponse(message='头像上传成功', avatar_url=avatar_url)


@app.get(
    '/api/alerts',
    response_model=AlertsListResponse,
    tags=['alerts'],
    summary='获取告警列表',
    response_description='返回告警列表、服务筛选项与总数',
    responses={401: {'description': '未登录或 token 无效'}},
)
def list_alerts(
    _: dict = Depends(get_current_user),
    level: str = Query(default='all'),
    status: str = Query(default='all'),
    service: str = Query(default='all'),
    q: str = Query(default=''),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict:
    return list_alerts_db(level=level, status=status, service=service, q=q, page=page, page_size=page_size)


@app.get(
    '/api/alerts/{alert_id}',
    response_model=AlertDetailResponse,
    tags=['alerts'],
    summary='获取告警详情',
    response_description='返回告警影响面、时间线与处置记录（支持按操作人/时间筛选处置记录）',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def get_alert_detail(
    alert_id: str,
    _: dict = Depends(get_current_user),
    action_operator: str = Query(default=''),
    action_from: str = Query(default=''),
    action_to: str = Query(default=''),
    action_limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    detail = get_alert_detail_db(
        alert_id,
        action_operator=action_operator,
        action_from=action_from,
        action_to=action_to,
        action_limit=action_limit,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail='告警不存在')
    return detail


@app.post(
    '/api/alerts/{alert_id}/ack',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='确认告警',
    response_description='返回确认结果',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def ack_alert(alert_id: str, user: dict = Depends(get_current_user)) -> MessageResponse:
    ok, reason = transition_alert_status(
        alert_id,
        ALERT_STATUS_ACKED,
        user['username'],
        allowed_current_statuses={ALERT_STATUS_OPEN},
    )
    if not ok:
        if reason == 'not_found':
            raise HTTPException(status_code=404, detail='告警不存在')
        raise HTTPException(status_code=400, detail='仅 open 状态可确认')

    add_alert_action(alert_id, user['username'], '确认告警')
    return MessageResponse(message='告警已确认')


@app.post(
    '/api/alerts/{alert_id}/silence',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='静默告警',
    response_description='返回静默结果',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def silence_alert(alert_id: str, user: dict = Depends(get_current_user)) -> MessageResponse:
    ok, reason = transition_alert_status(
        alert_id,
        ALERT_STATUS_SILENCED,
        user['username'],
        allowed_current_statuses={ALERT_STATUS_OPEN, ALERT_STATUS_ACKED, ALERT_STATUS_CLOSED},
    )
    if not ok:
        if reason == 'not_found':
            raise HTTPException(status_code=404, detail='告警不存在')
        raise HTTPException(status_code=400, detail='仅 open/acked/closed 状态可静默')

    add_alert_action(alert_id, user['username'], '静默告警')
    return MessageResponse(message='告警已静默')


@app.post(
    '/api/alerts/{alert_id}/close',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='关闭告警',
    response_description='将告警状态更新为 closed',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def close_alert(alert_id: str, user: dict = Depends(get_current_user)) -> MessageResponse:
    ok, reason = transition_alert_status(
        alert_id,
        ALERT_STATUS_CLOSED,
        user['username'],
        allowed_current_statuses={ALERT_STATUS_OPEN, ALERT_STATUS_ACKED},
    )
    if not ok:
        if reason == 'not_found':
            raise HTTPException(status_code=404, detail='告警不存在')
        raise HTTPException(status_code=400, detail='仅 open/acked 状态可关闭')

    add_alert_action(alert_id, user['username'], '关闭告警')
    return MessageResponse(message='告警已关闭')


@app.post(
    '/api/alerts/{alert_id}/reopen',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='重新打开告警',
    response_description='将 closed 告警状态重置为 open',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def reopen_alert(alert_id: str, user: dict = Depends(get_current_user)) -> MessageResponse:
    ok, reason = transition_alert_status(
        alert_id,
        ALERT_STATUS_OPEN,
        user['username'],
        allowed_current_statuses={ALERT_STATUS_CLOSED},
    )
    if not ok:
        if reason == 'not_found':
            raise HTTPException(status_code=404, detail='告警不存在')
        raise HTTPException(status_code=400, detail='仅已关闭告警可重新打开')

    add_alert_action(alert_id, user['username'], '重新打开告警')
    return MessageResponse(message='告警已重新打开')


@app.post(
    '/api/alerts/{alert_id}/assign',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='指派告警',
    response_description='返回指派结果',
    responses={
        400: {'description': 'assignee 不能为空'},
        401: {'description': '未登录或 token 无效'},
        403: {'description': '仅管理员可指派告警'},
        404: {'description': '告警不存在'},
    },
)
def assign_alert(alert_id: str, payload: AssignAlertRequest, user: dict = Depends(get_current_user)) -> MessageResponse:
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='仅管理员可指派告警')

    assignee = payload.assignee.strip()
    if not assignee:
        raise HTTPException(status_code=400, detail='assignee 不能为空')

    ok = assign_alert_db(alert_id, assignee)
    if not ok:
        raise HTTPException(status_code=404, detail='告警不存在')

    add_alert_action(alert_id, user['username'], f'指派给 {assignee}')
    return MessageResponse(message=f'已指派给 {assignee}')
