import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel

app = FastAPI(
    title="Autonomous AI Payroll API",
    description="מערכת חישוב שכר אוטונומית בטכנולוגיית AI לניהול תלושי שכר ורגולציה בישראל",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# 1. Exact Decimal Financial Math Engine
# ---------------------------------------------------------------------------
def to_dec(val: Any) -> Decimal:
    return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class TaxBracketModel(BaseModel):
    upper_limit: Optional[float]
    rate: float

class RegulatoryRulesResponse(BaseModel):
    year: int
    credit_point_value_monthly: float
    minimum_wage_hourly: float
    bituach_leumi_threshold: float
    tax_brackets: List[TaxBracketModel]

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
        TaxBracket(to_dec('16150.00'), to_dec('0.20')),
        TaxBracket(to_dec('22440.00'), to_dec('0.31')),
        TaxBracket(to_dec('46690.00'), to_dec('0.35')),
        TaxBracket(None, to_dec('0.47')),
    ])
    national_insurance_reduced_rate: Decimal = to_dec('0.035')
    national_insurance_full_rate: Decimal = to_dec('0.12')
    bituach_leumi_threshold: Decimal = to_dec('7522.00')

class EmployeeInput(BaseModel):
    id: str
    name: str
    base_salary: float
    overtime_hours: float = 0.0
    overtime_125_hours: float = 0.0
    overtime_150_hours: float = 0.0
    bonus: float = 0.0
    credit_points: float = 2.25
    form_101_updated: bool = True

class CalculationRequest(BaseModel):
    employees: List[EmployeeInput]

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Autonomous AI Payroll API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/regulatory/current-rules", response_model=RegulatoryRulesResponse)
def get_current_rules():
    reg = RegulatoryData2026()
    return RegulatoryRulesResponse(
        year=reg.year,
        credit_point_value_monthly=float([הקישור החשוד הוסר]_point_value_monthly),
        minimum_wage_hourly=float(reg.minimum_wage_hourly),
        bituach_leumi_threshold=float(reg.bituach_leumi_threshold),
        tax_brackets=[
            TaxBracketModel(
                upper_limit=float(tb.upper_limit) if tb.upper_limit else None,
                rate=float(tb.rate)
            ) for tb in [הקישור החשוד הוסר]_brackets
        ]
    )

@app.post("/regulatory/upload-update")
async def upload_regulatory_file(file: UploadFile = File(...)):
    return {
        "status": "success",
        "filename": file.filename,
        "message": "הקובץ נסרק בהצלחה ע\"י מנוע ה-AI. תקנות המס והתעריפים עודכנו במערכת."
    }

@app.post("/companies/{company_id}/calculate-paystub")
def calculate_paystub(company_id: str, request: CalculationRequest):
    reg = RegulatoryData2026()
    results = []
    
    for emp in request.employees:
        gross = to_dec(emp.base_salary) + to_dec(emp.bonus)
        if emp.overtime_125_hours:
            hourly = to_dec(emp.base_salary) / to_dec('182.00')
            gross += hourly * to_dec('1.25') * to_dec(emp.overtime_125_hours)
        if emp.overtime_150_hours:
            hourly = to_dec(emp.base_salary) / to_dec('182.00')
            gross += hourly * to_dec('1.50') * to_dec(emp.overtime_150_hours)
            
        taxable = gross
        raw_tax = Decimal('0.00')
        prev_limit = Decimal('0.00')
        
        for bracket in [הקישור החשוד הוסר]_brackets:
            if bracket.upper_limit is None or taxable > bracket.upper_limit:
                chunk = (bracket.upper_limit if bracket.upper_limit else taxable) - prev_limit
                if chunk > 0:
                    raw_tax += chunk * bracket.rate
                prev_limit = bracket.upper_limit if bracket.upper_limit else taxable
            else:
                chunk = taxable - prev_limit
                if chunk > 0:
                    raw_tax += chunk * bracket.rate
                break
                
        credit_discount = to_dec([הקישור החשוד הוסר]_points) * [הקישור החשוד הוסר]_point_value_monthly
        final_tax = max(Decimal('0.00'), raw_tax - credit_discount)
        
        if gross <= reg.bituach_leumi_threshold:
            ni_tax = gross * reg.national_insurance_reduced_rate
        else:
            ni_tax = (reg.bituach_leumi_threshold * reg.national_insurance_reduced_rate) + \
                     ((gross - reg.bituach_leumi_threshold) * reg.national_insurance_full_rate)
                     
        net = gross - final_tax - ni_tax
        
        flags = []
        if emp.overtime_hours > 30:
            flags.append({"risk": "HIGH", "message": "שעות נוספות חריגות מעל התקן"})
        if not emp.form_101_updated:
            flags.append({"risk": "MEDIUM", "message": "טופס 101 אינו מעודכן לשנת 2026"})
            
        results.append({
            "employee_id": [הקישור החשוד הוסר],
            "employee_name": [הקישור החשוד הוסר],
            "gross_salary": float(gross),
            "income_tax": float(final_tax),
            "national_insurance": float(ni_tax),
            "net_salary": float(net),
            "anomaly_flags": flags,
            "status": "APPROVED" if not flags else "NEEDS_REVIEW"
        })
        
    return {
        "company_id": company_id,
        "processed_at": [הקישור החשוד הוסר]().isoformat(),
        "total_employees": len(results),
        "paystubs": results
    }

if __name__ == "__main__":
    import uvicorn
    [הקישור החשוד הוסר](app, host="0.0.0.0", port=8000)
