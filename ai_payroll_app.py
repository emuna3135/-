
import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import html
import json

# ===========================================================================
# 🤖 אפליקציית AI Payroll - מערכת חישוב שכר אוטונומית (תקני מיסוי 2026)
# Autonomous AI Payroll System - Israeli Tax & Regulatory Compliance 2026
# ===========================================================================

st.set_page_config(
    page_title="AI Payroll - מערכת שכר חכמה 2026",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# 0. הגדרות עיצוב RTL (מימין לשמאל), אבטחת אייקונים ועיצוב כרטיסים
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* כיוון כללי מימין לשמאל */
    html, body, [data-testid="stAppViewContainer"], .main, .stApp {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* יישור טקסטים וכותרות */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, div, span, caption {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* שמירה על כיוון LTR עבור אייקונים ומספרים בלבד למניעת חפיפת טקסטים */
    .material-symbols-outlined, .stIcon, [data-testid="stMetricValue"] {
        direction: ltr !important;
        display: inline-block;
    }

    /* יישור שדות קלט, תיבות בחירה וכפתורים */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"], .stButton button, .stFileUploader {
        direction: rtl !important;
        text-align: right !important;
    }

    /* עיצוב כרטיסי עובדים ודגלי אנומליות */
    .emp-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        margin-bottom: 16px;
        border: 1px solid #E2E8F0;
        direction: rtl;
        text-align: right;
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

# ניהול מצבי זיכרון עבור אישורים, דחיות ועריכות ב-Session State
if "approved_stubs" not in st.session_state:
    st.session_state.approved_stubs = set()
if "rejected_stubs" not in st.session_state:
    st.session_state.rejected_stubs = set()
if "edited_employees" not in st.session_state:
    st.session_state.edited_employees = {}

# ---------------------------------------------------------------------------
# 1. מנוע חישוב פיננסי מדויק (Exact Decimal Financial Engine - 2026)
# ---------------------------------------------------------------------------
def to_dec(val: float | str | int | None) -> Decimal:
    """המרת ערך ל-Decimal מדויק עם עיגול בנקאי ל-2 ספרות (מתמודד בבטחה עם None/NaN)"""
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
    credit_point_value_monthly: Decimal = to_dec('242.00')  # שווי נקודת זיכוי מעודכן ל-2026
    minimum_wage_hourly: Decimal = to_dec('32.30')
    
    # מדרגות מס הכנסה חודשיות מעודכנות לשנת 2026
    tax_brackets: List[TaxBracket] = field(default_factory=lambda: [
        TaxBracket(to_dec('7010.00'), to_dec('0.10')),
        TaxBracket(to_dec('10060.00'), to_dec('0.14')),
        TaxBracket(to_dec('19000.00'), to_dec('0.20')),  # הורחב ב-2026 ל-19,000 ש"ח
        TaxBracket(to_dec('25100.00'), to_dec('0.31')),  # הורחב ב-2026 ל-25,100 ש"ח
        TaxBracket(to_dec('46690.00'), to_dec('0.35')),
        TaxBracket(None, to_dec('0.47')),
    ])
    
    # מס יסף (3% על חלק הכנסה חודשית מעל 60,130 ש"ח)
    sur_tax_threshold: Decimal = to_dec('60130.00')
    sur_tax_rate: Decimal = to_dec('0.03')
    
    # ביטוח לאומי ומס בריאות מעודכנים לשנת 2026
    bituach_leumi_threshold: Decimal = to_dec('7703.00')  # 60% משכר ממוצע ב-2026
    national_insurance_reduced_rate: Decimal = to_dec('0.0427')  # 4.27% שיעור מופחת
    national_insurance_full_rate: Decimal = to_dec('0.1217')     # 12.17% שיעור מלא
    bituach_leumi_max_income_cap: Decimal = to_dec('51910.00')   # תקרת גבייה מרבית חודשית

# ---------------------------------------------------------------------------
# 2. סרגל צד - לוח בקרת רגולציה וחוקי מס דינמיים (Human-in-the-Loop)
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ בקרת רגולציה וחוקי מס")
st.sidebar.markdown("באפשרות חשב השכר לעדכן פרמטרים או להעלות קובץ רגולציה מעודכן:")

use_custom_reg = st.sidebar.checkbox("הפעל הגדרות רגולציה מותאמות אישית", value=False)

if use_custom_reg:
    custom_credit_val = st.sidebar.number_input("שווי נקודת זיכוי חודשי (₪)", value=242.0, step=1.0)
    custom_ni_thresh = st.sidebar.number_input("תקרת ביטוח לאומי מופחת (₪)", value=7703.0, step=10.0)
    custom_ni_cap = st.sidebar.number_input("תקרת גבייה מרבית ב.לאומי (₪)", value=51910.0, step=100.0)
    
    current_rules = RegulatoryData2026(
        credit_point_value_monthly=to_dec(custom_credit_val),
        bituach_leumi_threshold=to_dec(custom_ni_thresh),
        bituach_leumi_max_income_cap=to_dec(custom_ni_cap)
    )
    st.sidebar.success("✅ מופעלות הגדרות רגולציה מותאמות אישית")
else:
    current_rules = RegulatoryData2026()
    st.sidebar.info("ℹ️ מופעלות הגדרות ברירת מחדל מעודכנות לשנת 2026")

# ---------------------------------------------------------------------------
# 3. מנגנון סריקת אנומליות ודירוג סיכונים ב-AI
# ---------------------------------------------------------------------------
@dataclass
class AnomalyFlag:
    risk_level: str  # HIGH, MEDIUM, LOW
    field_name: str
    message_hebrew: str
    historical_baseline: str
    current_value: str

class AIAnomalyDetector:
    """סורק AI לזיהוי חריגות בשכר ובשעות נוספות להצגה לחשב השכר בלבד"""
    @staticmethod
    def scan_employee_payroll(emp_data: dict, historical_avg: dict) -> List[AnomalyFlag]:
        flags = []
        
        # 1. קפיצה בשעות נוספות (Overtime Spike)
        curr_ot = float(emp_data.get('overtime_hours', 0) or 0)
        avg_ot = float(historical_avg.get('overtime_hours', 0) or 0)
        if avg_ot > 0 and curr_ot > avg_ot * 1.8 and curr_ot > 15:
            pct_increase = int((curr_ot / avg_ot - 1) * 100)
            flags.append(AnomalyFlag(
                risk_level="HIGH",
                field_name="overtime_hours",
                message_hebrew=f"קפיצה חריגה של {pct_increase}% בשעות נוספות ביחס לממוצע ההיסטורי.",
                historical_baseline=f"{avg_ot} שעות",
                current_value=f"{curr_ot} שעות"
            ))
            
        # 2. בונוס/עמלה חריגה
        curr_bonus = float(emp_data.get('bonus', 0) or 0)
        avg_bonus = float(historical_avg.get('bonus', 0) or 0)
        if curr_bonus > 0 and (avg_bonus == 0 or curr_bonus > avg_bonus * 2):
            flags.append(AnomalyFlag(
                risk_level="MEDIUM",
                field_name="bonus",
                message_hebrew=f"בונוס/עמלה בגובה ₪{curr_bonus:,.2f} חורג מהנורמה החודשית.",
                historical_baseline=f"₪{avg_bonus:,.2f}",
                current_value=f"₪{curr_bonus:,.2f}"
            ))

        # 3. בדיקת 0 נקודות זיכוי (מקרה קצה ד': תושב חוץ / ללא זכאות)
        pts = float(emp_data.get('credit_points', 2.25) if emp_data.get('credit_points') is not None else 2.25)
        if pts == 0.0:
            flags.append(AnomalyFlag(
                risk_level="MEDIUM",
                field_name="credit_points",
                message_hebrew="הגדרת 0.00 נקודות זיכוי (תושב חוץ / ללא זכאות) - נדרש וידוא מעמד מס.",
                historical_baseline="2.25 נקודות זיכוי",
                current_value="0.00 נקודות זיכוי"
            ))

        # 4. עדכון טופס 101 חדש
        if emp_data.get('form_101_updated') and pts == float(historical_avg.get('credit_points', 2.25) or 2.25):
            flags.append(AnomalyFlag(
                risk_level="LOW",
                field_name="credit_points",
                message_hebrew="עודכן טופס 101 חדש במערכת - יש לוודא התאמת נקודות זיכוי.",
                historical_baseline=f"{historical_avg.get('credit_points', 2.25)} נקודות זיכוי",
                current_value=f"{pts} נקודות זיכוי"
            ))

        return flags

# ---------------------------------------------------------------------------
# 4. מנוע חישוב שכר מפורט (Calculated Paystub Processor)
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
    credit_points: Decimal
    credit_point_value: Decimal
    income_tax: Decimal
    sur_tax: Decimal
    national_insurance: Decimal
    pension_employee: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    flags: List[AnomalyFlag]

class PayrollProcessor:
    def __init__(self, rules: RegulatoryData2026):
        self.rules = rules
        
    def calculate_tax(self, gross: Decimal, credit_points: Decimal) -> Tuple[Decimal, Decimal]:
        """חישוב מס הכנסה לפי מדרגות 2026 ומס יסף"""
        tax = Decimal('0.00')
        remaining = gross
        prev_limit = Decimal('0.00')
        
        # חישוב מס לפי מדרגות
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
                
        # ניכוי נקודות זיכוי
        tax_credit = credit_points * self.rules.credit_point_value_monthly
        final_income_tax = max(Decimal('0.00'), tax - tax_credit)
        
        # חישוב מס יסף (3% מעל 60,130 ש"ח לחודש ב-2026)
        sur_tax = Decimal('0.00')
        if gross > self.rules.sur_tax_threshold:
            sur_tax = (gross - self.rules.sur_tax_threshold) * self.rules.sur_tax_rate
            
        return to_dec(final_income_tax), to_dec(sur_tax)

    def calculate_national_insurance(self, gross: Decimal) -> Decimal:
        """חישוב ביטוח לאומי ומס בריאות כולל תקרת גבייה מרבית (51,910 ש"ח ב-2026)"""
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
        
        ot_125_pay = to_dec(ot_125_h * hourly_rate * Decimal('1.25'))
        ot_150_pay = to_dec(ot_150_h * hourly_rate * Decimal('1.50'))
        ot_pay = ot_125_pay + ot_150_pay
        
        bonus = to_dec(emp_data.get('bonus', 0))
        gross = base + ot_pay + bonus
        
        # טיפול מדויק בנקודות זיכוי: אם צוין 0.00 לא משנים ל-2.25
        raw_pts = emp_data.get('credit_points')
        if raw_pts is None or str(raw_pts).strip() == "":
            credit_pts = Decimal('2.25')
        else:
            credit_pts = to_dec(raw_pts)
            
        income_tax, sur_tax = self.calculate_tax(gross, credit_pts)
        ni = self.calculate_national_insurance(gross)
        pension_emp = to_dec(gross * Decimal('0.06'))  # 6% חלק עובד
        
        total_tax_and_sur = income_tax + sur_tax
        total_deductions = total_tax_and_sur + ni + pension_emp
        net = gross - total_deductions
        
        flags = AIAnomalyDetector.scan_employee_payroll(emp_data, historical_avg)
        
        return CalculatedPaystub(
            emp_id=str(emp_data.get('id', '')),
            emp_name=str(emp_data.get('name', '')),
            base_salary=base,
            hourly_rate=hourly_rate,
            ot_hours_125=ot_125_h,
            ot_hours_150=ot_150_h,
            overtime_125_pay=ot_125_pay,
            overtime_150_pay=ot_150_pay,
            overtime_pay=ot_pay,
            bonus=bonus,
            gross_salary=gross,
            credit_points=credit_pts,
            credit_point_value=self.rules.credit_point_value_monthly,
            income_tax=total_tax_and_sur,
            sur_tax=sur_tax,
            national_insurance=ni,
            pension_employee=pension_emp,
            total_deductions=total_deductions,
            net_salary=net,
            flags=flags
        )

# ---------------------------------------------------------------------------
# 5. מנוע הפקת HTML מוגן ומעוצב (Escaping & Security)
# ---------------------------------------------------------------------------
def generate_paystub_html(stub: CalculatedPaystub, company_name: str = "חברה בע\"מ") -> str:
    """הפקת HTML מעוצב מוגן מפני הזרקות (HTML Escaping)"""
    safe_emp_name = html.escape(stub.emp_name)
    safe_emp_id = html.escape(stub.emp_id)
    
    # טיפול נקי ומאובטח בשם החברה והתבנית למניעת AttributeError
    clean_company = company_name.rsplit('.', 1)[0] if '.' in company_name else company_name
    safe_company = html.escape(clean_company.replace('_', ' '))
    
    ot_125_row = f"<tr><td style='padding: 8px;'>שעות נוספות 125%</td><td style='padding: 8px;'>{stub.ot_hours_125} שעות</td><td style='padding: 8px;'>₪{stub.overtime_125_pay:,.2f}</td></tr>" if stub.ot_hours_125 > 0 else ""
    ot_150_row = f"<tr><td style='padding: 8px;'>שעות נוספות 150%</td><td style='padding: 8px;'>{stub.ot_hours_150} שעות</td><td style='padding: 8px;'>₪{stub.overtime_150_pay:,.2f}</td></tr>" if stub.ot_hours_150 > 0 else ""
    bonus_row = f"<tr><td style='padding: 8px;'>בונוס / עמלות</td><td style='padding: 8px;'>-</td><td style='padding: 8px;'>₪{stub.bonus:,.2f}</td></tr>" if stub.bonus > 0 else ""

    return f"""
    <div style="font-family: Arial, sans-serif; direction: rtl; text-align: right; border: 2px solid #2B6CB0; border-radius: 12px; padding: 24px; max-width: 680px; margin: auto; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 16px;">
            <div>
                <h2 style="color: #2B6CB0; margin: 0;">תלוש שכר חודשי - {safe_company}</h2>
                <p style="margin: 4px 0; color: #718096; font-size: 14px;">תקופת חישוב: שנת מס 2026</p>
            </div>
            <div style="text-align: left;">
                <span style="background-color: #EBF8FF; color: #2B6CB0; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 14px;">מאושר לשילום</span>
            </div>
        </div>
        
        <table style="width: 100%; margin-bottom: 16px; font-size: 15px; border-collapse: collapse;">
            <tr style="background-color: #F7FAFC;">
                <td style="padding: 8px; font-weight: bold;">שם העובד/ת:</td>
                <td style="padding: 8px;">{safe_emp_name}</td>
                <td style="padding: 8px; font-weight: bold;">ת.ז / מספר עובד:</td>
                <td style="padding: 8px;">{safe_emp_id}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">נקודות זיכוי:</td>
                <td style="padding: 8px;">{stub.credit_points} נ"ז (₪{stub.credit_points * stub.credit_point_value:,.2f})</td>
                <td style="padding: 8px; font-weight: bold;">תעריף שעתי:</td>
                <td style="padding: 8px;">₪{stub.hourly_rate:,.2f}</td>
            </tr>
        </table>

        <h4 style="color: #2D3748; border-bottom: 1px solid #CBD5E0; padding-bottom: 6px; margin-bottom: 8px;">📊 פירוט הכנסות (ברוטו)</h4>
        <table style="width: 100%; margin-bottom: 16px; font-size: 14px; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #EDF2F7; text-align: right;">
                    <th style="padding: 8px;">רכיב</th>
                    <th style="padding: 8px;">כמות/שעות</th>
                    <th style="padding: 8px;">סכום</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 8px;">שכר יסוד</td>
                    <td style="padding: 8px;">182 שעות</td>
                    <td style="padding: 8px;">₪{stub.base_salary:,.2f}</td>
                </tr>
                {ot_125_row}
                {ot_150_row}
                {bonus_row}
                <tr style="font-weight: bold; background-color: #F7FAFC;">
                    <td style="padding: 8px;">סה"כ שכר ברוטו</td>
                    <td style="padding: 8px;">-</td>
                    <td style="padding: 8px; color: #2B6CB0;">₪{stub.gross_salary:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <h4 style="color: #2D3748; border-bottom: 1px solid #CBD5E0; padding-bottom: 6px; margin-bottom: 8px;">📉 פירוט ניקויים וניכויים</h4>
        <table style="width: 100%; margin-bottom: 20px; font-size: 14px; border-collapse: collapse;">
            <tbody>
                <tr>
                    <td style="padding: 8px;">מס הכנסה ומס יסף</td>
                    <td style="padding: 8px; color: #C53030;">₪{stub.income_tax:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">ביטוח לאומי ומס בריאות</td>
                    <td style="padding: 8px; color: #C53030;">₪{stub.national_insurance:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">פנסיה חלק עובד (6%)</td>
                    <td style="padding: 8px; color: #C53030;">₪{stub.pension_employee:,.2f}</td>
                </tr>
                <tr style="font-weight: bold; background-color: #FFF5F5;">
                    <td style="padding: 8px; color: #9B2C2C;">סה"כ ניכויים</td>
                    <td style="padding: 8px; color: #9B2C2C;">₪{stub.total_deductions:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div style="background-color: #2B6CB0; color: white; padding: 16px; border-radius: 8px; text-align: center; font-size: 20px; font-weight: bold;">
            💰 שכר נטו לתשלום: ₪{stub.net_salary:,.2f}
        </div>
    </div>
    """

# ---------------------------------------------------------------------------
# 6. ממשק משתמש ראשי (Streamlit Dashboard Interface)
# ---------------------------------------------------------------------------
st.title("🤖 Autonomous AI Payroll System (2026)")
st.caption("מערכת חישוב שכר אוטונומית בבינה מלאכותית עם לוח בקרה ואישור חשב שכר (Human-in-the-Loop)")

# צעד 1: טעינת נתונים
st.header("1️⃣ קליטת נתוני שכר וקובץ עובדים")

uploaded_file = st.file_uploader("העלי קובץ נתוני שכר (Excel / CSV):", type=["xlsx", "xls", "csv"])

# הגדרת נתוני דמו כברירת מחדל לכיסוי כל מקרי הקצה
sample_employees = [
    {
        "id": "101", "name": "ישראל ישראלי", "base_salary": 12500,
        "overtime_hours": 42, "overtime_125_hours": 30, "overtime_150_hours": 12,
        "bonus": 1850, "credit_points": 2.25, "form_101_updated": False
    },
    {
        "id": "102", "name": "דנה לוי", "base_salary": 16000,
        "overtime_hours": 5, "overtime_125_hours": 5, "overtime_150_hours": 0,
        "bonus": 4500, "credit_points": 2.75, "form_101_updated": True
    },
    {
        "id": "103", "name": "ג'ון דו (תושב חוץ)", "base_salary": 15000,
        "overtime_hours": 0, "overtime_125_hours": 0, "overtime_150_hours": 0,
        "bonus": 0, "credit_points": 0.0, "form_101_updated": False
    },
    {
        "id": "104", "name": "משה כהן (שכר גבוה)", "base_salary": 65000,
        "overtime_hours": 0, "overtime_125_hours": 0, "overtime_150_hours": 0,
        "bonus": 0, "credit_points": 2.25, "form_101_updated": False
    }
]

historical_averages = {
    "101": {"overtime_hours": 15, "bonus": 500, "credit_points": 2.25},
    "102": {"overtime_hours": 4, "bonus": 1500, "credit_points": 2.75},
    "103": {"overtime_hours": 0, "bonus": 0, "credit_points": 0.0},
    "104": {"overtime_hours": 0, "bonus": 0, "credit_points": 2.25}
}

active_emp_list = sample_employees

if uploaded_file is not None:
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf") or filename.endswith(".png") or filename.endswith(".jpg"):
        st.error("❌ הקובץ שהועלה אינו נתמך. נא להעלות קובץ Excel (.xlsx) או CSV מובנה.")
    else:
        try:
            if filename.endswith(".csv"):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
                
            st.success(f"✅ הקובץ '{uploaded_file.name}' נקלט בהצלחה! נמצאו {len(df_raw)} שורות נתונים.")
            
            parsed_list = []
            for idx, row in df_raw.iterrows():
                emp_dict = {
                    "id": str(row.get("ת.ז", row.get("id", idx + 1))),
                    "name": str(row.get("שם עובד", row.get("name", f"עובד {idx+1}"))),
                    "base_salary": float(row.get("שכר יסוד", row.get("base_salary", 10000))),
                    "overtime_hours": float(row.get("שעות נוספות", row.get("overtime_hours", 0))),
                    "overtime_125_hours": float(row.get("שעות 125%", row.get("overtime_125_hours", 0))),
                    "overtime_150_hours": float(row.get("שעות 150%", row.get("overtime_150_hours", 0))),
                    "bonus": float(row.get("בונוס", row.get("bonus", 0))),
                    "credit_points": float(row.get("נקודות זיכוי", row.get("credit_points", 2.25)))
                }
                parsed_list.append(emp_dict)
            if parsed_list:
                active_emp_list = parsed_list
        except Exception as e:
            st.error(f"שגיאה בקריאת הקובץ: {e}. מציג נתוני דמו להתנסות.")

# עיבוד כל התלושים במנוע
processor = PayrollProcessor(current_rules)
calculated_stubs: List[CalculatedPaystub] = []

for emp in active_emp_list:
    emp_id = str(emp.get('id', ''))
    if emp_id in st.session_state.edited_employees:
        emp = emp.copy()
        emp.update(st.session_state.edited_employees[emp_id])
        
    hist = historical_averages.get(emp_id, {})
    stub = processor.process_employee(emp, hist)
    calculated_stubs.append(stub)

# ---------------------------------------------------------------------------
# צעד 2: לוח בקרה ואישור חשב שכר (Human-in-the-Loop Dashboard)
# ---------------------------------------------------------------------------
st.header("2️⃣ לוח בקרה ואישור חשב שכר (Items to Review)")

total_count = len(calculated_stubs)
flagged_count = sum(1 for s in calculated_stubs if s.flags)
clean_count = total_count - flagged_count

m1, m2, m3, m4 = st.columns(4)
m1.metric("סה\"כ עובדים במחזור", total_count)
m2.metric("תלושים תקינים (ללא דגלים)", clean_count, delta="🟢 תקין")
m3.metric("תלושים לבדיקת חשב שכר", flagged_count, delta="⚠️ חריגות", delta_color="inverse")
m4.metric("סה\"כ נטו לתשלום", f"₪{sum(s.net_salary for s in calculated_stubs):,.2f}")

st.markdown("---")

for stub in calculated_stubs:
    emp_id = stub.emp_id
    is_approved = emp_id in st.session_state.approved_stubs
    is_rejected = emp_id in st.session_state.rejected_stubs
    
    status_badge = "🟢 מאושר" if is_approved else ("🔴 נדחה" if is_rejected else "⚠️ ממתין לבדיקה")
    
    with st.expander(f"👤 עובד/ת: {stub.emp_name} (ת.ז: {stub.emp_id}) | שכר ברוטו: ₪{stub.gross_salary:,.2f} | נטו: ₪{stub.net_salary:,.2f} | סטטוס: {status_badge}", expanded=not is_approved):
        
        col_info, col_actions = st.columns(2)
        
        with col_info:
            st.write(f"**שכר יסוד:** ₪{stub.base_salary:,.2f} | **שעות נוספות:** ₪{stub.overtime_pay:,.2f} | **בונוס:** ₪{stub.bonus:,.2f}")
            st.write(f"**מס הכנסה ומס יסף:** ₪{stub.income_tax:,.2f} | **ביטוח לאומי:** ₪{stub.national_insurance:,.2f} | **פנסיה עובד:** ₪{stub.pension_employee:,.2f}")
            st.write(f"**נקודות זיכוי:** {stub.credit_points} נ\"ז (שווי זיכוי: ₪{stub.credit_points * stub.credit_point_value:,.2f})")
            
            if stub.flags:
                st.write("🔍 **חריגות שזוהו על ידי סורק ה-AI:**")
                for flag in stub.flags:
                    css_class = "flag-high" if flag.risk_level == "HIGH" else ("flag-medium" if flag.risk_level == "MEDIUM" else "flag-low")
                    st.markdown(f"<div class='{css_class}'><b>[{flag.risk_level}]</b> {flag.message_hebrew} (ממוצע: {flag.historical_baseline} -> נוכחי: {flag.current_value})</div>", unsafe_allow_html=True)
            else:
                st.success("✅ לא זוהו חריגות - התלוש תקין ומאומת ברמת הדיוק הפיננסי.")

        with col_actions:
            st.write("**פעולות חשב שכר:**")
            btn_app, btn_rej = st.columns(2)
            
            if btn_app.button(f"✅ אשר תלוש", key=f"app_{emp_id}", use_container_width=True):
                st.session_state.approved_stubs.add(emp_id)
                st.session_state.rejected_stubs.discard(emp_id)
                st.rerun()
                
            if btn_rej.button(f"🔴 דחה תלוש", key=f"rej_{emp_id}", use_container_width=True):
                st.session_state.rejected_stubs.add(emp_id)
                st.session_state.approved_stubs.discard(emp_id)
                st.rerun()
                
            with st.popover("✏️ ערוך נתונים"):
                st.write(f"עריכת נתונים עבור {stub.emp_name}:")
                new_base = st.number_input("שכר יסוד חדש:", value=float(stub.base_salary), key=f"base_{emp_id}")
                new_bonus = st.number_input("בונוס חדש:", value=float(stub.bonus), key=f"bon_{emp_id}")
                new_pts = st.number_input("נקודות זיכוי:", value=float(stub.credit_points), step=0.25, key=f"pts_{emp_id}")
                
                if st.button("עדכן וחשב מחדש", key=f"save_{emp_id}"):
                    st.session_state.edited_employees[emp_id] = {
                        "base_salary": new_base,
                        "bonus": new_bonus,
                        "credit_points": new_pts
                    }
                    st.success("הנתונים עודכנו! המערכת מחשבת מחדש...")
                    st.rerun()

# ---------------------------------------------------------------------------
# צעד 3: הפקת תלוש ומשלוח במייל
# ---------------------------------------------------------------------------
st.header("3️⃣ הפקת תלוש מעוצב ותצוגה מקדימה")

selected_emp_name = st.selectbox("בחרי עובד/ת להצגת תלוש מעוצב:", options=[s.emp_name for s in calculated_stubs])
selected_stub = next(s for s in calculated_stubs if s.emp_name == selected_emp_name)

html_paystub = generate_paystub_html(selected_stub)

st.components.v1.html(html_paystub, height=620, scrolling=True)

st.download_button(
    label=f"📥 הורד תלוש שכר (HTML) עבור {selected_stub.emp_name}",
    data=html_paystub,
    file_name=f"paystub_{selected_stub.emp_id}_2026.html",
    mime="text/html"
)
