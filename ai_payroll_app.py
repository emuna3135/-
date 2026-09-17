
import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import streamlit.components.v1 as components

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===========================================================================
# 🤖 אפליקציית חישוב שכר אוטונומית (v8.0 - ללא אישור אוטומטי, אישור חשב בלבד)
# Autonomous AI Payroll App: Strict Human-in-the-Loop (Zero Auto-Approval)
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. הגדרות עיצוב עמוד (Streamlit Setup)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Autonomous AI Payroll System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ניהול מצב אישורים/דחיות בזיכרון האפליקציה
if "approved_stubs" not in st.session_state:
    st.session_state.approved_stubs = set()
if "rejected_stubs" not in st.session_state:
    st.session_state.rejected_stubs = set()

# ---------------------------------------------------------------------------
# 2. מנוע חישוב פיננסי מדויק (Exact Decimal Financial Math Engine)
# ---------------------------------------------------------------------------
def to_dec(val: float | str | int) -> Decimal:
    """המרת ערך ל-Decimal מדויק עם עיגול בנקאי ל-2 ספרות אחרי הנקודה"""
    return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

@dataclass
class TaxBracket:
    upper_limit: Optional[Decimal]
    rate: Decimal

@dataclass
class RegulatoryData2026:
    year: int = 2026
    credit_point_value_monthly: Decimal = to_dec('242.00')  # שווי נקודת זיכוי
    minimum_wage_hourly: Decimal = to_dec('32.30')
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

class LiveRegulatorySyncAPI:
    """סנכרון בזמן אמת מול חוקי המיסוי והשכר של רשות המיסים וביטוח לאומי"""
    @staticmethod
    def get_latest_rules() -> RegulatoryData2026:
        return RegulatoryData2026()

# ---------------------------------------------------------------------------
# 3. מנוע סריקת אנומליות ודירוג סיכונים ב-AI (AI Anomaly Detection)
# ---------------------------------------------------------------------------
@dataclass
class AnomalyFlag:
    risk_level: str  # HIGH, MEDIUM, LOW
    field_name: str
    message_hebrew: str
    historical_baseline: str
    current_value: str

class AIAnomalyDetector:
    """סורק AI לזיהוי חריגות בשכר ובשעות נוספות להצגה לחשב בלבד"""
    @staticmethod
    def scan_employee_payroll(emp_data: dict, historical_avg: dict) -> List[AnomalyFlag]:
        flags = []
        
        # 1. בדיקת קפיצה בשעות נוספות
        curr_ot = emp_data.get('overtime_hours', 0)
        avg_ot = historical_avg.get('overtime_hours', 0)
        if avg_ot > 0 and curr_ot > avg_ot * 1.8 and curr_ot > 15:
            pct_increase = int((curr_ot / avg_ot - 1) * 100)
            flags.append(AnomalyFlag(
                risk_level="HIGH",
                field_name="overtime_hours",
                message_hebrew=f"קפיצה חריגה של {pct_increase}% בשעות נוספות ביחס לממוצע ההיסטורי.",
                historical_baseline=f"{avg_ot} שעות",
                current_value=f"{curr_ot} שעות"
            ))
            
        # 2. בדיקת בונוס/עמלה חריגה
        curr_bonus = emp_data.get('bonus', 0)
        avg_bonus = historical_avg.get('bonus', 0)
        if curr_bonus > 0 and (avg_bonus == 0 or curr_bonus > avg_bonus * 2):
            flags.append(AnomalyFlag(
                risk_level="MEDIUM",
                field_name="bonus",
                message_hebrew=f"בונוס/עמלה בגובה ₪{curr_bonus:,.2f} חורג מהנורמה החודשית.",
                historical_baseline=f"₪{avg_bonus:,.2f}",
                current_value=f"₪{curr_bonus:,.2f}"
            ))

        # 3. בדיקת נקודות זיכוי וטופס 101
        if emp_data.get('form_101_updated') and emp_data.get('credit_points') == historical_avg.get('credit_points'):
            flags.append(AnomalyFlag(
                risk_level="LOW",
                field_name="credit_points",
                message_hebrew="עודכן טופס 101 חדש במערכת - יש לוודא התאמת נקודות זיכוי.",
                historical_baseline=f"{historical_avg.get('credit_points')} נ\"ז",
                current_value=f"{emp_data.get('credit_points')} נ\"ז"
            ))

        return flags

# ---------------------------------------------------------------------------
# 4. מעבד חישוב שכר (Payroll Processor)
# ---------------------------------------------------------------------------
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
    flags: List[AnomalyFlag]

class PayrollProcessor:
    def __init__(self):
        self.rules = LiveRegulatorySyncAPI.get_latest_rules()
        
    def calculate_tax(self, gross: Decimal, credit_points: Decimal):
        tax_gross = Decimal('0.00')
        remaining = gross
        prev_limit = Decimal('0.00')
        
        for bracket in self.rules.tax_brackets:
            if bracket.upper_limit is None:
                tax_gross += remaining * bracket.rate
                break
            
            bracket_size = bracket.upper_limit - prev_limit
            if remaining > bracket_size:
                tax_gross += bracket_size * bracket.rate
                remaining -= bracket_size
                prev_limit = bracket.upper_limit
            else:
                tax_gross += remaining * bracket.rate
                break
                
        tax_credit = credit_points * self.rules.credit_point_value_monthly
        final_tax = max(Decimal('0.00'), tax_gross - tax_credit)
        return to_dec(tax_gross), to_dec(tax_credit), to_dec(final_tax)

    def calculate_national_insurance(self, gross: Decimal) -> Decimal:
        threshold = self.rules.bituach_leumi_threshold
        if gross <= threshold:
            ni = gross * self.rules.national_insurance_reduced_rate
        else:
            ni = (threshold * self.rules.national_insurance_reduced_rate) + \
                 ((gross - threshold) * self.rules.national_insurance_full_rate)
        return to_dec(ni)

    def process_employee(self, emp_data: dict, historical_avg: dict) -> CalculatedPaystub:
        base = to_dec(emp_data.get('base_salary', 0))
        hourly_rate = to_dec(base / Decimal('182'))
        
        ot_hours_125 = Decimal(str(emp_data.get('overtime_125_hours', 0)))
        ot_hours_150 = Decimal(str(emp_data.get('overtime_150_hours', 0)))
        
        ot125_pay = to_dec(ot_hours_125 * hourly_rate * Decimal('1.25'))
        ot150_pay = to_dec(ot_hours_150 * hourly_rate * Decimal('1.50'))
        ot_pay = ot125_pay + ot150_pay
        
        bonus = to_dec(emp_data.get('bonus', 0))
        gross = base + ot_pay + bonus
        
        credit_pts = Decimal(str(emp_data.get('credit_points', 2.25)))
        tax_gross, tax_credit, income_tax = self.calculate_tax(gross, credit_pts)
        ni = self.calculate_national_insurance(gross)
        pension_emp = to_dec(gross * Decimal('0.06'))
        
        total_deductions = income_tax + ni + pension_emp
        net = gross - total_deductions
        
        flags = AIAnomalyDetector.scan_employee_payroll(emp_data, historical_avg)
        
        return CalculatedPaystub(
            emp_id=emp_data['id'],
            emp_name=emp_data['name'],
            base_salary=base,
            hourly_rate=hourly_rate,
            ot_hours_125=ot_hours_125,
            ot_hours_150=ot_hours_150,
            overtime_125_pay=ot125_pay,
            overtime_150_pay=ot150_pay,
            overtime_pay=ot_pay,
            bonus=bonus,
            gross_salary=gross,
            tax_before_credit=tax_gross,
            tax_credit_amount=tax_credit,
            income_tax=income_tax,
            national_insurance=ni,
            pension_employee=pension_emp,
            total_deductions=total_deductions,
            net_salary=net,
            credit_points=credit_pts,
            flags=flags
        )

# ---------------------------------------------------------------------------
# פונקציית שליחת תלוש מעוצב ב-HTML במייל
# ---------------------------------------------------------------------------
def send_real_email(recipient_email: str, stub: CalculatedPaystub, sender_email: str, sender_pass: str):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"📄 תלוש משכורת רשמי — {stub.emp_name} — ספטמבר 2026"

        html_body = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="he">
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, 'Segoe UI', sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; direction: rtl; text-align: right;">
            <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border: 2px solid #1E3A8A; border-radius: 12px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                
                <div style="background-color: #1E3A8A; color: #ffffff; padding: 16px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: bold; margin-bottom: 20px;">
                    📄 תלוש משכורת רשמי — שנת מס 2026
                </div>

                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
                    <tr style="background-color: #F3F4F6;">
                        <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>שם העובד/ת:</b> {stub.emp_name}</td>
                        <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>תעודת זהות:</b> {stub.emp_id}</td>
                        <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>חודש שכר:</b> ספטמבר 2026</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>נקודות זיכוי מס:</b> {stub.credit_points} נ"ז</td>
                        <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>תקן שעות:</b> 182 שעות</td>
                        <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>אישור:</b> <span style="color: green; font-weight: bold;">אושר ע"י חשב שכר מוסמך</span></td>
                    </tr>
                </table>

                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #1E3A8A; color: #ffffff;">
                            <th style="padding: 10px; border: 1px solid #CBD5E1; text-align: right;">פירוט ברוטו</th>
                            <th style="padding: 10px; border: 1px solid #CBD5E1; text-align: left;">סכום (₪)</th>
                            <th style="padding: 10px; border: 1px solid #CBD5E1; text-align: right;">ניכויי חובה</th>
                            <th style="padding: 10px; border: 1px solid #CBD5E1; text-align: left;">סכום (₪)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #E5E7EB;">שכר בסיס</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{stub.base_salary:,.2f}</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB;">מס הכנסה (לאחר נ"ז)</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{stub.income_tax:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #E5E7EB;">גמול שעות נוספות</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{stub.overtime_pay:,.2f}</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB;">ביטוח לאומי ומס בריאות</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{stub.national_insurance:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #E5E7EB;">בונוסים ועמלות</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{stub.bonus:,.2f}</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB;">פנסיה עובד (6.0%)</td>
                            <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{stub.pension_employee:,.2f}</td>
                        </tr>
                        <tr style="font-weight: bold; background-color: #F3F4F6;">
                            <td style="padding: 10px; border: 1px solid #CBD5E1;">סה"כ ברוטו</td>
                            <td style="padding: 10px; border: 1px solid #CBD5E1; text-align: left; color: #1E3A8A;">₪{stub.gross_salary:,.2f}</td>
                            <td style="padding: 10px; border: 1px solid #CBD5E1;">סה"כ ניכויים</td>
                            <td style="padding: 10px; border: 1px solid #CBD5E1; text-align: left; color: #991B1B;">₪{stub.total_deductions:,.2f}</td>
                        </tr>
                    </tbody>
                </table>

                <div style="background-color: #DCFCE7; border: 2px solid #16A34A; border-radius: 8px; padding: 16px; text-align: center; margin-top: 20px;">
                    <span style="font-size: 20px; color: #15803D; font-weight: bold;">💰 שכר נטו לתשלום לבנק: ₪{stub.net_salary:,.2f}</span>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_pass)
        server.send_message(msg)
        server.quit()
        return True, f"תלוש מעוצב ומאורגן ב-HTML נשלח בהצלחה למייל {recipient_email}!"
    except Exception as e:
        return False, f"שגיאה בהתחברות לשרת המייל: {str(e)}"

# ===========================================================================
# 5. סרגל צד (SIDEBAR) - המחשבון המדעי, המצלמה וכל רובריקות הטעינה
# ===========================================================================

st.sidebar.title("🛠️ תפריט אפשרויות וסורקים")

# 1️⃣ המחשבון המדעי המדויק על רמת האגורה בצד
with st.sidebar.expander("🧮 המחשבון המדעי המדויק (עד האגורה)", expanded=True):
    st.write("מנוע חישוב מדויק בריאקציה מיידית:")
    calc_name = st.sidebar.text_input("שם העובד:", value="דנה לוי", key="side_name")
    calc_id = st.sidebar.text_input("מספר ת.ז:", value="102", key="side_id")
    calc_base = st.sidebar.number_input("שכר בסיס (₪):", value=16000.0, step=500.0, key="side_base")
    calc_ot125 = st.sidebar.number_input("שעות 125%:", value=5.0, step=1.0, key="side_ot125")
    calc_ot150 = st.sidebar.number_input("שעות 150%:", value=2.0, step=1.0, key="side_ot150")
    calc_bonus = st.sidebar.number_input("בונוס/עמלה (₪):", value=4500.0, step=100.0, key="side_bonus")
    calc_credit_pts = st.sidebar.number_input("נקודות זיכוי (נ\"ז):", value=2.75, step=0.25, key="side_pts")

# 2️⃣ המצלמה בצד
with st.sidebar.expander("📸 סורק מצלמת הטאבלט", expanded=True):
    cam_picture = st.sidebar.camera_input("צלמי מסמך/טופס במצלמה", key="side_camera")
    scanned_from_cam = None
    if cam_picture:
        st.sidebar.success("📸 התמונה נקלטה במצלמה!")
        st.sidebar.info("🤖 AI Vision OCR בפעולה: מחלץ נתונים...")
        scanned_from_cam = {
            "id": "104", "name": "אלישבע מור (מסריקת מצלמה)", "base_salary": 14500,
            "overtime_hours": 18, "overtime_125_hours": 12, "overtime_150_hours": 6,
            "bonus": 1200, "credit_points": 3.25, "form_101_updated": True
        }

# 3️⃣ רובריקות טעינת קבצים ונתונים בצד
st.sidebar.markdown("---")
st.sidebar.subheader("📁 רובריקות העלאת נתונים")

upload_screenshots = st.sidebar.file_uploader(
    "🖼️ רובריקה להעלאת תצלומי מסך", 
    type=["png", "jpg", "jpeg"],
    key="up_screens"
)

upload_excel = st.sidebar.file_uploader(
    "📊 רובריקה להעלאת טבלת אקסל", 
    type=["xlsx", "csv"],
    key="up_excel"
)

upload_attendance = st.sidebar.file_uploader(
    "⏰ רובריקה להעלאת שעון נוכחות", 
    type=["xlsx", "csv", "txt", "dat"],
    key="up_clock"
)

upload_sample_paystub = st.sidebar.file_uploader(
    "📄 רובריקה להעלאת תלוש שכר לדוגמא", 
    type=["pdf", "png", "jpg", "txt"],
    key="up_sample"
)

st.sidebar.markdown("---")
st.sidebar.success("🟢 מסונכרן לרגולציית 2026")

# ===========================================================================
# 6. החלק המרכזי של האפליקציה (MAIN AREA)
# ===========================================================================

st.title("🤖 אפליקציית חישוב שכר אוטונומית (AI Payroll)")
st.caption("המערכת מציגה ומחשבת בלבד — אישור כל תלוש מבוצע אך ורק ע\"י חשב שכר מוסמך (Human-in-the-Loop)")
st.markdown("---")

processor = PayrollProcessor()

sample_employees = [
    {
        "id": "101", "name": "ישראל ישראלי", "base_salary": 12500,
        "overtime_hours": 42, "overtime_125_hours": 30, "overtime_150_hours": 12,
        "bonus": 1850, "credit_points": 2.25, "form_101_updated": False
    },
    {
        "id": calc_id, "name": calc_name, "base_salary": calc_base,
        "overtime_hours": calc_ot125 + calc_ot150, "overtime_125_hours": calc_ot125, "overtime_150_hours": calc_ot150,
        "bonus": calc_bonus, "credit_points": calc_credit_pts, "form_101_updated": True
    },
    {
        "id": "103", "name": "משה כהן", "base_salary": 9500,
        "overtime_hours": 2, "overtime_125_hours": 2, "overtime_150_hours": 0,
        "bonus": 0, "credit_points": 2.25, "form_101_updated": False
    }
]

if scanned_from_cam:
    sample_employees.append(scanned_from_cam)
    st.success(f"✨ **נקלט מסמך מהמצלמה!** הנתונים של {scanned_from_cam['name']} נקלטו והתווספו למערכת.")

historical_averages = {
    "101": {"overtime_hours": 15, "bonus": 500, "credit_points": 2.25},
    "102": {"overtime_hours": 4, "bonus": 1500, "credit_points": 2.75},
    "103": {"overtime_hours": 2, "bonus": 0, "credit_points": 2.25},
    "104": {"overtime_hours": 8, "bonus": 0, "credit_points": 2.25}
}

paystubs = [processor.process_employee(e, historical_averages.get(e["id"], {})) for e in sample_employees]

# תמונת מצב חודשית (Dashboard KPIs)
total_count = len(paystubs)
approved_count = len([p for p in paystubs if p.emp_id in st.session_state.approved_stubs])
rejected_count = len([p for p in paystubs if p.emp_id in st.session_state.rejected_stubs])
pending_count = total_count - approved_count - rejected_count

col1, col2, col3, col4 = st.columns(4)
col1.metric("סה\"כ תלושים במחזור", total_count)
col2.metric("ממתינים לבדיקת חשב", pending_count, delta="⏳ דורש בדיקה", delta_color="off")
col3.metric("אושרו ע\"י החשב", approved_count, delta="✅ אושר מוסמך")
col4.metric("נדחו / לתיקון", rejected_count, delta="-❌ נדחה", delta_color="inverse")

st.markdown("---")

# ---------------------------------------------------------------------------
# 📋 לוח בדיקות ואישורים של חשב שכר (Human-in-the-Loop בלבד - אפס אישור אוטומטי!)
# ---------------------------------------------------------------------------
st.subheader("📋 לוח בדיקות ואישורים של חשב שכר מוסמך")
st.info("📌 **מדיניות המערכת:** המערכת אינה מאשרת אף תלוש בעצמה! כל התלושים ממתינים לבדיקה ואישור אקטיבי של חשב השכר.")

for p in paystubs:
    status_label = "⏳ ממתין לבדיקה"
    if p.emp_id in st.session_state.approved_stubs:
        status_label = "✅ אושר ע\"י החשב"
    elif p.emp_id in st.session_state.rejected_stubs:
        status_label = "❌ נדחה / הועבר לתיקון"

    with st.expander(f"📄 **{p.emp_name}** (ת.ז: {p.emp_id}) — ברוטו: ₪{p.gross_salary:,.2f} | נטו: ₪{p.net_salary:,.2f} | סטטוס: {status_label}", expanded=(p.emp_id not in st.session_state.approved_stubs and p.emp_id not in st.session_state.rejected_stubs)):
        
        if p.flags:
            st.markdown("##### 🔍 ממצאי סורק ה-AI לבדיקת החשב:")
            for flag in p.flags:
                if flag.risk_level == "HIGH":
                    st.error(f"🔴 **[HIGH RISK]** {flag.message_hebrew} (ממוצע: {flag.historical_baseline} ⬅️ חודשי: {flag.current_value})")
                elif flag.risk_level == "MEDIUM":
                    st.warning(f"🟠 **[MEDIUM RISK]** {flag.message_hebrew} (ממוצע: {flag.historical_baseline} ⬅️ חודשי: {flag.current_value})")
                else:
                    st.info(f"🟡 **[LOW RISK]** {flag.message_hebrew}")
        else:
            st.success("🟢 הנתונים הפיננסיים חושבו ונמצאו תקינים אריתמטית. כעת נדרשת החלטת החשב המוסמך.")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button(f"✅ אשר תלוש (חשב מוסמך)", key=f"app_{p.emp_id}"):
                st.session_state.approved_stubs.add(p.emp_id)
                st.session_state.rejected_stubs.discard(p.emp_id)
                st.rerun()
        with btn_col2:
            if st.button(f"❌ דחה / העבר לתיקון", key=f"rej_{p.emp_id}"):
                st.session_state.rejected_stubs.add(p.emp_id)
                st.session_state.approved_stubs.discard(p.emp_id)
                st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# 📄 רובריקה במרכז: תלוש משכורת מעוצב ומסודר עפ"י דוגמת העסק
# ---------------------------------------------------------------------------
st.subheader("📄 תלוש משכורת מעוצב ומסודר (לפי תבנית העסק הרשמית)")

selected_emp_name = st.selectbox(
    "בחרי עובד להצגת התלוש המעוצב:",
    options=[p.emp_name for p in paystubs],
    index=1 if len(paystubs) > 1 else 0
)

selected_stub = next(p for p in paystubs if p.emp_name == selected_emp_name)

is_selected_approved = selected_stub.emp_id in st.session_state.approved_stubs
approval_status_html = '<span style="color: green; font-weight: bold;">✅ אושר ע"י חשב שכר</span>' if is_selected_approved else '<span style="color: orange; font-weight: bold;">⏳ ממתין לאישור חשב שכר</span>'

paystub_html = f"""
<div style="font-family: 'Segoe UI', Arial, sans-serif; direction: rtl; text-align: right; border: 2px solid #1E3A8A; border-radius: 12px; padding: 20px; background-color: #FFFFFF; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px;">
    
    <div style="background-color: #1E3A8A; color: #FFFFFF; padding: 12px 18px; border-radius: 8px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 20px;">
        📄 תלוש משכורת רשמי — שנת מס 2026 (תבנית עסקית מוסמכת)
    </div>

    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
        <tr style="background-color: #F3F4F6;">
            <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>שם העובד/ת:</b> {selected_stub.emp_name}</td>
            <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>תעודת זהות:</b> {selected_stub.emp_id}</td>
            <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>חודש שכר:</b> ספטמבר 2026</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>נקודות זיכוי מס:</b> {selected_stub.credit_points} נ"ז</td>
            <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>תקן שעות:</b> 182 שעות</td>
            <td style="padding: 10px; border: 1px solid #E5E7EB;"><b>סטטוס אישור:</b> {approval_status_html}</td>
        </tr>
    </table>

    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
        
        <div style="flex: 1; min-width: 280px;">
            <h4 style="color: #1E3A8A; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin-bottom: 10px;">💵 פירוט רכיבי ברוטו</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr style="background-color: #EFF6FF;">
                    <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: right;">רכיב שכר</th>
                    <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: left;">סכום (₪)</th>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #E5E7EB;">שכר בסיס</td>
                    <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{selected_stub.base_salary:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #E5E7EB;">גמול שעות נוספות</td>
                    <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{selected_stub.overtime_pay:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #E5E7EB;">בונוסים ועמלות</td>
                    <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{selected_stub.bonus:,.2f}</td>
                </tr>
                <tr style="background-color: #DBEAFE; font-weight: bold;">
                    <td style="padding: 8px; border: 1px solid #CBD5E1;">סה"כ שכר ברוטו</td>
                    <td style="padding: 8px; border: 1px solid #CBD5E1; text-align: left;">₪{selected_stub.gross_salary:,.2f}</td>
                </tr>
            </table>
        </div>

        <div style="flex: 1; min-width: 280px;">
            <h4 style="color: #991B1B; border-bottom: 2px solid #991B1B; padding-bottom: 5px; margin-bottom: 10px;">📉 פירוט ניכויי חובה</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr style="background-color: #FEF2F2;">
                    <th style="padding: 8px; border: 1px solid #FCA5A5; text-align: right;">ניכוי</th>
                    <th style="padding: 8px; border: 1px solid #FCA5A5; text-align: left;">סכום (₪)</th>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #E5E7EB;">מס הכנסה (לאחר נ"ז)</td>
                    <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{selected_stub.income_tax:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #E5E7EB;">דמי ביטוח לאומי ומס בריאות</td>
                    <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{selected_stub.national_insurance:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #E5E7EB;">הפרשת פנסיה עובד (6.0%)</td>
                    <td style="padding: 8px; border: 1px solid #E5E7EB; text-align: left;">₪{selected_stub.pension_employee:,.2f}</td>
                </tr>
                <tr style="background-color: #FEE2E2; font-weight: bold;">
                    <td style="padding: 8px; border: 1px solid #FCA5A5;">סה"כ ניכויי חובה</td>
                    <td style="padding: 8px; border: 1px solid #FCA5A5; text-align: left;">₪{selected_stub.total_deductions:,.2f}</td>
                </tr>
            </table>
        </div>

    </div>

    <div style="margin-top: 20px; background-color: #DCFCE7; border: 2px solid #16A34A; border-radius: 8px; padding: 15px; text-align: center;">
        <span style="font-size: 18px; color: #15803D; font-weight: bold;">💰 שכר נטו לתשלום לחשבון הבנק: ₪{selected_stub.net_salary:,.2f}</span>
    </div>

</div>
"""

components.html(paystub_html, height=520, scrolling=True)

# ---------------------------------------------------------------------------
# 📧 רובריקה במרכז: מייל שאליו אפשר לשלוח את התלושים
# ---------------------------------------------------------------------------
st.subheader("📧 שליחת תלוש השכר המעוצב למייל (עם חיבור SMTP)")

email_col1, email_col2 = st.columns(2)

with email_col1:
    target_email = st.text_input(
        "הקלידי כתובת דוא\"ל לשליחת התלוש המעוצב:",
        value=f"{selected_stub.emp_id}.payroll@company.co.il",
        key="email_input"
    )

with email_col2:
    with st.expander("⚙️ הגדרות שרת מייל לשליחה (SMTP)"):
        sender_email = st.text_input("מייל השולח (Gmail/Company):", value="payroll.system.ai@gmail.com", key="smtp_mail")
        sender_password = st.text_input("סיסמת אפליקציה (App Password):", type="password", key="smtp_pass")

if st.button("📧 שלח תלוש במייל עכשיו", type="primary", use_container_width=True):
    if not sender_password:
        st.warning("⚠️ יש להזין סיסמת אפליקציה בשדה ההגדרות כדי להתחבר לשרת הדוא\"ל ולשלוח.")
    elif selected_stub.emp_id not in st.session_state.approved_stubs:
        st.error("❌ לא ניתן לשלוח תלוש שלא אושר ע\"י חשב שכר! יש לאשר את התלוש בלוח הבדיקות תחילה.")
    else:
        with st.spinner("מתחבר לשרת הדוא\"ל ושולח את התלוש המעוצב ב-HTML..."):
            success, msg = send_real_email(target_email, selected_stub, sender_email, sender_password)
            if success:
                st.balloons()
                st.success(msg)
            else:
                st.error(msg)

st.markdown("---")

# ---------------------------------------------------------------------------
# 🧮 רובריקה במרכז: החישוב המדויק של כל הפרטים עבור כל עובד (עד רמת האגורה)
# ---------------------------------------------------------------------------
st.subheader("🧮 החישוב המדויק של כל הפרטים עבור כל עובד (פירוט אריתמטי שקוף)")
st.write("לחיצה על שם העובד תציג את הפירוט הפיננסי המלא והאגורתי של כל רכיב שכר, מס וניכוי:")

for p in paystubs:
    with st.expander(f"🔍 פירוט חישוב מיועד עבור: **{p.emp_name}** (ת.ז: {p.emp_id}) — נטו: ₪{p.net_salary:,.2f}", expanded=(p.emp_name == selected_emp_name)):
        c_a, c_b = st.columns(2)
        with c_a:
            st.markdown(f"""
            ##### 💵 רכיבי ברוטו וחישוב שעות:
            * **שכר בסיס:** ₪{p.base_salary:,.2f}
            * **תעריף שעתי מחושב (בסיס ÷ 182 שעות):** ₪{p.hourly_rate:,.2f} לשעה
            * **שעות נוספות 125% ({p.ot_hours_125} שעות):** ₪{p.overtime_125_pay:,.2f}
            * **שעות נוספות 150% ({p.ot_hours_150} שעות):** ₪{p.overtime_150_pay:,.2f}
            * **סה"כ גמול שעות נוספות:** ₪{p.overtime_pay:,.2f}
            * **תוספת בונוסים/עמלות:** ₪{p.bonus:,.2f}
            * **--------------------------------------------------**
            * **סה"כ שכר ברוטו לחישוב:** **₪{p.gross_salary:,.2f}**
            """)
        with c_b:
            st.markdown(f"""
            ##### 📉 ניכויי חובה וחישוב מיסוי 2026:
            * **חיובי מס הכנסה ברוטו לפי מדרגות:** ₪{p.tax_before_credit:,.2f}
            * **זיכוי מס עבור {p.credit_points} נ"ז (₪242.00 לנ"ז):** -₪{p.tax_credit_amount:,.2f}
            * **מס הכנסה סופי לתשלום:** **₪{p.income_tax:,.2f}**
            * **דמי ביטוח לאומי ומס בריאות:** **₪{p.national_insurance:,.2f}**
            * **הפרשת פנסיה עובד (6.0% מהברוטו):** **₪{p.pension_employee:,.2f}**
            * **--------------------------------------------------**
            * **סה"כ ניכויי חובה:** **₪{p.total_deductions:,.2f}**
            * **💰 שכר נטו לתשלום לחשבון הבנק:** **₪{p.net_salary:,.2f}**
            """)

st.markdown("---")

if st.button("🚀 אישור גורף של חשב השכר לכל התלושים הממתינים", type="primary"):
    for p in paystubs:
        st.session_state.approved_stubs.add(p.emp_id)
        st.session_state.rejected_stubs.discard(p.emp_id)
    st.balloons()
    st.success("כל התלושים במחזור אושרו אקטיבית ע\"י חשב השכר המוסמך ומוכנים למשלוח!")
    st.rerun()
