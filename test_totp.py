import base64
import unittest
import totp

# וקטורי הבדיקה של RFC 6238 (נספח B), SHA-1, סוד ASCII "12345678901234567890", 8 ספרות
SECRET = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
VECTORS = {59: "94287082", 1111111109: "07081804", 1111111111: "14050471",
           1234567890: "89005924", 2000000000: "69279037", 20000000000: "65353130"}


class Rfc6238(unittest.TestCase):
    def test_vectors(self):
        for t, expected in VECTORS.items():
            self.assertEqual(totp.code_at(SECRET, t, digits=8), expected, t)

    def test_verify_window(self):
        c = totp.code_at(SECRET, 1000)
        self.assertTrue(totp.verify(SECRET, c, now=1000))
        self.assertTrue(totp.verify(SECRET, c, now=1030))
        self.assertFalse(totp.verify(SECRET, c, now=1000 + 90))

    def test_bad_input(self):
        for bad in ("", None, "12345", "abcdef", "1234567"):
            self.assertFalse(totp.verify(SECRET, bad, now=1000))

    def test_new_secret_and_uri(self):
        s = totp.new_secret()
        self.assertTrue(totp.verify(s, totp.code_at(s, 5000), now=5000))
        self.assertIn("secret=" + s, totp.otpauth_uri(s, "a@b.com"))


class Replay(unittest.TestCase):
    def test_match_step_returns_counter(self):
        c = totp.code_at(SECRET, 1000)
        self.assertEqual(totp.match_step(SECRET, c, now=1000), 1000 // 30)
        self.assertEqual(totp.match_step(SECRET, c, now=1030), 1000 // 30)   # בתוך החלון
        self.assertIsNone(totp.match_step(SECRET, c, now=1000 + 90))
        self.assertIsNone(totp.match_step(SECRET, "12345", now=1000))

    def test_step_monotonic_rule(self):
        # הכלל ב-main_api: קוד מתקבל רק אם הצעד שלו גדול מהצעד האחרון שנוצל
        last = totp.match_step(SECRET, totp.code_at(SECRET, 1000), now=1000)
        same = totp.match_step(SECRET, totp.code_at(SECRET, 1000), now=1000)
        later = totp.match_step(SECRET, totp.code_at(SECRET, 1060), now=1060)
        self.assertFalse(same > last)
        self.assertTrue(later > last)


if __name__ == "__main__":
    unittest.main()
