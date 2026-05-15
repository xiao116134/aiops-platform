from __future__ import annotations

from psycopg import connect
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from .config import settings


ALERT_STATUS_OPEN = 'open'
ALERT_STATUS_ACKED = 'acked'
ALERT_STATUS_SILENCED = 'silenced'
ALERT_STATUS_CLOSED = 'closed'
ALERT_STATUSES = {
    ALERT_STATUS_OPEN,
    ALERT_STATUS_ACKED,
    ALERT_STATUS_SILENCED,
    ALERT_STATUS_CLOSED,
}


def get_conn():
    if not settings.database_url:
        raise RuntimeError('DATABASE_URL 未配置，无法连接 PostgreSQL')
    return connect(settings.database_url, row_factory=dict_row)


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                  username TEXT PRIMARY KEY,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL,
                  avatar_url TEXT DEFAULT '',
                  email TEXT DEFAULT '',
                  phone TEXT DEFAULT '',
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  last_login_at TIMESTAMPTZ
                )
                '''
            )

            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT DEFAULT ''")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT DEFAULT ''")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ")

            for username, password, role, email, phone in [
                ('admin', 'admin123', 'admin', 'admin@aiops.local', '13800000001'),
                ('ops', 'ops123456', 'ops', 'ops@aiops.local', '13800000002'),
            ]:
                cur.execute(
                    'INSERT INTO users (username, password, role, email, phone) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING',
                    (username, password, role, email, phone),
                )

            cur.execute("UPDATE users SET email = 'admin@aiops.local' WHERE username = 'admin' AND COALESCE(email, '') = ''")
            cur.execute("UPDATE users SET email = 'ops@aiops.local' WHERE username = 'ops' AND COALESCE(email, '') = ''")
            cur.execute("UPDATE users SET phone = '13800000001' WHERE username = 'admin' AND COALESCE(phone, '') = ''")
            cur.execute("UPDATE users SET phone = '13800000002' WHERE username = 'ops' AND COALESCE(phone, '') = ''")

            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE COALESCE(email, '') <> ''")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users(phone) WHERE COALESCE(phone, '') <> ''")

            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS alerts (
                  id TEXT PRIMARY KEY,
                  level TEXT NOT NULL,
                  status TEXT NOT NULL,
                  service TEXT NOT NULL,
                  title TEXT NOT NULL,
                  assignee TEXT NOT NULL DEFAULT '',
                  happened_at TIMESTAMPTZ NOT NULL
                )
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS alert_details (
                  alert_id TEXT PRIMARY KEY REFERENCES alerts(id) ON DELETE CASCADE,
                  impact TEXT NOT NULL
                )
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS alert_timeline (
                  id BIGSERIAL PRIMARY KEY,
                  alert_id TEXT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
                  event_time TIMESTAMPTZ NOT NULL,
                  event TEXT NOT NULL
                )
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS alert_actions (
                  id BIGSERIAL PRIMARY KEY,
                  alert_id TEXT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
                  action_time TIMESTAMPTZ NOT NULL,
                  operator TEXT NOT NULL,
                  action TEXT NOT NULL
                )
                '''
            )

            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_profile_audit (
                  id BIGSERIAL PRIMARY KEY,
                  username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                  operator TEXT NOT NULL,
                  old_email TEXT NOT NULL,
                  new_email TEXT NOT NULL,
                  old_phone TEXT NOT NULL,
                  new_phone TEXT NOT NULL,
                  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                '''
            )

            seed_alerts = [
                ('ALT-1001', 'P1', 'open', 'payment-api', '支付接口错误率突增', '', "2026-05-15 22:58:00+08"),
                ('ALT-1002', 'P2', 'open', 'user-center', '登录延迟超过阈值', '', "2026-05-15 22:41:00+08"),
                ('ALT-1003', 'P3', 'silenced', 'k8s-node-03', '磁盘使用率超过 85%', 'ops', "2026-05-15 22:33:00+08"),
                ('ALT-1004', 'P2', 'acked', 'mysql-main', '主从延迟波动', 'admin', "2026-05-15 22:19:00+08"),
                ('ALT-1005', 'P2', 'open', 'gateway', 'API 网关 5xx 比例升高', '', "2026-05-15 22:12:00+08"),
                ('ALT-1006', 'P3', 'open', 'redis-cluster', '缓存命中率下降', '', "2026-05-15 22:05:00+08"),
                ('ALT-1007', 'P1', 'open', 'order-service', '下单成功率异常下跌', '', "2026-05-15 21:58:00+08"),
                ('ALT-1008', 'P3', 'acked', 'prometheus', '采集延迟波动', 'ops', "2026-05-15 21:49:00+08"),
                ('ALT-1009', 'P2', 'silenced', 'kafka-broker', '消费堆积接近阈值', 'admin', "2026-05-15 21:37:00+08"),
                ('ALT-1010', 'P3', 'acked', 'auth-service', '认证请求抖动', 'ops', "2026-05-15 21:26:00+08"),
                ('ALT-1011', 'P2', 'acked', 'billing-service', '账单任务执行延迟', 'ops', "2026-05-15 21:18:00+08"),
                ('ALT-1012', 'P3', 'silenced', 'dns-gateway', 'DNS 解析耗时波动', 'admin', "2026-05-15 21:11:00+08"),
                ('ALT-1013', 'P2', 'acked', 'search-api', '搜索接口超时率上升', 'ops', "2026-05-15 21:03:00+08"),
                ('ALT-1014', 'P3', 'silenced', 'object-storage', '对象存储读延迟升高', 'admin', "2026-05-15 20:56:00+08"),
                ('ALT-1015', 'P2', 'acked', 'payment-worker', '支付回调积压', 'ops', "2026-05-15 20:48:00+08"),
                ('ALT-1016', 'P3', 'silenced', 'edge-proxy', '边缘代理连接重置增多', 'admin', "2026-05-15 20:40:00+08"),
                ('ALT-1017', 'P2', 'acked', 'notification', '通知发送失败率波动', 'ops', "2026-05-15 20:31:00+08"),
                ('ALT-1018', 'P3', 'silenced', 'cmdb-sync', 'CMDB 同步延迟', 'admin', "2026-05-15 20:23:00+08"),
                ('ALT-1019', 'P2', 'acked', 'report-center', '报表导出队列积压', 'ops', "2026-05-15 20:16:00+08"),
                ('ALT-1020', 'P3', 'silenced', 'ops-portal', '运维门户静态资源命中率下降', 'admin', "2026-05-15 20:08:00+08"),
            ]
            for row in seed_alerts:
                cur.execute(
                    '''
                    INSERT INTO alerts (id, level, status, service, title, assignee, happened_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    ''',
                    row,
                )

            baseline_alert_state = [
                ('ALT-1001', 'P1', 'open', 'payment-api', '支付接口错误率突增', ''),
                ('ALT-1002', 'P2', 'open', 'user-center', '登录延迟超过阈值', ''),
                ('ALT-1003', 'P3', 'silenced', 'k8s-node-03', '磁盘使用率超过 85%', 'ops'),
                ('ALT-1004', 'P2', 'acked', 'mysql-main', '主从延迟波动', 'admin'),
                ('ALT-1005', 'P2', 'open', 'gateway', 'API 网关 5xx 比例升高', ''),
                ('ALT-1006', 'P3', 'open', 'redis-cluster', '缓存命中率下降', ''),
                ('ALT-1007', 'P1', 'open', 'order-service', '下单成功率异常下跌', ''),
                ('ALT-1008', 'P3', 'acked', 'prometheus', '采集延迟波动', 'ops'),
                ('ALT-1009', 'P2', 'silenced', 'kafka-broker', '消费堆积接近阈值', 'admin'),
                ('ALT-1010', 'P3', 'acked', 'auth-service', '认证请求抖动', 'ops'),
                ('ALT-1011', 'P2', 'acked', 'billing-service', '账单任务执行延迟', 'ops'),
                ('ALT-1012', 'P3', 'silenced', 'dns-gateway', 'DNS 解析耗时波动', 'admin'),
                ('ALT-1013', 'P2', 'acked', 'search-api', '搜索接口超时率上升', 'ops'),
                ('ALT-1014', 'P3', 'silenced', 'object-storage', '对象存储读延迟升高', 'admin'),
                ('ALT-1015', 'P2', 'acked', 'payment-worker', '支付回调积压', 'ops'),
                ('ALT-1016', 'P3', 'silenced', 'edge-proxy', '边缘代理连接重置增多', 'admin'),
                ('ALT-1017', 'P2', 'acked', 'notification', '通知发送失败率波动', 'ops'),
                ('ALT-1018', 'P3', 'silenced', 'cmdb-sync', 'CMDB 同步延迟', 'admin'),
                ('ALT-1019', 'P2', 'acked', 'report-center', '报表导出队列积压', 'ops'),
                ('ALT-1020', 'P3', 'silenced', 'ops-portal', '运维门户静态资源命中率下降', 'admin'),
            ]
            for alert_id, level, status, service, title, assignee in baseline_alert_state:
                cur.execute(
                    '''
                    UPDATE alerts
                    SET level = %s, status = %s, service = %s, title = %s, assignee = %s
                    WHERE id = %s
                    ''',
                    (level, status, service, title, assignee, alert_id),
                )

            for alert_id, impact in [
                ('ALT-1001', '支付成功率从 99.2% 降至 93.7%，华东与华南可用区受影响，主要体现在下单支付与回调确认链路。'),
                ('ALT-1002', '登录 P95 延迟提升到 1.8s，少量用户登录等待变慢。'),
                ('ALT-1003', 'k8s-node-03 磁盘余量不足，风险可控。'),
                ('ALT-1004', 'MySQL 主从延迟波动，当前业务读写未见明显失败。'),
                ('ALT-1005', '网关错误率短时上升，部分 API 响应失败。'),
                ('ALT-1006', '缓存命中率下降导致后端查询压力升高。'),
                ('ALT-1007', '下单链路多点超时，影响交易成功率。'),
                ('ALT-1008', '监控采集链路拥塞，指标存在轻微延迟。'),
                ('ALT-1009', '消息消费速度下降，堆积持续增长。'),
                ('ALT-1010', '认证服务响应抖动，对登录体验有轻微影响。'),
                ('ALT-1011', '账单生成任务延迟，影响财务数据准时性。'),
                ('ALT-1012', 'DNS 解析耗时波动，可能影响部分请求首包时间。'),
                ('ALT-1013', '搜索接口超时率增加，查询体验下降。'),
                ('ALT-1014', '对象存储读延迟升高，附件加载变慢。'),
                ('ALT-1015', '支付回调积压，订单状态更新延后。'),
                ('ALT-1016', '边缘代理连接重置增多，部分请求重试。'),
                ('ALT-1017', '通知发送失败率波动，触达成功率受影响。'),
                ('ALT-1018', 'CMDB 同步延迟，配置数据更新不及时。'),
                ('ALT-1019', '报表导出排队时间增加，生成速度下降。'),
                ('ALT-1020', '运维门户静态资源命中率下降，页面加载变慢。'),
            ]:
                cur.execute(
                    '''
                    INSERT INTO alert_details (alert_id, impact)
                    VALUES (%s, %s)
                    ON CONFLICT (alert_id) DO UPDATE SET impact = EXCLUDED.impact
                    ''',
                    (alert_id, impact),
                )

            timeline_seed = [
                ('ALT-1001', '2026-05-15 22:40:00+08', '支付网关错误率出现异常抬升趋势'),
                ('ALT-1001', '2026-05-15 22:48:00+08', '错误率开始爬升，超过 3% 阈值'),
                ('ALT-1001', '2026-05-15 22:53:00+08', '触发 P1 告警并通知值班群'),
                ('ALT-1001', '2026-05-15 22:56:00+08', '值班同学定位到 payment-api 与 gateway 链路抖动'),
                ('ALT-1001', '2026-05-15 22:58:00+08', '错误率达峰值 6.4%'),
                ('ALT-1001', '2026-05-15 23:02:00+08', '临时流量切换后错误率开始回落'),
                ('ALT-1002', '2026-05-15 22:31:00+08', '用户中心 CPU 使用率持续上升'),
                ('ALT-1002', '2026-05-15 22:38:00+08', '登录接口 P95 超过阈值 1.5s'),
                ('ALT-1002', '2026-05-15 22:41:00+08', '触发 P2 延迟告警'),
                ('ALT-1003', '2026-05-15 22:20:00+08', '磁盘使用率超过 80%'),
                ('ALT-1003', '2026-05-15 22:27:00+08', '磁盘使用率超过 85%，触发告警'),
                ('ALT-1003', '2026-05-15 22:33:00+08', '告警被静默 30 分钟'),
                ('ALT-1004', '2026-05-15 22:05:00+08', '复制延迟上升到 2.2s'),
                ('ALT-1004', '2026-05-15 22:12:00+08', '超过阈值触发 P2 告警'),
                ('ALT-1004', '2026-05-15 22:19:00+08', '管理员确认并持续观察'),
                ('ALT-1005', '2026-05-15 22:10:00+08', '网关 5xx 比例连续 3 分钟超阈值'),
                ('ALT-1006', '2026-05-15 22:03:00+08', '缓存命中率跌破 80% 阈值'),
                ('ALT-1007', '2026-05-15 21:56:00+08', '下单请求超时比例快速上升'),
                ('ALT-1008', '2026-05-15 21:46:00+08', 'Prometheus 抓取队列出现排队'),
                ('ALT-1009', '2026-05-15 21:34:00+08', '消费者 lag 超过预警值'),
                ('ALT-1010', '2026-05-15 21:24:00+08', '认证节点响应时间抖动升高'),
                ('ALT-1011', '2026-05-15 21:16:00+08', '账单任务队列等待时间增加'),
                ('ALT-1012', '2026-05-15 21:09:00+08', 'DNS 平均解析耗时超过阈值'),
                ('ALT-1013', '2026-05-15 21:01:00+08', '搜索请求超时比例升高'),
                ('ALT-1014', '2026-05-15 20:54:00+08', '对象存储读取 P95 延迟上升'),
                ('ALT-1015', '2026-05-15 20:46:00+08', '支付回调消费速率下降'),
                ('ALT-1016', '2026-05-15 20:38:00+08', '边缘代理连接重置次数升高'),
                ('ALT-1017', '2026-05-15 20:29:00+08', '通知发送失败波动超阈值'),
                ('ALT-1018', '2026-05-15 20:21:00+08', 'CMDB 同步延迟持续增加'),
                ('ALT-1019', '2026-05-15 20:14:00+08', '报表导出任务排队数量升高'),
                ('ALT-1020', '2026-05-15 20:06:00+08', '门户静态资源缓存命中率下降'),
            ]
            for alert_id, event_time, event in timeline_seed:
                cur.execute(
                    '''
                    INSERT INTO alert_timeline (alert_id, event_time, event)
                    SELECT %s, %s, %s
                    WHERE NOT EXISTS (
                      SELECT 1 FROM alert_timeline WHERE alert_id = %s AND event_time = %s AND event = %s
                    )
                    ''',
                    (alert_id, event_time, event, alert_id, event_time, event),
                )

            action_seed = [
                ('ALT-1001', '2026-05-15 22:49:00+08', 'system', '检测到支付失败率异常，触发预警规则'),
                ('ALT-1001', '2026-05-15 22:52:00+08', 'ops', '值班确认告警并开始排查上下游依赖'),
                ('ALT-1001', '2026-05-15 22:54:00+08', 'system', '自动升级告警级别 P2 → P1'),
                ('ALT-1001', '2026-05-15 22:57:00+08', 'admin', '指派 payment-api 负责人介入处理'),
                ('ALT-1001', '2026-05-15 23:01:00+08', 'ops', '执行临时限流与流量切换，观察错误率回落'),
                ('ALT-1001', '2026-05-15 23:06:00+08', 'admin', '记录事件结论并安排次日复盘'),
                ('ALT-1002', '2026-05-15 22:42:00+08', 'system', '已通知 user-center 值班人'),
                ('ALT-1003', '2026-05-15 22:33:00+08', 'ops', '静默告警 30 分钟'),
                ('ALT-1004', '2026-05-15 22:19:00+08', 'admin', '确认告警，观察延迟曲线'),
                ('ALT-1008', '2026-05-15 21:49:00+08', 'ops', '确认告警并观察采集延迟'),
                ('ALT-1009', '2026-05-15 21:37:00+08', 'admin', '静默 20 分钟等待峰值回落'),
                ('ALT-1010', '2026-05-15 21:26:00+08', 'ops', '确认告警并标记持续观察'),
            ]
            for alert_id, action_time, operator, action in action_seed:
                cur.execute(
                    '''
                    INSERT INTO alert_actions (alert_id, action_time, operator, action)
                    SELECT %s, %s, %s, %s
                    WHERE NOT EXISTS (
                      SELECT 1 FROM alert_actions WHERE alert_id = %s AND action_time = %s AND operator = %s AND action = %s
                    )
                    ''',
                    (alert_id, action_time, operator, action, alert_id, action_time, operator, action),
                )

        conn.commit()


def get_user(username: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT username, password, role, avatar_url, email, phone, created_at, last_login_at FROM users WHERE username = %s',
                (username,),
            )
            return cur.fetchone()


def update_password(username: str, new_password: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET password = %s WHERE username = %s', (new_password, username))
        conn.commit()


def update_avatar(username: str, avatar_url: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET avatar_url = %s WHERE username = %s', (avatar_url, username))
        conn.commit()


def update_profile(username: str, email: str, phone: str, operator: str) -> tuple[bool, str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT email, phone FROM users WHERE username = %s', (username,))
            current = cur.fetchone()
            if current is None:
                return False, 'not_found'

            old_email = current.get('email') or ''
            old_phone = current.get('phone') or ''

            try:
                cur.execute(
                    'UPDATE users SET email = %s, phone = %s WHERE username = %s',
                    (email, phone, username),
                )
            except UniqueViolation:
                conn.rollback()
                return False, 'duplicate'

            cur.execute(
                '''
                INSERT INTO user_profile_audit (username, operator, old_email, new_email, old_phone, new_phone)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (username, operator, old_email, email, old_phone, phone),
            )
        conn.commit()

    return True, 'ok'


def touch_last_login(username: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET last_login_at = NOW() WHERE username = %s', (username,))
        conn.commit()


def list_alerts(level: str, status: str, service: str, q: str, page: int, page_size: int) -> dict:
    conditions = []
    params: list[str] = []
    if level != 'all':
        conditions.append('a.level = %s')
        params.append(level)
    if status != 'all':
        conditions.append('a.status = %s')
        params.append(status)
    if service != 'all':
        conditions.append('a.service = %s')
        params.append(service)
    if q.strip():
        conditions.append('(a.title ILIKE %s OR a.id ILIKE %s OR a.service ILIKE %s)')
        keyword = f"%{q.strip()}%"
        params.extend([keyword, keyword, keyword])

    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    offset = (safe_page - 1) * safe_page_size
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT COUNT(*) AS total
                FROM alerts a
                {where_sql}
                ''',
                params,
            )
            total = int(cur.fetchone()['total'])

            cur.execute(
                f'''
                SELECT a.id, a.level, a.status, a.service, a.title, a.assignee,
                       TO_CHAR(a.happened_at AT TIME ZONE 'Asia/Shanghai', 'HH24:MI') AS time
                FROM alerts a
                {where_sql}
                ORDER BY a.happened_at DESC
                LIMIT %s OFFSET %s
                ''',
                [*params, safe_page_size, offset],
            )
            items = cur.fetchall()

            cur.execute('SELECT DISTINCT service FROM alerts ORDER BY service')
            services = [row['service'] for row in cur.fetchall()]

    total_pages = max(1, (total + safe_page_size - 1) // safe_page_size)
    return {
        'items': items,
        'services': services,
        'total': total,
        'page': safe_page,
        'page_size': safe_page_size,
        'total_pages': total_pages,
    }


def get_alert_detail(
    alert_id: str,
    action_operator: str = '',
    action_from: str = '',
    action_to: str = '',
    action_limit: int = 50,
) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT a.id, a.level, a.status, a.service, a.title, a.assignee,
                       TO_CHAR(a.happened_at AT TIME ZONE 'Asia/Shanghai', 'HH24:MI') AS time,
                       d.impact
                FROM alerts a
                JOIN alert_details d ON d.alert_id = a.id
                WHERE a.id = %s
                ''',
                (alert_id,),
            )
            detail = cur.fetchone()
            if detail is None:
                return None

            cur.execute(
                '''
                SELECT TO_CHAR(event_time AT TIME ZONE 'Asia/Shanghai', 'HH24:MI') AS time, event
                FROM alert_timeline
                WHERE alert_id = %s
                ORDER BY event_time ASC
                ''',
                (alert_id,),
            )
            timeline = cur.fetchall()

            action_conditions = ['alert_id = %s']
            action_params: list[str | int] = [alert_id]

            if action_operator.strip():
                action_conditions.append('operator = %s')
                action_params.append(action_operator.strip())
            if action_from.strip():
                action_conditions.append('action_time >= %s::timestamptz')
                action_params.append(action_from.strip())
            if action_to.strip():
                action_conditions.append('action_time <= %s::timestamptz')
                action_params.append(action_to.strip())

            where_sql = ' AND '.join(action_conditions)
            action_params.append(max(1, min(action_limit, 200)))

            cur.execute(
                f'''
                SELECT TO_CHAR(action_time AT TIME ZONE 'Asia/Shanghai', 'HH24:MI') AS time, operator, action
                FROM alert_actions
                WHERE {where_sql}
                ORDER BY action_time DESC
                LIMIT %s
                ''',
                action_params,
            )
            actions = cur.fetchall()

    return {
        'id': detail['id'],
        'level': detail['level'],
        'status': detail['status'],
        'service': detail['service'],
        'title': detail['title'],
        'assignee': detail['assignee'],
        'time': detail['time'],
        'impact': detail['impact'],
        'timeline': timeline,
        'actions': actions,
    }


def update_alert_status(alert_id: str, status: str, default_assignee: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE alerts
                SET status = %s,
                    assignee = CASE WHEN COALESCE(assignee, '') = '' THEN %s ELSE assignee END
                WHERE id = %s
                RETURNING id
                ''',
                (status, default_assignee, alert_id),
            )
            updated = cur.fetchone()
        conn.commit()
    return updated is not None


def transition_alert_status(
    alert_id: str,
    target_status: str,
    default_assignee: str,
    allowed_current_statuses: set[str] | None = None,
) -> tuple[bool, str | None]:
    if target_status not in ALERT_STATUSES:
        return False, 'invalid_target_status'

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT status FROM alerts WHERE id = %s', (alert_id,))
            current = cur.fetchone()
            if current is None:
                return False, 'not_found'

            current_status = current.get('status')
            if allowed_current_statuses is not None and current_status not in allowed_current_statuses:
                return False, 'invalid_current_status'

            cur.execute(
                '''
                UPDATE alerts
                SET status = %s,
                    assignee = CASE WHEN COALESCE(assignee, '') = '' THEN %s ELSE assignee END
                WHERE id = %s
                ''',
                (target_status, default_assignee, alert_id),
            )
        conn.commit()

    return True, None


def assign_alert(alert_id: str, assignee: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE alerts SET assignee = %s WHERE id = %s RETURNING id', (assignee, alert_id))
            updated = cur.fetchone()
        conn.commit()
    return updated is not None


def add_alert_action(alert_id: str, operator: str, action: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO alert_actions (alert_id, action_time, operator, action) VALUES (%s, NOW(), %s, %s)',
                (alert_id, operator, action),
            )
        conn.commit()
