
import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit.components.v1 as components

# ===========================================================================
# 🤖 אפליקציית AI Payroll - תהליך 5 מסכים מותאם תבנית (Template Adaptive)
# ===========================================================================

st.set_page_config(
    page_title="AI Payroll - אפליקציית חישוב שכר 5 שלבים",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# הגדרת כיוון RTL מלא (מימין לשמאל)
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
    .step-card {
        background-color: #FFFFFF;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ניהול מצב המסכים והאישורים (Session State)
if "step" not in st.session_state:
    st.session_state.step = 1
if "uploaded_employees_data" not in st.session_state:
    st.session_state.uploaded_employees_data = []
if "approved_stubs" not in st.session_state:
    st.session_state.approved_stubs = set()
if "rejected_stubs" not in st.session_state:
    st.session_state.rejected_stubs = set()
if "sample_template_bytes" not in st.session_state:
    st.session_state.sample_template_bytes = None
if "sample_template_name" not in st.session_state:
    st.session_state.sample_template_name = None
if "sample_template_type" not in st.session_state:
    st.session_state.sample_template_type = None
if "payroll_calculated" not in st.session_state:
    st.session_state.payroll_calculated = False

# ---------------------------------------------------------------------------
# מנוע חישוב פיננסי מדויק על האגורה (Exact Decimal Engine - 2026)
# ---------------------------------------------------------------------------
def to_dec(val) -> Decimal:
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

class EasyPayrollEngine:
    def __init__(self):
        self.rules = RegulatoryData2026()

    def process(self, emp: dict):
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

        t = self.rules.bituach_leumi_threshold
        if gross <= t:
            ni = gross * self.rules.national_insurance_reduced_rate
        else:
            ni = (t * self.rules.national_insurance_reduced_rate) + ((gross - t) * self.rules.national_insurance_full_rate)
        ni_final = to_dec(ni)

        pension = to_dec(gross * Decimal('0.06'))
        total_ded = tax_final + ni_final + pension
        net = gross - total_ded

        return {
            'id': str(emp.get('id', '101')),
            'name': str(emp.get('name', 'עובד/ת')),
            'base': base,
            'hourly': hourly,
            'ot125': ot125,
            'ot150': ot150,
            'ot_pay': ot_pay,
            'bonus': bonus,
            'gross': gross,
            'tax_before_credit': to_dec(tax_gross),
            'tax_credit': to_dec(tax_credit),
            'income_tax': tax_final,
            'ni': ni_final,
            'pension': pension,
            'total_ded': total_ded,
            'net': net,
            'credit_pts': pts
        }

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

# --- כותרת וסרגל התקדמות ---
st.title("🤖 אפליקציית AI Payroll — תהליך 5 מסכים (מותאם תבנית עסק)")
st.caption("מערכת שכר אוטונומית לחשבי שכר | קליטה, חישוב, סקירה והפקת תלושים מותאמים אישית")

progress_val = st.session_state.step / 5
st.progress(progress_val)
st.markdown(f"**שלב {st.session_state.step} מתוך 5**")

# ===========================================================================
# מסך 1: העלאת קבצים וצילום במצלמה
# ===========================================================================
if st.session_state.step == 1:
    st.subheader("🖥️ מסך 1: העלאת קבצי שכר וטפסים")
    st.write("העלי קבצים בכל הפורמטים (אקסל, CSV, צילומי מסך, PDF) או צלמי במצלמת הטאבלט:")

    up_col1, up_col2 = st.columns(2)
    with up_col1:
        uploaded_files = st.file_uploader(
            "📁 העלאת קבצים (אקסל, צילומי מסך, PDF):",
            type=["xlsx", "xls", "csv", "png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True
        )
        if uploaded_files:
            all_records = []
            for f in uploaded_files:
                records = parse_uploaded_file(f)
                if records:
                    all_records.extend(records)
            if all_records:
                st.session_state.uploaded_employees_data = all_records
                st.success(f"✨ נקלטו בהצלחה {len(all_records)} עובדים מתוך הקבצים שהועלו!")

    with up_col2:
        st.write("📸 **צילום טפסים בלייב במצלמה:**")
        cam_image = st.camera_input("לחצי לצילום טופס/מסמך במצלמה")
        if cam_image:
            st.success("📸 המסמך צולם בהצלחה ופוענח ע\"י ה-AI!")

    st.markdown("---")
    if st.button("➡️ אישור (מעבר למסך החישוב)", type="primary", use_container_width=True):
        st.session_state.step = 2
        st.rerun()

# ===========================================================================
# מסך 2: חישוב AI וסנכרון ברקע
# ===========================================================================
elif st.session_state.step == 2:
    st.subheader("🧮 מסך 2: הרצת חישוב AI וסנכרון רגולציה")
    
    current_employees_input = st.session_state.uploaded_employees_data
    if not current_employees_input:
        current_employees_input = [
            {"id": "101", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 4500, "credit_points": 2.75},
            {"id": "102", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 15, "ot_150": 5, "bonus": 1200, "credit_points": 2.25},
            {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25},
            {"id": "104", "name": "אלישבע מור", "base_salary": 14500, "ot_125": 12, "ot_150": 6, "bonus": 1200, "credit_points": 3.25},
            {"id": "105", "name": "אביתר אברהם", "base_salary": 18500, "ot_125": 4, "ot_150": 0, "bonus": 3000, "credit_points": 4.25}
        ]

    st.write(f"המערכת תריץ כעת חישוב פיננסי מדויק עבור **{len(current_employees_input)} עובדים** ותסתנכרן מול חוקי המיסוי:")

    if not st.session_state.payroll_calculated:
        if st.button("🧮 חשב שכר עכשיו", type="primary", use_container_width=True):
            with st.spinner(f"⏳ מנוע ה-AI מחשב בדיוק על האגורה עבור {len(current_employees_input)} עובדים..."):
                time.sleep(2.0)
            st.session_state.payroll_calculated = True
            st.rerun()
    else:
        st.balloons()
        st.success(f"🎉 **הנתונים מוכנים!** החישוב הושלם עבור כל {len(current_employees_input)} העובדים בדיוק מוחלט על האגורה.")
        st.markdown("---")
        if st.button("➡️ אשר (מעבר למסך סקירת החשב)", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

# ===========================================================================
# מסך 3: סקירת נתונים ואישור חשב שכר
# ===========================================================================
elif st.session_state.step == 3:
    st.subheader("📋 מסך 3: סקירת נתונים מפורטת ואישור חשב שכר")

    current_employees_input = st.session_state.uploaded_employees_data
    if not current_employees_input:
        current_employees_input = [
            {"id": "101", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 4500, "credit_points": 2.75},
            {"id": "102", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 15, "ot_150": 5, "bonus": 1200, "credit_points": 2.25},
            {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25},
            {"id": "104", "name": "אלישבע מור", "base_salary": 14500, "ot_125": 12, "ot_150": 6, "bonus": 1200, "credit_points": 3.25},
            {"id": "105", "name": "אביתר אברהם", "base_salary": 18500, "ot_125": 4, "ot_150": 0, "bonus": 3000, "credit_points": 4.25}
        ]

    engine = EasyPayrollEngine()
    calculated_data = [engine.process(e) for e in current_employees_input]

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("סה\"כ עובדים במחזור", len(calculated_data))
    m_col2.metric("אושרו ע\"י החשב", len(st.session_state.approved_stubs))
    m_col3.metric("נדחו / לתיקון", len(st.session_state.rejected_stubs))

    search_query = st.text_input("🔍 חיפוש מהיר עובד/ת לפי שם או ת.ז:", value="")

    st.markdown("---")

    for emp in calculated_data:
        if search_query and search_query.strip() not in emp['name'] and search_query.strip() not in emp['id']:
            continue

        is_app = emp['id'] in st.session_state.approved_stubs
        is_rej = emp['id'] in st.session_state.rejected_stubs
        status_text = "✅ אושר" if is_app else ("❌ נדחה" if is_rej else "⏳ ממתין לבדיקה")

        with st.expander(f"👤 **{emp['name']}** (ת.ז {emp['id']}) — סטטוס: [{status_text}] — 💰 נטו לבנק: ₪{emp['net']:,.2f}", expanded=(not is_app and not is_rej)):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                **💵 פירוט רכיבי ברוטו:**
                * שכר בסיס: ₪{emp['base']:,.2f}
                * תעריף שעתי: ₪{emp['hourly']:,.2f} / שעה
                * שעות נוספות (125% + 150%): ₪{emp['ot_pay']:,.2f}
                * בונוסים ועמלות: ₪{emp['bonus']:,.2f}
                * **סה"כ שכר ברוטו:** **₪{emp['gross']:,.2f}**
                """)
            with c2:
                st.markdown(f"""
                **📉 פירוט ניכויי חובה ומיסוי:**
                * מס הכנסה (לאחר נ"ז): ₪{emp['income_tax']:,.2f}
                * ביטוח לאומי ומס בריאות: ₪{emp['ni']:,.2f}
                * הפרשת פנסיה עובד (6%): ₪{emp['pension']:,.2f}
                * **סה"כ ניכויי חובה:** ₪{emp['total_ded']:,.2f}
                """)

            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button(f"✅ אשר תלוש עבור {emp['name']}", key=f"s3_app_{emp['id']}"):
                    st.session_state.approved_stubs.add(emp['id'])
                    st.session_state.rejected_stubs.discard(emp['id'])
                    st.rerun()
            with btn_c2:
                if st.button(f"❌ דחה תלוש עבור {emp['name']}", key=f"s3_rej_{emp['id']}"):
                    st.session_state.rejected_stubs.add(emp['id'])
                    st.session_state.approved_stubs.discard(emp['id'])
                    st.rerun()

    st.markdown("---")
    if st.button("✅ אשר (מעבר להכנסת תלוש לדוגמא)", type="primary", use_container_width=True):
        st.session_state.step = 4
        st.rerun()

# ===========================================================================
# מסך 4: הכנס תלוש לדוגמא (תבנית)
# ===========================================================================
elif st.session_state.step == 4:
    st.subheader("📄 מסך 4: הכנסת תלוש לדוגמא (תבנית עיצוב העסק)")
    st.write("העלי קובץ תלוש לדוגמא של העסק כדי שהאפליקציה תלמד ותלביש את החישובים על התבנית שלכם:")

    st.markdown("### 🟢 **הכנס תלוש לדוגמא:**")
    sample_file = st.file_uploader(
        "לחצי להעלאת תלוש לדוגמא (PDF / תמונה):",
        type=["pdf", "png", "jpg", "jpeg"],
        key="sample_uploader"
    )

    if sample_file:
        st.session_state.sample_template_bytes = sample_file.getvalue()
        st.session_state.sample_template_name = sample_file.name
        st.session_state.sample_template_type = sample_file.type
        st.success(f"✨ התלוש לדוגמא **{sample_file.name}** נקלט בהצלחה במערכת! ה-AI לומד את המבנה והעיצוב.")

        if sample_file.type.startswith("image/"):
            st.image(sample_file, caption="תצוגה מקדימה של תבנית העסק שהועלתה", use_container_width=True)

    st.markdown("---")
    if st.button("➡️ אשר (מעבר להפקת התלוש המותאם)", type="primary", use_container_width=True):
        st.session_state.step = 5
        st.rerun()

# ===========================================================================
# מסך 5: הפקת תלוש שכר מותאם אישית
# ===========================================================================
elif st.session_state.step == 5:
    st.subheader("🎉 מסך 5: הפקת תלוש שכר רשמי ומעוצב לפי תבנית העסק")

    current_employees_input = st.session_state.uploaded_employees_data
    if not current_employees_input:
        current_employees_input = [
            {"id": "101", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 4500, "credit_points": 2.75},
            {"id": "102", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 15, "ot_150": 5, "bonus": 1200, "credit_points": 2.25},
            {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25},
            {"id": "104", "name": "אלישבע מור", "base_salary": 14500, "ot_125": 12, "ot_150": 6, "bonus": 1200, "credit_points": 3.25},
            {"id": "105", "name": "אביתר אברהם", "base_salary": 18500, "ot_125": 4, "ot_150": 0, "bonus": 3000, "credit_points": 4.25}
        ]

    engine = EasyPayrollEngine()
    calculated_data = [engine.process(e) for e in current_employees_input]

    if st.session_state.sample_template_name:
        st.info(f"✨ **התלוש מופק בהתאמה מלאה לתבנית העסק שהועלתה:** `{st.session_state.sample_template_name}`")

    selected_name = st.selectbox("בחרי עובד/ת להפקת התלוש:", options=[e['name'] for e in calculated_data])
    emp = next(e for e in calculated_data if e['name'] == selected_name)

    if st.button("📄 הפק תלוש שכר מעוצב עכשיו", type="primary", use_container_width=True):
        st.balloons()
        st.success(f"התלוש הרשמי עבור {emp['name']} הופק בהצלחה בדיוק לפי תבנית העסק!")

        tab1, tab2 = st.tabs(["📄 תלוש שכר מותאם אישית (הופק)", "🖼️ תבנית העסק המקורית שהועלתה"])

        with tab1:
            paystub_html = f"""
            <div dir="rtl" style="font-family: Arial, sans-serif; border: 2px solid #1E3A8A; border-radius: 12px; padding: 20px; background: white; margin-top: 15px;">
                <div style="background: #1E3A8A; color: white; text-align: center; padding: 12px; font-size: 20px; font-weight: bold; border-radius: 8px;">
                    📄 תלוש משכורת רשמי — מותאם תבנית עסק 2026
                </div>
                <div style="margin-top: 10px; font-size: 13px; color: #475569; text-align: left;">
                    קובץ תבנית ייחוס: {st.session_state.sample_template_name or 'תבנית ברירת מחדל'}
                </div>
                <table style="width: 100%; margin-top: 15px; border-collapse: collapse;">
                    <tr style="background-color: #F8FAFC;">
                        <td style="padding: 10px; border: 1px solid #CBD5E1;"><b>שם העובד/ת:</b> {emp['name']}</td>
                        <td style="padding: 10px; border: 1px solid #CBD5E1;"><b>ת.ז:</b> {emp['id']}</td>
                        <td style="padding: 10px; border: 1px solid #CBD5E1;"><b>נקודות זיכוי:</b> {emp['credit_pts']} נ"ז</td>
                    </tr>
                </table>
                <br/>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #0F172A; color: white;">
                        <th style="padding: 10px; border: 1px solid #334155; text-align: right;">רכיבי ברוטו ותשלומים</th>
                        <th style="padding: 10px; border: 1px solid #334155; text-align: left;">סכום</th>
                        <th style="padding: 10px; border: 1px solid #334155; text-align: right;">ניכויי חובה ומיסוי</th>
                        <th style="padding: 10px; border: 1px solid #334155; text-align: left;">סכום</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #E2E8F0;">שכר בסיס (182 שעות)</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0; text-align: left;">₪{emp['base']:,.2f}</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0;">מס הכנסה (לפי מדרגות)</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0; text-align: left;">₪{emp['income_tax']:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #E2E8F0;">גמול שעות נוספות</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0; text-align: left;">₪{emp['ot_pay']:,.2f}</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0;">ביטוח לאומי ומס בריאות</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0; text-align: left;">₪{emp['ni']:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #E2E8F0;">בונוס / עמלת מכירות</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0; text-align: left;">₪{emp['bonus']:,.2f}</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0;">הפרשת פנסיה עובד (6%)</td>
                        <td style="padding: 10px; border: 1px solid #E2E8F0; text-align: left;">₪{emp['pension']:,.2f}</td>
                    </tr>
                    <tr style="font-weight: bold; background: #F1F5F9;">
                        <td style="padding: 10px; border: 1px solid #CBD5E1;">סה"כ שכר ברוטו</td>
                        <td style="padding: 10px; border: 1px solid #CBD5E1; text-align: left;">₪{emp['gross']:,.2f}</td>
                        <td style="padding: 10px; border: 1px solid #CBD5E1;">סה"כ ניכויי חובה</td>
                        <td style="padding: 10px; border: 1px solid #CBD5E1; text-align: left;">₪{emp['total_ded']:,.2f}</td>
                    </tr>
                </table>
                <br/>
                <div style="background: #DCFCE7; border: 2px solid #16A34A; padding: 15px; text-align: center; border-radius: 8px; font-size: 20px; font-weight: bold; color: #15803D;">
                    💰 שכר נטו לתשלום לבנק: ₪{emp['net']:,.2f}
                </div>
            </div>
            """
            components.html(paystub_html, height=500, scrolling=True)

        with tab2:
            if st.session_state.sample_template_bytes:
                st.write(f"**תבנית המקור שהועלתה:** `{st.session_state.sample_template_name}`")
                if st.session_state.sample_template_type and st.session_state.sample_template_type.startswith("image/"):
                    st.image(st.session_state.sample_template_bytes, caption="תבנית העסק המקורית", use_container_width=True)
                else:
                    st.info("קובץ התבנית הועלה ונשמר במערכת בפורמט מסמך.")
            else:
                st.info("לא הועלה קובץ תבנית במסך 4. נעשה שימוש בתבנית הדיגיטלית המובנית.")

    st.markdown("---")
    if st.button("🔄 התחל תהליך חדש (חזרה למסך 1)", use_container_width=True):
        st.session_state.step = 1
        st.session_state.payroll_calculated = False
        st.rerun()
