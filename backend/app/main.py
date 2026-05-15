from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import get_user, init_db, update_avatar, update_password, update_profile
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

mock_alerts = [
    {'id': 'ALT-1001', 'level': 'P1', 'status': 'open', 'service': 'payment-api', 'title': '支付接口错误率突增', 'assignee': '', 'time': '22:58'},
    {'id': 'ALT-1002', 'level': 'P2', 'status': 'open', 'service': 'user-center', 'title': '登录延迟超过阈值', 'assignee': '', 'time': '22:41'},
    {'id': 'ALT-1003', 'level': 'P3', 'status': 'silenced', 'service': 'k8s-node-03', 'title': '磁盘使用率超过 85%', 'assignee': 'ops', 'time': '22:33'},
    {'id': 'ALT-1004', 'level': 'P2', 'status': 'acked', 'service': 'mysql-main', 'title': '主从延迟波动', 'assignee': 'admin', 'time': '22:19'},
]

alert_detail_map = {
    'ALT-1001': {
        'impact': '支付成功率从 99.2% 降至 93.7%，影响华东与华南可用区。',
        'timeline': [
            {'time': '22:48', 'event': '错误率开始爬升，超过 3% 阈值'},
            {'time': '22:53', 'event': '触发 P1 告警并通知值班群'},
            {'time': '22:58', 'event': '错误率达峰值 6.4%'}
        ],
        'actions': [
            {'time': '22:54', 'operator': 'system', 'action': '自动升级告警级别 P2 → P1'}
        ],
    },
    'ALT-1002': {
        'impact': '登录 P95 延迟提升到 1.8s，少量用户登录等待变慢。',
        'timeline': [
            {'time': '22:31', 'event': '用户中心 CPU 使用率持续上升'},
            {'time': '22:38', 'event': '登录接口 P95 超过阈值 1.5s'},
            {'time': '22:41', 'event': '触发 P2 延迟告警'}
        ],
        'actions': [
            {'time': '22:42', 'operator': 'system', 'action': '已通知 user-center 值班人'}
        ],
    },
    'ALT-1003': {
        'impact': 'k8s-node-03 磁盘余量不足，风险可控。',
        'timeline': [
            {'time': '22:20', 'event': '磁盘使用率超过 80%'},
            {'time': '22:27', 'event': '磁盘使用率超过 85%，触发告警'},
            {'time': '22:33', 'event': '告警被静默 30 分钟'}
        ],
        'actions': [
            {'time': '22:33', 'operator': 'ops', 'action': '静默告警 30 分钟'}
        ],
    },
    'ALT-1004': {
        'impact': 'MySQL 主从延迟波动，当前业务读写未见明显失败。',
        'timeline': [
            {'time': '22:05', 'event': '复制延迟上升到 2.2s'},
            {'time': '22:12', 'event': '超过阈值触发 P2 告警'},
            {'time': '22:19', 'event': '管理员确认并持续观察'}
        ],
        'actions': [
            {'time': '22:19', 'operator': 'admin', 'action': '确认告警，观察延迟曲线'}
        ],
    },
}


def find_alert(alert_id: str) -> dict | None:
    for alert in mock_alerts:
        if alert['id'] == alert_id:
            return alert
    return None


def append_alert_action(alert_id: str, operator: str, action: str) -> None:
    detail = alert_detail_map.get(alert_id)
    if detail is None:
        return
    detail['actions'].insert(0, {'time': '刚刚', 'operator': operator, 'action': action})


@app.on_event('startup')
def on_startup() -> None:
    init_db()


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

    token = create_access_token(user['username'], user['role'])
    refresh_token = create_refresh_token(user['username'], user['role'])
    return LoginResponse(
        token=token,
        refresh_token=refresh_token,
        user=UserInfo(
            username=user['username'],
            role=user['role'],
            avatar_url=user['avatar_url'] or '',
            email=user.get('email') or '',
            phone=user.get('phone') or '',
        ),
    )


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
    return UserInfo(
        username=user_record['username'],
        role=user_record['role'],
        avatar_url=user_record['avatar_url'] or '',
        email=user_record.get('email') or '',
        phone=user_record.get('phone') or '',
    )


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
    responses={400: {'description': '邮箱或手机号格式不合法'}, 401: {'description': '未登录或 token 无效'}, 404: {'description': '用户不存在'}},
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

    update_profile(user['username'], email, phone)
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
) -> dict:
    filtered = []
    keyword = q.strip().lower()

    for alert in mock_alerts:
        if level != 'all' and alert['level'] != level:
            continue
        if status != 'all' and alert['status'] != status:
            continue
        if service != 'all' and alert['service'] != service:
            continue
        if keyword and keyword not in (alert['title'] + alert['id'] + alert['service']).lower():
            continue
        filtered.append(deepcopy(alert))

    services = sorted({item['service'] for item in mock_alerts})
    return {'items': filtered, 'services': services, 'total': len(filtered)}


@app.get(
    '/api/alerts/{alert_id}',
    response_model=AlertDetailResponse,
    tags=['alerts'],
    summary='获取告警详情',
    response_description='返回告警影响面、时间线与处置记录',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def get_alert_detail(alert_id: str, _: dict = Depends(get_current_user)) -> dict:
    alert = find_alert(alert_id)
    detail = alert_detail_map.get(alert_id)
    if alert is None or detail is None:
        raise HTTPException(status_code=404, detail='告警不存在')

    return {
        'id': alert['id'],
        'level': alert['level'],
        'status': alert['status'],
        'service': alert['service'],
        'title': alert['title'],
        'assignee': alert['assignee'],
        'time': alert['time'],
        'impact': detail['impact'],
        'timeline': detail['timeline'],
        'actions': detail['actions'],
    }


@app.post(
    '/api/alerts/{alert_id}/ack',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='确认告警',
    response_description='返回确认结果',
    responses={401: {'description': '未登录或 token 无效'}, 404: {'description': '告警不存在'}},
)
def ack_alert(alert_id: str, user: dict = Depends(get_current_user)) -> MessageResponse:
    alert = find_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail='告警不存在')

    alert['status'] = 'acked'
    if not alert['assignee']:
        alert['assignee'] = user['username']
    append_alert_action(alert_id, user['username'], '确认告警')
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
    alert = find_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail='告警不存在')

    alert['status'] = 'silenced'
    if not alert['assignee']:
        alert['assignee'] = user['username']
    append_alert_action(alert_id, user['username'], '静默告警')
    return MessageResponse(message='告警已静默')


@app.post(
    '/api/alerts/{alert_id}/assign',
    response_model=MessageResponse,
    tags=['alerts'],
    summary='指派告警',
    response_description='返回指派结果',
    responses={
        400: {'description': 'assignee 不能为空'},
        401: {'description': '未登录或 token 无效'},
        404: {'description': '告警不存在'},
    },
)
def assign_alert(alert_id: str, payload: AssignAlertRequest, user: dict = Depends(get_current_user)) -> MessageResponse:
    assignee = payload.assignee.strip()
    if not assignee:
        raise HTTPException(status_code=400, detail='assignee 不能为空')

    alert = find_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail='告警不存在')

    alert['assignee'] = assignee
    append_alert_action(alert_id, user['username'], f'指派给 {assignee}')
    return MessageResponse(message=f'已指派给 {assignee}')
