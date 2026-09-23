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
# 🤖 אפליקציית AI Payroll - ממשק בעברית עם התאמת RTL מלאה (מימין לשמאל)
# ===========================================================================

st.set_page_config(
    page_title="AI Payroll - מערכת שכר חכמה",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------------
# 0. הגדרת כיוון מימין לשמאל (RTL) מלאה עבור הממשק והאלמנטים
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* כיוון כללי מימין לשמאל */
    html, body, [data-testid="stAppViewContainer"], .main, .stApp {
        direction: rtl;
        text-align: right;
    }
    
    /* יישור טקסטים, כותרות ותווים */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, div, span, caption {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* יישור שדות קלט (אינפוטים), תיבות בחירה וכפתורים */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"], .stButton button, .stFileUploader {
        direction: rtl !important;
        text-align: right !important;
    }

    /* יישור כרטיסי המידע */
    .emp-card {
        background: white;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #E2E8F0;
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# ניהול זיכרון אישורים בזיכרון המערכת
if "approved_stubs" not in st.session_state:
    st.session_state.approved_stubs = set()
if "rejected_stubs" not in st.session_state:
    st.session_state.rejected_stubs = set()

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
    overtime_125_pay: Decimal
    overtime_150_pay: Decimal
    overtime_pay: Decimal
    bonus: Decimal
    gross_salary: Decimal
    tax_before_credit: Decimal
    tax_credit_amount: Decimal
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
        ot125_pay = to_dec(ot125 * hourly * Decimal('1.25'))
        ot150_pay = to_dec(ot150 * hourly * Decimal('1.50'))
        ot_pay = ot125_pay + ot150_pay
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
        
        # פנסיה עובד (6%)
        pension = to_dec(gross * Decimal('0.06'))
        total_ded = tax_final + ni_final + pension
        net = gross - total_ded
        
        # אנומליות לזיהוי
        anomalies = []
        if ot125 + ot150 > 20:
            anomalies.append(f"קפיצה בשעות נוספות ({ot125 + ot150} שעות) - מומלץ לבדוק")
        if bonus > 2000:
            anomalies.append(f"בונוס חריג בגובה ₪{bonus:,.2f}")

        return CalculatedPaystub(
            emp['id'], emp['name'], base, hourly, ot125, ot150,
            ot125_pay, ot150_pay, ot_pay, bonus, gross, to_dec(tax_gross),
            to_dec(tax_credit), tax_final, ni_final, pension, total_ded, net, pts, anomalies
        )

# פונקציית שליחת מייל
def send_email_html(recipient: str, stub: CalculatedPaystub, sender_email: str, sender_pass: str):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = f"📄 תלוש משכורת רשמי - {stub.emp_name}"
        
        html = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; padding: 20px; background-color: #f9fafb; border-radius: 12px; border: 1px solid #e5e7eb; text-align: right;">
            <h2 style="color: #1e3a8a; text-align: center;">📄 תלוש משכורת רשמי — שנת מס 2026</h2>
            <p><b>עובד/ת:</b> {stub.emp_name} (ת.ז {stub.emp_id})</p>
            <hr/>
            <p><b>שכר בסיס:</b> ₪{stub.base_salary:,.2f} | <b>גמול שעות נוספות:</b> ₪{stub.overtime_pay:,.2f} | <b>בונוסים:</b> ₪{stub.bonus:,.2f}</p>
            <p><b>סה"כ שכר ברוטו:</b> ₪{stub.gross_salary:,.2f}</p>
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
# 🖥️ ממשק משתמש בעברית בסידור RTL מלא
# ===========================================================================

st.title("✨ AI Payroll — מערכת שכר חכמה ופשוטה לחשבים")
st.caption("ממשק מותאם בעברית (מימין לשמאל) — החישובים והכפתורים מוצגים באופן גלוי וברור")
st.markdown("---")

engine = EasyPayrollEngine()

# ---------------------------------------------------------------------------
# צעד 1: העלאת נתונים
# ---------------------------------------------------------------------------
st.subheader("1️⃣ העלאת קבצי שכר / נוכחות")
uploaded_files = st.file_uploader(
    "גררי לכאן או לחצי להעלאת קבצי אקסל, שעוני נוכחות, טפסי 101 או צילומי מסך:",
    type=["xlsx", "csv", "png", "jpg", "pdf"],
    accept_multiple_files=True
)

# נתוני עובדים לדוגמה
sample_data = [
    {"id": "101", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 25, "ot_150": 10, "bonus": 2500, "credit_points": 2.25},
    {"id": "102", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 1500, "credit_points": 2.75},
    {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25}
]

ststubs = [engine.process(e) for e in sample_data]

st.markdown("---")

# ---------------------------------------------------------------------------
# צעד 2: הצגת החישובים המפורטים וכפתורי אישור/דחייה אישיים לכל עובד
# ---------------------------------------------------------------------------
st.subheader("2️⃣ חישובי השכר המפורטים והחלטת חשב השכר")
st.write("כל הנתונים מחושבים בדיוק על האגורה. לכל עובד יש כפתורי אישור ודחייה אישיים:")

for stub in ststubs:
    is_app = stub.emp_id in st.session_state.approved_stubs
    is_rej = stub.emp_id in st.session_state.rejected_stubs
    
    status_text = "⏳ ממתין לבדיקת חשב"
    if is_app:
        status_text = "✅ אושר ע\"י חשב שכר"
    elif is_rej:
        status_text = "❌ נדחה / הועבר לתיקון"

    # כרטיס גלוי ומלא עבור כל עובד
    with st.container():
        st.markdown(f"### 👤 {stub.emp_name} (ת.ז: {stub.emp_id}) — סטטוס: **{status_text}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **💵 פירוט רכיבי ברוטו:**
            * **שכר בסיס:** ₪{stub.base_salary:,.2f}
            * **תעריף שעתי:** ₪{stub.hourly_rate:,.2f} / שעה
            * **שעות נוספות 125% ({stub.ot_hours_125} שעות):** ₪{stub.overtime_125_pay:,.2f}
            * **שעות נוספות 150% ({stub.ot_hours_150} שעות):** ₪{stub.overtime_150_pay:,.2f}
            * **בונוסים ועמלות:** ₪{stub.bonus:,.2f}
            * **סה"כ שכר ברוטו:** **₪{stub.gross_salary:,.2f}**
            """)
        with col2:
            st.markdown(f"""
            **📉 פירוט ניכויי חובה ומיסוי:**
            * **מס הכנסה לפני זיכוי:** ₪{stub.tax_before_credit:,.2f}
            * **זיכוי מס ({stub.credit_points} נ"ז):** -₪{stub.tax_credit_amount:,.2f}
            * **מס הכנסה סופי:** ₪{stub.income_tax:,.2f}
            * **דמי ביטוח לאומי ומס בריאות:** ₪{stub.national_insurance:,.2f}
            * **הפרשת פנסיה עובד (6%):** ₪{stub.pension_employee:,.2f}
            * **סה"כ ניכויי חובה:** ₪{stub.total_deductions:,.2f}
            """)

        st.markdown(f"### 💰 **שכר נטו לתשלום לבנק: ₪{stub.net_salary:,.2f}**")

        if stub.anomalies:
            for a in stub.anomalies:
                st.warning(f"⚠️ **התראת AI:** {a}")

        st.markdown(f"**החלטת חשב שכר עבור {stub.emp_name}:**")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button(f"✅ אשר תלוש עבור {stub.emp_name}", key=f"rtl_app_{stub.emp_id}"):
                st.session_state.approved_stubs.add(stub.emp_id)
                st.session_state.rejected_stubs.discard(stub.emp_id)
                st.rerun()
        with btn_c2:
            if st.button(f"❌ דחה תלוש עבור {stub.emp_name}", key=f"rtl_rej_{stub.emp_id}"):
                st.session_state.rejected_stubs.add(stub.emp_id)
                st.session_state.approved_stubs.discard(stub.emp_id)
                st.rerun()

        st.markdown("---")

# ---------------------------------------------------------------------------
# צעד 3: הפקת תלוש ומשלוח במייל
# ---------------------------------------------------------------------------
st.subheader("3️⃣ הפקת תלוש מעוצב ומשלוח במייל")

selected_emp = st.selectbox("בחרי עובד להצגת התלוש והמשלוח:", options=[s.emp_name for s in ststubs])
curr_stub = next(s for s in ststubs if s.emp_name == selected_emp)

if curr_stub.emp_id not in st.session_state.approved_stubs:
    st.info(f"💡 התלוש של **{curr_stub.emp_name}** ממתין לאישור בשלב 2 למעלה. בלחיצה על '✅ אשר תלוש עבור {curr_stub.emp_name}' הוא יאושר למשלוח.")

m_col1, m_col2 = st.columns(2)
with m_col1:
    to_mail = st.text_input("כתובת המייל של העובד/ת:", value=f"{curr_stub.emp_id}@company.co.il")
with m_col2:
    app_pass = st.text_input("סיסמת אפליקציה שליחה (Google App Password):", type="password", key="rtl_pass")

if st.button("📧 שלח תלוש מעוצב במייל", type="primary", use_container_width=True):
    if curr_stub.emp_id not in st.session_state.approved_stubs:
        st.error(f"❌ לא ניתן לשלוח תלוש שלא אושר! יש לאשר את התלוש של {curr_stub.emp_name} בשלב 2 למעלה.")
    elif not app_pass:
        st.warning("נא להזין סיסמת אפליקציה לשליחה.")
    else:
        ok, msg = send_email_html(to_mail, curr_stub, "payroll.system.ai@gmail.com", app_pass)
        if ok:
            st.balloons()
            st.success(msg)
        else:
            st.error(msg)
