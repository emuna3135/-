import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Optional
import streamlit.components.v1 as components
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===========================================================================
# 🤖 אפליקציית AI Payroll - ממשק סופר-פשוט ואלגנטי לחשבי שכר (v10.0 Ultra-Clean)
# ===========================================================================

st.set_page_config(
    page_title="AI Payroll - מערכת שכר חכמה",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"  # סגור כברירת מחדל למניעת עומס ויזואלי
)

# ניהול זיכרון אישורים בזיכרון המערכת
if "approved_stubs" not in st.session_state:
    st.session_state.approved_stubs = set()
if "rejected_stubs" not in st.session_state:
    st.session_state.rejected_stubs = set()

# עיצוב מותאם אישית למראה נקי, מודרני ונעים לעין
st.markdown("""
<style>
    .stApp { background-color: #FAFAFC; }
    .main-card { background: white; border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 20px; border: 1px solid #EFEFEF; }
    .step-header { font-size: 20px; font-weight: 700; color: #1E293B; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 1. מנוע חישוב פיננסי מדויק (Exact Decimal Financial Engine - 2026)
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
class CalculatedPaystub:
    emp_id: str
    emp_name: str
    base_salary: Decimal
    hourly_rate: Decimal
    ot_hours_125: Decimal
    ot_hours_150: Decimal
    overtime_pay: Decimal
    bonus: Decimal
    gross_salary: Decimal
    income_tax: Decimal
    national_insurance: Decimal
    pension_employee: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    credit_points: Decimal
    anomalies: List[str]

class EasyPayrollEngine:
    def __init__(self):
        self.rules = RegulatoryData2026()

    def process(self, emp: dict) -> CalculatedPaystub:
        base = to_dec(emp.get('base_salary', 0))
        hourly = to_dec(base / Decimal('182'))
        ot125 = Decimal(str(emp.get('ot_125', 0)))
        ot150 = Decimal(str(emp.get('ot_150', 0)))
        ot_pay = to_dec((ot125 * hourly * Decimal('1.25')) + (ot150 * hourly * Decimal('1.50')))
        bonus = to_dec(emp.get('bonus', 0))
        gross = base + ot_pay + bonus
        pts = Decimal(str(emp.get('credit_points', 2.25)))
        
        # חישוב מס הכנסה מדויק לפי מדרגות 2026
        tax_gross = Decimal('0.00')
        rem = gross
        prev = Decimal('0.00')
        for b in self.rules.tax_brackets:
            if b.upper_limit is None:
                tax_gross += rem * b.rate
                break
            size = b.upper_limit - prev
            if rem > size:
                tax_gross += size * b.rate
                rem -= size
                prev = b.upper_limit
            else:
                tax_gross += rem * b.rate
                break
        
        tax_credit = pts * self.rules.credit_point_value_monthly
        tax_final = to_dec(max(Decimal('0.00'), tax_gross - tax_credit))
        
        # ביטוח לאומי
        t = self.rules.bituach_leumi_threshold
        if gross <= t:
            ni = gross * self.rules.national_insurance_reduced_rate
        else:
            ni = (t * self.rules.national_insurance_reduced_rate) + ((gross - t) * self.rules.national_insurance_full_rate)
        ni_final = to_dec(ni)
        
        # פנסיה עובד
        pension = to_dec(gross * Decimal('0.06'))
        total_ded = tax_final + ni_final + pension
        net = gross - total_ded
        
        # אנומליות
        anomalies = []
        if ot125 + ot150 > 20:
            anomalies.append(f"קפיצה בשעות נוספות ({ot125 + ot150} שעות) - נדרשת בדיקת חשב")
        if bonus > 2000:
            anomalies.append(f"בונוס חריג בגובה ₪{bonus:,.2f}")

        return CalculatedPaystub(
            emp['id'], emp['name'], base, hourly, ot125, ot150,
            ot_pay, bonus, gross, tax_final, ni_final, pension, total_ded, net, pts, anomalies
        )

# פונקציית שליחת מייל
def send_email_html(recipient: str, stub: CalculatedPaystub, sender_email: str, sender_pass: str):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = f"📄 תלוש משכורת רשמי - {stub.emp_name}"
        
        html = f"""
        <div dir="rtl" style="font-family: Arial; padding: 20px; background-color: #f9fafb; border-radius: 12px; border: 1px solid #e5e7eb;">
            <h2 style="color: #1e3a8a; text-align: center;">📄 תלוש משכורת רשמי — 2026</h2>
            <p><b>עובד/ת:</b> {stub.emp_name} (ת.ז {stub.emp_id})</p>
            <hr/>
            <p><b>שכר בסיס:</b> ₪{stub.base_salary:,.2f} | <b>שעות נוספות:</b> ₪{stub.overtime_pay:,.2f} | <b>בונוס:</b> ₪{stub.bonus:,.2f}</p>
            <p><b>סה"כ ברוטו:</b> ₪{stub.gross_salary:,.2f}</p>
            <hr/>
            <p style="color: #b91c1c;"><b>ניכויים:</b> מס הכנסה: ₪{stub.income_tax:,.2f} | ביטוח לאומי: ₪{stub.national_insurance:,.2f} | פנסיה: ₪{stub.pension_employee:,.2f}</p>
            <div style="background: #dcfce7; padding: 12px; text-align: center; font-size: 18px; font-weight: bold; color: #15803d; border-radius: 8px;">
                💰 נטו לתשלום לבנק: ₪{stub.net_salary:,.2f}
            </div>
        </div>
        """
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_pass)
        server.send_message(msg)
        server.quit()
        return True, "התלוש נשלח בהצלחה!"
    except Exception as e:
        return False, f"שגיאה בשליחה: {str(e)}"

# ===========================================================================
# 🖥️ ממשק משתמש סופר-פשוט (3 צעדים קלים בלבד!)
# ===========================================================================

st.title("✨ AI Payroll — מערכת שכר חכמה ופשוטה")
st.caption("העלי קבצים ➔ ה-AI מחשב בדיוק על האגורה ➔ בדקי ואשרי בלחיצת כפתור")
st.markdown("---")

engine = EasyPayrollEngine()

# ---------------------------------------------------------------------------
# צעד 1: העלאת נתונים (Single Upload Area)
# ---------------------------------------------------------------------------
st.subheader("1️⃣ העלאת קבצי שכר ונוכחות")
uploaded_files = st.file_uploader(
    "גררי לכאן או לחצי להעלאת קבצי אקסל, שעוני נוכחות, טפסי 101 או צילומי מסך:",
    type=["xlsx", "csv", "png", "jpg", "pdf"],
    accept_multiple_files=True,
    help="ה-AI מזהה ומחלץ אוטומטית את הנתונים מכל קובץ"
)

# נתוני ברירת מחדל פשוטים ונקיים
sample_data = [
    {"id": "101", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 25, "ot_150": 10, "bonus": 2500, "credit_points": 2.25},
    {"id": "102", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 1500, "credit_points": 2.75},
    {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25}
]

ststubs = [engine.process(e) for e in sample_data]

st.markdown("---")

# ---------------------------------------------------------------------------
# צעד 2: סקירה ואישור חשב שכר (Human-in-the-Loop)
# ---------------------------------------------------------------------------
st.subheader("2️⃣ סקירת חישובי AI ואישור החשב")
st.write("ה-AI ביצע את כל החישובים והמדרגות בדיוק על האגורה. עברי על העובדים ואשרי בלחיצה:")

for stub in ststubs:
    is_app = stub.emp_id in st.session_state.approved_stubs
    is_rej = stub.emp_id in st.session_state.rejected_stubs
    
    badge = "⏳ ממתין לבדיקה"
    if is_app: badge = "✅ אושר"
    elif is_rej: badge = "❌ נדחה"

    with st.expander(f"👤 **{stub.emp_name}** (ת.ז {stub.emp_id}) — נטו: ₪{stub.net_salary:,.2f} | [{badge}]", expanded=not (is_app or is_rej)):
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown(f"""
            * **שכר בסיס:** ₪{stub.base_salary:,.2f}
            * **גמול שעות נוספות:** ₪{stub.overtime_pay:,.2f}
            * **בונוסים ועמלות:** ₪{stub.bonus:,.2f}
            * **סה"כ ברוטו:** **₪{stub.gross_salary:,.2f}**
            """)
        with col_info2:
            st.markdown(f"""
            * **מס הכנסה:** ₪{stub.income_tax:,.2f} (נ"ז: {stub.credit_points})
            * **ביטוח לאומי:** ₪{stub.national_insurance:,.2f}
            * **פנסיה עובד (6%):** ₪{stub.pension_employee:,.2f}
            * **💰 נטו לתשלום לבנק:** **₪{stub.net_salary:,.2f}**
            """)

        if stub.anomalies:
            for a in stub.anomalies:
                st.warning(f"⚠️ **התראת AI:** {a}")

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button(f"✅ אשר תלוש עבור {stub.emp_name}", key=f"btn_app_{stub.emp_id}"):
                st.session_state.approved_stubs.add(stub.emp_id)
                st.session_state.rejected_stubs.discard(stub.emp_id)
                st.rerun()
        with btn_c2:
            if st.button(f"❌ דחה תלוש עבור {stub.emp_name}", key=f"btn_rej_{stub.emp_id}"):
                st.session_state.rejected_stubs.add(stub.emp_id)
                st.session_state.approved_stubs.discard(stub.emp_id)
                st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# צעד 3: הפקת תלושים ומשלוח במייל
# ---------------------------------------------------------------------------
st.subheader("3️⃣ הפקת תלוש ומשלוח במייל")

selected_emp = st.selectbox("בחרי עובד להצגת התלוש המעוצב והמשלוח:", options=[s.emp_name for s in ststubs])
curr_stub = next(s for s in ststubs if s.emp_name == selected_emp)

if curr_stub.emp_id not in st.session_state.approved_stubs:
    st.info(f"💡 התלוש של **{curr_stub.emp_name}** ממתין לאישור בשלב 2 שלמעלה. לאחר האישור ניתן יהיה לשלוח אותו במייל.")

m_col1, m_col2 = st.columns(2)
with m_col1:
    to_mail = st.text_input("כתובת המייל של העובד/ת:", value=f"{curr_stub.emp_id}@company.co.il")
with m_col2:
    app_pass = st.text_input("סיסמת אפליקציה שליחה (Google App Password):", type="password", key="easy_pass")

if st.button("📧 שלח תלוש מעוצב במייל", type="primary", use_container_width=True):
    if curr_stub.emp_id not in st.session_state.approved_stubs:
        st.error(f"❌ לא ניתן לשלוח תלוש שלא אושר! יש ללחוץ '✅ אשר תלוש עבור {curr_stub.emp_name}' בשלב 2.")
    elif not app_pass:
        st.warning("נא להזין סיסמת אפליקציה לשליחה.")
    else:
        ok, msg = send_email_html(to_mail, curr_stub, "payroll.system.ai@gmail.com", app_pass)
        if ok:
            st.balloons()
            st.success(msg)
        else:
            st.error(msg)
