import unittest

import authpolicy as ap


class Passwords(unittest.TestCase):
    def test_good_password(self):
        self.assertEqual(ap.password_problems("Blue-Sky-2026-xyz", "dana@example.com"), [])

    def test_too_short(self):
        self.assertTrue(any("קצרה" in p for p in ap.password_problems("Ab1")))

    def test_needs_letters_and_digits(self):
        self.assertTrue(any("אותיות" in p for p in ap.password_problems("abcdefghijklmnop")))
        self.assertTrue(any("אותיות" in p for p in ap.password_problems("123456789012345")))

    def test_hebrew_letters_count(self):
        self.assertEqual(ap.password_problems("שלוםעולם-2026-כחול", "x@y.com"), [])

    def test_repeats(self):
        self.assertTrue(any("חוזרת" in p for p in ap.password_problems("aaaaaaaaaaa1")))

    def test_contains_username(self):
        self.assertTrue(any("שם המשתמש" in p for p in ap.password_problems("danacohen-Blue-2026", "danacohen@x.com")))

    def test_common(self):
        self.assertTrue(any("נפוצה" in p for p in ap.password_problems("password12345")))

    def test_none(self):
        self.assertTrue(ap.password_problems(None))


class RateLimit(unittest.TestCase):
    def test_blocks_after_limit_and_recovers(self):
        rl = ap.RateLimiter()
        for i in range(5):
            self.assertTrue(rl.allow("ip1", 5, 60, now=100 + i))
        self.assertFalse(rl.allow("ip1", 5, 60, now=106))
        self.assertTrue(rl.allow("ip1", 5, 60, now=100 + 61))     # החלון עבר

    def test_keys_are_independent(self):
        rl = ap.RateLimiter()
        for i in range(3):
            rl.allow("a", 3, 60, now=1)
        self.assertFalse(rl.allow("a", 3, 60, now=2))
        self.assertTrue(rl.allow("b", 3, 60, now=2))


class TwoFactor(unittest.TestCase):
    def test_required_by_default_in_production_only(self):
        self.assertTrue(ap.two_factor_required({"ENV": "production"}))
        self.assertFalse(ap.two_factor_required({}))
        self.assertFalse(ap.two_factor_required({"ENV": "development"}))

    def test_explicit_setting_wins(self):
        self.assertTrue(ap.two_factor_required({"REQUIRE_2FA": "true"}))
        self.assertFalse(ap.two_factor_required({"ENV": "production", "REQUIRE_2FA": "false"}))

    def test_enrollment_needed(self):
        self.assertTrue(ap.needs_2fa_enrollment(True, False))
        self.assertFalse(ap.needs_2fa_enrollment(True, True))
        self.assertFalse(ap.needs_2fa_enrollment(False, False))


GOOD_ENV = {"ENV": "production", "JWT_SECRET": "x" * 40, "FIELD_KEY": "k",
            "DATABASE_URL": "postgresql://u:p@h/db", "REGISTRATION_OPEN": "false",
            "ALLOWED_ORIGINS": "https://app.example.com"}


class ProductionConfig(unittest.TestCase):
    def test_dev_environment_never_blocks(self):
        self.assertEqual(ap.production_config_problems({}), ([], []))

    def test_good_production(self):
        self.assertEqual(ap.production_config_problems(GOOD_ENV), ([], []))

    def test_each_missing_secret_blocks(self):
        for key in ("JWT_SECRET", "FIELD_KEY"):
            env = dict(GOOD_ENV)
            del env[key]
            errors, _ = ap.production_config_problems(env)
            self.assertTrue(any(key in e for e in errors), key)

    def test_short_jwt_secret_blocks(self):
        env = dict(GOOD_ENV, JWT_SECRET="short")
        self.assertTrue(ap.production_config_problems(env)[0])

    def test_sqlite_blocks_in_production(self):
        env = dict(GOOD_ENV, DATABASE_URL="sqlite:///./x.db")
        self.assertTrue(any("SQLite" in e for e in ap.production_config_problems(env)[0]))

    def test_disabling_2fa_blocks(self):
        env = dict(GOOD_ENV, REQUIRE_2FA="false")
        self.assertTrue(any("2FA" in e for e in ap.production_config_problems(env)[0]))

    def test_warnings(self):
        env = dict(GOOD_ENV, REGISTRATION_OPEN="true", ALLOW_EXTERNAL_AI="true")
        del env["ALLOWED_ORIGINS"]
        _, warnings = ap.production_config_problems(env)
        self.assertEqual(len(warnings), 3)




import datetime as _dtt


class SessionsAndRoles(unittest.TestCase):
    NOW = _dtt.datetime(2026, 11, 12, 12, 0, 0)

    def ts(self, dt):
        return dt.replace(tzinfo=_dtt.timezone.utc).timestamp()

    def test_roles(self):
        self.assertTrue(ap.role_can("viewer", "read"))
        self.assertFalse(ap.role_can("viewer", "write"))
        self.assertTrue(ap.role_can("accountant", "write"))
        self.assertFalse(ap.role_can("accountant", "admin"))
        self.assertTrue(ap.role_can("owner", "admin"))
        self.assertFalse(ap.role_can("hacker", "read"))
        self.assertFalse(ap.role_can(None, "read"))
        self.assertFalse(ap.role_can("owner", "delete-everything"))

    def test_password_expiry(self):
        self.assertTrue(ap.password_expired(None, self.NOW))
        self.assertFalse(ap.password_expired(self.NOW - _dtt.timedelta(days=180), self.NOW))
        self.assertTrue(ap.password_expired(self.NOW - _dtt.timedelta(days=181), self.NOW))

    def test_token_problem(self):
        ok = {"ver": 3, "at": self.ts(self.NOW - _dtt.timedelta(hours=1))}
        self.assertIsNone(ap.token_problem(ok, 3, False, self.NOW))
        self.assertEqual(ap.token_problem(ok, 4, False, self.NOW), "revoked")
        self.assertEqual(ap.token_problem(ok, 3, True, self.NOW), "disabled")
        old = {"ver": 3, "at": self.ts(self.NOW - _dtt.timedelta(hours=12, minutes=1))}
        self.assertEqual(ap.token_problem(old, 3, False, self.NOW), "absolute_timeout")
        self.assertEqual(ap.token_problem({"ver": 3}, 3, False, self.NOW), "no_auth_time")
        self.assertEqual(ap.token_problem({"at": self.ts(self.NOW)}, 3, False, self.NOW), "revoked")

    def test_should_refresh(self):
        self.assertFalse(ap.should_refresh(self.ts(self.NOW - _dtt.timedelta(minutes=4)), self.NOW))
        self.assertTrue(ap.should_refresh(self.ts(self.NOW - _dtt.timedelta(minutes=5)), self.NOW))
        self.assertFalse(ap.should_refresh(None, self.NOW))


if __name__ == "__main__":
    unittest.main()
