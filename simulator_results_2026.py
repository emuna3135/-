"""
תוצאות סימולטור נקודות הזיכוי של רשות המסים (secapp.taxes.gov.il/srsimulatorNZ), שנת מס 2026, הורצו אוטומטית ב-12.11.2026
(דפדפן ב-Claude; כל הרצה אחרי ניקוי וקלט ילדים מאופס). המפתח: (מין, נשוי, דגל מצב, ילדים בחזקה, ילדים לא בחזקה) -> סך נקודות.
מקור ראשוני לבדיקות (מחשבון רשמי). ראו DATA_LEDGER ב326.
דגלים: teen=נער/ה 16-18; benef=יחיד מוטב; nomesh=חי בנפרד, בלי משק בית משותף; yesmesh=חי בנפרד עם משק בית משותף;
niptar=הורה יחיד; mezonut=משלם מזונות על ילדים שלא בחזקתו; widower=נשואה לאלמן; esha=נשואים בשנית ומשלמים מזונות.
"""
# (gender, married, flag, custody_ages, noncust_ages, total)
R = []
def add(g, m, flag, custody, noncust, total):
    R.append((g, m, flag, tuple(custody), tuple(noncust), total))

# --- נשואים עם ילד אחד (גיל; 6 = טווח 6-17)
for a, w, m in [(0, 5.25, 4.75), (1, 7.25, 6.75), (2, 7.25, 6.75), (3, 6.25, 5.75), (4, 5.25, 4.75), (5, 5.25, 4.75), (6, 4.75, 3.25), (18, 3.25, 2.25)]:
    add("F", True, None, [a], [], w)
    add("M", True, None, [a], [], m)
# --- בסיס וקלטים בלי ילדים
add("F", True, None, [], [], 2.75); add("M", True, None, [], [], 2.25)
add("F", False, None, [], [], 2.75); add("M", False, None, [], [], 2.25)
add("F", False, "teen", [], [], 3.75); add("M", False, "teen", [], [], 3.25)
add("F", True, "teen", [], [], 3.75); add("M", True, "teen", [], [], 3.25)
# --- יחיד מוטב (נשואים)
add("F", True, "benef", [], [], 3.75); add("M", True, "benef", [], [], 3.25)
add("F", True, "benef", [2], [], 7.75); add("M", True, "benef", [2], [], 7.25)
# --- נשואה לאלמן
add("F", True, "widower", [], [], 2.75); add("F", True, "widower", [2], [], 7.25)
# --- חי בנפרד בלי משק בית משותף
add("F", False, "nomesh", [], [], 3.75); add("M", False, "nomesh", [], [], 3.25)
for a, w in [(0, 6.25), (1, 8.25), (2, 8.25), (3, 7.25), (4, 6.25), (5, 6.25), (6, 5.75), (18, 4.25)]:
    add("F", False, "nomesh", [a], [], w)
for a, m in [(0, 5.75), (2, 7.75), (3, 6.75), (5, 5.75), (6, 5.25), (18, 3.75)]:
    add("M", False, "nomesh", [a], [], m)
# --- חי בנפרד עם משק בית משותף
for a, w, m in [(0, 5.25, 4.75), (2, 7.25, 6.75), (6, 4.75, 4.25), (18, 3.25, 2.75)]:
    add("F", False, "yesmesh", [a], [], w); add("M", False, "yesmesh", [a], [], m)
# --- הורה יחיד
add("F", False, "niptar", [], [], 3.75); add("M", False, "niptar", [], [], 3.25)
for a, w in [(0, 8.75), (1, 12.75), (2, 12.75), (3, 10.75), (4, 8.75), (5, 8.75), (6, 6.75), (18, 4.25)]:
    add("F", False, "niptar", [a], [], w)
for a, m in [(0, 8.25), (2, 12.25), (3, 10.25), (6, 6.25), (18, 3.75)]:
    add("M", False, "niptar", [a], [], m)
# --- משלם מזונות על ילדים שלא בחזקתו
add("F", False, "mezonut", [], [], 3.75); add("M", False, "mezonut", [], [], 3.25)
for a, w in [(0, 6.25), (1, 8.25), (2, 8.25), (3, 7.25)]:
    add("F", False, "mezonut", [], [a], w)
for a, m in [(0, 5.75), (2, 7.75), (6, 4.25)]:
    add("M", False, "mezonut", [], [a], m)
# --- כמה ילדים
add("F", True, None, [0, 4], [], 7.75)
add("F", True, None, [2, 2], [], 11.75)
add("M", True, None, [6, 6], [], 4.25)


# --- הרצות נוספות 19.11.2026 (אותו סימולטור, שנת מס 2026): צירופי מצבים. הדגל כאן יכול להיות tuple של כמה מצבים.
# הכלל שעלה מההרצות: +1 על חי בנפרד בלי משק בית/הורה יחיד (פעם אחת, גם אם שניהם), +1 על מזונות, מצטברים; חי בנפרד עם משק בית משותף: 0.
for g, base in (("F", 2.75), ("M", 2.25)):
    add(g, True, "mezonut", [], [], base + 1)
    add(g, True, "mezonut", [6], [], base + 1 + (2 if g == "F" else 1))
    add(g, True, ("teen", "mezonut"), [], [], base + 2)
    add(g, False, ("nomesh", "niptar"), [], [], base + 1)
    add(g, False, ("nomesh", "niptar"), [6], [], base + 1 + 2 + 1)
    add(g, False, ("nomesh", "mezonut"), [], [], base + 2)
    add(g, False, ("nomesh", "mezonut"), [6], [], base + 2 + 2)
    add(g, False, ("nomesh", "mezonut"), [], [6], base + 3)
    add(g, False, ("nomesh", "mezonut"), [6], [0], base + 2 + 2 + 2.5)
    add(g, False, ("niptar", "mezonut"), [], [], base + 2)
    add(g, False, ("niptar", "mezonut"), [6], [], base + 2 + 2 + 1)
    add(g, False, ("niptar", "mezonut"), [], [6], base + 3)
    add(g, False, ("niptar", "mezonut"), [6], [6], base + 2 + 2 + 1 + 1)
    add(g, False, ("yesmesh", "niptar"), [], [], base + 1)
    add(g, False, ("yesmesh", "niptar"), [6], [], base + 1 + 2 + 1)
    add(g, False, ("yesmesh", "mezonut"), [], [], base + 1)
    add(g, False, ("yesmesh", "mezonut"), [6], [], base + 1 + 2)
    add(g, False, ("yesmesh", "mezonut"), [], [6], base + 2)
    add(g, False, ("nomesh", "niptar", "mezonut"), [], [], base + 2)
    add(g, False, ("nomesh", "niptar", "mezonut"), [6], [], base + 2 + 2 + 1)
    add(g, False, ("yesmesh", "niptar", "mezonut"), [6], [], base + 2 + 2 + 1)

# מצבים שהסימולטור נתן להם תוצאה שאינה מוסברת/אינה בהתאם לתווית, ולכן אינם נתמכים בחישוב (נשארים ידני):
UNEXPLAINED = [
    ("esha: נשואים בשנית ומשלמים מזונות (התווית: נקודה אחת; התוצאה: 0 תוספת)", "F", True, "esha", [], [], 2.75),
    ("niyud/nidcha: ניוד נקודות לא שינה את הסך; גבר עם ניוד בגיל 1 נתן 2.25 (ילד לא נספר)", "M", True, "nidcha", [1], [], 2.25),
    ("ילד בחזקה לא-נשוי בלי דגל מצב: הילד לא נספר (2.75 לאישה עם ילד בן 2)", "F", False, None, [2], [], 2.75),
]
