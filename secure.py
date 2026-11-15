"""הצפנת שדות רגישים (ת"ז, חשבון בנק). המפתח בא ממשתנה סביבה FIELD_KEY ולא נשמר במסד."""
import hashlib
import hmac
import os


class KeyMissing(RuntimeError):
    pass


def _key() -> str:
    k = os.getenv("FIELD_KEY", "")
    if not k:
        raise KeyMissing("FIELD_KEY לא הוגדר ב-Render. בלעדיו לא נשמרים נתונים רגישים.")
    return k


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(_key().encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def lookup_hash(value: str) -> str:
    """גיבוב קבוע לחיפוש לפי ת"ז בלי לפענח כל שורה. HMAC עם המפתח - לא ניתן לשחזור בלעדיו."""
    return hmac.new(_key().encode(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def mask(value: str) -> str:
    return "*" * max(len(value) - 4, 0) + value[-4:]


def valid_israeli_id(value: str) -> bool:
    """ספרת ביקורת של ת"ז ישראלית."""
    v = value.strip()
    if not v.isdigit() or len(v) > 9:
        return False
    v = v.zfill(9)
    total = 0
    for i, ch in enumerate(v):
        n = int(ch) * (1 if i % 2 == 0 else 2)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


# ---------------------------------------------------------------------------
# הצפנה מעטפתית: מפתח נתונים נפרד לכל משרד (DEK), מוצפן במפתח הראשי (FIELD_KEY)
# ---------------------------------------------------------------------------
import json


def new_dek() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def wrap_dek(dek: bytes) -> str:
    return encrypt(dek.decode("ascii"))


def unwrap_dek(token: str) -> bytes:
    return decrypt(token).encode("ascii")


def seal(dek: bytes, obj) -> str:
    from cryptography.fernet import Fernet
    return Fernet(dek).encrypt(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")).decode("ascii")


def unseal(dek: bytes, token: str):
    from cryptography.fernet import Fernet
    return json.loads(Fernet(dek).decrypt(token.encode("ascii")).decode("utf-8"))


def seal_bytes(dek: bytes, data: bytes) -> bytes:
    """הצפנת קובץ גולמי (PDF/תמונה) במפתח של המשרד."""
    from cryptography.fernet import Fernet
    return Fernet(dek).encrypt(data)


def unseal_bytes(dek: bytes, token: bytes) -> bytes:
    from cryptography.fernet import Fernet
    return Fernet(dek).decrypt(token)
