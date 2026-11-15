"""
הצעות לאישור חשב: העלאת מסמכים (טופס 101, טופס 106, הנחיות חדשות), חילוץ, אימות ואישור.

עקרונות (לפי ההנחיות של המשתמשת):
  1. שום דבר שחולץ ממסמך לא נכנס לשימוש לפני אישור מפורש של חשב השכר.
  2. ה-AI (אם יופעל) רק מציע. כל נתון שחולץ עובר סינון לפי סכמה קבועה (רשימה לבנה של שדות וסוגים),
     כך שהוראות מוסתרות בתוך קובץ לא יכולות להפוך לשדה או לפעולה.
  3. האימות הוא קוד דטרמיניסטי שלנו (למשל נקודות זיכוי מחושבות ב-card.py), לא ה-AI.
  4. ברירת המחדל לא פונה לשום ספק חיצוני. מחלץ אחר חייב להיות מוגדר במפורש ומאושר (ALLOW_EXTERNAL_AI).
  5. כללי חשב (הנחיות) לא יורדים מתחת לרצפת החוק. כשרצפה לא ידועה: נדרש אישור מפורש, וזה מסומן.
  6. אם משהו לא ברור: שגיאה או "נדרש טיפול ידני", אף פעם לא ניחוש.

הקובץ לוגיקה טהורה (בלי מסד נתונים ובלי FastAPI), ונבדק ב-test_proposals.py.
"""
import datetime
import hashlib
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

import card
import secure

KIND_FORM101 = "form101"
KIND_FORM106 = "form106"
KIND_GUIDELINE = "guideline"
KINDS = (KIND_FORM101, KIND_FORM106, KIND_GUIDELINE)

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
SUPERSEDED = "superseded"

MAX_FILE_BYTES = 10 * 1024 * 1024
_MAGIC = {"pdf": b"%PDF-", "png": b"\x89PNG\r\n\x1a\n", "jpg": b"\xff\xd8\xff"}

INCOME_TYPES = ("main", "additional")
GUIDELINE_BASES = ("collective_agreement", "extension_order", "personal_contract", "practice", "other")

MONEY_MAX = Decimal("1000000000")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ---------------------------------------------------------------------------
# קבצים
# ---------------------------------------------------------------------------
def sniff_file(data: bytes):
    """סוג הקובץ לפי תחילת התוכן (לא לפי שם או Content-Type שהלקוח שלח). None = לא מותר."""
    for ext, magic in _MAGIC.items():
        if data.startswith(magic):
            return ext
    return None


def check_upload(data: bytes):
    """(סוג, None) אם תקין, או (None, הודעת שגיאה)."""
    if not data:
        return None, "הקובץ ריק"
    if len(data) > MAX_FILE_BYTES:
        return None, "הקובץ גדול מדי (מעל 10MB)"
    ext = sniff_file(data)
    if ext is None:
        return None, "מותרים רק קבצי PDF, PNG או JPG"
    return ext, None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# סכמות: רשימה לבנה של שדות. כל מה שלא ברשימה נזרק (ומדווח).
# ---------------------------------------------------------------------------
def _clean_str(v, max_len):
    if not isinstance(v, str):
        raise ValueError("חייב להיות טקסט")
    s = _CTRL.sub("", v).strip()
    if not s:
        raise ValueError("ריק")
    if len(s) > max_len:
        raise ValueError(f"ארוך מדי (מעל {max_len} תווים)")
    return s


def _clean_int(v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, str)):
        raise ValueError("חייב להיות מספר שלם")
    try:
        n = int(v)
    except ValueError:
        raise ValueError("חייב להיות מספר שלם")
    if not lo <= n <= hi:
        raise ValueError(f"מחוץ לטווח {lo}-{hi}")
    return n


def _clean_bool(v):
    if not isinstance(v, bool):
        raise ValueError("חייב להיות true או false")
    return v


def _clean_date(v):
    if isinstance(v, datetime.date):
        return v.isoformat()
    if not isinstance(v, str):
        raise ValueError("חייב להיות תאריך YYYY-MM-DD")
    try:
        return datetime.date.fromisoformat(v.strip()).isoformat()
    except ValueError:
        raise ValueError("תאריך לא תקין (YYYY-MM-DD)")


def _clean_money(v):
    if isinstance(v, bool) or not isinstance(v, (int, float, str, Decimal)):
        raise ValueError("חייב להיות סכום")
    try:
        d = Decimal(str(v).strip())
    except InvalidOperation:
        raise ValueError("סכום לא תקין")
    if not d.is_finite() or d < 0 or d > MONEY_MAX:
        raise ValueError("סכום מחוץ לטווח")
    return str(d.quantize(Decimal("0.01")))


def _clean_year_list(v):
    if not isinstance(v, list) or len(v) > 20:
        raise ValueError("חייב להיות רשימה של שנות לידה (עד 20)")
    return [_clean_int(x, 1990, 2100) for x in v]


def _clean_degrees(v):
    if not isinstance(v, list) or len(v) > 3:
        raise ValueError("חייב להיות רשימת תארים (עד 3)")
    out = []
    for d in v:
        if not isinstance(d, dict):
            raise ValueError("תואר לא תקין")
        kind = d.get("kind")
        if kind not in ("first", "second", "profession"):
            raise ValueError("סוג תואר לא נתמך")
        out.append({"kind": kind, "study_years": _clean_int(d.get("study_years"), 1, 12),
                    "completion_year": _clean_int(d.get("completion_year"), 1990, 2100)})
    return out


def _clean_locality(v):
    import localities
    if not isinstance(v, str) or " ".join(v.split()) not in localities.names():
        raise ValueError("יישוב לא מופיע ברשימת היישובים המוטבים 2026 (לוח עזר רשות המסים)")
    return " ".join(v.split())


FAMILY_FLAGS = ("teen", "benef", "widower", "nomesh", "yesmesh", "niptar", "mezonut")


def _clean_flags(v):
    if not isinstance(v, list) or len(v) > len(FAMILY_FLAGS):
        raise ValueError("חייב להיות רשימת דגלי מצב משפחתי")
    out = []
    for x in v:
        if x not in FAMILY_FLAGS:
            raise ValueError("דגל לא מוכר: " + str(x)[:30])
        if x not in out:
            out.append(x)
    return out


def _enum(options):
    def f(v):
        if v not in options:
            raise ValueError("ערך לא מוכר")
        return v
    return f


# (שם שדה): (מנקה, חובה)
SCHEMAS = {
    KIND_FORM101: {
        "id_number": (lambda v: _clean_str(v, 9), True),
        "tax_year": (lambda v: _clean_int(v, 2000, 2100), True),
        "signed_on": (_clean_date, False),
        "income_type": (_enum(INCOME_TYPES), True),
        "other_income": (_clean_bool, True),
        "other_credits_claimed": (_clean_bool, True),
        "manual_points": (_clean_money, False),
        "marital": (_enum(("single", "married", "divorced", "widowed", "separated")), False),
        "custody_birth_years": (_clean_year_list, False),
        "noncustody_birth_years": (_clean_year_list, False),
        "family_flags": (_clean_flags, False),
        "aliyah_date": (_clean_date, False),
        "discharge_date": (_clean_date, False),
        "soldier_full_service": (_clean_bool, False),
        "degrees": (_clean_degrees, False),
        "disabled_children": (lambda v: _clean_int(v, 0, 20), False),
        "alimony_ex_spouse": (_clean_bool, False),
        "locality": (_clean_locality, False),
        "reserve_days_prev_year": (lambda v: _clean_int(v, 0, 366), False),
    },
    KIND_FORM106: {
        "tax_year": (lambda v: _clean_int(v, 2000, 2100), True),
        "gross_total": (_clean_money, True),
        "tax_withheld": (_clean_money, True),
        "ni_withheld": (_clean_money, False),
        "employer_name": (lambda v: _clean_str(v, 120), False),
    },
    KIND_GUIDELINE: {
        "topic": (lambda v: _clean_str(v, 80), True),
        "value": (lambda v: _clean_str(v if isinstance(v, str) else str(v), 80), True),
        "unit": (lambda v: _clean_str(v, 30), False),
        "effective_from": (_clean_date, True),
        "effective_to": (_clean_date, False),
        "basis": (_enum(GUIDELINE_BASES), True),
        "source_text": (lambda v: _clean_str(v, 2000), True),
    },
}


def coerce(kind, raw):
    """
    מסנן קלט גולמי (מהחילוץ או מהחשב) לפי הסכמה.
    מחזיר (שדות נקיים, שגיאות {שדה: הודעה}, התעלמות [שדות שלא בסכמה]).
    שדה לא מוכר לעולם לא נכנס, גם אם נראה תקין.
    """
    if kind not in SCHEMAS:
        raise ValueError(f"סוג מסמך לא מוכר: {kind}")
    schema = SCHEMAS[kind]
    raw = raw or {}
    clean, errors = {}, {}
    for name, (fn, required) in schema.items():
        if name not in raw or raw[name] in (None, ""):
            if required:
                errors[name] = "שדה חובה חסר"
            continue
        try:
            clean[name] = fn(raw[name])
        except ValueError as e:
            errors[name] = str(e)
    ignored = sorted(k for k in raw if k not in schema)
    return clean, errors, ignored


# ---------------------------------------------------------------------------
# אימות דטרמיניסטי
# ---------------------------------------------------------------------------
# רצפות חוק לנושאי הנחיות. ריק בכוונה: אף רצפה עוד לא אומתה מול נוסח החוק
# (למשל טבלת חופשה שנתית: סתירה בין הקורס לאתר, ראו סיכום). נושא ללא רצפה = "לא נבדק".
LAW_FLOORS = {}


@dataclass
class Validation:
    errors: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    checks: dict = field(default_factory=dict)
    floor_status: str = "n/a"      # n/a | ok | not_checked

    def ok(self):
        return not self.errors

    def to_dict(self):
        return {"errors": dict(self.errors), "warnings": list(self.warnings),
                "checks": dict(self.checks), "floor_status": self.floor_status}


def validate(kind, clean, ctx=None, today=None):
    """
    clean: פלט של coerce. ctx: נתוני העובד הידועים (id_number, is_resident, gender) לטופס 101.
    מחזיר Validation. שגיאות חוסמות אישור, אזהרות לא.
    """
    ctx = ctx or {}
    today = today or datetime.date.today()
    v = Validation()
    if kind == KIND_FORM101:
        idn = clean.get("id_number")
        if idn is not None and not secure.valid_israeli_id(idn):
            v.errors["id_number"] = "ספרת ביקורת של ת.ז לא תקינה"
        if idn is not None and ctx.get("id_number") not in (None, idn):
            v.errors["id_number"] = "ת.ז בטופס לא תואמת לעובד שנבחר"
        signed = clean.get("signed_on")
        year = clean.get("tax_year")
        if signed:
            sd = datetime.date.fromisoformat(signed)
            if sd > today:
                v.warnings.append("תאריך החתימה בעתיד: לבדוק מול הטופס")
            if year is not None and abs(sd.year - year) > 1:
                v.warnings.append("תאריך החתימה רחוק משנת המס: לבדוק מול הטופס")
        else:
            v.warnings.append("אין תאריך חתימה: ללא חתימה הטופס נחשב כלא קיים בחישוב המס")
        if "is_resident" in ctx and "gender" in ctx:
            y = dict(clean)
            if y.get("manual_points") is not None:
                y["manual_points"] = float(y["manual_points"])
            pts, status, note = card.points_from_form101(year if year is not None else today.year,
                                                         ctx["is_resident"], ctx["gender"], y)
            v.checks["credit_points"] = {"points": pts, "status": status, "note": note}
            if pts is None:
                v.warnings.append("נקודות הזיכוי לא נגזרות אוטומטית: נדרשת הזנה ידנית של הסך")
        else:
            v.warnings.append("חסרים נתוני עובד (תושבות/מין): נקודות הזיכוי לא נבדקו")
    elif kind == KIND_FORM106:
        if "gross_total" in clean and "tax_withheld" in clean:
            from decimal import Decimal as D
            if D(clean["tax_withheld"]) > D(clean["gross_total"]):
                v.warnings.append("המס שנוכה גבוה מההכנסה: לבדוק מול הטופס")
        v.warnings.append("טופס 106 נשמר לשימוש עתידי: הוא עדיין לא משפיע על חישוב המס המצטבר")
    elif kind == KIND_GUIDELINE:
        topic = clean.get("topic")
        floor = LAW_FLOORS.get(topic)
        if floor is None:
            v.floor_status = "not_checked"
            v.warnings.append("אין רצפת חוק מאומתת לנושא הזה: נדרש אישור מפורש שהכלל לא נבדק מול החוק")
        else:
            v.floor_status = "ok"
        ef, et = clean.get("effective_from"), clean.get("effective_to")
        if ef and et and datetime.date.fromisoformat(et) < datetime.date.fromisoformat(ef):
            v.errors["effective_to"] = "תאריך סיום לפני תאריך התחלה"
        v.warnings.append("כלל חשב נשמר בנפרד ולא משנה חישובים עד שיחובר ידנית לנושא מוגדר")
    else:
        raise ValueError(f"סוג מסמך לא מוכר: {kind}")
    return v


# ---------------------------------------------------------------------------
# מכונת מצבים
# ---------------------------------------------------------------------------
class TransitionError(Exception):
    pass


def decide(status, action, validation, confirm=False, floor_ack=False):
    """
    מחזיר את הסטטוס החדש או זורק TransitionError. רק הצעה ממתינה אפשר להכריע.
    אישור דורש: confirm מפורש, אפס שגיאות אימות, ובהנחיה בלי רצפת חוק מאומתת גם floor_ack.
    """
    if status != PENDING:
        raise TransitionError("אפשר להכריע רק הצעה שממתינה לאישור")
    if action == "reject":
        return REJECTED
    if action != "approve":
        raise TransitionError("פעולה לא מוכרת")
    if not confirm:
        raise TransitionError("נדרש אישור מפורש של חשב השכר (confirm)")
    if validation.errors:
        raise TransitionError("יש שגיאות אימות: לתקן לפני אישור")
    if validation.floor_status == "not_checked" and not floor_ack:
        raise TransitionError("נדרש אישור שהכלל לא נבדק מול רצפת החוק (floor_ack)")
    return APPROVED


def is_usable(status):
    """רק הצעה מאושרת נכנסת לשימוש."""
    return status == APPROVED


# ---------------------------------------------------------------------------
# מחלץ מסמכים (pluggable). ברירת מחדל: בלי AI ובלי פנייה החוצה.
# ---------------------------------------------------------------------------
class ExtractorNotConfigured(RuntimeError):
    pass


@dataclass
class Extraction:
    fields: dict
    notes: list
    source: str


class NoAIExtractor:
    """לא מחלץ דבר. החשב מזין את השדות ידנית. כך אין שום יציאה של נתונים לספק חיצוני."""
    name = "manual"

    def extract(self, kind, data, filename):
        return Extraction({}, ["לא הוגדר מחלץ אוטומטי: נדרשת הזנה ידנית של השדות"], self.name)


def external_ai_allowed(env=None):
    env = os.environ if env is None else env
    return str(env.get("ALLOW_EXTERNAL_AI", "false")).lower() == "true"


def get_extractor(name=None, env=None):
    env = os.environ if env is None else env
    name = (name or env.get("EXTRACTOR", "none")).lower()
    if name in ("none", "manual", ""):
        return NoAIExtractor()
    if name == "anthropic":
        import ai_extractor
        return ai_extractor.AnthropicForm101Extractor(env=env)   # זורק ExtractorNotConfigured אם לא מאושר
    raise ExtractorNotConfigured(f"המחלץ '{name}' לא מוגדר. עד ההחלטה על ספק, נשארים בהזנה ידנית")


def build_proposal(kind, raw_fields, extraction_source, extraction_notes, ctx=None, today=None):
    """
    בונה את תוכן ההצעה: שדות נקיים, שגיאות סכמה, התעלמות ותוצאת אימות.
    שגיאות סכמה נכללות באימות, ולכן חוסמות אישור.
    """
    clean, schema_errors, ignored = coerce(kind, raw_fields)
    val = validate(kind, clean, ctx, today)
    val.errors.update(schema_errors)
    return {
        "kind": kind,
        "fields": clean,
        "ignored_fields": ignored,
        "extraction": {"source": extraction_source, "notes": list(extraction_notes)},
        "validation": val.to_dict(),
    }, val


def form101_to_employee_year(fields: dict) -> dict:
    """שדות טופס 101 מאושרים -> התוכן ש-EmployeeYear שומר (תואם Form101In). בלי ניחוש: חסר = ברירת מחדל שקולה ל'לא סומן'."""
    return {"signed_on": fields.get("signed_on"),
            "income_type": fields.get("income_type", "main"),
            "other_income": bool(fields.get("other_income", False)),
            "other_credits_claimed": bool(fields.get("other_credits_claimed", False)),
            "manual_points": (float(fields["manual_points"]) if fields.get("manual_points") is not None else None),
            "marital": fields.get("marital"),
            "custody_birth_years": list(fields.get("custody_birth_years") or []),
            "noncustody_birth_years": list(fields.get("noncustody_birth_years") or []),
            "family_flags": list(fields.get("family_flags") or []),
            "aliyah_date": fields.get("aliyah_date"),
            "discharge_date": fields.get("discharge_date"),
            "soldier_full_service": fields.get("soldier_full_service"),
            "degrees": list(fields.get("degrees") or []),
            "disabled_children": fields.get("disabled_children"),
            "alimony_ex_spouse": fields.get("alimony_ex_spouse"),
            "locality": fields.get("locality"),
            "reserve_days_prev_year": fields.get("reserve_days_prev_year")}
