"""Form 126 (annual employer report to the Tax Authority) – fixed-width writer.

Source: the Tax Authority's "מבנה רשומות דוח 126" specification (tax year 2025),
supplied by the user. Each record is 964 data columns followed by CRLF.

Status of this module:
  * records 10 (leading), 30 (summary) and 50 (monthly) are specified here
    field by field and checked for contiguity 1..964;
  * record 20 (employee) has its full column layout (see form126_rec20.py);
  * record 40 (reconciliation with the monthly 102 reports) is specified too.
    Names of the 30-series fields are shortened; the printed specification
    governs the meaning of each value.

Things the specification leaves open are never guessed. The caller must pass
them explicitly:
  * ``encoding``      - the spec allows "ASCII NEW CODE" (cp862) or
                        "ASCII WINDOWS" (cp1255);
  * ``hebrew_visual`` - whether Hebrew text is stored reversed (visual order).
Money values are written as the integers the caller supplies; converting
shekels/agorot is the caller's job.

The authority validates the file after submission. The accountant must run the
file through the authority's own validation before sending it.
"""
from __future__ import annotations

from dataclasses import dataclass

RECORD_WIDTH = 964
EOL = "\r\n"


@dataclass(frozen=True)
class Field:
    no: str            # field number as printed in the spec ("14א'" etc.)
    name: str
    start: int         # first column, 1-based
    end: int           # last column, inclusive
    kind: str          # "N" numeric, "A" alphanumeric, "E" e-mail (case kept), "F" filler
    const: str | None = None   # fixed value mandated by the spec

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def _f(no, name, start, end, kind="N", const=None):
    return Field(no, name, start, end, kind, const)


SPEC: dict[str, list[Field]] = {
    "10": [
        _f("1", "מספר תיק ניכויים", 1, 9),
        _f("2", "מספר אגיד", 10, 11),
        _f("3", "סוג רשומה", 12, 13, const="10"),
        _f("4", "שנת מס מדווחת", 14, 17),
        _f("5", "אפסים", 18, 26, const="0" * 9),
        _f("6", "מספר אגידים", 27, 28),
        _f("7", "מספר עובדים באגיד", 29, 33),
        _f("8", "FILLER", 34, 34, "F"),
        _f("9", "שם המעביד", 35, 52, "A"),
        _f("10", "ריק", 53, 95, "F"),
        _f("11", "מספר טלפון של המעביד", 96, 104),
        _f("12", "מעביד באזור סחר חופשי אילת", 105, 105, "A"),
        _f("13", "מעביד פטור/חייב במס מעסיקים", 106, 106),
        _f("14", "כתובת המפעל – רחוב", 107, 125, "A"),
        _f("15", "כתובת המפעל – מספר", 126, 130, "A"),
        _f("16", "כתובת המפעל – עיר", 131, 150, "A"),
        _f("17", "כתובת המפעל – מיקוד", 151, 155),
        _f("18", "כתובת למשלוח דואר – רחוב", 156, 174, "A"),
        _f("19", "כתובת למשלוח דואר – מספר", 175, 179, "A"),
        _f("20", "כתובת למשלוח דואר – עיר", 180, 199, "A"),
        _f("21", "כתובת למשלוח דואר – מיקוד", 200, 204),
        _f("22", "תיבת דואר", 205, 209),
        _f("23", "מספר פקס", 210, 218),
        _f("23א'", "ביטוח לאומי בלבד", 219, 220),
        _f("23ב'", "ביטוח לאומי בלבד", 221, 222),
        _f("23ג'", "ריק", 223, 877, "F"),
        _f("23ד'", "מספר תיק ניכויים בביטוח לאומי", 878, 888),
        _f("24", "ריק", 889, 959, "F"),
        _f("25", "מספר מפעל", 960, 964),
    ],
    "30": [
        _f("1", "מספר תיק ניכויים", 1, 9),
        _f("2", "מספר אגיד", 10, 11),
        _f("3", "סוג רשומה", 12, 13, const="30"),
        _f("4", "שנת מס", 14, 17),
        _f("5", "אפסים", 18, 26, const="0" * 9),
        _f("6", "FILLER", 27, 31, "F"),
        _f("7", "סה\"כ תשלומים מהם נוכה מס רגיל", 32, 43),
        _f("8", "שכר עבודה במשמרות במפעל תעשייתי ממנו נוכה מס מופחת", 44, 55),
        _f("9", "סכום ההפרשה לתגמולים, לקצבה או לקרן השתלמות ממנו נוכה מס", 56, 67),
        _f("10", "סה\"כ תשלומים הפטורים ממס מעסיקים", 68, 79),
        _f("11", "סה\"כ תשלומים ושווי הנחות הפטורים מניכוי מס", 80, 91),
        _f("12", "סה\"כ משכורת ותשלומים", 92, 103),
        _f("13", "סה\"כ מס הכנסה שנוכה", 104, 115),
        _f("14", "מספר רשומות פרט מסוג 20 בקובץ", 116, 121),
        _f("14א'", "ריק", 122, 125, "F"),
        _f("15", "תשלומים חייבים בדמי ביטוח לאומי עד המקסימום", 126, 137),
        _f("16", "תשלומים פטורים מדמי ביטוח לאומי", 138, 149),
        _f("17", "תשלומים פטורים מדמי ביטוח לאומי מעל המקסימום", 150, 161),
        _f("18", "ברוטו הפרשים שנים קודמות", 162, 173),
        _f("19", "תשלומים של שכר נוסף עד המקסימום", 174, 185),
        _f("20", "סה\"כ דמי ביטוח לאומי שנוכו מהעובדים", 186, 197),
        _f("21", "סה\"כ דמי ביטוח בריאות שנוכו מהעובדים", 198, 209),
        _f("22", "קבוע 44", 210, 211, const="44"),
        _f("23", "קבוע \"בדיקה\" (לפי הנחיות הרשות)", 212, 216, "A", const="בדיקה"),
        _f("24", "ריק", 217, 283, "F"),
        _f("24א'", "מספר כולל של רשומות בדוח (מכל הסוגים)", 284, 289),
        _f("24א'1", "FILLER", 290, 877, "F"),
        _f("24א'2", "מספר תיק ניכויים של ביטוח לאומי", 878, 888),
        _f("24ב'", "FILLER", 889, 959, "F"),
        _f("25", "מספר מפעל", 960, 964),
    ],
    "50": [
        _f("1", "מספר תיק ניכויים", 1, 9),
        _f("2", "מספר אגיד", 10, 11),
        _f("3", "סוג רשומה", 12, 13, const="50"),
        _f("4", "שנת מס", 14, 17),
        _f("5", "אפסים", 18, 26, const="0" * 9),
        _f("6", "חודש משכורת", 27, 28),
        _f("7", "מספר עובדים", 29, 34),
        _f("8", "סה\"כ משכורת ותשלומים (לא כולל עובדים יומיים)", 35, 46),
        _f("9", "ניכוי המס לפני קיזוז הטבת עלויות אילת", 47, 58),
        _f("10", "מס מעסיקים והיטל עובדים זרים", 59, 70),
        _f("11", "סה\"כ חיובים ניכוי מס הכנסה ומס מעסיקים", 71, 82),
        _f("12", "קיזוז הטבה למעסיק באילת", 83, 94),
        _f("13", "יתרת מס הכנסה לאחר קיזוז ההטבה", 95, 106),
        _f("14", "דמי ביטוח לאומי ומס בריאות כולל הניכוי מהעובדים", 107, 118),
        _f("15", "סה\"כ משכורת ותשלומים (כולל לעובדים יומיים)", 119, 130),
        _f("16", "מס שכר למוסד ללא כוונת רווח או מוסד כספי", 131, 142),
        _f("17", "משכורת לעניין מס שכר", 143, 154),
        _f("18", "FILLER", 155, 166, "F"),
        _f("19", "FILLER", 167, 178, "F"),
        _f("20", "משכורת שדווחה באמצעות שירות התעסוקה", 179, 190),
        _f("21", "ניכוי מס שדווח באמצעות שירות התעסוקה", 191, 202),
        _f("22", "משכורת בגין בונוס מנהלים", 203, 214),
        _f("23", "מס בגין בונוס מנהלים", 215, 226),
        _f("24", "משכורת בגין היטל עובדים זרים", 227, 238),
        _f("25", "FILLER", 239, 877, "F"),
        _f("25א'", "מספר תיק ניכויים של ביטוח לאומי", 878, 888),
        _f("25ב'", "FILLER", 889, 959, "F"),
        _f("26", "מספר מפעל", 960, 964),
    ],
}


from form126_rec20 import REC20 as _REC20  # noqa: E402

SPEC["20"] = [
    _f(no, name, a, b, kind, "20" if no == "3" else None)
    for no, name, a, b, kind in _REC20
]

SPEC["40"] = [
    _f("1", "מספר תיק ניכויים", 1, 9),
    _f("2", "מספר אגיד", 10, 11),
    _f("3", "סוג רשומה", 12, 13, const="40"),
    _f("4", "שנת מס", 14, 17),
    _f("5", "אפסים", 18, 26, const="0" * 9),
    _f("6", "FILLER", 27, 31, "F"),
    _f("7", "FILLER", 32, 32, "F"),
    _f("8", "האם שודר/ישודר דוח משלים (1 כן, 2 לא)", 33, 33),
    _f("9", "מספר תיק עצמאי או חברה במס הכנסה", 34, 42),
    _f("10", "מעמד משפטי של המשלם (1 חברה, 2 יחיד, 3 שותפות, 4 עמותה, 5 רשות)", 43, 43),
    _f("11", "סה\"כ משכורת ותשלומים לפי הדוח החודשי (102)", 44, 54),
    _f("12", "דמי ביטוח לאומי ודמי ביטוח בריאות (סה\"כ חובה לפי 102)", 55, 65),
    _f("13", "ריק", 66, 76, "F"),
    _f("14", "סה\"כ השכר הפטור מדמי ביטוח (צבירת שדה 123 ברשומה 20)", 77, 87),
    _f("15", "סה\"כ סכומים פטורים מעל המקסימום (צבירת שדה 127 ברשומה 20)", 88, 98),
    _f("16", "ריק", 99, 109, "F"),
    _f("17", "סה\"כ משכורת ותשלומים (צבירת שדה 39 ברשומה 20)", 110, 120),
    _f("18", "ריק", 121, 131, "F"),
    _f("19", "סה\"כ משכורת ותשלומים לפי דוח חודשי (102), ללא שירות התעסוקה", 132, 142),
    _f("20", "סה\"כ שכר שדווח באמצעות שירות התעסוקה לעובדים פלסטינים", 143, 153),
    _f("21", "מס מעסיקים לפי הדוח החודשי (102)", 154, 164),
    _f("22", "ניכוי מס הכנסה לפי דוח חודשי (102)", 165, 175),
    _f("23", "ההטבה להפחתת עלויות השכר באילת שקוזזה מניכוי המס", 176, 181),
    _f("24", "סה\"כ מס הכנסה שנוכה (צבירת שדה 116 ברשומה 20)", 182, 192),
    _f("25", "דמי פגיעה ששולמו על חשבון הביטוח הלאומי", 193, 203),
    _f("26", "סה\"כ תגמולי מילואים ששולמו על חשבון הביטוח הלאומי", 204, 214),
    _f("27", "סה\"כ קצובות הכלולות במשכורת לצורך חישובי המס", 215, 225),
    _f("28", "היטל על העסקת עובדים זרים", 226, 233),
    _f("29", "כתובת דואר אלקטרוני", 234, 283, "E"),
    _f("30", "סה\"כ עובדים בדוח במקום שדה 6", 284, 289),
    _f("30א'", "יתרת מס לאחר קיזוז", 290, 299),
    _f("30ב'", "סיכום כללי 18+20", 300, 311),
    _f("30ג'", "ההפרש בין 18 לטור ד'", 312, 321),
    _f("30ד'", "ההפרש בין שדה 26 לטור ז'", 322, 331),
    _f("30ה'", "מס מעסיקים בשירות התעסוקה", 332, 341),
    _f("30ו'", "מס שכר שדווח בשירות התעסוקה", 342, 351),
    _f("30ז'", "דמי ביטוח לאומי וביטוח בריאות (טור ו')", 352, 361),
    _f("30ח'", "דמי ביטוח לאומי ומס בריאות", 362, 371),
    _f("30ט'", "ניכוי מס הכנסה ומס (טור א')", 372, 381),
    _f("30י'", "מס שכר למוסד ללא כוונת רווח (טור ט')", 382, 393),
    _f("30י'1", "ההטבה להפחתת עלויות השכר (טור ח')", 394, 401),
    _f("30י\"א", "מספר הטלפון של החברה", 402, 411),
    _f("30יא'1", "FILLER", 412, 877, "F"),
    _f("30יא'2", "מספר תיק ניכויים של ביטוח לאומי", 878, 888),
    _f("30יא'3", "סה\"כ מחיר יום ההבראה", 889, 899),
    _f("30יא'4", "סה\"כ חלקו של המעסיק", 900, 910),
    _f("30יא'5", "סה\"כ משכורת להפחתה", 911, 921),
    _f("30יא'6", "סה\"כ חיובים מהפחתה", 922, 932),
    _f("30יא'7", "FILLER", 933, 957, "F"),
    _f("30י\"ב", "רבעון בדיווח השנתי", 958, 959),
    _f("31", "מספר מפעל", 960, 964),
]


class SpecError(ValueError):
    pass


def check_spec(rec: str) -> None:
    """The fields of a record must tile columns 1..964 with no gap or overlap."""
    if rec not in SPEC:
        raise SpecError(f"רשומה {rec} עדיין לא הוגדרה במחולל")
    nxt = 1
    for f in SPEC[rec]:
        if f.start != nxt:
            raise SpecError(f"רשומה {rec}: שדה {f.no} מתחיל בעמודה {f.start}, ציפינו ל-{nxt}")
        nxt = f.end + 1
    if nxt != RECORD_WIDTH + 1:
        raise SpecError(f"רשומה {rec}: הרשומה מסתיימת בעמודה {nxt - 1}, ולא ב-{RECORD_WIDTH}")


def _is_hebrew(s: str) -> bool:
    return any("א" <= c <= "ת" for c in s)


def _num(f: Field, v) -> str:
    n = int(v)
    s = str(abs(n))
    if n < 0:
        # minus sign in the left-most column of the field, zeros after it
        if len(s) > f.length - 1:
            raise ValueError(f"שדה {f.no}: הערך {n} ארוך מדי")
        return "-" + s.zfill(f.length - 1)
    if len(s) > f.length:
        raise ValueError(f"שדה {f.no}: הערך {n} ארוך מדי ({f.length} ספרות)")
    return s.zfill(f.length)


def _alpha(f: Field, v, hebrew_visual: bool | None) -> str:
    s = "" if v is None else str(v)
    if f.kind == "E":
        if len(s) > f.length:
            raise ValueError(f"שדה {f.no}: הטקסט ארוך מ-{f.length} תווים")
        return s.ljust(f.length)
    if len(s) > f.length:
        raise ValueError(f"שדה {f.no}: הטקסט ארוך מ-{f.length} תווים")
    if _is_hebrew(s):
        if hebrew_visual is None:
            raise SpecError("יש טקסט בעברית: חובה לקבוע hebrew_visual (המפרט לא מכריע)")
        if hebrew_visual:
            s = s[::-1]
    else:
        s = s.upper()  # Latin letters must be capitals (general rule 5)
    return s.ljust(f.length)


def build_record(rec: str, values: dict, hebrew_visual: bool | None = None) -> str:
    """One 964-column record (no line terminator). ``values`` is keyed by field no."""
    check_spec(rec)
    fields = SPEC[rec]
    known = {f.no for f in fields}
    extra = set(values) - known
    if extra:
        raise SpecError(f"שדות לא מוכרים ברשומה {rec}: {sorted(extra)}")
    out = []
    for f in fields:
        if f.kind == "F":
            out.append(" " * f.length)
        elif f.const is not None:
            if f.no in values and str(values[f.no]) != f.const:
                raise SpecError(f"שדה {f.no} ברשומה {rec} קבוע '{f.const}'")
            out.append(_alpha(f, f.const, hebrew_visual) if f.kind == "A" else f.const)
        elif f.kind == "N":
            out.append(_num(f, values.get(f.no, 0)))
        else:  # "A" or "E"
            out.append(_alpha(f, values.get(f.no), hebrew_visual))
    line = "".join(out)
    if len(line) != RECORD_WIDTH:
        raise SpecError(f"רשומה {rec} באורך {len(line)} ולא {RECORD_WIDTH}")
    return line


def encode_file(lines: list[str], encoding: str) -> bytes:
    if encoding not in ("cp862", "cp1255"):
        raise SpecError("הקידוד חייב להיות cp862 או cp1255 (לפי המפרט)")
    return "".join(l + EOL for l in lines).encode(encoding)


def check_id_digit(id9: str) -> bool:
    """Israeli ID check digit (mod 10), as the spec requires for column 26."""
    if len(id9) != 9 or not id9.isdigit():
        return False
    t = 0
    for i, c in enumerate(id9):
        d = int(c) * (1 if i % 2 == 0 else 2)
        t += d - 9 if d > 9 else d
    return t % 10 == 0


for _r in SPEC:
    check_spec(_r)
