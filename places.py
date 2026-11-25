"""
בדיקת שם יישוב (כתובת העובד) מול הרשימה הרשמית של שמות היישובים בישראל.

מקור: האקדמיה ללשון העברית, "רשימת שמות היישובים בישראל" (פורסמה 27.6.2022; מבוססת על רשימון ועדת השמות הממשלתית
והלשכה המרכזית לסטטיסטיקה). הקובץ places_2022.data = שמות בכתיב מלא, שורה לכל יישוב.
שונה מ-localities.py: שם הוא רשימת יישובים מוטבים להטבת מס בלבד; כאן רשימת כל היישובים.

עקרונות: המערכת לא מתקנת בעצמה. התאמה מדויקת = תקין. הבדל בכתיב או התאמה קרובה = הצעה לאישור החשב.
יישוב שנוסד אחרי 2022 לא יופיע ברשימה: לכן "לא נמצא" הוא אזהרה בלבד, לא חסימה.
"""
import difflib
import os
import re

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "places_2022.data")
SOURCE = "האקדמיה ללשון העברית, רשימת שמות היישובים בישראל (27.6.2022)"
_NIQQUD = re.compile(r"[֑-ׇ]")
_PUNCT = re.compile(r"[\s\-־–—'\"’׳״`()]")
_cache = {}


def _norm(s):
    s = _NIQQUD.sub("", s or "")
    s = re.sub(r"\([^)]*\)", "", s)           # (שבט), (איחוד) וכו'
    return _PUNCT.sub("", s)


def _skel(s):
    """שלד: בלי אותיות קריאה (ו, י) ובלי כפל, כדי ש'הרצליה' ו'הרצלייה' ייחשבו אותו שם."""
    return re.sub(r"[וי]", "", _norm(s))


def _load():
    if "names" not in _cache:
        with open(_PATH, encoding="utf-8") as f:
            names = [ln.strip() for ln in f if ln.strip()]
        exact, skel, alias = {}, {}, {}
        for n in names:
            exact.setdefault(_norm(n), n)
            skel.setdefault(_skel(n), n)
            for part in re.split(r"\s*[–—]\s*", n):      # "תל־אביב–יפו" -> "תל־אביב", "יפו"
                if part != n:
                    alias.setdefault(_norm(part), n)
        _cache.update(names=names, exact=exact, skel=skel, alias=alias)
    return _cache


def names():
    return list(_load()["names"])


def check(name):
    """
    {"status": exact|variant|suggest|unknown|empty, "canonical": שם רשמי או None, "suggestions": [...]}
    exact: תואם לשם הרשמי. variant: אותו שם בכתיב אחר (מוצע, לא מוחלף). suggest: דומה (מאר יעקב -> באר יעקב). unknown: לא נמצא.
    """
    c = _load()
    n = _norm(name)
    if not n:
        return {"status": "empty", "canonical": None, "suggestions": []}
    if n in c["exact"]:
        return {"status": "exact", "canonical": c["exact"][n], "suggestions": []}
    if n in c["alias"]:
        return {"status": "variant", "canonical": c["alias"][n], "suggestions": [c["alias"][n]]}
    s = _skel(name)
    if s in c["skel"]:
        return {"status": "variant", "canonical": c["skel"][s], "suggestions": [c["skel"][s]]}
    close = difflib.get_close_matches(s, list(c["skel"]), n=3, cutoff=0.75)
    if close:
        return {"status": "suggest", "canonical": None, "suggestions": [c["skel"][k] for k in close]}
    return {"status": "unknown", "canonical": None, "suggestions": []}


def warning_for(name):
    """הודעת אזהרה לחשב, או None אם השם תקין."""
    r = check(name)
    if r["status"] in ("exact", "empty"):
        return None
    if r["status"] in ("variant", "suggest"):
        return f"היישוב '{name}' לא כתוב כמו ברשימה הרשמית. האם התכוונת: {' / '.join(r['suggestions'])}? (לא תוקן אוטומטית)"
    return f"היישוב '{name}' לא נמצא ברשימת שמות היישובים ({SOURCE}). ייתכן יישוב חדש או שגיאת קריאה: לבדוק מול הטופס"
