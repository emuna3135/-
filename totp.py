"""TOTP לפי RFC 6238 (HMAC-SHA1, 6 ספרות, צעד 30 שניות). נכתב מחדש לפי התקן; נבדק מול וקטורי הבדיקה של התקן."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

DIGITS = 6
STEP = 30
WINDOW = 1  # סטייה מותרת של צעד אחד לכל כיוון


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret: str) -> bytes:
    s = secret.strip().replace(" ", "").upper()
    return base64.b32decode(s + "=" * (-len(s) % 8))


def code_at(secret: str, for_time: float, digits: int = DIGITS, step: int = STEP) -> str:
    counter = int(for_time // step)
    mac = hmac.new(_key(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    num = (struct.unpack(">I", mac[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(num).zfill(digits)


def match_step(secret: str, code: str, now: float = None):
    """מספר הצעד (counter) שהקוד מתאים לו, או None. משמש למניעת שימוש חוזר באותו קוד."""
    code = (code or "").strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    now = time.time() if now is None else now
    found = None
    for w in range(-WINDOW, WINDOW + 1):
        t = now + w * STEP
        if hmac.compare_digest(code_at(secret, t), code):
            found = int(t // STEP)
    return found


def verify(secret: str, code: str, now: float = None) -> bool:
    return match_step(secret, code, now) is not None


def otpauth_uri(secret: str, email: str, issuer: str = "AI Payroll") -> str:
    return (f"otpauth://totp/{quote(issuer)}:{quote(email)}?secret={secret}"
            f"&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}")
