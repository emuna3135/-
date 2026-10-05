
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP
import hmac
import hashlib
import time

# ===========================================================================
# 🤖 Autonomous Enterprise AI Payroll Engine + Security Architecture (v1.2)
# ===========================================================================

app = FastAPI(
    title="Autonomous Enterprise AI Payroll API (Secure v1.2)",
    description="מנוע חישוב שכר תעשייתי + מנגנון אבטחה והתחברות מוצפן (JWT/Bearer Token)",
    version="1.2.0"
)

security = HTTPBearer()

# מפתח הצפנה סודי
SECRET_KEY = "my_super_secret_payroll_key_2026"

# ---------------------------------------------------------------------------
# 1. Pydantic Schemas - מודלים לאימות נתונים והתחברות
# ---------------------------------------------------------------------------

class LoginSchema(BaseModel):
    username: str = Field(..., description="שם משתמש")
    password: str = Field(..., description="סיסמה")

class TokenOutputSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str

class CompanyCreateSchema(BaseModel):
    company_id: str = Field(..., description="ח.פ / מספר חברה")
    company_name: str = Field(..., description="שם החברה המנויה")

class EmployeeInputSchema(BaseModel):
    emp_id: str = Field(..., description="מספר תעודת זהות")
    emp_name: str = Field(..., description="שם העובד")
    company_id: str = Field(..., description="מזהה חברה משוייכת")
    base_salary: float = Field(..., gt=0)
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
# 2. Database Models (משתמשים, חברות ותלושים)
# ---------------------------------------------------------------------------

db_users = {
    "admin@payroll.ai": "Payroll2026!"  # משתמש מורשה ראשון
}
db_companies = {}
db_paystubs = []

# ---------------------------------------------------------------------------
# 3. Security Helper Functions - ייצור ואימות מפתחות גישה
# ---------------------------------------------------------------------------

def create_simple_token(username: str) -> str:
    """ייצור מפתח אבטחה מוצפן (Token) המבוסס על חתימת HMAC"""
    payload = f"{username}:{int(time.time())}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """שומר הראש של ה-API: בודק שכל בקשה מגיעה עם מפתח אבטחה תקף"""
    token = credentials.credentials
    try:
        parts = token.split(":")
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="מפתח אבטחה לא תקין")
        
        username, timestamp, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{username}:{timestamp}".encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=401, detail="חתימת אבטחה מזויפת או שגויה")
            
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="גישה נדחתה: נדרשת התחברות מאובטחת למערכת")

# ---------------------------------------------------------------------------
# 4. Endpoints - התחברות מאובטחת + הגנת נתיבים
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/login", response_model=TokenOutputSchema)
def login(credentials: LoginSchema):
    """מסך התחברות מאובטח - מחזיר מפתח גישה רק למשתמשים מאושרים"""
    user_pass = db_users.get(credentials.username)
    if not user_pass or user_pass != credentials.password:
        raise HTTPException(status_code=401, detail="שם משתמש או סיסמה שגויים")
    
    token = create_simple_token(credentials.username)
    return TokenOutputSchema(
        access_token=token,
        token_type="bearer",
        message="התחברות בוצעה בהצלחה! מפתח האבטחה נוצר."
    )

@app.post("/api/v1/companies", response_model=CompanyCreateSchema)
def create_company(company: CompanyCreateSchema, user: str = Depends(verify_token)):
    """נתיב מוגן: יצירת חברה דורשת מפתח אבטחה"""
    if company.company_id in db_companies:
        raise HTTPException(status_code=400, detail="חברה זו כבר רשומה במערכת")
    db_companies[company.company_id] = company.dict()
    return company

@app.post("/api/v1/calculate-and-save", response_model=PaystubOutputSchema)
def calculate_and_save_stub(emp: EmployeeInputSchema, user: str = Depends(verify_token)):
    """נתיב מוגן: חישוב שכר דורש מפתח אבטחה תקף"""
    try:
        base = Decimal(str(emp.base_salary)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        hourly_rate = (base / Decimal('182')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        ot_125_h = Decimal(str(emp.overtime_125_hours))
        ot_150_h = Decimal(str(emp.overtime_150_hours))
        ot_pay = (ot_125_h * hourly_rate * Decimal('1.25')) + (ot_150_h * hourly_rate * Decimal('1.50'))
        
        bonus = Decimal(str(emp.bonus))
        gross = base + ot_pay + bonus
        
        study_fund_cap = Decimal('15712.00')
        study_fund_excess = Decimal('0.00')
        if base > study_fund_cap:
            study_fund_excess = (base - study_fund_cap) * Decimal('0.075')
        
        taxable_gross = gross + study_fund_excess
        credit_pts = Decimal(str(emp.credit_points))
        
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
        
        sur_tax_threshold = Decimal('60130.00')
        sur_tax = Decimal('0.00')
        if taxable_gross > sur_tax_threshold:
            sur_tax = (taxable_gross - sur_tax_threshold) * Decimal('0.03')
            
        total_income_tax = final_income_tax + sur_tax
        
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
