from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP
import hmac
import hashlib
import time
from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ===========================================================================
# 🤖 Autonomous Enterprise AI Payroll Engine + Supabase Cloud DB (v1.3)
# ===========================================================================

# 🔗 כתובת החיבור למסד הנתונים הענני ב-Supabase
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.rwtukxxhnkonfughihfw:EMUNa3135%40%21@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")
Copy the connection details for your database.
Details:
If your database password contains special characters, percent-encode them in the connection string.
Connection parameters
host:db.rwtukxxhnkonfwqhihfw.supabase.co
port:5432
database:postgres
user:postgres
Code:
File: Code
```
postgresql://postgres:[YOUR-PASSWORD]@db.rwtukxxhnkonfwqhihfw.supabase.co:5432/postgres
```

2. Install Agent Skills (optional)
Agent Skills give AI coding tools ready-made instructions, scripts, and resources for working with Supabase more accurately and efficiently.
Code:
File: Code
```
npx skills add supabase/agent-skills
```Supabase"

# הגדרת מנוע מסד הנתונים
if DATABASE_URL.startswith("postgresql://"):
    # תיקון תאימות קטן לדרייבר של פייתון במידת הצורך
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception:
    # גיבוי לזיכרון מקומי במידה והקישור עדיין לא הוגדר
    engine = create_engine("sqlite:///./fallback_payroll.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

app = FastAPI(
    title="Autonomous Enterprise AI Payroll API & Supabase 2026",
    description="מנוע חישוב שכר תעשייתי + אבטחת Bearer + מסד נתונים ענני ב-Supabase",
    version="1.3.0"
)

security = HTTPBearer()
SECRET_KEY = "my_super_secret_payroll_key_2026"

# ---------------------------------------------------------------------------
# 1. Database ORM Models (טבלאות קבועות ב-Supabase)
# ---------------------------------------------------------------------------

class CompanyDB(Base):
    __tablename__ = "companies"
    company_id = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=False)

class PaystubDB(Base):
    __tablename__ = "paystubs"
    id = Column(String, primary_key=True, index=True)
    emp_id = Column(String, index=True)
    emp_name = Column(String)
    company_id = Column(String, index=True)
    gross_salary = Column(Float)
    income_tax = Column(Float)
    national_insurance = Column(Float)
    pension_employee = Column(Float)
    net_salary = Column(Float)

# יצירת הטבלאות ב-Supabase באופן אוטומטי
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# 2. Pydantic Schemas
# ---------------------------------------------------------------------------

class LoginSchema(BaseModel):
    username: str
    password: str

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

class PaystubOutputSchema(BaseModel):
    emp_id: str
    emp_name: str
    company_id: str
    gross_salary: float
    income_tax: float
    national_insurance: float
    pension_employee: float
    total_deductions: float
    net_salary: float

# ---------------------------------------------------------------------------
# 3. Security Helper Functions
# ---------------------------------------------------------------------------

db_users = {"admin@payroll.ai": "Payroll2026!"}

def create_simple_token(username: str) -> str:
    payload = f"{username}:{int(time.time())}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        parts = token.split(":")
        if len(parts) != 3:
            raise HTTPException(status_code=401, detail="מפתח אבטחה לא תקין")
        username, timestamp, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{username}:{timestamp}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=401, detail="חתימת אבטחה מזויפת")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="נדרשת התחברות מאובטחת למערכת")

# ---------------------------------------------------------------------------
# 4. Endpoints with Supabase Persistence
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/login", response_model=TokenOutputSchema)
def login(credentials: LoginSchema):
    user_pass = db_users.get(credentials.username)
    if not user_pass or user_pass != credentials.password:
        raise HTTPException(status_code=401, detail="שם משתמש או סיסמה שגויים")
    token = create_simple_token(credentials.username)
    return TokenOutputSchema(
        access_token=token,
        message="התחברות בוצעה בהצלחה! מפתח האבטחה נוצר."
    )

@app.post("/api/v1/companies", response_model=CompanyCreateSchema)
def create_company(company: CompanyCreateSchema, user: str = Depends(verify_token), db: Session = Depends(get_db)):
    existing = db.query(CompanyDB).filter(CompanyDB.company_id == company.company_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="חברה זו כבר רשומה במערכת")
    
    new_comp = CompanyDB(company_id=company.company_id, company_name=company.company_name)
    db.add(new_comp)
    db.commit()
    return company

@app.post("/api/v1/calculate-and-save", response_model=PaystubOutputSchema)
def calculate_and_save_stub(emp: EmployeeInputSchema, user: str = Depends(verify_token), db: Session = Depends(get_db)):
    try:
        base = Decimal(str(emp.base_salary)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        hourly_rate = (base / Decimal('182')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        ot_125_h = Decimal(str(emp.overtime_125_hours))
        ot_150_h = Decimal(str(emp.overtime_150_hours))
        ot_pay = (ot_125_h * hourly_rate * Decimal('1.25')) + (ot_150_h * hourly_rate * Decimal('1.50'))
        
        bonus = Decimal(str(emp.bonus))
        gross = base + ot_pay + bonus
        
        credit_pts = Decimal(str(emp.credit_points))
        tax_credit = credit_pts * Decimal('242.00')
        raw_tax = gross * Decimal('0.14')
        final_tax = max(Decimal('0.00'), raw_tax - tax_credit)
        
        ni = gross * Decimal('0.0427') if gross <= Decimal('7703') else (Decimal('7703') * Decimal('0.0427') + (gross - Decimal('7703')) * Decimal('0.1217'))
        pension = gross * Decimal('0.06')
        
        total_deductions = final_tax + ni + pension
        net = gross - total_deductions
        
        # שמירה קבועה ב-Supabase!
        stub_id = f"{emp.company_id}_{emp.emp_id}_{int(time.time())}"
        new_stub = PaystubDB(
            id=stub_id,
            emp_id=emp.emp_id,
            emp_name=emp.emp_name,
            company_id=emp.company_id,
            gross_salary=float(gross),
            income_tax=float(final_tax),
            national_insurance=float(ni),
            pension_employee=float(pension),
            net_salary=float(net)
        )
        db.add(new_stub)
        db.commit()
        
        return PaystubOutputSchema(
            emp_id=emp.emp_id,
            emp_name=emp.emp_name,
            company_id=emp.company_id,
            gross_salary=float(gross.quantize(Decimal('0.01'))),
            income_tax=float(final_tax.quantize(Decimal('0.01'))),
            national_insurance=float(ni.quantize(Decimal('0.01'))),
            pension_employee=float(pension.quantize(Decimal('0.01'))),
            total_deductions=float(total_deductions.quantize(Decimal('0.01'))),
            net_salary=float(net.quantize(Decimal('0.01')))
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בחישוב השכר: {str(e)}")
