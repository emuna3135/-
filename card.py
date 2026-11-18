"""
נקודות זיכוי ושיטת מס מנתוני טופס 101. שוחזר 11.11.2026 אחרי החלפת סביבה (הקובץ המקורי אבד),
על פי: שימושי הקובץ ב-main_api.py/proposals.py, בדיקות test_proposals, דוחות הקוד, ותקנות ניכוי ממשכורת 1993.
כל מה שלא נגזר מחוק -> None/MANUAL ("לא מנחשים").
"""
from decimal import Decimal as D  # noqa: F401  (עקביות עם שאר המודולים)

from engine import BY_LAW, MANUAL, VERIFIED

POINTS_RESIDENT = 2.25   # סעיף 34 לפקודה: תושב ישראל
POINTS_WOMAN_EXTRA = 0.5  # סעיף 36 לפקודה: אישה (2.75 סה"כ, מאומת מול תלושים והסימולטור)


# נקודות זיכוי בגין ילדים. מקור: פקודת מס הכנסה §66(ג)(4)-(5) ו-§40(ב)(1), כנוסחם בחוק סיוע להורים לילדים
# עד גיל שלוש (תיקוני חקיקה), התשפ"ד-2024 (ס"ח 3184, 20.3.2024; תחילה 1.1.2024; ללא הוראת סיום) ובנוסח נבו 27.9.2026.
# גיל = שנת המס פחות שנת הלידה. "שנת בגרות" = גיל 18 (§40(ב)(3)).
CHILD_ROLES = ("mother", "father", "single_parent")


def child_points_for_year(tax_year, birth_year, role):
    """נקודות הילד לשנת המס, לפי תפקיד ההורה. 0 אם הילד לא בטווח. role לא מוכר -> ValueError."""
    if role not in CHILD_ROLES:
        raise ValueError("תפקיד הורה לא מוכר")
    age = int(tax_year) - int(birth_year)
    if age < 0 or age > 18:
        return D(0)
    if age == 0:
        return D("2.5")
    if age <= 2:
        return D("4.5")
    if age == 3:
        return D("3.5")
    if age <= 5:
        return D("2.5")
    if age <= 17:
        return D(1) if role == "father" else D(2)      # §66(ג)(5)(ג) לגבר: 1; §66(ג)(4)(א) לאישה ו-§40(ב)(1) לחד-הורי: 2
    return D(0) if role == "father" else D("0.5")       # שנת בגרות: לגבר אין שורה בחוק


def _age_bucket(tax_year, birth_year):
    age = int(tax_year) - int(birth_year)
    if age < 0 or age > 18:
        return None
    return "0" if age == 0 else "1-2" if age <= 2 else "3" if age == 3 else "4-5" if age <= 5 else "6-17" if age <= 17 else "18"


# צירופים (תפקיד, טווח גיל) שנבדקו מול סימולטור רשות המסים (12.11.2026, ראו DATA_LEDGER ב324). רק הם מסומנים מאומתים.
SIMULATOR_YEARS = {2026}   # הסימולטור מאפשר רק את שנת המס הנוכחית; שנים אחרות: לפי חוק בלבד
SIMULATOR_VERIFIED = {("mother", "6-17"), ("mother", "1-2"), ("father", "1-2"), ("mother", "0"), ("mother", "3")}


def child_credit_points(tax_year, birth_years, role):
    """סך נקודות הילדים. מחזיר (נקודות Decimal, סטטוס, הערה). לא כולל נקודות קיצבה (ב"ל) ולא תוספות §40(ב)(1ב),(2)."""
    total = sum((child_points_for_year(tax_year, b, role) for b in birth_years), D(0))
    buckets = [_age_bucket(tax_year, b) for b in birth_years]
    in_range = [b for b in buckets if b is not None]
    verified = int(tax_year) in SIMULATOR_YEARS and all((role, b) in SIMULATOR_VERIFIED for b in in_range)
    if verified:
        note = ("נקודות ילדים לפי §66(ג)/§40(ב) כנוסחם בחוק 2024 (ס\"ח 3184), ומאומתות מול סימולטור רשות המסים לצירופי "
                "תפקיד/גיל שנבדקו. לא נכלל: נקודות קיצבה מביטוח לאומי, ותוספות להורה חד-הורי (§40(ב)(1ב),(2))")
        return total, VERIFIED, note
    note = ("נקודות ילדים לפי §66(ג)/§40(ב) כנוסחם בחוק 2024 (ס\"ח 3184): לפי חוק, לא נבדק מול סימולטור רשות המסים "
            "לצירוף תפקיד/גיל זה. לא נכלל: נקודות קיצבה מביטוח לאומי, ותוספות להורה חד-הורי (§40(ב)(1ב),(2))")
    return total, BY_LAW, note


def credit_points(is_resident, gender, other_credits_claimed=False, manual_points=None,
                  tax_year=None, child_birth_years=None, parent_role=None):
    """מחזיר (נקודות, סטטוס, הערה). זיכויים מעבר לתושב/ה ולאישה -> הזנה ידנית, פרט לילדים כשנמסרו
    tax_year, child_birth_years ו-parent_role (mother/father/single_parent)."""
    if manual_points is not None:
        return float(manual_points), MANUAL, "סך נקודות הוזן ידנית (לא נגזר אוטומטית)"
    if child_birth_years:
        if other_credits_claimed:
            return None, MANUAL, "סומנו זיכויים נוספים מעבר לילדים: נדרשת הזנה ידנית של הסך"
        if tax_year is None or parent_role is None:
            return None, MANUAL, "חסרים שנת מס או תפקיד הורה לחישוב נקודות ילדים: נדרשת הזנה ידנית"
        if not is_resident or gender not in ("F", "M"):
            return None, MANUAL, "תושבות או מין לא מוגדרים: נקודות הזיכוי לא נגזרות אוטומטית"
        try:
            kids, kids_status, kids_note = child_credit_points(tax_year, child_birth_years, parent_role)
        except ValueError as e:
            return None, MANUAL, str(e)
        base = POINTS_RESIDENT + (POINTS_WOMAN_EXTRA if gender == "F" else 0)
        return float(D(str(base)) + kids), kids_status, f"בסיס {base} + ילדים {kids}. {kids_note}"
    if other_credits_claimed:
        return None, MANUAL, "סומנו זיכויים נוספים: נדרשת הזנה ידנית של הסך"
    if not is_resident:
        return None, MANUAL, "לא תושב ישראל: נקודות הזיכוי לא נגזרות אוטומטית"
    if gender == "F":
        return POINTS_RESIDENT + POINTS_WOMAN_EXTRA, VERIFIED, "תושבת ישראל + אישה (2.25 + 0.5); מאומת מול תלושים וסימולטור רשות המסים"
    if gender == "M":
        return POINTS_RESIDENT, VERIFIED, "תושב ישראל (סעיפים 34, 36): מאומת מול סימולטור רשות המסים (12.11.2026, גבר נשוי, 2.25)"
    return None, MANUAL, "מין לא מוגדר: נקודות הזיכוי לא נגזרות אוטומטית"


def tax_mode(present, income_type="main", other_income=False, other_income_credit=None):
    """
    מחזיר (שיטה, הערה). 'cumulative' = ניכוי לפי לוח הניכויים; 'no_coordination' = שיעור מרבי (47%).
    other_income_credit (סעיף "הכנסות אחרות" בטופס 101, הערות 7-8): 'here' = "אבקש לקבל נקודות זיכוי ומדרגות מס כנגד הכנסתי זו"
    -> לוח הניכויים הרגיל. 'elsewhere' / לא סומן (None) עם הכנסה אחרת -> שיעור מרבי, אלא אם הוגש תיאום מס (fixed_rate).
    מקור: טופס 101 הרשמי (רשות המסים) + תקנה 5(א); אישור רואת חשבון (18.11.2026).
    """
    if not present:
        return "no_coordination", "אין טופס 101 חתום לשנה: ניכוי בשיעור המרבי (תקנה 5(א))"
    if income_type == "additional":
        return "no_coordination", "משרה נוספת: ניכוי בשיעור המרבי (תקנה 5(א)) אלא אם הוגש אישור תיאום מס"
    if other_income:
        if other_income_credit == "here":
            return "cumulative", "הוצהרה הכנסה אחרת ובחרו נקודות זיכוי ומדרגות כנגדה (טופס 101, הערות 7-8): ניכוי לפי לוח הניכויים"
        return "no_coordination", "הוצהרה הכנסה אחרת בלי בחירה בנקודות זיכוי ומדרגות כנגדה (או שהן מתקבלות בהכנסה האחרת): שיעור מרבי (טופס 101, הערות 7-8; תקנה 5(א))"
    return "cumulative", "משרה עיקרית עם טופס 101 חתום"


# ---------------------------------------------------------------------------
# נקודות זיכוי על בסיס מצב משפחתי מלא. מקור: פקודת מס הכנסה §§34-40ב, 66(ג), וסימולטור רשות המסים
# (secapp.taxes.gov.il/srsimulatorNZ, הורץ אוטומטית ב-12.11.2026, שנת מס 2026; ראו simulator_results_2026.py).
# מה שלא נבדק בסימולטור או שתוצאתו לא מוסברת -> MANUAL. לא כולל נקודות קיצבה (ב"ל) ונקודות מחוץ למצב משפחתי.
# ---------------------------------------------------------------------------
_T_MOTHER = {"0": D("2.5"), "1-2": D("4.5"), "3": D("3.5"), "4-5": D("2.5"), "6-17": D(2), "18": D("0.5")}
_T_FATHER_MARRIED = dict(_T_MOTHER, **{"6-17": D(1), "18": D(0)})
_T_NONCUST = {"0": D("2.5"), "1-2": D("4.5"), "3": D("3.5"), "4-5": D("2.5"), "6-17": D(1), "18": D(0)}
_SPECIAL = {"nomesh", "yesmesh", "niptar", "mezonut"}
_KNOWN_FLAGS = _SPECIAL | {"teen", "benef", "widower"}


def family_credit_points(tax_year, gender, married, custody_birth_years=(), noncust_birth_years=(), flags=()):
    """מחזיר (נקודות|None, סטטוס, הערה). flags: teen, benef, widower, nomesh, yesmesh, niptar, mezonut."""
    flags = set(flags or ())
    custody_birth_years = list(custody_birth_years or ())
    noncust_birth_years = list(noncust_birth_years or ())

    def manual(why):
        return None, MANUAL, "מצב משפחתי שלא נבדק או לא מוסבר בסימולטור: " + why + ". נדרשת הזנה ידנית"

    if gender not in ("F", "M"):
        return manual("מין לא מוגדר")
    unknown = flags - _KNOWN_FLAGS
    if unknown:
        return manual("דגל לא נתמך: " + ", ".join(sorted(unknown)))
    special = flags & _SPECIAL
    if len(special) > 1:
        return manual("צירוף כמה מצבי חיים בנפרד/הורה יחיד/מזונות")
    if married and special:
        return manual("נשוי/ה יחד עם מצב של חיים בנפרד/הורה יחיד/מזונות")
    if not married and ({"benef", "widower"} & flags):
        return manual("יחיד מוטב או נשואה לאלמן ללא נישואים")
    if "widower" in flags and gender != "F":
        return manual("נשואה לאלמן רלוונטי רק לאישה")
    if custody_birth_years and not (married or ({"nomesh", "yesmesh", "niptar"} & flags)):
        return manual("ילדים בחזקה ללא נישואים וללא מצב חיים מוגדר (הסימולטור לא סופר אותם)")
    if custody_birth_years and "mezonut" in flags:
        return manual("ילדים בחזקה יחד עם תשלום מזונות")
    if noncust_birth_years and "mezonut" not in flags:
        return manual("ילדים שלא בחזקה ללא דגל תשלום מזונות")
    kids_custody = len(custody_birth_years)
    pts = D("2.25") + (D("0.5") if gender == "F" else D(0))
    if "teen" in flags:
        pts += 1
    if "benef" in flags:
        pts += D("0.5") if kids_custody else D(1)
    if special & {"nomesh", "niptar", "mezonut"}:
        pts += 1
    table = _T_FATHER_MARRIED if (married and gender == "M") else _T_MOTHER
    for b in custody_birth_years:
        k = _age_bucket(tax_year, b)
        if k is not None:
            pts += table[k]
            if "niptar" in flags:
                pts += _T_NONCUST[k]
    for b in noncust_birth_years:
        k = _age_bucket(tax_year, b)
        if k is not None:
            pts += _T_NONCUST[k]
    year_ok = int(tax_year) in SIMULATOR_YEARS
    status = VERIFIED if year_ok else BY_LAW
    note = ("נקודות לפי מצב משפחתי (פקודה §§34-40ב, 66(ג)); " +
            ("מאומת מול סימולטור רשות המסים (12.11.2026)" if year_ok else "שנה שלא נבדקה בסימולטור: לפי חוק") +
            ". לא כולל נקודות קיצבה (ב\"ל)")
    return float(pts), status, note


MARITAL = ("single", "married", "divorced", "widowed", "separated")


def _points_base(tax_year, is_resident, gender, y):
    """נקודות זיכוי מנתוני טופס 101 מאושרים (y = תוכן EmployeeYear). מחזיר (נקודות|None, סטטוס, הערה).
    בלי נתוני משפחה: בסיס בלבד. עם נתוני משפחה: family_credit_points. כל מה שלא נתמך -> MANUAL."""
    y = y or {}
    manual_points = y.get("manual_points")
    if manual_points is not None:
        return float(manual_points), MANUAL, "סך נקודות הוזן ידנית (לא נגזר אוטומטית)"
    if y.get("other_credits_claimed"):
        return None, MANUAL, "סומנו זיכויים נוספים (עולה, חייל משוחרר, תואר, נכות וכד'): נדרשת הזנה ידנית של הסך"
    if not is_resident:
        return None, MANUAL, "לא תושב ישראל: נקודות הזיכוי לא נגזרות אוטומטית"
    custody = list(y.get("custody_birth_years") or [])
    noncust = list(y.get("noncustody_birth_years") or [])
    flags = list(y.get("family_flags") or [])
    if not (custody or noncust or flags):
        return credit_points(is_resident, gender)
    marital = y.get("marital")
    if marital not in MARITAL:
        return None, MANUAL, "נמסרו ילדים או מצב משפחתי מיוחד בלי מצב משפחתי: נדרשת הזנה ידנית של הסך"
    return family_credit_points(tax_year, gender, marital == "married", custody, noncust, flags)


# ---- זיכויים חודשיים לפי הפקודה: עולה (§35) וחייל משוחרר (§39א) ----
# נקודות "שנתיות-מקבילות" לחודש נתון = 12 x השבר החודשי שבחוק.
# עולה: אומת מול עלון רשות המסים לעולים (נקודה/3/2/1 בשנות הזכאות). חודש העלייה נספר כחודש 1 (הנחה: לא אומתה במקור רשמי).
# חייל משוחרר: מהנוסח של §39א בלבד (לא אומת מול הנחיית רשות המסים).


def _months_between(y1, m1, y2, m2):
    return (y2 - y1) * 12 + (m2 - m1)


def olim_points(aliyah_date, year, month):
    """aliyah_date: datetime.date. מחזיר (נקודות, סטטוס, הערה).
    לוח לפי §35 לפקודה ולפי מכתב רשות המסים למעסיקים (תיקון 262): עולה מ-1.1.2022: 1/12 לחודש ב-12 החודשים הראשונים,
    1/4 ב-18 הבאים, 1/6 ב-12 הבאים, 1/12 ב-12 הבאים (54 חודשים). עולה לפני 1.1.2022: 1/4 ב-18 החודשים הראשונים,
    1/6 ב-12 הבאים, 1/12 ב-12 הבאים (42 חודשים). הערכים כאן "שנתיים-מקבילים" (שבר החודש x 12)."""
    import datetime
    k = _months_between(aliyah_date.year, aliyah_date.month, year, month) + 1
    if k < 1:
        return 0.0, BY_LAW, "החודש לפני העלייה: אין זיכוי עולה"
    if aliyah_date >= datetime.date(2022, 1, 1):
        schedule, total = [(12, 1.0), (30, 3.0), (42, 2.0), (54, 1.0)], 54
    else:
        schedule, total = [(18, 3.0), (30, 2.0), (42, 1.0)], 42
    pts = None
    for upto, value in schedule:
        if k <= upto:
            pts = value
            break
    if pts is None:
        return 0.0, BY_LAW, f"חלפו {total} חודשים מהעלייה: אין זיכוי עולה"
    return pts, BY_LAW, (f"זיכוי עולה: חודש {k} מ-{total} (חודש העלייה נספר כחודש 1; לוח לפי §35 ומכתב רשות המסים; "
                         "היעדרויות מהארץ, זכאות קודמת וזיכוי בן/בת זוג לא נבדקו)")


def discharged_soldier_points(discharge_date, full_service, year, month):
    """full_service: True = גבר 23 חודשי שירות סדיר מלאים לפחות / אישה 22; False = פחות. None -> ידני.
    מקור: gov.il (שו"ת רשות המסים) ואתר האגף לחיילים משוחררים: 36 חודשים לאחר חודש השחרור; 2 נקודות / נקודה אחת (שחרור מ-2013)."""
    if full_service is None:
        return None, MANUAL, "אורך השירות הסדיר לא ידוע: נדרשת הזנה ידנית"
    k = _months_between(discharge_date.year, discharge_date.month, year, month)
    if 1 <= k <= 36:
        return (2.0 if full_service else 1.0), BY_LAW, (
            f"זיכוי חייל משוחרר: חודש {k} מ-36 לפי §39א (אומת מול gov.il ואתר האגף לחיילים משוחררים; חל על הכנסה מיגיעה אישית)")
    return 0.0, BY_LAW, "מחוץ ל-36 החודשים שלאחר חודש השחרור: אין זיכוי"


def points_from_form101(tax_year, is_resident, gender, y, month=None):
    """בסיס + משפחה + זיכויים נוספים: עולה/חייל משוחרר (חודשיים, דורשים month), תואר/מקצוע ומילואים (שנתיים).
    כל מה שלא ברור או לא נתמך -> MANUAL."""
    import datetime
    y = y or {}
    base = _points_base(tax_year, is_resident, gender, y)
    ali, dis = y.get("aliyah_date"), y.get("discharge_date")
    degs, rd = y.get("degrees") or [], y.get("reserve_days_prev_year")
    dk = y.get("disabled_children")
    alim = y.get("alimony_ex_spouse")
    if base[0] is None or not (ali or dis or degs or rd or dk or alim):
        return base
    total, notes, statuses = float(base[0]), [base[2]], [base[1]]

    def add(res):
        nonlocal total
        p, st, n = res
        if p is None:
            return False
        total += p
        statuses.append(st)
        notes.append(n)
        return True

    def _d(v):
        return v if isinstance(v, datetime.date) else datetime.date.fromisoformat(v)

    if degs:
        r = degree_points(degs, tax_year)
        if not add(r):
            return r
    if rd:
        r = reserve_points(rd, tax_year)
        if not add(r):
            return r
    if dk:
        r = disabled_children_points(dk)
        if not add(r):
            return r
    if alim:
        return None, MANUAL, ("זיכוי מזונות לבן/בת זוג לשעבר (נשואים בשנית): לפי הפקודה (§40א, נקרא בסבב 16) נקודת זיכוי אחת בצירוף פסק דין; "
                              "סימולטור רשות המסים (12.11.2026) לא הוסיף נקודה בהרצה. הסתירה בין החוק לסימולטור לא הוכרעה: נדרשת הזנה ידנית של הסך")
    if ali or dis:
        if month is None:
            notes.append("תוספות עולה/חייל משוחרר יחושבו לפי חודש החישוב (בתצוגה זו לא נכללות)")
        else:
            try:
                if ali:
                    add(olim_points(_d(ali), tax_year, month))
                if dis:
                    r = discharged_soldier_points(_d(dis), y.get("soldier_full_service"), tax_year, month)
                    if not add(r):
                        return r
            except (ValueError, TypeError):
                return None, MANUAL, "תאריך עלייה/שחרור לא תקין: נדרשת הזנה ידנית"
    status = MANUAL if MANUAL in statuses else (BY_LAW if BY_LAW in statuses else statuses[0])
    return total, status, " | ".join(n for n in notes if n)


# ---- תואר/מקצוע (§40ג, §40ד, §40ה) ומילואים (§39ב): נקודות שנתיות, לפי נוסח הפקודה (נבו 27.9.2026) ----
DEGREE_KINDS = ("first", "second", "profession")
_DEG_CAP = {"first": 3, "second": 2, "profession": 3}
_DEG_PTS = {"first": 1.0, "second": 0.5, "profession": 1.0}


def degree_points(degrees, tax_year):
    """degrees: רשימת {kind, study_years, completion_year}. נקודות מתחילות בשנה שאחרי שנת הסיום,
    למשך min(שנות לימוד, תקרה) שנות מס. תואר ראשון/שני לצד לימודי מקצוע: §40ה דורש בחירה -> ידני.
    תואר שלישי, התמחות (§40ג(ג1)) ושני תארים מאותו סוג -> ידני. אישור סיום (טופס 119) הוא תנאי: באחריות חשב השכר."""
    if not degrees:
        return 0.0, BY_LAW, ""
    kinds = [d.get("kind") for d in degrees]
    if any(k not in DEGREE_KINDS for k in kinds) or len(set(kinds)) != len(kinds):
        return None, MANUAL, "סוג תואר לא נתמך או כפול (תואר שלישי/התמחות/כפילות): נדרשת הזנה ידנית"
    if "profession" in kinds and ("first" in kinds or "second" in kinds):
        return None, MANUAL, "תואר אקדמי יחד עם לימודי מקצוע: §40ה דורש בחירה של הנישום, נדרשת הזנה ידנית"
    total, notes = 0.0, []
    for d in degrees:
        k, n, c = d["kind"], d.get("study_years"), d.get("completion_year")
        if not (isinstance(n, int) and not isinstance(n, bool) and n >= 1 and isinstance(c, int) and not isinstance(c, bool)):
            return None, MANUAL, "שנות לימוד או שנת סיום חסרות: נדרשת הזנה ידנית"
        if c < 2023:
            return None, MANUAL, ("סיום לימודים לפני 2023: הכללים שונים (2014-2022: נקודה בשנה אחת לפי בחירה; לימודי מקצוע לפי שנת הסיום): "
                                  "נדרשת הזנה ידנית")
        years = min(n, _DEG_CAP[k])
        if c < tax_year <= c + years:
            total += _DEG_PTS[k]
            notes.append(f"זיכוי {k}: שנה {tax_year - c} מ-{years}")
    return total, BY_LAW, ("; ".join(notes) + " (לפי חוק; אישור סיום לימודים/טופס 119 לא נבדק)") if notes else ""


def reserve_points(days_prev_year, tax_year=None):
    """זיכוי מילואים כלוחם לפי ימי שירות בשנה הקודמת. הלוח (30-39: 0.5; 40-49: 0.75; 50-54: 1; ועוד רבע לכל 5 ימים, עד 4)
    הוא הוראת השעה לשנות המס 2026 ו-2027 (חוק בספר החוקים 23.11.2025; מכתב רשות המסים למעסיקים 16.12.2025, אומת מול הטבלה שבו).
    משנת 2028 יחול נוסח קבוע אחר, ולשנות קודמות אין זיכוי לפי חוק זה: tax_year מחוץ ל-2026/2027 -> ידני.
    נדרש אישור צה"ל על שירות כלוחם."""
    if days_prev_year is None:
        return 0.0, BY_LAW, ""
    d = days_prev_year
    if not isinstance(d, int) or isinstance(d, bool) or d < 0:
        return None, MANUAL, "מספר ימי מילואים לא תקין: נדרשת הזנה ידנית"
    if tax_year is not None and int(tax_year) not in (2026, 2027):
        return None, MANUAL, "זיכוי מילואים כלוחם מחושב כאן רק לשנות המס 2026-2027 (הוראת שעה); שנה אחרת: הזנה ידנית"
    if d < 30:
        pts = 0.0
    elif d < 40:
        pts = 0.5
    elif d < 50:
        pts = 0.75
    else:
        pts = min(4.0, 1.0 + 0.25 * ((d - 50) // 5))
    note = f"זיכוי מילואים: {d} ימי לוחם בשנה הקודמת (לוח 2026-2027 לפי מכתב רשות המסים; נדרש אישור צה\"ל על שירות כלוחם)"
    return pts, BY_LAW, note


def disabled_children_points(count):
    """§45(א): שתי נקודות זיכוי בעבור כל ילד משותק, עיוור או עם מוגבלות שכלית-התפתחותית.
    §45(ג): בלי כפל עם זיכוי הוצאות מוסד (§44) - באחריות חשב השכר. תנאי זכאות נוספים (§45(ד)) לא נבדקו."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0 or count > 20:
        return None, MANUAL, "מספר ילדים עם מוגבלות לא תקין: נדרשת הזנה ידנית"
    if count == 0:
        return 0.0, BY_LAW, ""
    return 2.0 * count, BY_LAW, f"זיכוי ילד עם מוגבלות §45: {count} ילדים x 2 (לפי חוק; אישור ותנאים לפי §45(ד) לא נבדקו)"
