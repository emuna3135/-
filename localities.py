"""יישובים מוטבים (סעיף 11 לפקודה) לשנת 2026.
מקור ראשוני: לוח עזר לחישוב מס הכנסה ממשכורת ושכר עבודה לחודש ינואר 2026 ואילך, רשות המסים, פרק ח'
(נקרא בדפדפן; 491 יישובים; כל זוג שיעור/תקרה נבדק מול טבלת פרק ה'). קובץ הנתונים: localities_2026.data.
הנחה: שיעור x הכנסה חייבת מיגיעה אישית עד התקרה (השנתית). יישום חודשי: תקרה x משקל חודשים/12 (מצטבר)."""
import os
from decimal import Decimal as D

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "localities_2026.data")
LOCALITIES_YEAR = 2026
_cache = None
# הנחות נוספות מלוח העזר 2026, פרק ה' (לא ברשימת פרק ח'). תנאי הזכאות (הכנסה שהופקה באזור אילת/חבל אילות) באחריות חשב השכר.
EILAT = "אילת (חוק אזור סחר חופשי, הכנסה שהופקה באזור אילת/חבל אילות)"
_EXTRA = {EILAT: (D("10") / 100, D("268560"))}


def _load():
    global _cache
    if _cache is None:
        data = {}
        with open(_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                name, rate, cap = line.split("|")
                data[" ".join(name.split())] = (D(rate) / 100, D(cap))
        data.update(_EXTRA)
        _cache = data
    return _cache


def names():
    return sorted(_load())


def lookup(name, tax_year):
    """מחזיר (rate, cap) או None. רק שנת 2026 קיימת בידינו; שנה אחרת -> None (ידני)."""
    if tax_year != LOCALITIES_YEAR or not isinstance(name, str):
        return None
    return _load().get(" ".join(name.split()))
