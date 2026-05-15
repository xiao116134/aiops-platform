import json
import unittest
from urllib import error, request

BASE_URL = 'http://localhost:8000'


def http_json(method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    req = request.Request(f'{BASE_URL}{path}', data=body, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')

    try:
        with request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8') or '{}'
            return resp.status, json.loads(content)
    except error.HTTPError as exc:
        content = exc.read().decode('utf-8') or '{}'
        exc.close()
        return exc.code, json.loads(content)


class ProfileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        status, body = http_json('POST', '/api/login', {'username': 'admin', 'password': 'admin123'})
        if status != 200:
            raise RuntimeError(f'登录失败，无法执行测试: {status} {body}')
        cls.token = body['token']

    def test_update_profile_success(self):
        status, body = http_json(
            'POST',
            '/api/profile',
            {'email': 'admin+test@aiops.local', 'phone': '13800138000'},
            token=self.token,
        )

        self.assertEqual(status, 200)
        self.assertEqual(body.get('message'), '用户信息更新成功')

    def test_update_profile_rejects_invalid_email(self):
        status, body = http_json(
            'POST',
            '/api/profile',
            {'email': 'admin-at-aiops.local', 'phone': '13800138000'},
            token=self.token,
        )

        self.assertEqual(status, 400)
        self.assertEqual(body.get('detail'), '邮箱格式不正确')

    def test_update_profile_rejects_invalid_phone(self):
        status, body = http_json(
            'POST',
            '/api/profile',
            {'email': 'admin@aiops.local', 'phone': '23800138000'},
            token=self.token,
        )

        self.assertEqual(status, 422)
        detail = body.get('detail') or []
        self.assertTrue(detail and detail[0].get('type') in {'string_pattern_mismatch', 'string_too_short'})

    def test_update_profile_requires_auth(self):
        status, _ = http_json('POST', '/api/profile', {'email': 'admin@aiops.local', 'phone': '13800138000'})
        self.assertEqual(status, 401)


if __name__ == '__main__':
    unittest.main()
