
import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import streamlit.components.v1 as components
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===========================================================================
# 🤖 אפליקציית AI Payroll - גרסה דינמית ומגיבה בזמן אמת (v13.0 Reactive)
# ===========================================================================

st.set_page_config(
    page_title="AI Payroll - מערכת שכר חכמה ומגיבה",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------------
# 0. הגדרת כיוון מימין לשמאל (RTL) מלאה
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], .main, .stApp {
        direction: rtl;
        text-align: right;
    }
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, div, span, caption {
        direction: rtl !important;
        text-align: right !important;
    }
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"], .stButton button, .stFileUploader {
        direction: rtl !important;
        text-align: right !important;
    }
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
    try:
        if pd.isna(val) or val == "" or val is None:
            return Decimal('0.00')
        cleaned = str(val).replace('₪', '').replace(',', '').strip()
        return Decimal(cleaned).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')

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
        hourly = to_dec(base / Decimal('182')) if base > 0 else Decimal('0.00')
        ot125 = to_dec(emp.get('ot_125', 0))
        ot150 = to_dec(emp.get('ot_150', 0))
        ot125_pay = to_dec(ot125 * hourly * Decimal('1.25'))
        ot150_pay = to_dec(ot150 * hourly * Decimal('1.50'))
        ot_pay = ot125_pay + ot150_pay
        bonus = to_dec(emp.get('bonus', 0))
        gross = base + ot_pay + bonus
        pts = to_dec(emp.get('credit_points', 2.25))
        if pts == Decimal('0.00'):
            pts = Decimal('2.25')
        
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
        
        anomalies = []
        if ot125 + ot150 > 20:
            anomalies.append(f"קפיצה בשעות נוספות ({ot125 + ot150} שעות) - מומלץ לבדוק")
        if bonus > 2000:
            anomalies.append(f"בונוס חריג בגובה ₪{bonus:,.2f}")

        return CalculatedPaystub(
            str(emp.get('id', '100')), str(emp.get('name', 'עובד')), base, hourly, ot125, ot150,
            ot125_pay, ot150_pay, ot_pay, bonus, gross, to_dec(tax_gross),
            to_dec(tax_credit), tax_final, ni_final, pension, total_ded, net, pts, anomalies
        )

# ---------------------------------------------------------------------------
# פונקציית פענוח קבצים (CSV / Excel Parsing)
# ---------------------------------------------------------------------------
def parse_uploaded_file(uploaded_file) -> List[Dict[str, Any]]:
    parsed_records = []
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            return []
        
        col_map = {}
        for col in df.columns:
            c_clean = str(col).strip().lower()
            if 'שם' in c_clean or 'name' in c_clean:
                col_map[col] = 'name'
            elif 'תז' in c_clean or 'ת.ז' in c_clean or 'id' in c_clean:
                col_map[col] = 'id'
            elif 'בסיס' in c_clean or 'base' in c_clean or 'שכר' in c_clean:
                col_map[col] = 'base_salary'
            elif '125' in c_clean:
                col_map[col] = 'ot_125'
            elif '150' in c_clean:
                col_map[col] = 'ot_150'
            elif 'בונוס' in c_clean or 'bonus' in c_clean or 'עמלה' in c_clean:
                col_map[col] = 'bonus'
            elif 'זיכוי' in c_clean or 'credit' in c_clean or 'נז' in c_clean or 'נ"ז' in c_clean:
                col_map[col] = 'credit_points'
        
        df_renamed = df.rename(columns=col_map)
        for idx, row in df_renamed.iterrows():
            record = {
                'id': str(row.get('id', idx + 101)),
                'name': str(row.get('name', f"עובד {idx+1}")),
                'base_salary': row.get('base_salary', 10000),
                'ot_125': row.get('ot_125', 0),
                'ot_150': row.get('ot_150', 0),
                'bonus': row.get('bonus', 0),
                'credit_points': row.get('credit_points', 2.25)
            }
            parsed_records.append(record)
    except Exception as e:
        st.error(f"שגיאה בפענוח הקובץ {uploaded_file.name}: {str(e)}")
    return parsed_records

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
# 🖥️ ממשק משתמש דינמי ומגיב בלייב (Live Reactive Interface)
# ===========================================================================

st.title("⚡ AI Payroll — מערכת שכר חכמה ומגיבה בזמן אמת")
st.caption("העלי קובץ אקסל או הקלידי נתונים — החישובים מתעדכנים בלייב בדיוק על האגורה!")
st.markdown("---")

engine = EasyPayrollEngine()

# ---------------------------------------------------------------------------
# צעד 1: העלאת נתונים / הזנה דינמית
# ---------------------------------------------------------------------------
st.subheader("1️⃣ קליטת נתונים (העלאת אקסל/CSV או הזנה ישירה)")

file_col, manual_col = st.columns([2, 1])

with file_col:
    uploaded_file = st.file_uploader(
        "גררי לכאן קובץ אקסל (.xlsx) או CSV עם נתוני העובדים:",
        type=["xlsx", "xls", "csv"],
        key="reactive_uploader"
    )

employees_input_data = []

if uploaded_file is not None:
    parsed_data = parse_uploaded_file(uploaded_file)
    if parsed_data:
        st.success(f"✨ הקובץ **{uploaded_file.name}** נקלט בהצלחה! פוענחו {len(parsed_data)} עובדים והמערכת חישבה אותם בלייב.")
        employees_input_data = parsed_data
else:
    employees_input_data = [
        {"id": "101", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 25, "ot_150": 10, "bonus": 2500, "credit_points": 2.25},
        {"id": "102", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 1500, "credit_points": 2.75},
        {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25}
    ]

with manual_col:
    with st.expander("➕ הוספת עובד/ת חדש/ה בלייב", expanded=False):
        new_name = st.text_input("שם העובד/ת:", value="עובד חדש", key="m_name")
        new_id = st.text_input("ת.ז:", value="104", key="m_id")
        new_base = st.number_input("שכר בסיס (₪):", value=14000.0, step=500.0, key="m_base")
        new_ot125 = st.number_input("שעות 125%:", value=8.0, step=1.0, key="m_ot125")
        new_ot150 = st.number_input("שעות 150%:", value=0.0, step=1.0, key="m_ot150")
        new_bonus = st.number_input("בונוס (₪):", value=1000.0, step=100.0, key="m_bonus")
        new_pts = st.number_input("נקודות זיכוי:", value=2.25, step=0.25, key="m_pts")
        
        if st.button("➕ הוסף לרשימת החישוב", use_container_width=True):
            employees_input_data.append({
                "id": new_id, "name": new_name, "base_salary": new_base,
                "ot_125": new_ot125, "ot_150": new_ot150, "bonus": new_bonus, "credit_points": new_pts
            })
            st.success(f"העובד {new_name} התווסף לחישוב!")

# חישוב התלושים בלייב מתוך הנתונים המעודכנים!
ststubs = [engine.process(e) for e in employees_input_data]

st.markdown("---")

# ---------------------------------------------------------------------------
# צעד 2: הצגת החישובים המפורטים המגיבים בלייב
# ---------------------------------------------------------------------------
st.subheader("2️⃣ חישובי השכר המפורטים והחלטת חשב השכר (חישוב מיידי בלייב)")
st.write("המערכת חישבה את כל הנתונים מתוך הקובץ/ההזנה. לכל עובד יש כפתורי אישור ודחייה אישיים:")

for stub in ststubs:
    is_app = stub.emp_id in st.session_state.approved_stubs
    is_rej = stub.emp_id in st.session_state.rejected_stubs
    
    status_text = "⏳ ממתין לבדיקת חשב"
    if is_app:
        status_text = "✅ אושר ע\"י חשב שכר"
    elif is_rej:
        status_text = "❌ נדחה / הועבר לתיקון"

    with st.container():
        st.markdown(f"### 👤 {stub.emp_name} (ת.ז: {stub.emp_id}) — סטטוס: **{status_text}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **💵 פירוט רכיבי ברוטו:**
            * **שכר בסיס:** ₪{stub.base_salary:,.2f}
            * **תעריף שעתי מחושב:** ₪{stub.hourly_rate:,.2f} / שעה
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
            * **מס הכנסה סופי לתשלום:** ₪{stub.income_tax:,.2f}
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
            if st.button(f"✅ אשר תלוש עבור {stub.emp_name}", key=f"react_app_{stub.emp_id}"):
                st.session_state.approved_stubs.add(stub.emp_id)
                st.session_state.rejected_stubs.discard(stub.emp_id)
                st.rerun()
        with btn_c2:
            if st.button(f"❌ דחה תלוש עבור {stub.emp_name}", key=f"react_rej_{stub.emp_id}"):
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
    app_pass = st.text_input("סיסמת אפליקציה שליחה (Google App Password):", type="password", key="react_pass")

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
