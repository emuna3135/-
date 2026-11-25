"""
קובץ תשלומים במבנה מס"ב (זיכוי שכר לחשבונות עובדים). נוצר 25.11.2026, ענף dev-components.
המערכת לא משדרת: היא מייצרת קובץ שרואת החשבון מעלה בעצמה לבנק/מס"ב.

מקור: "מפרט טכני לביצוע תשלומים באמצעות מס"ב", מרכז סליקה בנקאי בע"מ (מס"ב), כפי שמפורסם באתר בנק לאומי
(leumi.co.il/.../Payments_Niss_Acc.pdf, נקרא 25.11.2026). רשומה 128 תווים + CR LF. רשומות: כותרת K, תנועה 1, סיכום 5.

מה שהמפרט לא קובע (לכן מסומן "נדרש אימות מול מס"ב/הבנק לפני שידור", ואינו עפ"י החוק):
- קידוד עברית (המפרט: ASCII בלבד) ואופן כתיבת שם הזכאי ("מימין לשמאל, מותאם להדפסה"); ברירת המחדל כאן cp862 וסדר הפוך (ויזואלי) לפי נוהג, לא לפי המפרט;
- אורך רשומת סוף הקובץ (תשיעיות) - כאן 128 תווים;
- תחילת שדה הריק ברשומת הסיכום (בפרסום "63 X" בעמדה 66, מתיישב עם 128 תווים);
- טבלאות בנק/סניף/סוג חשבון: אינן במפרט, ולכן לא נבדקות מעבר לאורך.
"""
from decimal import Decimal as D, ROUND_HALF_UP
import datetime

import secure

REC_LEN = 128
CRLF = "\r\n"
NOTES = [
    "קידוד עברית ואופן כתיבת שם הזכאי אינם מוגדרים במפרט מס\"ב: נדרש אימות מול מס\"ב/הבנק לפני שידור",
    "רשומת סוף הקובץ (תשיעיות) באורך 128 לפי הנחה, המפרט אינו קובע אורך",
    "טבלאות קודי בנק וסניף אינן במפרט ולא נבדקו",
]


def _num(v, width, name):
    s = str(v)
    if not s.isdigit() or len(s) > width:
        raise ValueError(f"{name}: נדרשות עד {width} ספרות")
    return s.zfill(width)


def _cents(amount):
    a = D(str(amount))
    if a <= 0:
        raise ValueError("סכום חייב להיות גדול מאפס")
    c = (a * 100).quantize(D("1"), rounding=ROUND_HALF_UP)
    if c != a * 100:
        raise ValueError("סכום עם יותר משתי ספרות אחרי הנקודה: נדרש סכום מדויק לאגורה")
    return int(c)


def _text(s, width, reverse):
    s = " ".join(str(s).split())
    if reverse:
        s = s[::-1]
    return s[:width].ljust(width) if not reverse else s[-width:].rjust(width) if len(s) > width else s.rjust(width)


def _pad(s):
    assert len(s) == REC_LEN, len(s)
    return s


def build(payments, institution_code, sending_code, institution_name, pay_date, created=None,
          reverse_names=True, encoding="cp862"):
    """
    payments: [{bank, branch, account, id_number, name, amount, ref, (period YYMM)}]
    מחזיר (bytes, summary dict). שגיאה בכל תנועה -> ValueError עם רשימת כל השגיאות (לא קובץ חלקי).
    """
    created = created or datetime.date.today()
    inst = _num(institution_code, 8, "קוד מוסד")
    send = _num(sending_code, 5, "מוסד שולח")
    errs = []
    rows = []
    for i, p in enumerate(payments, 1):
        try:
            idn = str(p["id_number"])
            if not secure.valid_israeli_id(idn):
                raise ValueError("ת.ז לא תקינה")
            bank = _num(p["bank"], 2, "בנק")
            branch = _num(p["branch"], 3, "סניף")
            acct = _num(p["account"], 9, "חשבון")
            cents = _cents(p["amount"])
            if cents >= 10 ** 13:
                raise ValueError("סכום גדול מדי לשדה")
            ref = _num(p.get("ref", i), 20, "אסמכתא")
            period = str(p.get("period") or "00000000")
            if not (period.isdigit() and len(period) == 8):
                raise ValueError("תקופה: 8 ספרות (YYMMYYMM) או ריק")
            name = _text(p["name"], 16, reverse_names)
            rows.append((bank, branch, acct, ref, cents, idn, name, period))
        except (ValueError, KeyError) as e:
            errs.append(f"תנועה {i}: {e}")
    if not payments:
        errs.append("אין תנועות")
    if errs:
        raise ValueError("; ".join(errs))
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))   # בנק, סניף, חשבון, אסמכתא (סדר המפתחות לפי המפרט §2.2, בקירוב; סוג חשבון תמיד 0000)
    d = pay_date.strftime("%y%m%d")
    c = created.strftime("%y%m%d")
    hname = _text(institution_name, 30, reverse_names)
    out = [_pad("K" + inst + "00" + d + "0" + "001" + "0" + c + send + "000000" + hname + " " * 56 + "KOT")]
    total = 0
    for bank, branch, acct, ref, cents, idn, name, period in rows:
        total += cents
        out.append(_pad("1" + inst + "00" + "000000" + bank + branch + "0000" + acct + "0" + idn.zfill(9)
                        + name + str(cents).zfill(13) + ref + period + "000" + "006" + "0" * 18 + "  "))
    out.append(_pad("5" + inst + "00" + d + "0" + "001" + str(total).zfill(15) + "0" * 15 + str(len(rows)).zfill(7)
                    + "0" * 7 + " " * 63))
    out.append("9" * REC_LEN)
    text = "".join(r + CRLF for r in out)
    data = text.encode(encoding)
    return data, {"count": len(rows), "total": D(total) / 100, "notes": list(NOTES), "encoding": encoding,
                  "status": "נדרש אימות מול מס\"ב/הבנק לפני שידור"}


def verify(data, encoding="cp862"):
    """בדיקה עצמית של קובץ שנוצר: אורך, סוגי רשומות, איזון סכום וכמות (§2.3). מחזיר רשימת בעיות (ריקה = תקין)."""
    problems = []
    text = data.decode(encoding)
    lines = text.split(CRLF)
    if lines and lines[-1] == "":
        lines.pop()
    if any(len(l) != REC_LEN for l in lines):
        problems.append("רשומה שאורכה אינו 128")
    if not lines or lines[0][0] != "K" or lines[0][125:128] != "KOT":
        problems.append("חסרה רשומת כותרת")
    if len(lines) < 4 or lines[-1] != "9" * REC_LEN or lines[-2][0] != "5":
        problems.append("חסרה רשומת סיכום או סוף קובץ")
        return problems
    tx = [l for l in lines if l[0] == "1"]
    tot = lines[-2]
    if sum(int(l[61:74]) for l in tx) != int(tot[21:36]):
        problems.append("סכום התנועות אינו שווה לסיכום")
    if len(tx) != int(tot[51:58]) or len(tx) == 0:
        problems.append("מספר התנועות אינו שווה לסיכום")
    return problems
