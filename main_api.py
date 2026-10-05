from fastapi import FastAPI
from pydantic import BaseModel

# 1. יוצרים את המוח החדש של האפליקציה
app = FastAPI(title="AI Payroll Engine 2026")

# 2. מגדירים איזה פרטים העובד חייב לשלוח לנו
class EmployeeInput(BaseModel):
    emp_id: str
    emp_name: str
    base_salary: float
    credit_points: float = 2.25

# 3. המנוע שמחשב את התלוש
@app.post("/calculate")
def calculate(data: EmployeeInput):
    # חישוב ברוטו
    gross = data.base_salary
    
    # חישוב מס הכנסה בסיסי
    tax_before_credit = gross * 0.14
    tax_credit = data.credit_points * 242.0
    final_tax = max(0.0, tax_before_credit - tax_credit)
    
    # ביטוח לאומי ופנסיה
    ni = gross * 0.0427 if gross <= 7703 else (7703 * 0.0427 + (gross - 7703) * 0.1217)
    pension = gross * 0.06
    
    net = gross - (final_tax + ni + pension)
    
    return {
        "emp_name": data.emp_name,
        "gross_salary": round(gross, 2),
        "income_tax": round(final_tax, 2),
        "national_insurance": round(ni, 2),
        "pension": round(pension, 2),
        "net_salary": round(net, 2)
    }
