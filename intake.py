"""
קליטת מסמכים: זיהוי סוג קובץ שהחשבת העלתה (תיבת העלאה אחת). נוצר 25.11.2026, ענף dev-components.

עקרונות:
1. זיהוי בלבד. הקובץ לא נקרא כאן לתוכן ולא מחושב ממנו דבר: אחרי הזיהוי הוא עובר לקורא המתאים (101 / נוכחות / אקסל),
   והחשבת מאשרת את מה שנקרא.
2. אם אי אפשר לזהות בביטחון, מחזירים "unknown" וסיבה. לא מנחשים.
3. קובץ PDF: מחפשים סימנים בטקסט העמוד הראשון. טקסט עברי ב-PDF לפעמים נשלף הפוך, לכן בודקים גם את הסימן ההפוך.
"""
import io

# סימנים: כל קבוצה היא ביטוי שאם מופיע נספר פעם אחת
FORM101_MARKERS = ("בקשה להקלה ולתיאום מס", "נקודות זיכוי", "הכנסות אחרות", "מספר תיק ניכויים", "כרטיס עובד", "0101", "תקנות מס הכנסה")
ATTENDANCE_MARKERS = ("כניסה", "יציאה", "שעות נוספות", "סה\"כ שעות", "נוכחות", "שעות עבודה", "הפסקה")
# כדי להכריע נדרשים לפחות 3 סימנים וגם פער של 2 לפחות בין הסוגים
MIN_HITS, MIN_GAP = 3, 2


def _hits(text, markers):
    rev = text[::-1]
    return sum(1 for m in markers if m in text or m in rev)


def classify_text(text):
    """מסווג לפי טקסט העמוד הראשון. מחזיר {"kind", "reason"}."""
    t = text or ""
    a, b = _hits(t, FORM101_MARKERS), _hits(t, ATTENDANCE_MARKERS)
    if a >= MIN_HITS and a - b >= MIN_GAP:
        return {"kind": "form101", "reason": f"נמצאו {a} סימנים של טופס 101"}
    if b >= MIN_HITS and b - a >= MIN_GAP:
        return {"kind": "attendance", "reason": f"נמצאו {b} סימנים של דוח נוכחות"}
    return {"kind": "unknown", "reason": f"לא ברור (סימני 101: {a}, סימני נוכחות: {b}); נא לבחור את סוג הקובץ"}


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
                text = pdf.pages[0].extract_text() or ""
        except Exception:
            return {"kind": "unknown", "reason": "לא ניתן לקרוא את ה-PDF"}
        if not text.strip():
            return {"kind": "unknown", "reason": "PDF סרוק (בלי טקסט): נא לבחור את סוג הקובץ"}
        return classify_text(text)
    return {"kind": "unknown", "reason": "סוג קובץ לא נתמך (מותר: PDF, אקסל, תמונה)"}
