"""
מנוע תבניות תלוש: ממלא מפרט תבנית (JSON) בנתוני תלוש שחושבו.

עקרונות (לא ניתנים לשינוי על ידי תבנית):
1. התבנית קובעת רק מראה: מיקום, כותרות, צבעים. כל מספר ותאריך מגיעים מהחישוב (d של payslip.prepare).
2. טקסט קבוע בתבנית לא יכול להכיל ספרות (למעט בתוך {שדה}): מונע מספר "מוטמע" שלא מהחישוב.
3. שדה שהתבנית מבקשת ואין לו נתון מוצג "-" ונרשם ברשימת החסרים. לא ממציאים ערך.
4. שדה/מקור לא מוכר בתבנית = שגיאה בטעינה (לא מתעלמים בשקט).
5. טבלה שלא נכנסת בגובה שהוגדר לה = שגיאה (לא חותכים שורות בשקט).
"""
import io
import json
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import payslip as ps

W, H = A4

# שדות בודדים שתבנית רשאית לקשור אליהם ({שם} בטקסט, או bind). כולם מגיעים מ-payslip.prepare או מחושבים כאן.
SCALAR_FIELDS = {
    "period", "employer_name", "employer_id", "employer_address",
    "employee_name", "employee_id", "employee_id_masked", "start_date", "position_scope",
    "worked", "seniority", "regular_hour_value", "min_wage", "vacation", "sick", "payment",
    "points", "gross", "taxable", "tax", "cum_taxable", "cum_tax", "ni_base", "cum_ni_base",
    "total_deductions", "net",
}
NUMERIC_FIELDS = {"regular_hour_value", "gross", "taxable", "tax", "cum_taxable", "cum_tax",
                   "ni_base", "cum_ni_base", "total_deductions", "net"}

# מקורות טבלה והעמודות שכל אחד מספק (לפי הנתונים ב-payslip.prepare)
TABLE_SOURCES = {
    "payments": ("label", "amount"),
    "deductions": ("label", "rate", "amount"),
    "tax_data": ("label", "month", "cum"),
    "employer": ("label", "base", "amount"),
}
ELEMENT_TYPES = {"box", "text", "kv", "table", "stat"}
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


class TemplateError(ValueError):
    pass


class TemplateOverflow(TemplateError):
    pass


def _static_text_ok(s, where):
    stripped = _PLACEHOLDER.sub("", s)
    if re.search(r"\d", stripped):
        raise TemplateError(f"{where}: טקסט קבוע בתבנית לא יכול להכיל ספרות ({s!r}); מספרים רק מהחישוב")


def validate(spec: dict) -> dict:
    if not isinstance(spec, dict) or "elements" not in spec:
        raise TemplateError("מפרט תבנית חייב להכיל elements")
    for i, el in enumerate(spec["elements"]):
        where = f"element {i}"
        t = el.get("type")
        if t not in ELEMENT_TYPES:
            raise TemplateError(f"{where}: סוג לא מוכר {t!r}")
        rect = el.get("rect") or ([*el["at"], 0, 0] if "at" in el else None)
        if rect is None or len(rect) != 4:
            raise TemplateError(f"{where}: חסר rect/at")
        x, y, w, h = rect
        if x < 0 or y < 0 or x + w > 210.01 or y + h > 297.01:
            raise TemplateError(f"{where}: חורג מגבולות A4 ({rect})")
        for key in ("title", "label", "text"):
            if isinstance(el.get(key), str):
                _static_text_ok(el[key], f"{where}.{key}")
                for name in _PLACEHOLDER.findall(el[key]):
                    if name not in SCALAR_FIELDS:
                        raise TemplateError(f"{where}: שדה לא מוכר {{{name}}}")
        if t == "kv":
            for row in el.get("rows", []):
                lab, bind = row[0], row[1]
                _static_text_ok(lab, f"{where}.rows")
                if bind not in SCALAR_FIELDS:
                    raise TemplateError(f"{where}: שדה לא מוכר {bind!r}")
        if t == "stat" and el.get("bind") not in SCALAR_FIELDS:
            raise TemplateError(f"{where}: שדה לא מוכר {el.get('bind')!r}")
        if t == "table":
            src = el.get("source")
            if src not in TABLE_SOURCES:
                raise TemplateError(f"{where}: מקור טבלה לא מוכר {src!r}")
            cols = el.get("columns") or []
            if not cols:
                raise TemplateError(f"{where}: טבלה בלי עמודות")
            for c in cols:
                _static_text_ok(c.get("header", ""), f"{where}.header")
                if c.get("col") not in TABLE_SOURCES[src]:
                    raise TemplateError(f"{where}: עמודה {c.get('col')!r} לא קיימת במקור {src}")
            if sum(c["w"] for c in cols) > w + 0.01:
                raise TemplateError(f"{where}: רוחב העמודות ({sum(c['w'] for c in cols)}) גדול מרוחב הטבלה ({w})")
            tot = el.get("total")
            if tot:
                _static_text_ok(tot.get("label", ""), f"{where}.total")
                if tot.get("bind") not in SCALAR_FIELDS:
                    raise TemplateError(f"{where}: שדה סיכום לא מוכר {tot.get('bind')!r}")
    return spec


def _hex(s, default):
    return colors.HexColor(s) if s else default


def _scalar(d, name):
    v = d.get(name)
    if name == "min_wage":
        return f"{ps.n2(v[0])} / {ps.n2(v[1])}" if v else None
    if v is None or v == "":
        return None
    if name in NUMERIC_FIELDS:
        return ps.n2(v)
    return str(v)


def _fill_text(s, d, missing):
    def sub(m):
        v = _scalar(d, m.group(1))
        if v is None:
            missing.add(m.group(1))
            return "-"
        return v
    return _PLACEHOLDER.sub(sub, s)


def _table_rows(src, d):
    if src == "payments":
        return [(lab, ps.n2(a)) for lab, a in d["payments"]]
    if src == "deductions":
        return [(lab, rate, ps.n2(a)) for lab, rate, a in d["deductions"]]
    if src == "employer":
        return [(lab, base, ps.n2(a)) for lab, base, a in d.get("employer", [])]
    if src == "tax_data":
        return [("הכנסה חייבת במס", ps.n2(d["taxable"]), ps.n2(d["cum_taxable"])),
                ("מס הכנסה שנוכה", ps.n2(d["tax"]), ps.n2(d["cum_tax"])),
                ("שכר חייב בביטוח לאומי", ps.n2(d["ni_base"]),
                 ps.n2(d["cum_ni_base"]) if d.get("cum_ni_base") is not None else "-"),
                ("נקודות זיכוי", str(d["points"]), "-")]
    raise TemplateError(src)


def _y(top_mm):          # y במ"מ מלמעלה -> נקודות reportlab
    return H - top_mm * mm


def render(spec: dict, d: dict, draft: bool = False):
    """מחזיר (pdf_bytes, missing_fields_list). d = פלט payslip.prepare."""
    validate(spec)
    d = dict(d)
    d["period"] = f"{d['month']:02d}/{d['year']}"
    missing = set()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("תלוש שכר")
    ink = ps.INK
    for el in spec["elements"]:
        t = el["type"]
        if t == "box":
            x, y, w, h = el["rect"]
            if el.get("fill"):
                c.setFillColor(_hex(el["fill"], colors.white))
                c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=0, fill=1)
            if el.get("border", True):
                c.setStrokeColor(_hex(el.get("border_color"), colors.HexColor("#6b7b8a")))
                c.setLineWidth(0.6)
                c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=1, fill=0)
            if el.get("title"):
                _title_bar(c, el, x, y, w)
        elif t == "text":
            x, y = el["at"]
            s = _fill_text(el["text"], d, missing)
            c.setFont("HE-B" if el.get("bold") else "HE", el.get("size", 9))
            c.setFillColor(ink)
            tx = visual(s)
            ax = x * mm
            ay = _y(y)
            if el.get("align", "right") == "right":
                c.drawRightString(ax, ay, tx)
            elif el.get("align") == "center":
                c.drawCentredString(ax, ay, tx)
            else:
                c.drawString(ax, ay, tx)
        elif t == "kv":
            _draw_kv(c, el, d, missing)
        elif t == "stat":
            _draw_stat(c, el, d, missing)
        elif t == "table":
            _draw_table(c, el, d, missing)
    if draft:
        c.saveState()
        c.setFillColor(colors.Color(0.85, 0.1, 0.1, alpha=0.16))
        c.setFont("HE-B", 44)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, visual("טיוטה - לא לחלוקה"))
        c.restoreState()
    c.showPage()
    c.save()
    return buf.getvalue(), sorted(missing)


visual = ps.visual


def _title_bar(c, el, x, y, w):
    bh = el.get("title_h", 5.5)
    c.setFillColor(_hex(el.get("title_fill"), ps.HEAD))
    c.rect(x * mm, _y(y + bh), w * mm, bh * mm, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#6b7b8a"))
    c.setLineWidth(0.4)
    c.rect(x * mm, _y(y + bh), w * mm, bh * mm, stroke=1, fill=0)
    fill = _hex(el.get("title_fill"), ps.HEAD)
    lum = 0.299 * fill.red + 0.587 * fill.green + 0.114 * fill.blue
    c.setFillColor(colors.white if lum < 0.45 else ps.INK)     # כותרת על רקע כהה: טקסט לבן
    c.setFont("HE-B", el.get("title_size", 8.5))
    if el.get("title_align", "center") == "center":
        c.drawCentredString((x + w / 2) * mm, _y(y + bh * 0.72), visual(el["title"]))
    else:
        c.drawRightString((x + w - 1.5) * mm, _y(y + bh * 0.72), visual(el["title"]))


def _draw_kv(c, el, d, missing):
    x, y, w, h = el["rect"]
    if el.get("border", True):
        c.setStrokeColor(colors.HexColor("#6b7b8a"))
        c.setLineWidth(0.6)
        c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=1, fill=0)
    ty = y
    if el.get("title"):
        _title_bar(c, el, x, y, w)
        ty = y + el.get("title_h", 5.5)
    lab_w = el.get("label_w", 24)
    step = el.get("row_h", 4.4)
    ry = ty + 3.6
    cap = int((y + h - ty) / step)
    if len(el.get("rows", [])) > cap:
        raise TemplateOverflow(f"kv '{el.get('title')}': {len(el['rows'])} שורות לא נכנסות בגובה {h} מ\"מ")
    for lab, bind in el.get("rows", []):
        v = _scalar(d, bind)
        if v is None:
            missing.add(bind)
            v = "-"
        c.setFont("HE", el.get("size", 7.5))
        c.setFillColor(ps.MUTED)
        c.drawRightString((x + w - 1.5) * mm, _y(ry), visual(lab))
        c.setFillColor(ps.INK)
        c.setFont("HE-B", el.get("size", 7.5))
        c.drawRightString((x + w - 1.5 - lab_w) * mm, _y(ry), visual(v))
        ry += step


def _draw_stat(c, el, d, missing):
    x, y, w, h = el["rect"]
    v = _scalar(d, el["bind"])
    if v is None:
        missing.add(el["bind"])
        v = "-"
    if el.get("fill"):
        c.setFillColor(_hex(el["fill"], colors.white))
        c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#1b2733"))
    c.setLineWidth(1.0 if el.get("heavy") else 0.6)
    c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=1, fill=0)
    c.setFillColor(ps.INK)
    c.setFont("HE-B", el.get("size", 10))
    base = y + h / 2 + 1.5
    c.drawRightString((x + w - 2) * mm, _y(base), visual(el.get("label", "")))
    c.drawString((x + 2) * mm, _y(base), v)


def _draw_table(c, el, d, missing):
    x, y, w, h = el["rect"]
    cols = el["columns"]
    row_h = el.get("row_h", 4.6)
    c.setStrokeColor(colors.HexColor("#6b7b8a"))
    c.setLineWidth(0.6)
    c.rect(x * mm, _y(y + h), w * mm, h * mm, stroke=1, fill=0)
    ty = y
    if el.get("title"):
        _title_bar(c, el, x, y, w)
        ty = y + el.get("title_h", 5.5)
    # כותרות עמודות: העמודה הראשונה בימין
    xs, cx = [], x + w
    for col in cols:
        xs.append(cx)
        cx -= col["w"]
    c.setFillColor(_hex(el.get("header_fill"), ps.HEAD))
    hh = 5.5
    c.rect(x * mm, _y(ty + hh), w * mm, hh * mm, stroke=0, fill=1)
    c.setFillColor(ps.INK)
    c.setFont("HE-B", 7.5)
    for rx, col in zip(xs, cols):
        c.drawRightString((rx - 1.5) * mm, _y(ty + hh * 0.72), visual(col["header"]))
        c.setStrokeColor(colors.HexColor("#b9c4ce"))
        c.setLineWidth(0.3)
        c.line((rx - col["w"]) * mm, _y(ty), (rx - col["w"]) * mm, _y(y + h))
    ty += hh
    rows = _table_rows(el["source"], d)
    tot = el.get("total")
    reserve = (row_h + 1) if tot else 0
    cap = int((y + h - ty - reserve) / row_h)
    if len(rows) > cap:
        raise TemplateOverflow(f"טבלה '{el.get('title')}': {len(rows)} שורות לא נכנסות (מקום ל-{cap})")
    ry = ty + 3.7
    for r in rows:
        for rx, col in zip(xs, cols):
            v = r[TABLE_SOURCES[el["source"]].index(col["col"])]
            c.setFont("HE", 7.5)
            c.setFillColor(ps.INK)
            if col.get("align") == "left":
                c.drawString((rx - col["w"] + 1.5) * mm, _y(ry), visual(str(v)))
            else:
                c.drawRightString((rx - 1.5) * mm, _y(ry), visual(str(v)))
        ry += row_h
    if tot:
        v = _scalar(d, tot["bind"])
        if v is None:
            missing.add(tot["bind"])
            v = "-"
        by = y + h - row_h - 0.5
        c.setStrokeColor(ps.INK)
        c.setLineWidth(0.6)
        c.line(x * mm, _y(by), (x + w) * mm, _y(by))
        c.setFont("HE-B", 8)
        c.setFillColor(ps.INK)
        c.drawRightString((x + w - 1.5) * mm, _y(by + 3.8), visual(tot.get("label", "")))
        c.drawString((x + 1.5) * mm, _y(by + 3.8), v)


def load(path_or_dict):
    if isinstance(path_or_dict, dict):
        return validate(path_or_dict)
    with open(path_or_dict, encoding="utf8") as f:
        return validate(json.load(f))
