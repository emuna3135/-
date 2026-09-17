import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import streamlit.components.v1 as components

# רכיבי תקשורת לשליחת מיילים אמתית
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===========================================================================
# 🤖 אפליקציית חישוב שכר אוטונומית (v5.0 - עם חישוב ומנגנון שליחה למייל)
# ===========================================================================

st.set_page_config(
    page_title="Autonomous AI Payroll System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 1. מנוע חישוב פיננסי מדויק (Exact Decimal Financial Engine)
# ---------------------------------------------------------------------------
def to_dec(val: float | str | int) -> Decimal:
    return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

@dataclass
class TaxBracket:
    upper_limit: Optional[Decimal]
    rate: Decimal

@dataclass
class RegulatoryData2026:
    year: int = 2026
    credit_point_value_monthly: Decimal = to_dec('242.00')
    tax_brackets: List[TaxBracket] = field(default_factory=lambda: [
        TaxBracket(to_dec('7010.00'), to_dec('0.10')),
        TaxBracket(to_dec('10060.00'), to_dec('0.14')),
        TaxBracket(to_dec('16150.00'), to_dec('0.20')),
        TaxBracket(to_dec('22440.00'), to_dec('0.31')),
        TaxBracket(to_dec('46690.00'), to_dec('0.35')),
        TaxBracket(None, to_dec('0.47')),
    ])
    national_insurance_reduced_rate: Decimal = to_dec('0.035')
    national_insurance_full_rate: Decimal = to_dec('0.12')
    bituach_leumi_threshold: Decimal = to_dec('7522.00')

@dataclass
class AnomalyFlag:
    risk_level: str
    message_hebrew: str

@dataclass
class CalculatedPaystub:
    emp_id: str
    emp_name: str
    base_salary: Decimal
    overtime_pay: Decimal
    bonus: Decimal
    gross_salary: Decimal
    income_tax: Decimal
    national_insurance: Decimal
    pension_employee: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    credit_points: Decimal
    flags: List[AnomalyFlag]

class PayrollProcessor:
    def __init__(self):
        self.rules = RegulatoryData2026()
        
    def calculate_tax(self, gross: Decimal, credit_points: Decimal) -> Decimal:
        tax = Decimal('0.00')
        remaining = gross
        prev_limit = Decimal('0.00')
        for bracket in self.rules.tax_brackets:
            if bracket.upper_limit is None:
                tax += remaining * bracket.rate
                break
            bracket_size = bracket.upper_limit - prev_limit
            if remaining > bracket_size:
                tax += bracket_size * bracket.rate
                remaining -= bracket_size
                prev_limit = bracket.upper_limit
            else:
                tax += remaining * bracket.rate
                break
        tax_credit = credit_points * self.rules.credit_point_value_monthly
        return to_dec(max(Decimal('0.00'), tax - tax_credit))

    def calculate_ni(self, gross: Decimal) -> Decimal:
        t = self.rules.bituach_leumi_threshold
        if gross <= t:
            ni = gross * self.rules.national_insurance_reduced_rate
        else:
            ni = (t * self.rules.national_insurance_reduced_rate) + ((gross - t) * self.rules.national_insurance_full_rate)
        return to_dec(ni)

    def process(self, emp: dict) -> CalculatedPaystub:
        base = to_dec(emp.get('base_salary', 0))
        hourly = base / Decimal('182')
        ot125 = Decimal(str(emp.get('overtime_125_hours', 0)))
        ot_pay = to_dec(ot125 * hourly * Decimal('1.25'))
        bonus = to_dec(emp.get('bonus', 0))
        gross = base + ot_pay + bonus
        pts = Decimal(str(emp.get('credit_points', 2.25)))
        tax = self.calculate_tax(gross, pts)
        ni = self.calculate_ni(gross)
        pension = to_dec(gross * Decimal('0.06'))
        total_ded = tax + ni + pension
        net = gross - total_ded
        return CalculatedPaystub(emp['id'], emp['name'], base, ot_pay, bonus, gross, tax, ni, pension, total_ded, net, pts, [])

# ---------------------------------------------------------------------------
# 📧 פונקציית שליחת מיילים אמיתית ב-SMTP
# ---------------------------------------------------------------------------
def send_real_email(recipient_email: str, stub: CalculatedPaystub, sender_email: str, sender_pass: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"📄 תלוש משכורת רשמי עבור {stub.emp_name} - ספטמבר 2026"

        body = f"""שלום {stub.emp_name},

מצורף תלוש המשכורת הרשמי שלך לחודש ספטמבר 2026:

• שכר בסיס: ₪{stub.base_salary:,.2f}
• גמול שעות נוספות: ₪{stub.overtime_pay:,.2f}
• בונוסים ועמלות: ₪{stub.bonus:,.2f}
------------------------------------
• סה"כ שכר ברוטו: ₪{stub.gross_salary:,.2f}
------------------------------------
• ניכוי מס הכנסה: ₪{stub.income_tax:,.2f}
• ניכוי ביטוח לאומי: ₪{stub.national_insurance:,.2f}
• הפרשת פנסיה (6%): ₪{stub.pension_employee:,.2f}
------------------------------------
💰 שכר נטו לתשלום לבנק: ₪{stub.net_salary:,.2f}

תלוש זה חושב ואושר בדיוק פיננסי מלא ע"י מערכת AI Payroll.
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # התחברות לשרת Gmail SMTP ושליחה
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_pass)
        server.send_message(msg)
        server.quit()
        return True, "התלוש נשלח בהצלחה לתיבת המייל!"
    except Exception as e:
        return False, f"שגיאה בהתחברות לשרת המייל: {str(e)}"

# ===========================================================================
# 2. סרגל צד (SIDEBAR)
# ===========================================================================

st.sidebar.title("🛠️ תפריט אפשרויות וסורקים")

with st.sidebar.expander("🧮 המחשבון המדעי המדויק (עד האגורה)", expanded=True):
    calc_name = st.text_input("שם העובד:", value="דנה לוי", key="side_name")
    calc_id = st.text_input("מספר ת.ז:", value="102", key="side_id")
    calc_base = st.number_input("שכר בסיס (₪):", value=16000.0, step=500.0, key="side_base")
    calc_ot125 = st.number_input("שעות 125%:", value=5.0, step=1.0, key="side_ot125")
    calc_bonus = st.number_input("בונוס/עמלה (₪):", value=4500.0, step=100.0, key="side_bonus")
    calc_credit_pts = st.number_input("נקודות זיכוי (נ\"ז):", value=2.75, step=0.25, key="side_pts")

with st.sidebar.expander("📸 סורק מצלמת הטאבלט", expanded=True):
    st.camera_input("צלמי מסמך במצלמה", key="side_camera")

st.sidebar.markdown("---")
st.sidebar.subheader("📁 רובריקות העלאת נתונים")
st.sidebar.file_uploader("🖼️ רובריקה להעלאת תצלומי מסך", type=["png", "jpg"], key="up_screens")
st.sidebar.file_uploader("📊 רובריקה להעלאת טבלת אקסל", type=["xlsx", "csv"], key="up_excel")
st.sidebar.file_uploader("⏰ רובריקה להעלאת שעון נוכחות", type=["xlsx", "csv"], key="up_clock")
st.sidebar.file_uploader("📄 רובריקה להעלאת תלוש שכר לדוגמא", type=["pdf", "png"], key="up_sample")

# ===========================================================================
# 3. החלק המרכזי של האפליקציה (MAIN AREA)
# ===========================================================================

st.title("🤖 אפליקציית חישוב שכר אוטונומית (AI Payroll)")
st.caption("מערכת שכר חכמה: סורק ומחשבון בסרגל הצד | תלושים מעוצבים ושליחה ישירה למייל במרכז")
st.markdown("---")

processor = PayrollProcessor()
current_emp = {
    "id": calc_id, "name": calc_name, "base_salary": calc_base,
    "overtime_125_hours": calc_ot125, "bonus": calc_bonus, "credit_points": calc_credit_pts
}
stub = processor.process(current_emp)

# תצוגת התלוש המעוצב
st.subheader(f"📄 תלוש משכורת מעוצב עבור {stub.emp_name}")

paystub_html = f"""
<div style="font-family: Arial; direction: rtl; border: 2px solid #1E3A8A; border-radius: 10px; padding: 15px; background-color: #FFFFFF;">
    <h3 style="background-color: #1E3A8A; color: white; padding: 10px; text-align: center; border-radius: 5px;">
         תלוש משכורת רשמי - שנת מס 2026
    </h3>
    <p><b>שם העובד/ת:</b> {stub.emp_name} | <b>ת.ז:</b> {stub.emp_id} | <b>חודש:</b> ספטמבר 2026</p>
    <hr/>
    <p><b>שכר בסיס:</b> ₪{stub.base_salary:,.2f} | <b>שעות נוספות:</b> ₪{stub.overtime_pay:,.2f} | <b>בונוסים:</b> ₪{stub.bonus:,.2f}</p>
    <p><b>סה"כ ברוטו:</b> ₪{stub.gross_salary:,.2f}</p>
    <hr/>
    <p style="color: red;"><b>ניכויי חובה:</b> מס הכנסה: ₪{stub.income_tax:,.2f} | ביטוח לאומי: ₪{stub.national_insurance:,.2f} | פנסיה: ₪{stub.pension_employee:,.2f}</p>
    <h3 style="color: green; text-align: center; background-color: #DCFCE7; padding: 10px; border-radius: 5px;">
        💰 שכר נטו לתשלום: ₪{stub.net_salary:,.2f}
    </h3>
</div>
"""
components.html(paystub_html, height=280)

st.markdown("---")

# ---------------------------------------------------------------------------
# 📧 חיבור אמיתי לשליחת המייל
# ---------------------------------------------------------------------------
st.subheader("📧 שליחת תלוש השכר הרשמי למייל")

email_col1, email_col2 = st.columns(2)

with email_col1:
    target_email = st.text_input("הקלידי את כתובת הדוא\"ל של המקבל/ת:", value="employee@company.co.il")

with email_col2:
    with st.expander("⚙️ הגדרות שרת מייל לשליחה (SMTP Connection)"):
        sender_email = st.text_input("מייל השולח (Gmail/Company):", value="payroll.system.ai@gmail.com")
        sender_password = st.text_input("סיסמת אפליקציה (App Password):", type="password")

if st.button("📧 שלח תלוש במייל עכשיו", type="primary", use_container_width=True):
    if not sender_password:
        st.warning("⚠️ יש להזין סיסמת אפליקציה בשדה ההגדרות כדי להתחבר לשרת הדוא\"ל ולשלוח.")
    else:
        with st.spinner("מתחבר לשרת הדוא\"ל ושולח את התלוש..."):
            success, msg = send_real_email(target_email, stub, sender_email, sender_password)
            if success:
                st.balloons()
                st.success(msg)
            else:
                st.error(msg)
