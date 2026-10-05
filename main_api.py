from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP

# ===========================================================================
# 🤖 Autonomous Enterprise AI Payroll Engine + Database Architecture (v1.1)
# ===========================================================================

app = FastAPI(
    title="Autonomous Enterprise AI Payroll API & DB 2026",
    description="מנוע חישוב שכר תעשייתי + תשתית מסד נתונים מאובטחת",
    version="1.1.0"
)

# ---------------------------------------------------------------------------
# 1. Pydantic Schemas - אימות נתונים קשיח למניעת קריסות
# ---------------------------------------------------------------------------

class CompanyCreateSchema(BaseModel):
    company_id: str = Field(..., description="ח.פ / מספר חברה")
    company_name: str = Field(..., description="שם החברה המנויה")

class EmployeeInputSchema(BaseModel):
    emp_id: str = Field(..., description="מספר תעודת זהות")
    emp_name: str = Field(..., description="שם העובד")
    company_id: str = Field(..., description="מזהה חברה משוייכת")
    base_salary: float = Field(..., gt=0, description="שכר יסוד")
    overtime_125_hours: float = Field(0.0, ge=0)
    overtime_150_hours: float = Field(0.0, ge=0)
    bonus: float = Field(0.0, ge=0)
    credit_points: float = Field(2.25, ge=0)

class AnomalyFlagOutput(BaseModel):
    risk_level: str
    field_name: str
    message_hebrew: str

class PaystubOutputSchema(BaseModel):
    emp_id: str
    emp_name: str
    company_id: str
    base_salary: float
    hourly_rate: float
    overtime_pay: float
    bonus: float
    gross_salary: float
    taxable_gross: float
    credit_points: float
    income_tax: float
    sur_tax: float
    national_insurance: float
    pension_employee: float
    total_deductions: float
    net_salary: float
    flags: List[AnomalyFlagOutput]

# ---------------------------------------------------------------------------
# 2. Database Models (שמירת חברות, עובדים ותלושים)
# ---------------------------------------------------------------------------

db_companies = {}
db_employees = {}
db_paystubs = []

# ---------------------------------------------------------------------------
# 3. Main Calculation & Database Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/companies", response_model=CompanyCreateSchema)
def create_company(company: CompanyCreateSchema):
    if company.company_id in db_companies:
        raise HTTPException(status_code=400, detail="חברה זו כבר רשומה במערכת")
    db_companies[company.company_id] = company.dict()
    return company

@app.post("/api/v1/calculate-and-save", response_model=PaystubOutputSchema)
def calculate_and_save_stub(emp: EmployeeInputSchema):
    try:
        base = Decimal(str(emp.base_salary)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        hourly_rate = (base / Decimal('182')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        ot_125_h = Decimal(str(emp.overtime_125_hours))
        ot_150_h = Decimal(str(emp.overtime_150_hours))
        ot_pay = (ot_125_h * hourly_rate * Decimal('1.25')) + (ot_150_h * hourly_rate * Decimal('1.50'))
        
        bonus = Decimal(str(emp.bonus))
        gross = base + ot_pay + bonus
        
        # זקופות שווי קרן השתלמות מעל התקרה (15,712 ₪)
        study_fund_cap = Decimal('15712.00')
        study_fund_excess = Decimal('0.00')
        if base > study_fund_cap:
            study_fund_excess = (base - study_fund_cap) * Decimal('0.075')
        
        taxable_gross = gross + study_fund_excess
        credit_pts = Decimal(str(emp.credit_points))
        
        # מדרגות מס 2026
        brackets = [
            (Decimal('7010.00'), Decimal('0.10')),
            (Decimal('10060.00'), Decimal('0.14')),
            (Decimal('19000.00'), Decimal('0.20')),
            (Decimal('25100.00'), Decimal('0.31')),
            (Decimal('46690.00'), Decimal('0.35')),
            (None, Decimal('0.47'))
        ]
        
        tax = Decimal('0.00')
        remaining = taxable_gross
        prev_limit = Decimal('0.00')
        
        for upper_limit, rate in brackets:
            if upper_limit is None:
                tax += remaining * rate
                break
            bracket_size = upper_limit - prev_limit
            if remaining > bracket_size:
                tax += bracket_size * rate
                remaining -= bracket_size
                prev_limit = upper_limit
            else:
                tax += remaining * rate
                break
                
        tax_credit = credit_pts * Decimal('242.00')
        final_income_tax = max(Decimal('0.00'), tax - tax_credit)
        
        # מס יסף (3% מעל 60,130 ₪)
        sur_tax_threshold = Decimal('60130.00')
        sur_tax = Decimal('0.00')
        if taxable_gross > sur_tax_threshold:
            sur_tax = (taxable_gross - sur_tax_threshold) * Decimal('0.03')
            
        total_income_tax = final_income_tax + sur_tax
        
        # ביטוח לאומי
        ni_cap = Decimal('51910.00')
        ni_thresh = Decimal('7703.00')
        taxable_ni = min(gross, ni_cap)
        
        if taxable_ni <= ni_thresh:
            ni = taxable_ni * Decimal('0.0427')
        else:
            ni = (ni_thresh * Decimal('0.0427')) + ((taxable_ni - ni_thresh) * Decimal('0.1217'))
            
        pension_emp = gross * Decimal('0.06')
        
        total_deductions = total_income_tax + ni + pension_emp
        net = gross - total_deductions
        
        flags = []
        if credit_pts == Decimal('0.00'):
            flags.append(AnomalyFlagOutput(
                risk_level="MEDIUM",
                field_name="credit_points",
                message_hebrew="0.00 נקודות זיכוי (תושב חוץ) - דורש אימות רגולטורי"
            ))
        if (ot_125_h + ot_150_h) > Decimal('30.00'):
            flags.append(AnomalyFlagOutput(
                risk_level="HIGH",
                field_name="overtime_hours",
                message_hebrew="כמות שעות נוספות חריגה (מעל 30 שעות בחודש)"
            ))

        result = PaystubOutputSchema(
            emp_id=emp.emp_id,
            emp_name=emp.emp_name,
            company_id=emp.company_id,
            base_salary=float(base),
            hourly_rate=float(hourly_rate.quantize(Decimal('0.01'))),
            overtime_pay=float(ot_pay.quantize(Decimal('0.01'))),
            bonus=float(bonus),
            gross_salary=float(gross.quantize(Decimal('0.01'))),
            taxable_gross=float(taxable_gross.quantize(Decimal('0.01'))),
            credit_points=float(credit_pts),
            income_tax=float(total_income_tax.quantize(Decimal('0.01'))),
            sur_tax=float(sur_tax.quantize(Decimal('0.01'))),
            national_insurance=float(ni.quantize(Decimal('0.01'))),
            pension_employee=float(pension_emp.quantize(Decimal('0.01'))),
            total_deductions=float(total_deductions.quantize(Decimal('0.01'))),
            net_salary=float(net.quantize(Decimal('0.01'))),
            flags=flags
        )
        
        db_paystubs.append(result.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בחישוב השכר: {str(e)}")
