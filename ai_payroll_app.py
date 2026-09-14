import sys
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

# ---------------------------------------------------------------------------
# 1. Exact Decimal Financial Math Engine (מנוע חישוב פיננסי מדויק)
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
    credit_point_value_monthly: Decimal = to_dec('242.00')  # שווי נקודת זיכוי לחישוב מס
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
    """רכיב סנכרון בזמן אמת מול חוקי המיסוי והשכר המעודכנים"""
    @staticmethod
    def get_latest_rules() -> RegulatoryData2026:
        # בחיבור אמת: קריאת API בזמן אמת משרתי רשות המיסים וביטוח לאומי
        return RegulatoryData2026()

# ---------------------------------------------------------------------------
# 2. AI Anomaly & Risk Detection Engine (מנגנון סריקת אנומליות ודירוג סיכונים)
# ---------------------------------------------------------------------------
@dataclass
class AnomalyFlag:
    risk_level: str  # HIGH, MEDIUM, LOW
    field_name: str
    message_hebrew: str
    historical_baseline: str
    current_value: str

class AIAnomalyDetector:
    """סורק AI לזיהוי חריגות בשכר ובשעות נוספות לפני אישור החשב"""
    
    @staticmethod
    def scan_employee_payroll(emp_data: dict, historical_avg: dict) -> List[AnomalyFlag]:
        flags = []
        
        # 1. בדיקת קפיצה בשעות נוספות (Overtime Spike)
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
# 3. Payroll Calculation Processor (מנוע חישוב שכר)
# ---------------------------------------------------------------------------
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
    flags: List[AnomalyFlag]
    status: str = "PENDING_REVIEW" # PENDING_REVIEW, APPROVED, REJECTED

class PayrollProcessor:
    def __init__(self):
        self.rules = LiveRegulatorySyncAPI.get_latest_rules()
        
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
                
        # ניכוי נקודות זיכוי
        tax_credit = credit_points * self.rules.credit_point_value_monthly
        final_tax = max(Decimal('0.00'), tax - tax_credit)
        return to_dec(final_tax)

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
        hourly_rate = base / Decimal('182') # תקן 182 שעות
        
        ot_hours_125 = Decimal(str(emp_data.get('overtime_125_hours', 0)))
        ot_hours_150 = Decimal(str(emp_data.get('overtime_150_hours', 0)))
        
        ot_pay = (ot_hours_125 * hourly_rate * Decimal('1.25')) + \
                 (ot_hours_150 * hourly_rate * Decimal('1.50'))
        ot_pay = to_dec(ot_pay)
        
        bonus = to_dec(emp_data.get('bonus', 0))
        gross = base + ot_pay + bonus
        
        credit_pts = Decimal(str(emp_data.get('credit_points', 2.25)))
        income_tax = self.calculate_tax(gross, credit_pts)
        ni = self.calculate_national_insurance(gross)
        pension_emp = to_dec(gross * Decimal('0.06')) # 6% חלק עובד
        
        total_deductions = income_tax + ni + pension_emp
        net = gross - total_deductions
        
        flags = AIAnomalyDetector.scan_employee_payroll(emp_data, historical_avg)
        
        return CalculatedPaystub(
            emp_id=emp_data['id'],
            emp_name=emp_data['name'],
            base_salary=base,
            overtime_pay=ot_pay,
            bonus=bonus,
            gross_salary=gross,
            income_tax=income_tax,
            national_insurance=ni,
            pension_employee=pension_emp,
            total_deductions=total_deductions,
            net_salary=net,
            flags=flags
        )

# ---------------------------------------------------------------------------
# 4. Human-in-the-Loop CLI / Dashboard Interface
# ---------------------------------------------------------------------------
def run_demo():
    print("="*70)
    print("  🤖 מערכת חישוב שכר אוטונומית בבינה מלאכותית (Human-in-the-Loop)")
    print("="*70)
    
    processor = PayrollProcessor()
    
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
            "id": "103", "name": "משה כהן", "base_salary": 9500,
            "overtime_hours": 2, "overtime_125_hours": 2, "overtime_150_hours": 0,
            "bonus": 0, "credit_points": 2.25, "form_101_updated": False
        }
    ]
    
    historical_averages = {
        "101": {"overtime_hours": 15, "bonus": 500, "credit_points": 2.25},
        "102": {"overtime_hours": 4, "bonus": 1500, "credit_points": 2.75},
        "103": {"overtime_hours": 2, "bonus": 0, "credit_points": 2.25}
    }

    paystubs: List[CalculatedPaystub] = []
    for emp in sample_employees:
        hist = historical_averages.get(emp["id"], {})
        paystub = processor.process_employee(emp, hist)
        paystubs.append(paystub)

    print("\n📊 תמונת מצב סריקת AI חודשית:")
    total_count = len(paystubs)
    flagged = [p for p in paystubs if p.flags]
    clean = [p for p in paystubs if not p.flags]
    
    print(f" • סה\"כ תלושים שחושבו: {total_count}")
    print(f" • תלושים תקינים (מאושרים אוטומטית): {len(clean)} 🟢")
    print(f" • תלושים הממתינים לבדיקת חשב שכר: {len(flagged)} ⚠️\n")

    print("-" * 70)
    print("📋 לוח בקרה ואישור חשב שכר (Items to Review):")
    print("-" * 70)

    for p in paystubs:
        status_icon = "🟢 תקין" if not p.flags else "⚠️ דורש בדיקה"
        print(f"\n👤 עובד: {p.emp_name} (ת.ז: {p.emp_id}) | סטטוס: {status_icon}")
        print(f"   ברוטו: ₪{p.gross_salary:,.2f} | מס: ₪{p.income_tax:,.2f} | ב.לאומי: ₪{p.national_insurance:,.2f} | נטו: ₪{p.net_salary:,.2f}")
        
        if p.flags:
            print("   🔍 חריגות שזוהו ע\"י סורק ה-AI:")
            for flag in p.flags:
                risk_icon = "🔴" if flag.risk_level == "HIGH" else ("🟠" if flag.risk_level == "MEDIUM" else "🟡")
                print(f"      {risk_icon} [{flag.risk_level}] {flag.message_hebrew} (ממוצע: {flag.historical_baseline} -> חודשי: {flag.current_value})")
            print("   👉 פעולת חשב שכר: [1] אשר תלוש  [2] דחה/עדכן  [3] תחקור מקור נתונים")
        else:
            print("   ✅ אושר אוטומטית במנוע החישוב המדויק.")

if __name__ == "__main__":
    run_demo()
