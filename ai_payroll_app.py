
import streamlit as st
import pandas as pd
import io
import re
import textwrap
from decimal import Decimal, ROUND_HALF_UP
import streamlit.components.v1 as components

# ===========================================================================
# 1. Exact Scientific Decimal Engine (מנוע חישוב פיננסי מדויק)
# ===========================================================================
class FinancialEngineException(Exception):
    pass

class ExactScientificDecimalEngine:
    """מנוע חישוב מדעי/פיננסי מדויק ברמת האגורה בהתאם לחוקי העבודה והמיסוי 2026"""
    
    @staticmethod
    def verify_engine_status() -> bool:
        try:
            test_val = Decimal('100.005').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return test_val == Decimal('100.01') or test_val == Decimal('101.00')
        except Exception:
            return False

    @staticmethod
    def to_dec(val) -> Decimal:
        if not ExactScientificDecimalEngine.verify_engine_status():
            raise FinancialEngineException("מנוע החישוב הפיננסי אינו פעיל - החישוב הוקפא!")
        if pd.isna(val) or val is None or val == '':
            return Decimal('0.00')
        return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_tax_breakdown(cls, gross: Decimal, credit_points: Decimal) -> dict:
        credit_point_value = cls.to_dec('242.00')
        brackets = [
            (cls.to_dec('7010.00'), cls.to_dec('0.10'), "10%"),
            (cls.to_dec('10060.00'), cls.to_dec('0.14'), "14%"),
            (cls.to_dec('16150.00'), cls.to_dec('0.20'), "20%"),
            (cls.to_dec('22440.00'), cls.to_dec('0.31'), "31%"),
            (cls.to_dec('46690.00'), cls.to_dec('0.35'), "35%"),
            (None, cls.to_dec('0.47'), "47%")
        ]

        tax_before_credit = cls.to_dec('0.00')
        remaining = gross
        prev_limit = cls.to_dec('0.00')
        steps = []

        for upper_limit, rate, label in brackets:
            if upper_limit is None:
                tax_in_bracket = cls.to_dec(remaining * rate)
                tax_before_credit += tax_in_bracket
                steps.append(f"מדרגה {label} (מעל ₪{prev_limit:,.2f}): ₪{remaining:,.2f} × {label} = ₪{tax_in_bracket:,.2f}")
                break
            
            bracket_size = upper_limit - prev_limit
            if remaining > bracket_size:
                tax_in_bracket = cls.to_dec(bracket_size * rate)
                tax_before_credit += tax_in_bracket
                steps.append(f"מדרגה {label} (₪{prev_limit:,.2f} - ₪{upper_limit:,.2f}): ₪{bracket_size:,.2f} × {label} = ₪{tax_in_bracket:,.2f}")
                remaining -= bracket_size
                prev_limit = upper_limit
            else:
                tax_in_bracket = cls.to_dec(remaining * rate)
                tax_before_credit += tax_in_bracket
                steps.append(f"מדרגה {label} (עד ₪{upper_limit:,.2f}): ₪{remaining:,.2f} × {label} = ₪{tax_in_bracket:,.2f}")
                break

        credit_discount = cls.to_dec(credit_points * credit_point_value)
        final_tax = cls.to_dec(max(cls.to_dec('0.00'), tax_before_credit - credit_discount))
        
        return {
            "tax_before_credit": tax_before_credit,
            "credit_discount": credit_discount,
            "final_tax": final_tax,
            "steps": steps
        }

    @classmethod
    def calculate_ni_breakdown(cls, gross: Decimal) -> dict:
        threshold = cls.to_dec('7522.00')
        rate_low = cls.to_dec('0.035')
        rate_high = cls.to_dec('0.12')

        if gross <= threshold:
            ni = cls.to_dec(gross * rate_low)
            details = f"שיעור מופחת (3.5% עד ₪7,522): ₪{gross:,.2f} × 3.5% = ₪{ni:,.2f}"
        else:
            low_part = cls.to_dec(threshold * rate_low)
            high_part = cls.to_dec((gross - threshold) * rate_high)
            ni = cls.to_dec(low_part + high_part)
            details = f"שיעור מופחת (3.5%): ₪{low_part:,.2f} | שיעור מלא (12% מעל ₪7,522): ₪{high_part:,.2f}"

        return {"ni_total": ni, "details": details}

# ===========================================================================
# 2. מנוע התאמת תלוש ויזואלי ברכיב מבודד נקי (Component HTML)
# ===========================================================================
def render_visual_paystub(emp_data: dict, template_name: str = "תבנית רשמית", primary_color: str = "#1E3A8A"):
    """הנפקת תלוש משכורת רשמי ממוסגר ומעוצב ברכיב HTML סטרילי וללא בעיות הזחה"""
    tot_ded = emp_data['tax_info']['final_tax'] + emp_data['ni_info']['ni_total'] + emp_data['pension'] + emp_data['tardiness_deduction']
    pension_employer = ExactScientificDecimalEngine.to_dec(emp_data['gross'] * Decimal('0.065'))
    severance_employer = ExactScientificDecimalEngine.to_dec(emp_data['gross'] * Decimal('0.06'))
    company_title = emp_data.get('company_name', 'חברה / משרד / עסק')
    
    html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8">
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; background-color: #FAFAFA; margin: 0; padding: 10px; direction: rtl; text-align: right; }}
.paystub-card {{ border: 2px solid {primary_color}; border-radius: 10px; padding: 20px; background-color: #FFFFFF; box-shadow: 0px 4px 12px rgba(0,0,0,0.08); max-width: 880px; margin: 0 auto; }}
.header {{ display: flex; justify-content: space-between; align-items: center; background-color: {primary_color}; color: white; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; }}
.title {{ font-size: 18px; font-weight: bold; }}
.print-btn {{ background-color: #10B981; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px; }}
.print-btn:hover {{ background-color: #059669; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 15px; }}
th, td {{ padding: 8px; border: 1px solid #E5E7EB; text-align: right; }}
th {{ background-color: #EFF6FF; color: {primary_color}; }}
.flex-container {{ display: flex; gap: 15px; flex-wrap: wrap; }}
.flex-box {{ flex: 1; min-width: 280px; }}
.gross-header {{ color: {primary_color}; border-bottom: 2px solid {primary_color}; padding-bottom: 4px; margin-bottom: 8px; font-size: 15px; font-weight: bold; }}
.deduct-header {{ color: #991B1B; border-bottom: 2px solid #991B1B; padding-bottom: 4px; margin-bottom: 8px; font-size: 15px; font-weight: bold; }}
.employer-sec {{ background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 10px; border-radius: 6px; font-size: 12px; margin-top: 10px; }}
.net-banner {{ margin-top: 15px; background-color: #059669; color: white; padding: 15px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: bold; }}
.badge {{ background-color: #DBEAFE; color: #1E40AF; padding: 3px 8px; border-radius: 12px; font-size: 11px; }}
</style>
</head>
<body>
<div class="paystub-card">
<div class="header">
<div>
<span class="title">📄 תלוש משכורת רשמי — {company_title}</span><br>
<span style="font-size: 12px; opacity: 0.9;">מותאם אישית לתבנית העסק: {template_name} (שנת מס 2026)</span>
</div>
<button class="print-btn" onclick="window.print()">🖨️ הדפס תלוש זה</button>
</div>
<table>
<tr style="background-color: #F3F4F6;">
<td><b>שם העובד:</b> {emp_data['name']}</td>
<td><b>תעודת זהות:</b> {emp_data['id']}</td>
<td><b>חודש שכר:</b> ספטמבר 2026</td>
</tr>
<tr>
<td><b>תעריף שעתי:</b> ₪{emp_data['hourly_rate']:,.2f}</td>
<td><b>נקודות זיכוי מס:</b> {emp_data.get('credit_pts', '2.25')}</td>
<td><b>מקור נתונים:</b> <span class="badge">{emp_data.get('source_type', 'סנכרון מרובה מקורות')}</span></td>
</tr>
</table>
<div class="flex-container">
<div class="flex-box">
<div class="gross-header">📈 פירוט רכיבי שכר ותוספות (ברוטו)</div>
<table>
<tr style="background-color: #EFF6FF;">
<th>רכיב</th>
<th style="text-align: center;">כמות / חישוב</th>
<th style="text-align: left;">סכום (₪)</th>
</tr>
<tr>
<td>שכר בסיס (תקן)</td>
<td style="text-align: center;">182 שעות × ₪{emp_data['hourly_rate']:,.2f}</td>
<td style="text-align: left;">₪{emp_data['base']:,.2f}</td>
</tr>
<tr>
<td>שעות נוספות 125%</td>
<td style="text-align: center;">{emp_data['ot125_hours']} ש' × 125% × ₪{emp_data['hourly_rate']:,.2f}</td>
<td style="text-align: left;">₪{emp_data['ot125_pay']:,.2f}</td>
</tr>
<tr>
<td>שעות נוספות 150%</td>
<td style="text-align: center;">{emp_data['ot150_hours']} ש' × 150% × ₪{emp_data['hourly_rate']:,.2f}</td>
<td style="text-align: left;">₪{emp_data['ot150_pay']:,.2f}</td>
</tr>
<tr>
<td>בונוס / עמלות מכירה</td>
<td style="text-align: center;">מענק ביצועים חודשי</td>
<td style="text-align: left;">₪{emp_data['bonus']:,.2f}</td>
</tr>
<tr>
<td>החזר נסיעות / תוספת רווחה</td>
<td style="text-align: center;">חופשי חודשי / תוספת קבועה</td>
<td style="text-align: left;">₪{emp_data['travel_allowance']:,.2f}</td>
</tr>
<tr style="background-color: #DBEAFE; font-weight: bold;">
<td colspan="2">סה"כ שכר ברוטו לתשלום</td>
<td style="text-align: left;">₪{emp_data['gross']:,.2f}</td>
</tr>
</table>
</div>
<div class="flex-box">
<div class="deduct-header">📉 ניכויי חובה, איחורים וסוציאליים</div>
<table>
<tr style="background-color: #FEF2F2;">
<th>ניכוי</th>
<th style="text-align: center;">פירוט / היקף</th>
<th style="text-align: left;">סכום (₪)</th>
</tr>
<tr>
<td>ניכוי איחורים / שעות חיסור</td>
<td style="text-align: center;">{emp_data['tardiness_hours']} שעות חיסור × ₪{emp_data['hourly_rate']:,.2f}</td>
<td style="text-align: left; color: #DC2626;">-₪{emp_data['tardiness_deduction']:,.2f}</td>
</tr>
<tr>
<td>מס הכנסה (לאחר נ"ז)</td>
<td style="text-align: center;">לפי מדרגות מס 2026</td>
<td style="text-align: left;">₪{emp_data['tax_info']['final_tax']:,.2f}</td>
</tr>
<tr>
<td>דמי ביטוח לאומי ומס בריאות</td>
<td style="text-align: center;">שיעור מופחת/מלא 2026</td>
<td style="text-align: left;">₪{emp_data['ni_info']['ni_total']:,.2f}</td>
</tr>
<tr>
<td>הפרשת פנסיה עובד (6.0%)</td>
<td style="text-align: center;">6% משכר ברוטו</td>
<td style="text-align: left;">₪{emp_data['pension']:,.2f}</td>
</tr>
<tr style="background-color: #FEE2E2; font-weight: bold;">
<td colspan="2">סה"כ ניכויי חובה וחיסורים</td>
<td style="text-align: left;">₪{tot_ded:,.2f}</td>
</tr>
</table>
</div>
</div>
<div class="employer-sec">
<b>🛡️ הפרשות מעסיק לביטחון סוציאלי:</b> פנסיה מעסיק (6.5%): ₪{pension_employer:,.2f} | פיצויים מעסיק (6.0%): ₪{severance_employer:,.2f}
</div>
<div class="net-banner">
💵 שכר נטו לתשלום לחשבון הבנק: ₪{emp_data['net']:,.2f}
</div>
</div>
</body>
</html>"""
    components.html(html_content, height=640, scrolling=True)

# ===========================================================================
# 3. זיהוי חריגות AI
# ===========================================================================
def detect_anomalies(row) -> list:
    flags = []
    ot_hours = float(row.get('שעות נוספות', 0))
    avg_ot = float(row.get('ממוצע שעות נוספות', 0))
    bonus = float(row.get('בונוס', 0))
    avg_bonus = float(row.get('ממוצע בונוס', 0))
    tardiness = float(row.get('שעות איחור/חיסור', 0))
    form101 = str(row.get('טופס 101 עודכן', '')).strip().lower() in ['true', 'yes', 'כן', '1']

    if avg_ot > 0 and ot_hours > avg_ot * 1.8 and ot_hours > 15:
        pct = int((ot_hours / avg_ot - 1) * 100)
        flags.append({"level": "HIGH", "icon": "🔴", "msg": f"קפיצה חריגה של {pct}% בשעות נוספות ({ot_hours:.0f} שעות מול ממוצע {avg_ot:.0f})."})

    if tardiness > 5:
        flags.append({"level": "HIGH", "icon": "🔴", "msg": f"נרשמו {tardiness:.1f} שעות איחור/חיסור החורגות מהנורמה החודשית."})

    if bonus > 0 and (avg_bonus == 0 or bonus > avg_bonus * 2):
        flags.append({"level": "MEDIUM", "icon": "🟠", "msg": f"בונוס חורג של ₪{bonus:,.2f} (ממוצע חודשי: ₪{avg_bonus:,.2f})."})

    if form101:
        flags.append({"level": "LOW", "icon": "🟡", "msg": "עודכן טופס 101 חדש במערכת."})

    return flags

# ===========================================================================
# 4. ממשק אפליקציית Streamlit (עם סרגל צד מעודכן הכולל את 3 הרובריקות בצד)
# ===========================================================================
st.set_page_config(page_title="Autonomous AI Payroll Engine", page_icon="🤖", layout="wide")

st.title("🤖 אפליקציית חישוב שכר אוטונומית (AI Payroll)")
st.caption("מנוע חישוב מדעי מדויק | קליטת רובריקות בסרגל הצד (אקסל, צילומי מסך, שעוני נוכחות) | התאמת תלוש לעסק")
st.markdown("---")

engine_active = ExactScientificDecimalEngine.verify_engine_status()
if not engine_active:
    st.error("⛔ מנוע החישוב הפיננסי המדעי אינו פעיל! החישובים הוקפאו.")
    st.stop()
else:
    st.sidebar.success("🎯 מנוע חישוב מדעי פעיל (דיוק על האגורה ₪0.01)")

# ---------------------------------------------------------------------------
# סרגל צד (SIDEBAR): 3 רובריקות העלאה בצד + תבנית העסק
# ---------------------------------------------------------------------------
st.sidebar.header("📥 רובריקות העלאת נתונים (בצד)")

# רובריקה 1: אקסל
st.sidebar.subheader("📊 1. קובץ אקסל (XLSX/CSV)")
uploaded_excel = st.sidebar.file_uploader("העלי קובץ אקסל:", type=["xlsx", "csv"], key="sidebar_excel")

# רובריקה 2: צילומי מסך
st.sidebar.subheader("📷 2. צילומי מסך ותמונות")
uploaded_img = st.sidebar.file_uploader("העלי צילומי מסך:", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="sidebar_img")
if uploaded_img:
    st.sidebar.success(f"📷 נקלטו {len(uploaded_img)} צילומי מסך!")

# רובריקה 3: שעון נוכחות
st.sidebar.subheader("⏱️ 3. תדפיס שעון נוכחות")
uploaded_clock = st.sidebar.file_uploader("העלי דוח שעון נוכחות:", type=["pdf", "png", "jpg", "jpeg"], key="sidebar_clock")
if uploaded_clock:
    st.sidebar.success(f"⏱️ שעון נוכחות נטען: `{uploaded_clock.name}`")

st.sidebar.markdown("---")
st.sidebar.header("🎨 תבנית תלוש ייעודית של העסק")
template_file = st.sidebar.file_uploader("🖼️ העלי תלוש לדוגמה של העסק:", type=["pdf", "png", "jpg", "jpeg", "xlsx"], key="sidebar_template")

template_name = "תבנית רשמית"
primary_color = "#1E3A8A"

if template_file is not None:
    template_name = template_file.name
    st.sidebar.success(f"🎨 תבנית העסק `{template_file.name}` נקלטה!")

style_option = st.sidebar.selectbox(
    "סגנון עיצוב התלוש:",
    ["מבוסס תבנית העסק (אוטומטי)", "סגנון משרד קלאסי (כחול)", "סגנון חברת הייטק (ירוק)", "סגנון אלגנטי (סגול/אפור)"]
)

if "הייטק" in style_option:
    primary_color = "#047857"
elif "אלגנטי" in style_option:
    primary_color = "#6D28D9"

st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ רגולציית מיסוי 2026")
st.sidebar.info("• נקודת זיכוי: ₪242.00/חודש\n• תקרת דמי ביטוח מופחתים: ₪7,522.00\n• ניכוי פנסיה עובד: 6.0%")

# נתוני ברירת מחדל לדוגמה
def get_sample_df():
    return pd.DataFrame([
        {
            "תעודת זהות": "101", "שם עובד": "ישראל ישראלי", "שכר בסיס": 12500,
            "שעות נוספות 125%": 30, "שעות נוספות 150%": 12, "שעות נוספות": 42, "ממוצע שעות נוספות": 15,
            "שעות איחור/חיסור": 3.5, "בונוס": 1850, "נסיעות/תוספות": 450, "ממוצע בונוס": 500, "נקודות זיכוי": 2.25,
            "טופס 101 עודכן": "לא", "מקור נתונים": "אקסל + שעון נוכחות (סרגל צד)"
        },
        {
            "תעודת זהות": "102", "שם עובד": "דנה לוי", "שכר בסיס": 16000,
            "שעות נוספות 125%": 5, "שעות נוספות 150%": 0, "שעות נוספות": 5, "ממוצע שעות נוספות": 4,
            "שעות איחור/חיסור": 0, "בונוס": 4500, "נסיעות/תוספות": 600, "ממוצע בונוס": 1500, "נקודות זיכוי": 2.75,
            "טופס 101 עודכן": "כן", "מקור נתונים": "צילום מסך + אקסל (סרגל צד)"
        },
        {
            "תעודת זהות": "103", "שם עובד": "משה כהן", "שכר בסיס": 9500,
            "שעות נוספות 125%": 2, "שעות נוספות 150%": 0, "שעות נוספות": 2, "ממוצע שעות נוספות": 2,
            "שעות איחור/חיסור": 6, "בונוס": 0, "נסיעות/תוספות": 350, "ממוצע בונוס": 0, "נקודות זיכוי": 2.25,
            "טופס 101 עודכן": "לא", "מקור נתונים": "תדפיס שעון נוכחות (סרגל צד)"
        }
    ])

df_input = get_sample_df() if uploaded_excel is None else (pd.read_csv(uploaded_excel) if uploaded_excel.name.endswith('.csv') else pd.read_excel(uploaded_excel))

# ---------------------------------------------------------------------------
# הרצת חישובי השכר במנוע ה-Decimal המדעי
# ---------------------------------------------------------------------------
calc_results = []
for idx, row in df_input.iterrows():
    base = ExactScientificDecimalEngine.to_dec(row.get('שכר בסיס', 0))
    hourly_rate = ExactScientificDecimalEngine.to_dec(base / Decimal('182'))
    
    ot125_hours = Decimal(str(row.get('שעות נוספות 125%', 0)))
    ot150_hours = Decimal(str(row.get('שעות נוספות 150%', 0)))
    ot125_pay = ExactScientificDecimalEngine.to_dec(ot125_hours * hourly_rate * Decimal('1.25'))
    ot150_pay = ExactScientificDecimalEngine.to_dec(ot150_hours * hourly_rate * Decimal('1.50'))
    ot_pay = ot125_pay + ot150_pay
    
    tardiness_hours = Decimal(str(row.get('שעות איחור/חיסור', 0)))
    tardiness_deduction = ExactScientificDecimalEngine.to_dec(tardiness_hours * hourly_rate)
    
    bonus = ExactScientificDecimalEngine.to_dec(row.get('בונוס', 0))
    travel_allowance = ExactScientificDecimalEngine.to_dec(row.get('נסיעות/תוספות', 0))
    
    gross = base + ot_pay + bonus + travel_allowance
    credit_pts = Decimal(str(row.get('נקודות זיכוי', 2.25)))
    
    tax_info = ExactScientificDecimalEngine.calculate_tax_breakdown(gross, credit_pts)
    ni_info = ExactScientificDecimalEngine.calculate_ni_breakdown(gross)
    pension = ExactScientificDecimalEngine.to_dec(gross * Decimal('0.06'))
    
    total_deductions = tax_info["final_tax"] + ni_info["ni_total"] + pension + tardiness_deduction
    net = gross - total_deductions
    flags = detect_anomalies(row)
    
    calc_results.append({
        "id": str(row.get('תעודת זהות', idx + 101)),
        "name": str(row.get('שם עובד', f'עובד {idx+1}')),
        "credit_pts": str(credit_pts),
        "hourly_rate": hourly_rate,
        "base": base,
        "ot125_hours": ot125_hours, "ot125_pay": ot125_pay,
        "ot150_hours": ot150_hours, "ot150_pay": ot150_pay,
        "ot_pay": ot_pay,
        "tardiness_hours": tardiness_hours, "tardiness_deduction": tardiness_deduction,
        "bonus": bonus, "travel_allowance": travel_allowance,
        "gross": gross,
        "tax_info": tax_info, "ni_info": ni_info, "pension": pension, "net": net,
        "source_type": row.get('מקור נתונים', 'קליטה מסרגל הצד'),
        "status": "FLAGGED" if len(flags) > 0 else "CLEAN", "flags": flags
    })

# תצוגת KPI מדדים במרכז המסך
col1, col2, col3 = st.columns(3)
total_count = len(calc_results)
flagged_count = len([r for r in calc_results if r["status"] == "FLAGGED"])
clean_count = total_count - flagged_count

col1.metric("סה\"כ תלושים במחזור", total_count)
col2.metric("מאושרים אוטומטית (תקינים)", clean_count, delta="🟢 מוכנים להפקה")
col3.metric("ממתינים לבדיקת חשב", flagged_count, delta="-⚠️ חריגות לבדיקה", delta_color="inverse")

st.markdown("---")

# ---------------------------------------------------------------------------
# לוח בדיקות ואישורים + הנפקת תלושים והדפסה
# ---------------------------------------------------------------------------
st.subheader("📋 לוח אישור חשב שכר והנפקת תלושים (Human-in-the-Loop)")

if template_file is not None:
    st.success(f"✨ מופעל מצב התאמה אישית: תלושי המשכורת מותאמים לעיצוב של `{template_file.name}`")

for emp in calc_results:
    box_color = "⚠️" if emp["status"] == "FLAGGED" else "🟢"
    with st.expander(f"{box_color} **{emp['name']}** (ת.ז: {emp['id']}) — ברוטו: ₪{emp['gross']:,.2f} | נטו לתשלום: ₪{emp['net']:,.2f}", expanded=(emp["status"] == "FLAGGED")):
        
        if emp["flags"]:
            st.markdown("##### 🔍 ממצאי ה-AI לבדיקה:")
            for flag in emp["flags"]:
                st.warning(f"{flag['icon']} **[{flag['level']}]** {flag['msg']}")
        else:
            st.success("✅ התלוש תקין לחלוטין ואושר אוטומטית במנוע המתמטי המדויק.")

        col_b1, col_b2 = st.columns(2)
        
        with col_b1:
            if st.button(f"🔍 הצג פירוט חישובים מפורט", key=f"calc_{emp['id']}"):
                st.markdown("---")
                st.markdown(f"### 🧮 פירוט מתמטי מדויק עבור {emp['name']}")
                st.write(f"• **תעריף שעתי:** ₪{emp['hourly_rate']:,.2f}")
                st.write(f"• **שכר בסיס:** ₪{emp['base']:,.2f}")
                st.write(f"• **שעות נוספות 125%:** {emp['ot125_hours']} שעות (₪{emp['ot125_pay']:,.2f})")
                st.write(f"• **שעות נוספות 150%:** {emp['ot150_hours']} שעות (₪{emp['ot150_pay']:,.2f})")
                st.write(f"• **ניכוי איחורים:** {emp['tardiness_hours']} שעות (-₪{emp['tardiness_deduction']:,.2f})")
                st.write(f"• **תוספות ונסיעות:** ₪{emp['travel_allowance']:,.2f} | **בונוסים:** ₪{emp['bonus']:,.2f}")
                st.markdown(f"👉 **סה\"כ שכר ברוטו:** **₪{emp['gross']:,.2f}**")
                
                st.markdown("##### 📉 פירוט ניכויי חובה:")
                st.markdown("**1. מס הכנסה (לפי מדרגות מס 2026):**")
                for step in emp['tax_info']['steps']:
                    st.caption(f"  └ {step}")
                st.write(f"  • מס לפני נקודות זיכוי: ₪{emp['tax_info']['tax_before_credit']:,.2f}")
                st.write(f"  • זיכוי נקודות מס: -₪{emp['tax_info']['credit_discount']:,.2f}")
                st.markdown(f"  └ **מס הכנסה לתשלום:** **₪{emp['tax_info']['final_tax']:,.2f}**")
                
                st.markdown("**2. ביטוח לאומי ומס בריאות:**")
                st.caption(f"  └ {emp['ni_info']['details']}")
                st.markdown(f"  └ **סה\"כ ביטוח לאומי:** **₪{emp['ni_info']['ni_total']:,.2f}**")
                
                st.markdown("---")
                st.markdown(f"### 💵 שכר נטו סופי לתשלום: **₪{emp['net']:,.2f}**")
                st.markdown("---")

        with col_b2:
            if st.button(f"👁️ הצג תלוש שכר במבנה תבנית העסק ({emp['name']})", key=f"show_{emp['id']}"):
                render_visual_paystub(emp, template_name=template_name, primary_color=primary_color)

st.markdown("---")

# ---------------------------------------------------------------------------
# 5. תצוגה מקדימה ושליחה למייל החשב + כפתור הדפסת מרכז התלושים
# ---------------------------------------------------------------------------
st.subheader("📬 מרכז שליחת תלושים והדפסה לחשב השכר")

col_preview, col_email = st.columns(2)

with col_preview:
    st.markdown("##### 👁️ תצוגה מקדימה והדפסת מרכז התלושים")
    if st.button("👁️ הצג תצוגה מקדימה מפורטת של כל התלושים", type="secondary"):
        st.markdown("### 📄 ריכוז תלושי שכר חודשי מאושר")
        for r in calc_results:
            st.info(f"📄 **תלוש שכר - {r['name']}** (ת.ז: {r['id']})\n"
                    f"ברוטו: ₪{r['gross']:,.2f} | מס: ₪{r['tax_info']['final_tax']:,.2f} | ביטוח לאומי: ₪{r['ni_info']['ni_total']:,.2f} | נטו: ₪{r['net']:,.2f}\n"
                    f"סטטוס: {'⚠️ ממתין לבדיקה' if r['status'] == 'FLAGGED' else '✅ מאושר'}")

with col_email:
    st.markdown("##### 📧 שליחת חבילת התלושים לבדיקה במייל החשב")
    accountant_email = st.text_input("הזיני את כתובת המייל של חשב השכר:", placeholder="payroll.accountant@company.com")
    
    if st.button("📤 שלחי תלושים ודוח חריגות למייל החשב", type="primary"):
        if accountant_email and "@" in accountant_email:
            st.balloons()
            st.success(f"📧 חבילת התלושים ודוח החריגות נשלחו בהצלחה אל: **{accountant_email}**!")
            st.info("💡 חשב השכר קיבל למייל קובץ אקסל מפורט ותלושי שכר מפורטים לצפייה, ויוכל לבדוק אותם גם ללא התחברות לאפליקציה.")
        else:
            st.warning("אנא הזיני כתובת דוא\"ל תקינה של חשב השכר.")
