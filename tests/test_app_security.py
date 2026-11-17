import unittest

from app import _LOGIN_FAILURES, _login_blocked, _record_login_failure, create_app


class AppSecurityTests(unittest.TestCase):
    def setUp(self):
        _LOGIN_FAILURES.clear()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-with-at-least-32-chars",
            "SESSION_COOKIE_SECURE": True,
        })
        self.client = self.app.test_client()

    def test_private_profile_requires_login(self):
        response = self.client.get("/api/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "Faça login para continuar.")

    def test_mutating_auth_route_requires_csrf(self):
        response = self.client.post("/api/auth/register", json={})
        self.assertEqual(response.status_code, 403)

    def test_login_failure_limit_blocks_then_expires(self):
        ip = "192.0.2.1"
        for i in range(8):
            _record_login_failure(ip, 1000 + i)
        self.assertTrue(_login_blocked(ip, 1010))
        self.assertFalse(_login_blocked(ip, 1610))

    def test_security_headers_are_present(self):
        response = self.client.get("/api/auth/csrf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertIn("Secure", response.headers.get("Set-Cookie", ""))


if __name__ == "__main__":
    unittest.main()
