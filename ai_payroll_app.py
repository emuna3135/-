
import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import html
import json
from datetime import datetime
from cryptography.fernet import Fernet

# ===========================================================================
# 🤖 Autonomous Enterprise AI Payroll System (v7.0 - Production Grade)
# Smart Header Detection | Safe Float Parsing | Exact Decimal Math | AES-256
# ===========================================================================

st.set_page_config(
    page_title="AI Payroll Enterprise - מערכת שכר ואבטחה 2026",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 0. RTL Styling & Custom CSS Protections
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], .main, .stApp {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, div, span, caption {
        direction: rtl !important;
        text-align: right !important;
    }
    .material-symbols-outlined, .stIcon, [data-testid="stMetricValue"], code {
        direction: ltr !important;
        display: inline-block;
    }
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"], .stButton button, .stFileUploader {
        direction: rtl !important;
        text-align: right !important;
    }
    .flag-high {
        background-color: #FEF2F2;
        border-right: 4px solid #EF4444;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 6px;
        color: #991B1B;
        font-size: 14px;
    }
    .flag-medium {
        background-color: #FFFBEB;
        border-right: 4px solid #F59E0B;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 6px;
        color: #92400E;
        font-size: 14px;
    }
    .flag-low {
        background-color: #EFF6FF;
        border-right: 4px solid #3B82F6;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 6px;
        color: #1E40AF;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "approved_stubs" not in st.session_state:
    st.session_state.approved_stubs = set()
if "rejected_stubs" not in st.session_state:
    st.session_state.rejected_stubs = set()
if "edited_employees" not in st.session_state:
    st.session_state.edited_employees = {}
if "audit_trail" not in st.session_state:
    st.session_state.audit_trail = []
if "cipher_key" not in st.session_state:
    st.session_state.cipher_key = Fernet.generate_key().decode('utf-8')
if "last_uploaded_file" not in st.session_state:
    st.session_state.last_uploaded_file = None

# ---------------------------------------------------------------------------
# 1. Security Manager & AES-256 Encryption
# ---------------------------------------------------------------------------
class SecurityManager:
    @staticmethod
    def get_cipher() -> Fernet:
        return Fernet(st.session_state.cipher_key.encode('utf-8'))
        
    @classmethod
    def encrypt_val(cls, val: str) -> str:
        if not val:
            return ""
        cipher = cls.get_cipher()
        return cipher.encrypt(val.encode('utf-8')).decode('utf-8')

    @classmethod
    def decrypt_val(cls, token: str) -> str:
        if not token:
            return ""
        try:
            cipher = cls.get_cipher()
            return cipher.decrypt(token.encode('utf-8')).decode('utf-8')
        except Exception:
            return "[הצפנה לא תקינה]"

    @staticmethod
    def log_action(user_role: str, action_type: str, emp_id: str, details: str):
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_role": user_role,
            "action_type": action_type,
            "emp_id": emp_id,
            "details": details
        }
        st.session_state.audit_trail.append(log_entry)

# ---------------------------------------------------------------------------
# 2. Exact Decimal Math & Regulatory Data (2026 Israeli Law)
# ---------------------------------------------------------------------------
def to_dec(val: float | str | int | None) -> Decimal:
    if val is None or pd.isna(val) or str(val).strip() == "":
        return Decimal('0.00')
    try:
        cleaned = str(val).replace(',', '').strip()
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
    minimum_wage_hourly: Decimal = to_dec('32.30')
    
    tax_brackets: List[TaxBracket] = field(default_factory=lambda: [
        TaxBracket(to_dec('7010.00'), to_dec('0.10')),
        TaxBracket(to_dec('10060.00'), to_dec('0.14')),
        TaxBracket(to_dec('19000.00'), to_dec('0.20')),
        TaxBracket(to_dec('25100.00'), to_dec('0.31')),
        TaxBracket(to_dec('46690.00'), to_dec('0.35')),
        TaxBracket(None, to_dec('0.47')),
    ])
    
    sur_tax_threshold: Decimal = to_dec('60130.00')
    sur_tax_rate: Decimal = to_dec('0.03')
    
    bituach_leumi_threshold: Decimal = to_dec('7703.00')
    national_insurance_reduced_rate: Decimal = to_dec('0.0427')
    national_insurance_full_rate: Decimal = to_dec('0.1217')
    bituach_leumi_max_income_cap: Decimal = to_dec('51910.00')
    study_fund_cap_monthly: Decimal = to_dec('15712.00')

# ---------------------------------------------------------------------------
# 3. Sidebar Dynamic Tax & Regulatory Rules Control
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ בקרת כללי מס ורגולציה מתעדכנים")
st.sidebar.markdown("כאן ניתן לעדכן פרמטרים או להעלות קובץ כללים חדש:")

reg_file = st.sidebar.file_uploader("📥 העלי קובץ כללי מס (JSON / Config):", type=["json"])
use_custom_reg = st.sidebar.checkbox("הפעל הגדרות מותאמות אישית", value=False)

if reg_file is not None:
    try:
        reg_json = json.load(reg_file)
        current_rules = RegulatoryData2026(
            credit_point_value_monthly=to_dec(reg_json.get("credit_point_value", 242.0)),
            bituach_leumi_threshold=to_dec(reg_json.get("ni_threshold", 7703.0)),
            bituach_leumi_max_income_cap=to_dec(reg_json.get("ni_max_cap", 51910.0))
        )
        st.sidebar.success("✅ קובץ כללי מס נטען בהצלחה!")
    except Exception as e:
        st.sidebar.error(f"שגיאה בטעינת הקובץ: {e}")
        current_rules = RegulatoryData2026()
elif use_custom_reg:
    custom_credit_val = st.sidebar.number_input("שווי נקודת זיכוי חודשי (₪)", value=242.0, step=1.0)
    custom_ni_thresh = st.sidebar.number_input("תקרת ביטוח לאומי מופחת (₪)", value=7703.0, step=10.0)
    custom_ni_cap = st.sidebar.number_input("תקרת גבייה מרבית ב.לאומי (₪)", value=51910.0, step=100.0)
    
    current_rules = RegulatoryData2026(
        credit_point_value_monthly=to_dec(custom_credit_val),
        bituach_leumi_threshold=to_dec(custom_ni_thresh),
        bituach_leumi_max_income_cap=to_dec(custom_ni_cap)
    )
    st.sidebar.success("⚙️ מופעלות הגדרות מותאמות אישית")
else:
    current_rules = RegulatoryData2026()
    st.sidebar.info("ℹ️ מופעלים כללי מס ברירת מחדל (2026)")

# ---------------------------------------------------------------------------
# 4. Smart Header Detection & Robust Excel Parsing
# ---------------------------------------------------------------------------
def safe_float(val, default: float = 0.0) -> float:
    if val is None or pd.isna(val):
        return default
    try:
        cleaned = str(val).replace(',', '').strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return default

def load_excel_smart(df_raw: pd.DataFrame) -> pd.DataFrame:
    """זיהוי אוטומטי של שורת הכותרות באקסל גם אם מופיעות שורות תיאור בראש הדף"""
    cols_str = ' '.join([str(c) for c in df_raw.columns])
    matches_top = sum(1 for k in ['שכר', 'ת.ז', 'שם', 'בונוס', 'זיכוי', '125%'] if k in cols_str)
    if matches_top >= 2:
        return df_raw
    
    # סריקת 10 השורות הראשונות למציאת שורת הכותרות האמיתית
    for r_idx in range(min(10, len(df_raw))):
        row_vals = [str(val).strip() for val in df_raw.iloc[r_idx].values]
        row_str = ' '.join(row_vals)
        matches_row = sum(1 for k in ['שכר', 'ת.ז', 'שם', 'בונוס', 'זיכוי', '125%'] if k in row_str)
        if matches_row >= 2:
            new_df = df_raw.iloc[r_idx + 1:].copy()
            new_df.columns = row_vals
            return new_df.reset_index(drop=True)
            
    return df_raw

def parse_excel_dataframe(df_input: pd.DataFrame) -> List[dict]:
    """מנגנון מיפוי עמודות חכם ומוגן המדלג על שורות כותרת ומונע שגיאות מיקום"""
    df_clean = load_excel_smart(df_input)
    df_clean.columns = [str(col).strip() for col in df_clean.columns]
    
    def find_col(keywords: List[str]) -> Optional[str]:
        for col in df_clean.columns:
            col_lower = str(col).lower()
            for kw in keywords:
                if kw.lower() in col_lower:
                    return col
        return None

    col_id = find_col(['ת.ז', 'זהות', 'מספר עובד', 'id', 'emp_id'])
    col_name = find_col(['שם', 'שם עובד', 'name', 'employee'])
    col_salary = find_col(['שכר יסוד', 'שכר בסיס', 'שכר', 'base_salary', 'salary'])
    col_ot_total = find_col(['שעות נוספות', 'סך שעות נוספות', 'overtime_hours', 'ot_hours'])
    col_ot_125 = find_col(['125%', '125', 'overtime_125'])
    col_ot_150 = find_col(['150%', '150', 'overtime_150'])
    col_bonus = find_col(['בונוס', 'עמלה', 'עמלות', 'bonus'])
    col_credits = find_col(['נקודות זיכוי', 'נ"ז', 'נז', 'זיכוי', 'credit_points', 'credits'])

    parsed_employees = []
    for idx, row in df_clean.iterrows():
        raw_name = row[col_name] if col_name else None
        emp_name = str(raw_name).strip() if (raw_name is not None and not pd.isna(raw_name)) else f"עובד {idx + 1}"
        
        # דילוג על שורות סיכום או הסבר
        if any(term in emp_name for term in ["נתונים", "2026", "תקן", "הסבר", "ממוצע", "סה\"כ"]):
            continue

        raw_id = row[col_id] if col_id else None
        emp_id = str(raw_id).strip() if (raw_id is not None and not pd.isna(raw_id)) else str(idx + 1)
        if emp_id.endswith('.0'):
            emp_id = emp_id[:-2]

        salary_val = safe_float(row[col_salary] if col_salary else 10000.0, default=10000.0)
        ot_total = safe_float(row[col_ot_total] if col_ot_total else 0.0, default=0.0)
        ot_125 = safe_float(row[col_ot_125] if col_ot_125 else 0.0, default=0.0)
        ot_150 = safe_float(row[col_ot_150] if col_ot_150 else 0.0, default=0.0)
        
        if ot_total > 0 and ot_125 == 0 and ot_150 == 0:
            ot_125 = ot_total
            
        bonus_val = safe_float(row[col_bonus] if col_bonus else 0.0, default=0.0)
        credit_pts_val = safe_float(row[col_credits] if col_credits else 2.25, default=2.25)

        parsed_employees.append({
            "id": emp_id,
            "name": emp_name,
            "base_salary": salary_val if salary_val > 0 else 10000.0,
            "overtime_hours": ot_total if ot_total > 0 else (ot_125 + ot_150),
            "overtime_125_hours": ot_125,
            "overtime_150_hours": ot_150,
            "bonus": bonus_val,
            "credit_points": credit_pts_val
        })
        
    return parsed_employees

# ---------------------------------------------------------------------------
# 5. Payroll Calculation Engine
# ---------------------------------------------------------------------------
@dataclass
class AnomalyFlag:
    risk_level: str
    field_name: str
    message_hebrew: str

@dataclass
class CalculatedPaystub:
    emp_id: str
    emp_name: str
    month_num: int
    base_salary: Decimal
    hourly_rate: Decimal
    ot_hours_125: Decimal
    ot_hours_150: Decimal
    overtime_pay: Decimal
    bonus: Decimal
    taxable_benefit_study_fund: Decimal
    gross_salary: Decimal
    taxable_gross: Decimal
    credit_points: Decimal
    credit_point_value: Decimal
    income_tax: Decimal
    sur_tax: Decimal
    national_insurance: Decimal
    pension_employee: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    ytd_gross: Decimal
    ytd_tax: Decimal
    flags: List[AnomalyFlag]

class CumulativePayrollProcessor:
    def __init__(self, rules: RegulatoryData2026):
        self.rules = rules
        
    def calculate_tax_monthly(self, gross: Decimal, credit_points: Decimal) -> Tuple[Decimal, Decimal]:
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
        final_income_tax = max(Decimal('0.00'), tax - tax_credit)
        
        sur_tax = Decimal('0.00')
        if gross > self.rules.sur_tax_threshold:
            sur_tax = (gross - self.rules.sur_tax_threshold) * self.rules.sur_tax_rate
            
        return to_dec(final_income_tax), to_dec(sur_tax)

    def calculate_national_insurance(self, gross: Decimal) -> Decimal:
        taxable_gross = min(gross, self.rules.bituach_leumi_max_income_cap)
        threshold = self.rules.bituach_leumi_threshold
        
        if taxable_gross <= threshold:
            ni = taxable_gross * self.rules.national_insurance_reduced_rate
        else:
            ni = (threshold * self.rules.national_insurance_reduced_rate) + \
                 ((taxable_gross - threshold) * self.rules.national_insurance_full_rate)
        return to_dec(ni)

    def process_employee(self, emp_data: dict, historical_avg: dict) -> CalculatedPaystub:
        base = to_dec(emp_data.get('base_salary', 0))
        hourly_rate = to_dec(base / Decimal('182'))
        
        ot_125_h = to_dec(emp_data.get('overtime_125_hours', 0))
        ot_150_h = to_dec(emp_data.get('overtime_150_hours', 0))
        ot_pay = to_dec(ot_125_h * hourly_rate * Decimal('1.25')) + to_dec(ot_150_h * hourly_rate * Decimal('1.50'))
        
        bonus = to_dec(emp_data.get('bonus', 0))
        gross = base + ot_pay + bonus
        
        study_fund_excess = Decimal('0.00')
        if base > self.rules.study_fund_cap_monthly:
            study_fund_excess = (base - self.rules.study_fund_cap_monthly) * Decimal('0.075')
        taxable_benefit_sf = to_dec(study_fund_excess)
        taxable_gross = gross + taxable_benefit_sf
        
        raw_pts = emp_data.get('credit_points')
        credit_pts = Decimal('2.25') if (raw_pts is None or str(raw_pts).strip() == "") else to_dec(raw_pts)
            
        income_tax, sur_tax = self.calculate_tax_monthly(taxable_gross, credit_pts)
        ni = self.calculate_national_insurance(gross)
        pension_emp = to_dec(gross * Decimal('0.06'))
        
        total_tax_and_sur = income_tax + sur_tax
        total_deductions = total_tax_and_sur + ni + pension_emp
        net = gross - total_deductions
        
        flags = []
        curr_ot = float(emp_data.get('overtime_hours', 0) or 0)
        avg_ot = float(historical_avg.get('overtime_hours', 0) or 0)
        if avg_ot > 0 and curr_ot > avg_ot * 1.8 and curr_ot > 15:
            flags.append(AnomalyFlag("HIGH", "overtime_hours", f"קפיצה חריגה בשעות נוספות ({curr_ot} שעות)."))
        if credit_pts == Decimal('0.00'):
            flags.append(AnomalyFlag("MEDIUM", "credit_points", "0.00 נקודות זיכוי (תושב חוץ) - דורש אימות."))

        return CalculatedPaystub(
            emp_id=str(emp_data.get('id', '')),
            emp_name=str(emp_data.get('name', '')),
            month_num=int(emp_data.get('month_num', 1)),
            base_salary=base,
            hourly_rate=hourly_rate,
            ot_hours_125=ot_125_h,
            ot_hours_150=ot_150_h,
            overtime_pay=ot_pay,
            bonus=bonus,
            taxable_benefit_study_fund=taxable_benefit_sf,
            gross_salary=gross,
            taxable_gross=taxable_gross,
            credit_points=credit_pts,
            credit_point_value=self.rules.credit_point_value_monthly,
            income_tax=total_tax_and_sur,
            sur_tax=sur_tax,
            national_insurance=ni,
            pension_employee=pension_emp,
            total_deductions=total_deductions,
            net_salary=net,
            ytd_gross=gross,
            ytd_tax=total_tax_and_sur,
            flags=flags
        )

# ---------------------------------------------------------------------------
# 6. Interface & Layout Tabs
# ---------------------------------------------------------------------------
st.title("🛡️️ Enterprise AI Payroll System (2026)")

tab_dashboard, tab_security, tab_paystub = st.tabs([
    "📊 לוח בקרה וחישוב שכר",
    "🔐 אבטחה ויומן ביקורת",
    "📑 הפקת תלושי שכר"
])

sample_employees = [
    {"id": "101", "name": "ישראל ישראלי", "base_salary": 12500, "overtime_hours": 42, "overtime_125_hours": 30, "overtime_150_hours": 12, "bonus": 1850, "credit_points": 2.25},
    {"id": "102", "name": "דנה לוי", "base_salary": 16000, "overtime_hours": 5, "overtime_125_hours": 5, "overtime_150_hours": 0, "bonus": 4500, "credit_points": 2.75},
    {"id": "103", "name": "ג'ון דו (תושב חוץ)", "base_salary": 15000, "overtime_hours": 0, "overtime_125_hours": 0, "overtime_150_hours": 0, "bonus": 0, "credit_points": 0.0}
]

with tab_dashboard:
    st.header("1️⃣ קליטת נתונים ולוח בקרת שכר")
    
    # 📥 רובריקת העלאת אקסל עם מנגנון איפוס זיכרון אוטומטי
    uploaded_file = st.file_uploader("📥 העלי קובץ נתוני שכר (Excel / CSV):", type=["xlsx", "xls", "csv"])
    
    active_emp_list = sample_employees
    if uploaded_file is not None:
        if st.session_state.last_uploaded_file != uploaded_file.name:
            st.session_state.edited_employees = {}
            st.session_state.approved_stubs = set()
            st.session_state.rejected_stubs = set()
            st.session_state.last_uploaded_file = uploaded_file.name
            st.toast(f"🔄 הועלה קובץ חדש: {uploaded_file.name}. זיכרון המטמון אופס בהצלחה!", icon="✨")
            
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            parsed_employees = parse_excel_dataframe(df_raw)
            if parsed_employees:
                active_emp_list = parsed_employees
                st.success(f"✅ הקובץ '{uploaded_file.name}' פוענח בהצלחה! מחושבים כעת {len(parsed_employees)} עובדים בזמן אמת.")
                
                with st.expander("🔍 הצג טבלת נתונים שפוענחה מהקובץ"):
                    st.dataframe(pd.DataFrame(parsed_employees), use_container_width=True)
        except Exception as e:
            st.error(f"שגיאה בקריאת הקובץ: {e}")
    else:
        if st.session_state.last_uploaded_file is not None:
            st.session_state.last_uploaded_file = None
            st.session_state.edited_employees = {}

    processor = CumulativePayrollProcessor(current_rules)
    calculated_stubs = [processor.process_employee(emp, {}) for emp in active_emp_list]

    st.subheader(f"📋 סיכום תלושים מחושבים ({len(calculated_stubs)} עובדים):")
    
    total_gross = sum(s.gross_salary for s in calculated_stubs)
    total_net = sum(s.net_salary for s in calculated_stubs)
    total_tax = sum(s.income_tax for s in calculated_stubs)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ ברוטו למחזור", f"₪{total_gross:,.2f}")
    m2.metric("סה\"כ ניכויי מס", f"₪{total_tax:,.2f}")
    m3.metric("סה\"כ נטו לתשלום", f"₪{total_net:,.2f}")
    
    st.markdown("---")

    for stub in calculated_stubs:
        with st.expander(f"👤 {stub.emp_name} (ת.ז: {stub.emp_id}) | ברוטו: ₪{stub.gross_salary:,.2f} | נטו: ₪{stub.net_salary:,.2f}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**שכר יסוד:** ₪{stub.base_salary:,.2f} | **שעות נוספות:** ₪{stub.overtime_pay:,.2f} | **בונוס:** ₪{stub.bonus:,.2f}")
                st.write(f"**נקודות זיכוי:** {stub.credit_points} נ\"ז")
            with c2:
                st.write(f"**מס הכנסה ומס יסף:** ₪{stub.income_tax:,.2f}")
                st.write(f"**ביטוח לאומי ומס בריאות:** ₪{stub.national_insurance:,.2f}")
                st.write(f"**פנסיה עובד (6%):** ₪{stub.pension_employee:,.2f}")
