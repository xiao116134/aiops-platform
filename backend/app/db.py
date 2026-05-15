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
                  avatar_url TEXT DEFAULT ''
                )
                '''
            )

            for username, password, role in [
                ('admin', 'admin123', 'admin'),
                ('ops', 'ops123456', 'ops'),
            ]:
                cur.execute(
                    'INSERT INTO users (username, password, role) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING',
                    (username, password, role),
                )
        conn.commit()


def get_user(username: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT username, password, role, avatar_url FROM users WHERE username = %s',
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
