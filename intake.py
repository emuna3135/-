"""
קליטת מסמכים: זיהוי סוג קובץ שהחשבת העלתה (תיבת העלאה אחת). נוצר 25.11.2026, ענף dev-components.

עקרונות:
1. זיהוי בלבד. הקובץ לא נקרא כאן לתוכן ולא מחושב ממנו דבר: אחרי הזיהוי הוא עובר לקורא המתאים (101 / נוכחות / אקסל),
   והחשבת מאשרת את מה שנקרא.
2. אם אי אפשר לזהות בביטחון, מחזירים "unknown" וסיבה. לא מנחשים.
3. קובץ PDF: מחפשים סימנים בטקסט כל העמודים (עד 6). טקסט עברי ב-PDF לפעמים נשלף הפוך, לכן בודקים גם את הסימן ההפוך.
"""
import io

# סימני זיהוי של טופס 101: שמות סעיפים ושדות מנספח א' של רשות המסים (כללים והוראות להפקת טופס 101 אלקטרוני לשנת 2026, 12.1.2026).
# מנרמלים (בלי רווחים, גרשיים וסימני פיסוק) לפני ההשוואה.
FORM101_MARKERS = (
    "כרטיס עובד", "בקשה להקלה ולתיאום מס", "פרטי המעסיק", "מספר תיק ניכויים", "פרטי העובד", "מספר זהות",
    "שם משפחה", "שם פרטי", "תאריך לידה", "תאריך עלייה", "מצב משפחתי", "תושב ישראל", "חבר קיבוץ",
    "חבר בקופת חולים", "פרטים על ילדי", "בחזקתך", "קצבת ילדים", "הכנסותיי ממעסיק זה", "משכורת חודש",
    "משכורת חלקית", "שכר עבודה", "תאריך תחילת העבודה", "הכנסות אחרות", "נקודות זיכוי ומדרגות מס",
    "קרן השתלמות", "בן/בת הזוג", "אני מבקש פטור או זיכוי ממס", "עולה חדש", "חייל משוחרר", "הצהרה",
)
FORM101_MIN = 12        # לפחות 12 מתוך 30 סימנים שונים
# מסמך הוראות/הסבר ל-101 (לא טופס ממולא): מכיל את אותן מילים ולכן חייבים להוציא אותו
INSTRUCTION_MARKERS = ("נספח א", "הוראות בדבר אופן מילוי", "חובה/רשות", "בתי תוכנה", "טופס 101 אלקטרוני לשנת")
ATTENDANCE_MARKERS = ("כניסה", "יציאה", "שעות נוספות", "סה\"כ שעות", "נוכחות", "שעות עבודה", "הפסקה", "שעת כניסה", "שעת יציאה")
ATTENDANCE_MIN = 4
MAX_PAGES = 6


def _norm(t):
    return "".join(ch for ch in (t or "") if ch.isalnum())


def _has(n, rev, m):
    k = _norm(m)
    return bool(k) and (k in n or k in rev)


def _hits(text, markers, loose=False):
    """סימן נספר אם הביטוי מופיע (בכיוון כלשהו), או אם כל מילה שלו מופיעה בנפרד (כשה-PDF מערבב כיווני כתיבה בתוך משפט)."""
    n = _norm(text)
    rev = n[::-1]
    c = 0
    for m in markers:
        words = m.replace("/", " ").split()
        if _has(n, rev, m) or (loose and len(words) > 1 and all(_has(n, rev, w) for w in words)):
            c += 1
    return c


def classify_text(text):
    """מסווג לפי טקסט (כל עמודי הקובץ). מחזיר {"kind", "reason"}."""
    t = text or ""
    ins = _hits(t, INSTRUCTION_MARKERS)
    if ins >= 2:
        return {"kind": "unknown", "reason": "נראה מסמך הוראות או הסבר ולא טופס ממולא; נא לבחור את סוג הקובץ"}
    a, b = _hits(t, FORM101_MARKERS, loose=True), _hits(t, ATTENDANCE_MARKERS)
    if a >= FORM101_MIN and a > b:
        return {"kind": "form101", "reason": f"נמצאו {a} מתוך {len(FORM101_MARKERS)} סימני זיהוי של טופס 101"}
    if b >= ATTENDANCE_MIN and b >= a:
        return {"kind": "attendance", "reason": f"נמצאו {b} סימנים של דוח נוכחות"}
    return {"kind": "unknown", "reason": f"לא ברור (סימני 101: {a} מתוך {len(FORM101_MARKERS)}, נוכחות: {b}); נא לבחור את סוג הקובץ"}


def classify(data, filename=""):
    """data: bytes. מחזיר {"kind": form101|attendance|excel|image|unknown, "reason": str}."""
    if not data:
        return {"kind": "unknown", "reason": "הקובץ ריק"}
    if data.startswith(b"PK\x03\x04"):
        if (filename or "").lower().endswith((".xlsx", ".xlsm")):
            return {"kind": "excel", "reason": "קובץ אקסל"}
        return {"kind": "unknown", "reason": "קובץ דחוס שאינו אקסל מוכר"}
    if data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff":
        return {"kind": "image", "reason": "תמונה: אי אפשר לזהות סוג בלי קריאה בבינה מלאכותית; נא לבחור את סוג הקובץ"}
    if data.startswith(b"%PDF"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                if not pdf.pages:
                    return {"kind": "unknown", "reason": "PDF בלי עמודים"}
                text = "\n".join((p.extract_text() or "") for p in pdf.pages[:MAX_PAGES])
        except Exception:
            return {"kind": "unknown", "reason": "לא ניתן לקרוא את ה-PDF"}
        if not text.strip():
            return {"kind": "unknown", "reason": "PDF סרוק (בלי טקסט): נא לבחור את סוג הקובץ"}
        return classify_text(text)
    return {"kind": "unknown", "reason": "סוג קובץ לא נתמך (מותר: PDF, אקסל, תמונה)"}
