from __future__ import annotations

from psycopg import connect
from psycopg.rows import dict_row

from .config import settings


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
                  phone TEXT DEFAULT ''
                )
                '''
            )

            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT DEFAULT ''")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT DEFAULT ''")

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
        conn.commit()


def get_user(username: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT username, password, role, avatar_url, email, phone FROM users WHERE username = %s',
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


def update_profile(username: str, email: str, phone: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET email = %s, phone = %s WHERE username = %s',
                (email, phone, username),
            )
        conn.commit()
