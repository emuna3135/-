"""
מדיניות אימות ואבטחה: סיסמאות, הגבלת קצב, חובת 2FA ובדיקת הגדרות פרודקשן.
לוגיקה טהורה (בלי FastAPI ובלי מסד), נבדקת ב-test_authpolicy.py.
"""
import collections
import threading
import time

MIN_PASSWORD = 12

_COMMON = {
    "password1234", "password12345", "123456789012", "qwerty123456", "1q2w3e4r5t6y",
    "abcdefghijkl1", "israel123456", "admin1234567", "welcome12345",
}


def password_problems(password, email=""):
    """רשימת בעיות בסיסמה (ריקה = תקינה). הודעות בעברית להצגה למשתמש."""
    problems = []
    pw = password or ""
    if len(pw) < MIN_PASSWORD:
        problems.append(f"הסיסמה קצרה מדי (לפחות {MIN_PASSWORD} תווים)")
    if not any(c.isalpha() for c in pw) or not any(c.isdigit() for c in pw):
        problems.append("הסיסמה חייבת לכלול אותיות וגם ספרות")
    if len(set(pw)) < 6:
        problems.append("הסיסמה חוזרת על עצמה מדי")
    local = (email or "").split("@")[0].lower()
    if len(local) >= 4 and local in pw.lower():
        problems.append("הסיסמה לא יכולה לכלול את שם המשתמש")
    if pw.lower() in _COMMON:
        problems.append("הסיסמה נפוצה מדי")
    return problems


class RateLimiter:
    """
    חלון הזזה בזיכרון לפי מפתח (למשל כתובת IP + נתיב). נכון למופע שרת אחד.
    בפריסה עם כמה מופעים צריך מאגר משותף (Redis או מסד), ולכן זו הגנה בסיסית ולא סופית.
    """

    def __init__(self):
        self._hits = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()

    def allow(self, key, limit, window_seconds, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            if len(self._hits) > 10000:        # הגנה מגדילת זיכרון בלתי מוגבלת
                for k in [k for k, v in self._hits.items() if not v][:5000]:
                    self._hits.pop(k, None)
            return True


def two_factor_required(env):
    """2FA חובה כברירת מחדל בפרודקשן. אפשר לכבות רק במפורש ב-REQUIRE_2FA=false (פיתוח)."""
    explicit = str(env.get("REQUIRE_2FA", "")).strip().lower()
    if explicit in ("true", "false"):
        return explicit == "true"
    return str(env.get("ENV", "")).strip().lower() == "production"


def needs_2fa_enrollment(required, totp_enabled):
    """משתמש בלי 2FA כשהוא חובה מקבל טוקן מוגבל להקמת 2FA בלבד."""
    return bool(required) and not totp_enabled


def production_config_problems(env):
    """
    בדיקת הגדרות לפני עליית השרת. מחזיר (שגיאות חוסמות, אזהרות).
    בסביבה שאינה production: בלי שגיאות חוסמות (נוחות פיתוח).
    """
    errors, warnings = [], []
    prod = str(env.get("ENV", "")).strip().lower() == "production"
    if not prod:
        return errors, warnings
    jwt_secret = env.get("JWT_SECRET", "")
    if len(jwt_secret) < 32:
        errors.append("JWT_SECRET חסר או קצר מ-32 תווים")
    if not env.get("FIELD_KEY"):
        errors.append("FIELD_KEY חסר: אי אפשר להצפין נתונים")
    if str(env.get("DATABASE_URL", "sqlite")).startswith("sqlite"):
        errors.append("DATABASE_URL מצביע על SQLite: בפרודקשן נדרש מסד נתונים אמיתי")
    if str(env.get("REQUIRE_2FA", "true")).strip().lower() == "false":
        errors.append("REQUIRE_2FA=false אסור בפרודקשן")
    if str(env.get("REGISTRATION_OPEN", "true")).strip().lower() == "true":
        warnings.append("ההרשמה פתוחה: לסגור (REGISTRATION_OPEN=false) אחרי יצירת המשתמשים")
    if not env.get("ALLOWED_ORIGINS"):
        warnings.append("ALLOWED_ORIGINS ריק: רק אתר מאותו מקור יוכל לפנות ל-API")
    if str(env.get("ALLOW_EXTERNAL_AI", "false")).strip().lower() == "true":
        warnings.append("ALLOW_EXTERNAL_AI=true: נתונים עשויים לצאת לספק AI חיצוני. לוודא הסכם עיבוד נתונים")
    return errors, warnings


# ---------------------------------------------------------------------------
# סשנים, תוקף סיסמה ותפקידים (תקנות אבטחת מידע 8, 9; רמה בינונית: סיסמה עד 6 חודשים, ניתוק אוטומטי)
# ---------------------------------------------------------------------------
import datetime as _dt

PASSWORD_MAX_DAYS = 180        # תקנה 9(ב)(2)(א): בכל מקרה לא יותר מ-6 חודשים
IDLE_MINUTES = 30              # ניתוק אוטומטי באי-פעילות (תקנה 9(ב)(2)(ב))
ABSOLUTE_SESSION_HOURS = 12    # תקרה מוחלטת לסשן, גם עם פעילות רציפה
REFRESH_AFTER_MINUTES = 5      # חידוש טוקן בפעילות (טוקן חדש רק אם הישן בן 5 דקות ומעלה)

ROLES = ("owner", "accountant", "viewer")
_WRITE_ROLES = ("owner", "accountant")
_ADMIN_ROLES = ("owner",)


def role_can(role, action):
    """action: read | write | admin. תפקיד לא מוכר = אין הרשאה (ברירת מחדל חוסמת)."""
    if role not in ROLES:
        return False
    if action == "read":
        return True
    if action == "write":
        return role in _WRITE_ROLES
    if action == "admin":
        return role in _ADMIN_ROLES
    return False


def password_expired(changed_at, now=None, max_days=PASSWORD_MAX_DAYS):
    """changed_at חסר (משתמש ותיק בלי רישום) נחשב כפג תוקף: חייב לבחור סיסמה חדשה."""
    if changed_at is None:
        return True
    now = _dt.datetime.utcnow() if now is None else now
    return (now - changed_at) > _dt.timedelta(days=max_days)


def token_problem(claims, user_token_version, user_disabled, now=None):
    """
    בדיקות שרת על טוקן שכבר עבר אימות חתימה. מחזיר None אם תקין, אחרת קוד סיבה.
    claims: sub, ver (גרסת טוקן), at (זמן הכניסה המקורי, epoch שניות).
    """
    if user_disabled:
        return "disabled"
    if claims.get("ver") != user_token_version:
        return "revoked"
    at = claims.get("at")
    if not isinstance(at, (int, float)):
        return "no_auth_time"
    now_ts = (_dt.datetime.utcnow() if now is None else now).replace(tzinfo=_dt.timezone.utc).timestamp()
    if now_ts - at > ABSOLUTE_SESSION_HOURS * 3600:
        return "absolute_timeout"
    return None


def should_refresh(iat, now=None):
    """האם להנפיק טוקן חדש בתשובה (חלון הזזה של אי-פעילות)."""
    if not isinstance(iat, (int, float)):
        return False
    now_ts = (_dt.datetime.utcnow() if now is None else now).replace(tzinfo=_dt.timezone.utc).timestamp()
    return now_ts - iat >= REFRESH_AFTER_MINUTES * 60
