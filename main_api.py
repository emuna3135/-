import csv
import datetime
import io
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

import bcrypt
import jwt
import card
import payslip
import templating
import termination
import attendance_pdf
import engine as pe  # מנוע החישוב המאומת (engine.py)
import authpolicy
import proposals
import overrides
import upload_rules
import localities
import secure
import totp
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric,
                        String, create_engine, text)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# הגדרות - כל הסודות מגיעים ממשתני סביבה ב-Render (לא כתובים בקוד!)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_test.db")
JWT_SECRET = os.getenv("JWT_SECRET", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
_cfg_errors, _cfg_warnings = authpolicy.production_config_problems(os.environ)
for _w in _cfg_warnings:
    print("CONFIG WARNING:", _w)
if _cfg_errors:
    # בפרודקשן השרת לא עולה עם הגדרות אבטחה חסרות
    raise RuntimeError("הגדרות אבטחה חסרות בפרודקשן: " + "; ".join(_cfg_errors))
REQUIRE_2FA = authpolicy.two_factor_required(os.environ)
if not JWT_SECRET:
    # פיתוח בלבד (בפרודקשן נחסם למעלה). מפתח זמני אקראי - כל הכניסות יתאפסו בכל הפעלה.
    JWT_SECRET = uuid.uuid4().hex + uuid.uuid4().hex
    print("WARNING: JWT_SECRET not set - using a temporary random key")
RATE_LIMITER = authpolicy.RateLimiter()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def new_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=new_id)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)


class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    tax_id = Column(String)


class Membership(Base):
    """מי מורשה לעבוד על איזה משרד. זה מה שמבטיח הפרדה בין משרדים."""
    __tablename__ = "memberships"
    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    # owner / accountant / viewer (authpolicy.ROLES). ברירת מחדל = owner רק עבור יוצר המשרד (create_company)
    role = Column(String, nullable=False, default="viewer")


class Paystub(Base):
    __tablename__ = "paystubs"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    emp_id_number = Column(String, nullable=False)
    emp_name = Column(String, nullable=False)
    period = Column(String)
    gross = Column(Numeric(12, 2))
    income_tax = Column(Numeric(12, 2))
    # ביטוח לאומי ובריאות: שורות נפרדות, ללא עיגול באחסון (תשובת רו"ח 11.11.2026)
    national_insurance = Column(Numeric(16, 8))
    health_insurance = Column(Numeric(16, 8))
    pension_employee = Column(Numeric(12, 2))
    net = Column(Numeric(12, 2))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CompanyKey(Base):
    """מפתח הצפנה נפרד לכל משרד. מוצפן במפתח הראשי (FIELD_KEY)."""
    __tablename__ = "company_keys"
    company_id = Column(String, ForeignKey("companies.id"), primary_key=True)
    dek_enc = Column(String, nullable=False)


# כל הנתונים הרגישים נשמרים ב-payload_enc (JSON מוצפן במפתח המשרד).
# בעמודות גלויות נשארים רק מזהים טכניים לחיפוש.
class Employee(Base):
    __tablename__ = "employees_v2"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    id_hash = Column(String, index=True, nullable=False)
    payload_enc = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmployeeYear(Base):
    """נתוני טופס 101 לשנת מס אחת."""
    __tablename__ = "employee_years_v2"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, index=True, nullable=False)
    employee_id = Column(String, ForeignKey("employees_v2.id"), index=True, nullable=False)
    year = Column(Integer, nullable=False)
    payload_enc = Column(String, nullable=False)


class Cumulative(Base):
    """מצטבר מתחילת שנת מס לכל עובד (לחישוב מס מצטבר)."""
    __tablename__ = "cumulative_v2"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, index=True, nullable=False)
    emp_key = Column(String, index=True, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    payload_enc = Column(String, nullable=False)


class PaystubV2(Base):
    __tablename__ = "paystubs_v2"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, index=True, nullable=False)
    emp_key = Column(String, index=True, nullable=False)
    year = Column(Integer)
    month = Column(Integer)
    payload_enc = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserSecurity(Base):
    """הגדרות אבטחה למשתמש (2FA). טבלה נפרדת כדי לא לשנות את טבלת users הקיימת."""
    __tablename__ = "user_security"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    totp_secret_enc = Column(String)
    totp_enabled = Column(Boolean, default=False)
    totp_last_step = Column(Integer)                              # הצעד האחרון שנוצל: קוד לא משמש פעמיים
    token_version = Column(Integer, nullable=False, default=0)   # העלאה = ביטול כל הטוקנים הקיימים
    disabled = Column(Boolean, nullable=False, default=False)    # משתמש שהושבת (תקנה 9(ג))
    password_changed_at = Column(DateTime)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(String, primary_key=True, default=new_id)
    email = Column(String, index=True, nullable=False)
    ok = Column(Boolean, nullable=False)
    at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AuditLog(Base):
    """יומן פעולות. לא נשמרים בו ערכים רגישים (ת"ז, שכר) - רק מה נעשה ועל איזו ישות."""
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True, default=new_id)
    at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    user_id = Column(String, index=True)
    company_id = Column(String, index=True)
    action = Column(String, nullable=False)
    entity = Column(String)
    entity_id = Column(String)
    detail = Column(String)


class Document(Base):
    """קובץ שהועלה (PDF/תמונה). התוכן מוצפן במפתח המשרד; נשמר גיבוב לזיהוי כפילויות."""
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    kind = Column(String, nullable=False)
    ext = Column(String, nullable=False)
    sha256 = Column(String, index=True, nullable=False)
    size = Column(Integer, nullable=False)
    blob_enc = Column(LargeBinary, nullable=False)
    uploaded_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Proposal(Base):
    """הצעה שממתינה לאישור חשב שכר. התוכן (שדות + אימות) מוצפן; רק מצב ומזהים גלויים."""
    __tablename__ = "proposals"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    document_id = Column(String, ForeignKey("documents.id"))
    kind = Column(String, nullable=False)
    status = Column(String, index=True, nullable=False, default=proposals.PENDING)
    employee_id = Column(String)
    year = Column(Integer)
    payload_enc = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    decided_by = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    decided_at = Column(DateTime)


class CompanyRule(Base):
    """הנחיה שאושרה על ידי חשב. שייכת למשרד אחד בלבד, גרסאות, לא נמחקת. לא משנה חישוב עד חיבור מפורש."""
    __tablename__ = "company_rules"
    id = Column(String, primary_key=True, default=new_id)
    company_id = Column(String, ForeignKey("companies.id"), index=True, nullable=False)
    proposal_id = Column(String, nullable=False)
    topic = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    payload_enc = Column(String, nullable=False)
    approved_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# הצפנה: מפתח לכל משרד
# ---------------------------------------------------------------------------
def company_dek(db: Session, company_id: str) -> bytes:
    row = db.get(CompanyKey, company_id)
    if row:
        return secure.unwrap_dek(row.dek_enc)
    dek = secure.new_dek()
    db.add(CompanyKey(company_id=company_id, dek_enc=secure.wrap_dek(dek)))
    db.flush()
    return dek


def seal(db: Session, company_id: str, obj) -> str:
    return secure.seal(company_dek(db, company_id), obj)


def unseal(db: Session, company_id: str, token: str):
    return secure.unseal(company_dek(db, company_id), token)


def emp_key(company_id: str, id_number: str) -> str:
    return secure.lookup_hash(f"{company_id}:{id_number}")


# ---------------------------------------------------------------------------
# קלט וחישוב - כל הכללים נמצאים ב-engine.py ונבדקים ב-test_engine.py
# ---------------------------------------------------------------------------
MONTHLY_HOURS = Decimal("182")   # לא מאומת - משמש רק לחישוב שעות נוספות


class PaystubIn(BaseModel):
    emp_id_number: str
    emp_name: str
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    base_salary: float = Field(..., gt=0)
    ot_hours_125: float = Field(0, ge=0)
    ot_hours_150: float = Field(0, ge=0)
    bonus: float = Field(0, ge=0)
    tax_exempt: float = Field(0, ge=0)            # רכיבים פטורים ממס (למשל החזר טלפון)
    month_weight: float = Field(1, gt=0, le=1)    # חודש עבודה חלקי (למשל 17/25); לא מאומת מעבר לתלוש אחד
    # הטבות (זקיפת שווי): חייבות במס וב"ל, לא משולמות במזומן
    phone_expense: float = Field(0, ge=0)         # הוצאה חודשית על רט"ן שהמעסיק משלם
    phone_employee_share_rate: float = Field(0, ge=0, le=1)
    phone_employee_share_amount: float = Field(0, ge=0)   # השתתפות בסכום קבוע בחודש
    car_price: float = Field(0, ge=0)             # מחיר מתואם לצרכן (רכב שנרשם מ-2010)
    car_kind: str = Field("regular", pattern="^(regular|hybrid|plugin|electric)$")
    # השתתפות מעסיק בפעילות ועד עובדים (יום כיף וכד'): סכום לעובד, ואם נקבעה לפי עובד ספציפית
    committee_per_employee: float = Field(0, ge=0)
    committee_specific_per_employee: Optional[bool] = None
    # רכב תפעולי = כל שלושת התנאים מתקיימים (אחרת נזקף שווי):
    car_business_use_only: Optional[bool] = None
    car_leaves_workplace_after_hours: Optional[bool] = None
    car_workplace_is_residence: bool = False
    car_gross_weight_kg: Optional[float] = Field(None, gt=0)   # מעל 3,500 ק"ג: אין שווי
    credit_points: float = Field(2.25, ge=0)
    locality: Optional[str] = Field(None, max_length=80)      # יישוב מוטב §11 (שם כמו בלוח העזר 2026)
    tax_mode: str = Field("cumulative", pattern="^(cumulative|no_coordination|fixed_rate)$")
    fixed_rate: Optional[float] = Field(None, ge=0, le=0.5)      # אישור תיאום מס: שיעור ניכוי קבוע (tax_mode=fixed_rate)
    pension_employee_rate: float = Field(0.06, ge=0, le=0.5)
    study_fund_employee_rate: float = Field(0, ge=0, le=0.5)
    life_insurance: float = Field(0, ge=0)
    employer_pension_rate: float = Field(0, ge=0, le=0.5)
    employer_severance_rate: float = Field(0, ge=0, le=0.5)
    employer_study_fund_rate: float = Field(0, ge=0, le=0.5)
    other_deductions: float = Field(0, ge=0)
    manual_income_tax: Optional[float] = None     # הזנה ידנית כשהמערכת לא מחשבת
    # מצטבר ממערכת קודמת - רק לעובד שמתחיל באמצע שנה ואין לו חודשים קודמים כאן
    prev_cum_taxable: Optional[float] = None
    prev_cum_tax: Optional[float] = None
    prev_cum_deposits: Optional[float] = None
    prev_cum_life: Optional[float] = None
    prev_cum_ni_base: Optional[float] = None
    period: Optional[str] = None


def load_prev(db: Session, company_id: str, p: PaystubIn) -> dict:
    """המצטבר עד החודש הקודם. חסר ובאמצע השנה -> שגיאה ברורה, לא ניחוש."""
    if p.month == 1:
        return dict(pe.ZERO_PREV)
    row = (db.query(Cumulative)
           .filter(Cumulative.company_id == company_id,
                   Cumulative.emp_key == emp_key(company_id, p.emp_id_number),
                   Cumulative.year == p.year, Cumulative.month == p.month - 1)
           .first())
    if row:
        d = unseal(db, company_id, row.payload_enc)
        out = {"cum_taxable": Decimal(d["cum_taxable"]), "cum_tax": int(d["cum_tax"]),
               "cum_deposits": Decimal(d["cum_deposits"]), "cum_life": Decimal(d["cum_life"])}
        if "cum_weight" in d:
            out["cum_weight"] = Decimal(d["cum_weight"])
        if "cum_ni_base" in d:
            out["cum_ni_base"] = Decimal(d["cum_ni_base"])
        return out
    if p.prev_cum_taxable is not None and p.prev_cum_tax is not None:
        return {"cum_taxable": Decimal(str(p.prev_cum_taxable)),
                "cum_tax": int(round(p.prev_cum_tax)),
                "cum_deposits": Decimal(str(p.prev_cum_deposits or 0)),
                "cum_life": Decimal(str(p.prev_cum_life or 0)),
                **({"cum_ni_base": Decimal(str(p.prev_cum_ni_base))} if p.prev_cum_ni_base is not None else {})}
    raise ValueError(
        f"חסר מצטבר לחודש {p.month - 1}/{p.year} של העובד. חשבו את החודשים הקודמים כאן "
        "או הזינו מצטבר ממערכת קודמת (prev_cum_taxable, prev_cum_tax)")


def compute(p: PaystubIn, db: Session, company_id: str) -> dict:
    base = Decimal(str(p.base_salary))
    hourly = base / MONTHLY_HOURS
    ot = hourly * Decimal("1.25") * Decimal(str(p.ot_hours_125)) \
        + hourly * Decimal("1.50") * Decimal(str(p.ot_hours_150))
    cash_gross = base + ot + Decimal(str(p.bonus))
    benefits = {}
    if p.phone_expense > 0:
        benefits["שווי רט\"ן"] = pe.phone_benefit(p.phone_expense, p.phone_employee_share_rate,
                                                       p.phone_employee_share_amount)["value"]
    if p.committee_per_employee > 0 and p.committee_specific_per_employee is not False:
        cb = pe.works_committee_benefit(p.committee_per_employee, p.committee_specific_per_employee)
        if cb["value"] is None:
            raise ValueError(cb["note"])
        benefits["השתתפות מעסיק בפעילות ועד"] = cb["value"]
    operational = pe.is_operational_car(p.car_business_use_only, p.car_leaves_workplace_after_hours,
                                        p.car_workplace_is_residence)
    if p.car_price > 0 or operational or p.car_gross_weight_kg:
        car = pe.car_benefit(p.car_price, p.car_kind, operational, p.car_gross_weight_kg, year=p.year)
        if car["value"] is None:
            raise ValueError("סוג רכב לא מוכר")
        if car["value"]:
            benefits["שווי שימוש ברכב"] = car["value"]
    noncash = sum(benefits.values(), Decimal(0))
    gross = cash_gross + noncash          # ברוטו למס ולביטוח לאומי כולל ההטבות
    taxable = gross - Decimal(str(p.tax_exempt))

    prev = load_prev(db, company_id, p)
    loc = None
    if p.locality:
        loc = localities.lookup(p.locality, p.year)
        if loc is None:
            raise ValueError("יישוב לא מוכר או שנת מס שאינה 2026: אין הנחת יישוב מוטב, נדרשת הזנה ידנית")
    r = pe.compute_month(
        year=p.year, month=p.month, gross=gross, taxable_gross=taxable,
        points=p.credit_points, mode=p.tax_mode, prev=prev,
        pension_employee_rate=p.pension_employee_rate,
        study_fund_employee_rate=p.study_fund_employee_rate,
        life_insurance=p.life_insurance, manual_income_tax=p.manual_income_tax,
        pension_base=cash_gross, noncash_benefits=noncash,
        other_deductions=p.other_deductions,
        employer_pension_rate=p.employer_pension_rate,
        employer_severance_rate=p.employer_severance_rate,
        employer_study_fund_rate=p.employer_study_fund_rate, weight=p.month_weight,
        locality=loc, fixed_rate=p.fixed_rate)

    flags = []
    if ot > 0:
        flags.append("שעות נוספות: חישוב לפי שכר יסוד/182, לא אומת מול תלוש")
    if p.bonus > 0:
        flags.append("בונוס: ננוכה כשכר רגיל, לא אומת טיפול מיוחד")
    if p.credit_points == 0 and p.tax_mode == "cumulative":
        flags.append("0 נקודות זיכוי - לוודא מול טופס 101")
    mw = payslip.min_wage(p.year, p.month)    # (חודשי, שעתי) מאומת לפי תקופה; None = תקופה לא מאומתת
    if mw is None:
        flags.append("שכר מינימום לתקופה זו לא מאומת במערכת - לבדוק ידנית")
    elif hourly < Decimal(mw[1]):
        flags.append(f"שכר שעתי נמוך משכר המינימום השעתי ({mw[1]} ל-182 שעות) - לבדוק")
    if p.other_deductions > 0 and Decimal(str(p.other_deductions)) > gross / 4:
        flags.append("ניכויי רשות מעל רבע מהשכר: חוק הגנת השכר §25(א)(6) מגביל ניכוי חוב על פי התחייבות בכתב "
                     "לרבע משכר העבודה (לבדוק סוג הניכוי; מקדמות לפי §25(א)(7) כפופות לכלל אחר)")

    items = {k: {"value": (float(v["value"]) if v["value"] is not None else None),
                 "status": v["status"], "note": v["note"]}
             for k, v in r["items"].items()}
    return {
        "emp_id_number": p.emp_id_number, "emp_name": p.emp_name, "period": p.period or f"{p.month:02d}/{p.year}",
        "year": p.year, "month": p.month,
        "gross": float(pe.r2(gross)), "overtime_pay": float(pe.r2(ot)),
        "taxable": float(pe.r2(taxable)), "bonus": float(p.bonus),
        "benefits": {k: float(v) for k, v in benefits.items()},
        "points": p.credit_points if p.tax_mode == "cumulative" else "-",
        "items": items,
        "income_tax": items["income_tax"]["value"],
        "national_insurance": items["national_insurance"]["value"],
        "health": items["health"]["value"],
        "pension_employee": items["pension_employee"]["value"],
        "net": float(r["net"]) if r["net"] is not None else None,
        "employer": {k: float(v["value"]) for k, v in r["employer"].items()},
        "pension_base": float(r["pension_base"]),
        "cumulative_taxable": float(r["cumulative"]["cum_taxable"]),
        "cumulative_tax": int(r["cumulative"]["cum_tax"]),
        "cumulative_ni_base": (float(r["cumulative"]["cum_ni_base"]) if "cum_ni_base" in r["cumulative"] else None),
        "overall_status": r["overall_status"],
        "unresolved": r["unresolved"],
        "flags": flags,
        "_cumulative": r["cumulative"],
    }


# ---------------------------------------------------------------------------
# אבטחה
# ---------------------------------------------------------------------------
bearer = HTTPBearer(auto_error=False)


TOKEN_ISSUER = "ai-payroll"


def _epoch(dt: datetime.datetime) -> int:
    return int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())


def make_token(user: User, scope: str = "full", ver: int = 0, auth_time: Optional[int] = None) -> str:
    """
    scope=full: גישה מלאה. scope=enroll: רק להקמת 2FA (משתמש שעוד אין לו 2FA כשהוא חובה).
    תוקף הטוקן = חלון אי-פעילות (authpolicy.IDLE_MINUTES); נחדש בפעילות. auth_time = זמן הכניסה המקורי (תקרה מוחלטת).
    ver = גרסת הטוקן של המשתמש; העלאתה מבטלת את כל הטוקנים.
    """
    minutes = authpolicy.IDLE_MINUTES if scope == "full" else 15
    now = datetime.datetime.utcnow()
    payload = {
        "sub": user.id, "scope": scope, "iss": TOKEN_ISSUER, "jti": uuid.uuid4().hex,
        "iat": now, "exp": now + datetime.timedelta(minutes=minutes),
        "ver": ver, "at": auth_time if auth_time is not None else _epoch(now),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _sec_state(db: Session, user: User):
    sec = db.get(UserSecurity, user.id)
    return (sec.token_version or 0) if sec else 0, bool(sec and sec.disabled), sec


def _user_from_token(cred, db: Session, allowed_scopes, response: Optional[Response] = None) -> User:
    if cred is None:
        raise HTTPException(401, "נדרשת התחברות")
    try:
        data = jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"], issuer=TOKEN_ISSUER,
                          options={"require": ["exp", "sub", "iss"]})
    except Exception:
        raise HTTPException(401, "הכניסה פגה או לא תקינה - התחברי מחדש")
    if data.get("scope") not in allowed_scopes:
        raise HTTPException(403, "נדרשת הקמת אימות דו-שלבי לפני שימוש במערכת")
    user = db.get(User, data.get("sub"))
    if not user:
        raise HTTPException(401, "משתמש לא קיים")
    ver, disabled, _sec = _sec_state(db, user)
    if authpolicy.token_problem(data, ver, disabled):
        # מושבת / בוטל / פג תוקף מוחלט: אותה הודעה, בלי לחשוף את הסיבה
        raise HTTPException(401, "הכניסה פגה או לא תקינה - התחברי מחדש")
    if response is not None and data.get("scope") == "full" and authpolicy.should_refresh(data.get("iat")):
        # חלון אי-פעילות: טוקן חדש בתשובה (הלקוח מחליף). לא עוקף את התקרה המוחלטת (at נשמר)
        response.headers["X-Refreshed-Token"] = make_token(user, "full", ver, data.get("at"))
    return user


def current_user(
    response: Response,
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    return _user_from_token(cred, db, ("full",), response)


def user_for_2fa(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """לנקודות הקצה של הקמת 2FA בלבד: מקבל גם טוקן מוגבל."""
    return _user_from_token(cred, db, ("full", "enroll"))


def rate_limit(request: Request, bucket: str, limit: int, window: int = 60) -> None:
    ip = request.client.host if request.client else "unknown"
    if not RATE_LIMITER.allow(f"{bucket}:{ip}", limit, window):
        raise HTTPException(429, "יותר מדי בקשות. נסי שוב בעוד דקה")


def require_company(company_id: str, user: User, db: Session, action: str = "read") -> None:
    """action: read | write | admin (authpolicy.role_can). הרשאה לפי תפקיד, ברירת מחדל חוסמת."""
    ok = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.company_id == company_id)
        .first()
    )
    if not ok:
        # אותה תשובה גם אם המשרד לא קיים - לא חושפים מה קיים
        raise HTTPException(403, "אין הרשאה למשרד הזה")
    if not authpolicy.role_can(ok.role, action):
        raise HTTPException(403, "אין לך הרשאה לפעולה הזו במשרד הזה")


def audit(db: Session, user_id, company_id, action, entity=None, entity_id=None, detail=None):
    db.add(AuditLog(user_id=user_id, company_id=company_id, action=action,
                    entity=entity, entity_id=entity_id, detail=detail))


def check_totp_once(sec, code) -> bool:
    """מאמת קוד 2FA ורושם את הצעד שנוצל; אותו קוד (או ישן ממנו) נדחה. השמירה נעשית ב-commit של הקורא."""
    step = totp.match_step(secure.decrypt(sec.totp_secret_enc), code)
    if step is None or (sec.totp_last_step is not None and step <= sec.totp_last_step):
        return False
    sec.totp_last_step = step
    return True


MAX_FAILED = 5
LOCK_MINUTES = 15


def check_not_locked(db: Session, email: str) -> None:
    since = datetime.datetime.utcnow() - datetime.timedelta(minutes=LOCK_MINUTES)
    fails = (db.query(LoginAttempt)
             .filter(LoginAttempt.email == email, LoginAttempt.ok == False,  # noqa: E712
                     LoginAttempt.at > since).count())
    if fails >= MAX_FAILED:
        raise HTTPException(429, f"יותר מדי ניסיונות כושלים. נסי שוב בעוד {LOCK_MINUTES} דקות")


app = FastAPI(title="AI Payroll API", version="3.1.0")
# CORS: ברירת מחדל - אין גישה מאתרים אחרים. להגדרה: ALLOWED_ORIGINS=https://my-site.com,https://other.com
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Refreshed-Token"],
)


@app.exception_handler(secure.KeyMissing)
async def key_missing_handler(request: Request, exc: secure.KeyMissing):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Cache-Control"] = "no-store"
    return resp


class RegisterIn(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=10)
    full_name: str


class LoginIn(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None


class CompanyIn(BaseModel):
    name: str
    tax_id: Optional[str] = None


@app.get("/")
def root():
    # מגיש את מסך המערכת (index.html) מאותו שרת; הכתובת היחסית של ה-API נשארת ריקה
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(f.read(), media_type="text/html; charset=utf-8")
    return {"status": "online", "service": "AI Payroll API"}


@app.get("/params-status")
def params_status_endpoint():
    """סטטוס חלק הפרמטרים המשתנים לפי שנה (מעודכן ל-2026 / דרושה התערבות ידנית)."""
    import params
    return params.params_status()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database_connected": True}
    except Exception:
        return {"status": "degraded", "database_connected": False}


@app.post("/auth/register")
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "register", 5)
    if os.getenv("REGISTRATION_OPEN", "true").lower() != "true":
        raise HTTPException(403, "ההרשמה סגורה")
    email = body.email.strip().lower()
    problems = authpolicy.password_problems(body.password, email)
    if problems:
        raise HTTPException(422, "; ".join(problems))
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "האימייל כבר רשום")
    pw = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=email, password_hash=pw, full_name=body.full_name)
    db.add(user)
    db.flush()
    db.add(UserSecurity(user_id=user.id, password_changed_at=datetime.datetime.utcnow(), token_version=0))
    audit(db, user.id, None, "register")
    db.commit()
    scope = "enroll" if authpolicy.needs_2fa_enrollment(REQUIRE_2FA, False) else "full"
    return {"access_token": make_token(user, scope), "token_type": "bearer",
            "two_factor_setup_required": scope == "enroll"}


_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


@app.post("/auth/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "login", 10)
    email = body.email.strip().lower()
    check_not_locked(db, email)
    user = db.query(User).filter(User.email == email).first()
    # בדיקת סיסמה תמיד מתבצעת (גם למשתמש לא קיים) כדי שלא יהיה הבדל בזמן תגובה
    pw_ok = bcrypt.checkpw(body.password.encode(),
                           (user.password_hash if user else _DUMMY_HASH).encode())
    sec = db.get(UserSecurity, user.id) if user else None
    if not (user and pw_ok and not (sec and sec.disabled)):
        db.add(LoginAttempt(email=email, ok=False))
        audit(db, user.id if user else None, None, "login_failed")
        db.commit()
        raise HTTPException(401, "אימייל או סיסמה שגויים")
    if sec and sec.totp_enabled:
        if not body.totp_code:
            raise HTTPException(401, "נדרש קוד אימות דו-שלבי (totp_code)")
        if not check_totp_once(sec, body.totp_code):
            db.add(LoginAttempt(email=email, ok=False))
            audit(db, user.id, None, "login_failed_2fa")
            db.commit()
            raise HTTPException(401, "קוד אימות שגוי")
    if authpolicy.password_expired(sec.password_changed_at if sec else None):
        # תקנה 9(ב)(2)(א): סיסמה לא תעלה על 6 חודשים. מחליפים דרך /auth/change-password (בלי טוקן)
        audit(db, user.id, None, "login_password_expired")
        db.commit()
        raise HTTPException(403, "הסיסמה פגה (חלפו יותר מ-6 חודשים). יש להחליף סיסמה במסך 'החלפת סיסמה'")
    db.add(LoginAttempt(email=email, ok=True))
    enroll = authpolicy.needs_2fa_enrollment(REQUIRE_2FA, bool(sec and sec.totp_enabled))
    tver = (sec.token_version or 0) if sec else 0
    audit(db, user.id, None, "login_enroll_only" if enroll else "login")
    db.commit()
    if enroll:
        # אין 2FA והוא חובה: טוקן מוגבל להקמת 2FA בלבד, בלי גישה לנתונים
        return {"access_token": make_token(user, "enroll", tver), "token_type": "bearer",
                "two_factor_setup_required": True, "companies": []}
    companies = (
        db.query(Company)
        .join(Membership, Membership.company_id == Company.id)
        .filter(Membership.user_id == user.id)
        .all()
    )
    return {
        "access_token": make_token(user, "full", tver),
        "token_type": "bearer",
        "two_factor_setup_required": False,
        "companies": [{"id": c.id, "name": c.name} for c in companies],
    }


class TotpIn(BaseModel):
    code: str


@app.post("/auth/2fa/setup")
def setup_2fa(user: User = Depends(user_for_2fa), db: Session = Depends(get_db)):
    """יוצר סוד חדש. ההפעלה מתבצעת רק אחרי שהמשתמש מאמת קוד ב-/auth/2fa/enable."""
    try:
        secret = totp.new_secret()
        enc = secure.encrypt(secret)
    except secure.KeyMissing as e:
        raise HTTPException(500, str(e))
    sec = db.get(UserSecurity, user.id) or UserSecurity(user_id=user.id)
    if sec.totp_enabled:
        # 2FA פעיל לא מוחלף דרך טוקן בלבד (מונע השבתת 2FA בעזרת טוקן גנוב)
        raise HTTPException(409, "אימות דו-שלבי כבר פעיל. החלפה דורשת טיפול ידני של מנהל המערכת")
    sec.totp_secret_enc, sec.totp_enabled, sec.totp_last_step = enc, False, None
    db.merge(sec)
    audit(db, user.id, None, "2fa_setup")
    db.commit()
    return {"secret": secret, "otpauth_uri": totp.otpauth_uri(secret, user.email)}


@app.post("/auth/2fa/enable")
def enable_2fa(body: TotpIn, request: Request, user: User = Depends(user_for_2fa),
               db: Session = Depends(get_db)):
    rate_limit(request, "2fa_enable", 10)
    sec = db.get(UserSecurity, user.id)
    if not sec or not sec.totp_secret_enc:
        raise HTTPException(400, "קודם יש להפעיל /auth/2fa/setup")
    if not check_totp_once(sec, body.code):
        raise HTTPException(400, "קוד שגוי")
    sec.totp_enabled = True
    audit(db, user.id, None, "2fa_enabled")
    db.commit()
    # אחרי הקמה מוצלחת מונפק טוקן מלא
    return {"two_factor": "enabled", "access_token": make_token(user, "full", sec.token_version or 0),
            "token_type": "bearer"}


class ChangePasswordIn(BaseModel):
    email: str
    old_password: str
    new_password: str = Field(..., min_length=10)
    totp_code: Optional[str] = None


@app.post("/auth/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """מבטל את כל הטוקנים של המשתמש (גם במכשירים אחרים)."""
    sec = db.get(UserSecurity, user.id) or UserSecurity(user_id=user.id, token_version=0)
    sec.token_version = (sec.token_version or 0) + 1
    db.merge(sec)
    audit(db, user.id, None, "logout")
    db.commit()
    return {"status": "logged_out"}


@app.post("/auth/change-password")
def change_password(body: ChangePasswordIn, request: Request, db: Session = Depends(get_db)):
    """
    החלפת סיסמה בלי טוקן (גם כשהסיסמה פגה). דורש סיסמה ישנה (+ קוד 2FA אם פעיל).
    מבטל את כל הטוקנים הקיימים. אותה הגבלת ניסיונות כמו כניסה.
    """
    rate_limit(request, "chpw", 5)
    email = body.email.strip().lower()
    check_not_locked(db, email)
    user = db.query(User).filter(User.email == email).first()
    pw_ok = bcrypt.checkpw(body.old_password.encode(),
                           (user.password_hash if user else _DUMMY_HASH).encode())
    sec = db.get(UserSecurity, user.id) if user else None
    if not (user and pw_ok and not (sec and sec.disabled)):
        db.add(LoginAttempt(email=email, ok=False))
        audit(db, user.id if user else None, None, "change_password_failed")
        db.commit()
        raise HTTPException(401, "אימייל או סיסמה שגויים")
    if sec and sec.totp_enabled:
        if not body.totp_code or not check_totp_once(sec, body.totp_code):
            db.add(LoginAttempt(email=email, ok=False))
            audit(db, user.id, None, "change_password_failed_2fa")
            db.commit()
            raise HTTPException(401, "קוד אימות שגוי")
    problems = authpolicy.password_problems(body.new_password, email)
    if body.new_password == body.old_password:
        problems.append("הסיסמה החדשה חייבת להיות שונה מהישנה")
    if problems:
        raise HTTPException(422, "; ".join(problems))
    user.password_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    sec = sec or UserSecurity(user_id=user.id, token_version=0)
    sec.password_changed_at = datetime.datetime.utcnow()
    sec.token_version = (sec.token_version or 0) + 1
    db.merge(sec)
    audit(db, user.id, None, "password_changed")
    db.commit()
    return {"status": "password_changed", "note": "כל הכניסות הקיימות בוטלו. התחברי מחדש"}


class MemberIn(BaseModel):
    email: str
    role: str


@app.get("/companies/{company_id}/members")
def list_members(company_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """רשימת ההרשאות התקפות (תקנה 8(ב))."""
    require_company(company_id, user, db, "read")
    rows = (db.query(Membership, User).join(User, User.id == Membership.user_id)
            .filter(Membership.company_id == company_id).all())
    audit(db, user.id, company_id, "list_members", "membership", None, f"count={len(rows)}")
    db.commit()
    return [{"user_id": u.id, "email": u.email, "full_name": u.full_name, "role": m.role} for m, u in rows]


@app.post("/companies/{company_id}/members")
def add_member(company_id: str, body: MemberIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    """הוספת משתמש קיים למשרד. רק owner. תפקיד: owner / accountant / viewer."""
    require_company(company_id, user, db, "admin")
    if body.role not in authpolicy.ROLES:
        raise HTTPException(422, "תפקיד לא מוכר. מותר: " + ", ".join(authpolicy.ROLES))
    target = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if not target:
        raise HTTPException(404, "המשתמש לא קיים. הוא צריך להירשם קודם")
    if db.query(Membership).filter(Membership.user_id == target.id,
                                   Membership.company_id == company_id).first():
        raise HTTPException(409, "המשתמש כבר מורשה במשרד הזה")
    db.add(Membership(user_id=target.id, company_id=company_id, role=body.role))
    audit(db, user.id, company_id, "add_member", "membership", target.id, f"role={body.role}")
    db.commit()
    return {"user_id": target.id, "role": body.role}


@app.delete("/companies/{company_id}/members/{member_user_id}")
def remove_member(company_id: str, member_user_id: str, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """ביטול הרשאה (תקנה 9(ג)). רק owner. לא ניתן להסיר את ה-owner האחרון."""
    require_company(company_id, user, db, "admin")
    m = (db.query(Membership).filter(Membership.user_id == member_user_id,
                                     Membership.company_id == company_id).first())
    if not m:
        raise HTTPException(404, "המשתמש לא מורשה במשרד הזה")
    if m.role == "owner":
        owners = db.query(Membership).filter(Membership.company_id == company_id,
                                             Membership.role == "owner").count()
        if owners <= 1:
            raise HTTPException(409, "לא ניתן להסיר את הבעלים האחרון של המשרד")
    db.delete(m)
    db.flush()
    if not db.query(Membership).filter(Membership.user_id == member_user_id).count():
        # לא נשארה לו הרשאה באף משרד: משביתים את המשתמש ומבטלים את כל הטוקנים שלו (תקנה 9(ג))
        tsec = db.get(UserSecurity, member_user_id) or UserSecurity(user_id=member_user_id, token_version=0)
        tsec.disabled = True
        tsec.token_version = (tsec.token_version or 0) + 1
        db.merge(tsec)
    audit(db, user.id, company_id, "remove_member", "membership", member_user_id)
    db.commit()
    return {"status": "removed"}


@app.get("/companies/{company_id}/audit-log")
def get_audit_log(company_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = (db.query(AuditLog).filter(AuditLog.company_id == company_id)
            .order_by(AuditLog.at.desc()).limit(500).all())
    audit(db, user.id, company_id, "read_audit_log", "audit_log", None, f"count={len(rows)}")
    db.commit()
    return [{"at": r.at.isoformat(), "user_id": r.user_id, "action": r.action,
             "entity": r.entity, "entity_id": r.entity_id, "detail": r.detail} for r in rows]


@app.post("/companies")
def create_company(body: CompanyIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = Company(name=body.name, tax_id=body.tax_id)
    db.add(c)
    db.flush()
    db.add(Membership(user_id=user.id, company_id=c.id, role="owner"))
    audit(db, user.id, c.id, "create_company", "company", c.id)
    db.commit()
    return {"id": c.id, "name": c.name}


@app.get("/companies")
def my_companies(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Company)
        .join(Membership, Membership.company_id == Company.id)
        .filter(Membership.user_id == user.id)
        .all()
    )
    return [{"id": c.id, "name": c.name, "tax_id": c.tax_id} for c in rows]


def public_res(res: dict) -> dict:
    out = {k: v for k, v in res.items() if k != "_cumulative"}
    out["emp_id_number"] = "*****" + str(res["emp_id_number"])[-4:]
    return out


def save_stub(db: Session, company_id: str, res: dict) -> None:
    key = emp_key(company_id, res["emp_id_number"])
    stored = {k: v for k, v in res.items() if k != "_cumulative"}
    db.add(PaystubV2(company_id=company_id, emp_key=key, year=res["year"], month=res["month"],
                     payload_enc=seal(db, company_id, stored)))
    c = res.get("_cumulative")
    if c is not None:
        db.query(Cumulative).filter(
            Cumulative.company_id == company_id, Cumulative.emp_key == key,
            Cumulative.year == res["year"], Cumulative.month == res["month"]).delete()
        db.add(Cumulative(
            company_id=company_id, emp_key=key, year=res["year"], month=res["month"],
            payload_enc=seal(db, company_id, {k: str(v) for k, v in c.items()})))
    db.flush()  # כדי שהחודש הבא באותו קובץ יראה את המצטבר


@app.post("/companies/{company_id}/calculate-paystub")
def calculate(company_id: str, body: PaystubIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    try:
        res = compute(body, db, company_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    save_stub(db, company_id, res)
    audit(db, user.id, company_id, "calculate_paystub", "paystub", None,
          f"{res['month']:02d}/{res['year']} status={res['overall_status']}")
    db.commit()
    return {"company_id": company_id, **public_res(res)}


@app.get("/companies/{company_id}/paystubs")
def list_paystubs(company_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = (db.query(PaystubV2).filter(PaystubV2.company_id == company_id)
            .order_by(PaystubV2.created_at.desc()).limit(500).all())
    out = []
    for r in rows:
        d = unseal(db, company_id, r.payload_enc)
        out.append({"emp_id_number": "*****" + str(d["emp_id_number"])[-4:],
                    "emp_name": d["emp_name"], "period": d.get("period"),
                    "gross": d["gross"], "net": d["net"], "status": d["overall_status"]})
    audit(db, user.id, company_id, "list_paystubs", "paystub", None, f"count={len(out)}")
    db.commit()
    return out


class EmployeeIn(BaseModel):
    id_number: str
    full_name: str = Field(..., min_length=1)
    gender: str = Field(..., pattern="^(F|M)$")
    birth_date: Optional[datetime.date] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    is_resident: bool = True
    bank_account: Optional[str] = None
    base_salary: float = Field(..., gt=0)
    pension_employee_rate: float = Field(0.06, ge=0, le=0.5)
    study_fund_employee_rate: float = Field(0, ge=0, le=0.5)
    life_insurance_monthly: float = Field(0, ge=0)
    employer_pension_rate: float = Field(0.065, ge=0, le=0.5)
    employer_severance_rate: float = Field(0.06, ge=0, le=0.5)
    employer_study_fund_rate: float = Field(0, ge=0, le=0.5)
    position_scope_percent: float = Field(100, gt=0, le=100)


class Form101In(BaseModel):
    signed_on: Optional[datetime.date] = None     # תאריך חתימה. ריק = אין 101 לשנה
    income_type: str = Field("main", pattern="^(main|additional)$")
    other_income: bool = False
    other_credits_claimed: bool = False           # סומנו זיכויים מעבר לתושב/ה ואישה
    manual_points: Optional[float] = Field(None, ge=0)
    marital: Optional[str] = Field(None, pattern="^(single|married|divorced|widowed|separated)$")
    custody_birth_years: List[int] = Field(default_factory=list, max_length=20)
    noncustody_birth_years: List[int] = Field(default_factory=list, max_length=20)
    family_flags: List[str] = Field(default_factory=list, max_length=7)
    aliyah_date: Optional[datetime.date] = None
    discharge_date: Optional[datetime.date] = None
    soldier_full_service: Optional[bool] = None
    degrees: List[dict] = Field(default_factory=list, max_length=3)
    disabled_children: Optional[int] = Field(None, ge=0, le=20)
    alimony_ex_spouse: Optional[bool] = None
    locality: Optional[str] = Field(None, max_length=80)
    reserve_days_prev_year: Optional[int] = Field(None, ge=0, le=366)


def get_employee(db: Session, company_id: str, employee_id: str):
    emp = db.query(Employee).filter(Employee.id == employee_id,
                                    Employee.company_id == company_id).first()
    if not emp:
        raise HTTPException(404, "עובד לא נמצא")
    return emp, unseal(db, company_id, emp.payload_enc)


def emp_public(emp_id: str, d: dict) -> dict:
    return {"id": emp_id, "id_number_masked": "*****" + d["id_number"][-4:],
            "full_name": d["full_name"], "gender": d["gender"],
            "start_date": d.get("start_date"), "base_salary": d["base_salary"],
            "pension_employee_rate": d["pension_employee_rate"],
            "study_fund_employee_rate": d["study_fund_employee_rate"],
            "life_insurance_monthly": d["life_insurance_monthly"]}


@app.post("/companies/{company_id}/employees")
def create_employee(company_id: str, body: EmployeeIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    if not secure.valid_israeli_id(body.id_number):
        raise HTTPException(422, "מספר תעודת זהות לא תקין (ספרת ביקורת)")
    h = emp_key(company_id, body.id_number)
    if db.query(Employee).filter(Employee.company_id == company_id, Employee.id_hash == h).first():
        raise HTTPException(409, "עובד עם ת.ז הזו כבר קיים במשרד")
    data = body.model_dump(mode="json")
    emp = Employee(company_id=company_id, id_hash=h, payload_enc=seal(db, company_id, data))
    db.add(emp)
    db.flush()
    audit(db, user.id, company_id, "create_employee", "employee", emp.id)
    db.commit()
    return emp_public(emp.id, data)


@app.get("/companies/{company_id}/employees")
def list_employees(company_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = db.query(Employee).filter(Employee.company_id == company_id).all()
    out = sorted((emp_public(e.id, unseal(db, company_id, e.payload_enc)) for e in rows),
                 key=lambda x: x["full_name"])
    audit(db, user.id, company_id, "list_employees", "employee", None, f"count={len(out)}")
    db.commit()
    return out


@app.put("/companies/{company_id}/employees/{employee_id}/form101/{year}")
def set_form101(company_id: str, employee_id: str, year: int, body: Form101In,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    emp, d = get_employee(db, company_id, employee_id)
    data = body.model_dump(mode="json")
    row = db.query(EmployeeYear).filter(EmployeeYear.employee_id == emp.id,
                                        EmployeeYear.year == year).first()
    if row:
        row.payload_enc = seal(db, company_id, data)
    else:
        db.add(EmployeeYear(company_id=company_id, employee_id=emp.id, year=year,
                            payload_enc=seal(db, company_id, data)))
    audit(db, user.id, company_id, "set_form101", "employee", emp.id, f"year={year}")
    db.commit()
    pts, status, note = card.points_from_form101(year, d["is_resident"], d["gender"], data)
    return {"year": year, "credit_points": pts, "points_status": status, "points_note": note}


class CalcFromCardIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    ot_hours_125: float = Field(0, ge=0)
    ot_hours_150: float = Field(0, ge=0)
    bonus: float = Field(0, ge=0)
    tax_exempt: float = Field(0, ge=0)
    other_deductions: float = Field(0, ge=0)
    month_weight: float = Field(1, gt=0, le=1)
    phone_expense: float = Field(0, ge=0)
    phone_employee_share_rate: float = Field(0, ge=0, le=1)
    phone_employee_share_amount: float = Field(0, ge=0)
    committee_per_employee: float = Field(0, ge=0)
    committee_specific_per_employee: Optional[bool] = None
    car_price: float = Field(0, ge=0)
    car_kind: str = Field("regular", pattern="^(regular|hybrid|plugin|electric)$")
    car_business_use_only: Optional[bool] = None
    car_leaves_workplace_after_hours: Optional[bool] = None
    car_workplace_is_residence: bool = False
    car_gross_weight_kg: Optional[float] = Field(None, gt=0)
    base_salary: Optional[float] = Field(None, gt=0)   # חריגה חד-פעמית לחודש
    manual_income_tax: Optional[float] = None
    coordination_rate: Optional[float] = Field(None, ge=0, le=0.5)   # אישור תיאום מס: שיעור ניכוי קבוע מהאישור
    prev_cum_taxable: Optional[float] = None
    prev_cum_tax: Optional[float] = None
    prev_cum_deposits: Optional[float] = None
    prev_cum_life: Optional[float] = None
    prev_cum_ni_base: Optional[float] = None
    period: Optional[str] = None


@app.post("/companies/{company_id}/employees/{employee_id}/calculate")
def calculate_from_card(company_id: str, employee_id: str, body: CalcFromCardIn,
                        user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    emp, d = get_employee(db, company_id, employee_id)
    yr_row = db.query(EmployeeYear).filter(EmployeeYear.employee_id == emp.id,
                                           EmployeeYear.year == body.year).first()
    y = unseal(db, company_id, yr_row.payload_enc) if yr_row else None
    present = bool(y and y.get("signed_on"))
    mode, mode_note = card.tax_mode(present, y["income_type"] if y else "main",
                                    bool(y and y["other_income"]))
    pts, pts_note = 0.0, ""
    if mode == "cumulative" and body.coordination_rate is None:
        pts, _status, pts_note = card.points_from_form101(body.year, d["is_resident"], d["gender"], y, body.month)
        if pts is None and body.manual_income_tax is None:
            raise HTTPException(422, pts_note)
        pts = pts or 0.0
    p = PaystubIn(
        emp_id_number=d["id_number"], emp_name=d["full_name"], year=body.year, month=body.month,
        base_salary=body.base_salary or d["base_salary"],
        ot_hours_125=body.ot_hours_125, ot_hours_150=body.ot_hours_150, bonus=body.bonus,
        tax_exempt=body.tax_exempt, credit_points=pts, locality=(y or {}).get("locality"),
        tax_mode=("fixed_rate" if body.coordination_rate is not None else mode),
        fixed_rate=body.coordination_rate,
        pension_employee_rate=d["pension_employee_rate"],
        study_fund_employee_rate=d["study_fund_employee_rate"],
        life_insurance=d["life_insurance_monthly"],
        employer_pension_rate=d.get("employer_pension_rate", 0),
        employer_severance_rate=d.get("employer_severance_rate", 0),
        employer_study_fund_rate=d.get("employer_study_fund_rate", 0),
        other_deductions=body.other_deductions, manual_income_tax=body.manual_income_tax,
        month_weight=body.month_weight, phone_expense=body.phone_expense,
        phone_employee_share_rate=body.phone_employee_share_rate,
        phone_employee_share_amount=body.phone_employee_share_amount,
        committee_per_employee=body.committee_per_employee,
        committee_specific_per_employee=body.committee_specific_per_employee, car_price=body.car_price,
        car_kind=body.car_kind, car_business_use_only=body.car_business_use_only,
        car_leaves_workplace_after_hours=body.car_leaves_workplace_after_hours,
        car_workplace_is_residence=body.car_workplace_is_residence,
        car_gross_weight_kg=body.car_gross_weight_kg,
        prev_cum_taxable=body.prev_cum_taxable, prev_cum_tax=body.prev_cum_tax,
        prev_cum_deposits=body.prev_cum_deposits, prev_cum_life=body.prev_cum_life,
        prev_cum_ni_base=body.prev_cum_ni_base,
        period=body.period or f"{body.month:02d}/{body.year}")
    try:
        res = compute(p, db, company_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if mode_note:
        res["flags"].append(mode_note)
    if pts_note:
        res["flags"].append("נקודות זיכוי: " + pts_note)
    save_stub(db, company_id, res)
    audit(db, user.id, company_id, "calculate", "employee", emp.id,
          f"{body.month:02d}/{body.year} status={res['overall_status']}")
    db.commit()
    return {"company_id": company_id, "employee_id": emp.id, **public_res(res)}


class PayslipIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    employer_address: Optional[str] = None
    worked: Optional[str] = None        # למשל "22 ימים / 182 שעות"
    vacation: Optional[str] = None      # "ניצול / יתרה"
    sick: Optional[str] = None
    payment: Optional[str] = None
    regular_hour_value: Optional[float] = Field(None, gt=0)    # ערך שעת עבודה רגילה (סעיף 24)
    seniority_override: Optional[str] = None                   # ותק מצטבר אם שונה מתאריך תחילת העבודה
    approve: bool = False               # אישור חשב השכר: מסיר סימן "טיוטה"
    template: Optional[str] = Field(None, pattern="^[a-z0-9_]{1,40}$")   # שם תבנית מתיקיית templates (בלי נתיב)


def _payslip_inputs(db, company_id, employee_id, body):
    emp, d = get_employee(db, company_id, employee_id)
    key = emp_key(company_id, d["id_number"])
    row = (db.query(PaystubV2).filter(PaystubV2.company_id == company_id,
                                      PaystubV2.emp_key == key, PaystubV2.year == body.year,
                                      PaystubV2.month == body.month)
           .order_by(PaystubV2.created_at.desc()).first())
    if not row:
        raise HTTPException(404, "לא נמצא חישוב לחודש הזה. חשבו את החודש קודם")
    res = unseal(db, company_id, row.payload_enc)
    company = db.get(Company, company_id)
    extras = {"employer_address": body.employer_address, "worked": body.worked,
              "vacation": body.vacation, "sick": body.sick, "payment": body.payment,
              "regular_hour_value": body.regular_hour_value, "seniority_override": body.seniority_override,
              "bonus": res.get("bonus", 0)}
    return res, extras, d, {"name": company.name, "tax_id": company.tax_id}


class OverrideIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    field: str
    new_value: float
    reason: str = Field(..., min_length=1, max_length=500)


@app.post("/companies/{company_id}/employees/{employee_id}/override")
def override_item(company_id: str, employee_id: str, body: OverrideIn,
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    """תיקון ידני של חשב השכר לרכיב ניכוי. נרשם ביומן, מסומן בתלוש, והנטו מחושב מחדש בקוד."""
    require_company(company_id, user, db, "write")
    emp, d = get_employee(db, company_id, employee_id)
    key = emp_key(company_id, d["id_number"])
    row = (db.query(PaystubV2).filter(PaystubV2.company_id == company_id, PaystubV2.emp_key == key,
                                      PaystubV2.year == body.year, PaystubV2.month == body.month)
           .order_by(PaystubV2.created_at.desc()).first())
    if not row:
        raise HTTPException(404, "לא נמצא חישוב לחודש הזה. חשבו את החודש קודם")
    res = unseal(db, company_id, row.payload_enc)
    try:
        new_res = overrides.apply_override(res, body.field, body.new_value, body.reason, user.email)
    except overrides.OverrideError as e:
        raise HTTPException(422, str(e))
    db.add(PaystubV2(company_id=company_id, emp_key=key, year=body.year, month=body.month,
                     payload_enc=seal(db, company_id, new_res)))
    audit(db, user.id, company_id, "override", "employee", emp.id,
          f"{body.month:02d}/{body.year} field={body.field} reason={body.reason[:80]}")
    db.commit()
    return {"company_id": company_id, "employee_id": emp.id, **public_res(new_res)}


class TerminationIn(BaseModel):
    end_date: datetime.date
    ended_by: str = Field(..., pattern="^(dismissed|resigned)$")
    section14: bool = False
    section14_terms: Optional[dict] = Field(None, description="route(pension|insurance), deposit_rate, completion_rate, disability_insurance, agreement_ok, covered_fraction")
    severance_components: list = Field(default_factory=list, description="רשימת [סוג, סכום]; ראו labor_rules.severance_wage")
    unused_vacation_days: Optional[float] = Field(None, ge=0)
    vacation_day_value: Optional[float] = Field(None, ge=0)
    notice_days_unworked: Optional[float] = Field(None, ge=0)
    notice_day_value: Optional[float] = Field(None, ge=0)
    job_scope: Optional[float] = Field(None, gt=0, le=1, description="היקף משרה (1 = מלאה) לרצפת שכר מינימום §13ב")
    pay_type: str = Field("monthly", pattern="^(monthly|daily_hourly)$")
    quarter_wage: Optional[float] = Field(None, ge=0, description="עובד בשכר: שכר רבע השנה לחישוב שווי יום חופשה (§10(ב)(2))")


@app.post("/companies/{company_id}/employees/{employee_id}/termination")
def termination_settlement(company_id: str, employee_id: str, body: TerminationIn,
                           user: User = Depends(current_user), db: Session = Depends(get_db)):
    """חישוב זכויות סיום העסקה. מחשבון עזר בלבד: מה שלא ידוע מסומן ידני, והמס על הרכיבים לא מחושב."""
    require_company(company_id, user, db, "write")
    emp, d = get_employee(db, company_id, employee_id)
    if not d.get("start_date"):
        raise HTTPException(422, "חסר תאריך תחילת עבודה בכרטיס העובד")
    try:
        comps = [(str(k), v) for k, v in body.severance_components]
        mw = payslip.min_wage(body.end_date.year, body.end_date.month)   # שכר מינימום בחודש הסיום; None = לא מאומת
        r = termination.settlement(
            start_date=datetime.date.fromisoformat(str(d["start_date"])), end_date=body.end_date,
            ended_by=body.ended_by, severance_components=comps, section14=body.section14, section14_terms=body.section14_terms,
            unused_vacation_days=body.unused_vacation_days, vacation_day_value=body.vacation_day_value,
            notice_days_unworked=body.notice_days_unworked, notice_day_value=body.notice_day_value,
            min_wage_monthly=(mw[0] if mw else None), job_scope=body.job_scope,
            pay_type=body.pay_type, quarter_wage=body.quarter_wage)
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))
    audit(db, user.id, company_id, "termination_calc", "employee", emp.id, f"end={body.end_date}")
    db.commit()
    return {"months": r["months"], "overall_status": r["overall"], "notes": r["notes"],
            "items": {k: {"value": (str(v["value"]) if v["value"] is not None else None),
                          "status": v["status"], "note": v["note"]} for k, v in r["items"].items()}}


@app.get("/templates")
def list_templates(user: User = Depends(current_user)):
    """תבניות התלוש הזמינות (קבצי JSON בתיקיית templates). רק שם ותיאור, בלי נתיבים."""
    import glob
    out = []
    for path in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "*.json"))):
        try:
            spec = templating.load(path)
        except templating.TemplateError:
            continue
        out.append({"id": os.path.splitext(os.path.basename(path))[0], "name": spec.get("name", ""),
                    "unmapped": spec.get("unmapped", [])})
    return out


@app.post("/companies/{company_id}/employees/{employee_id}/payslip/check")
def payslip_check(company_id: str, employee_id: str, body: PayslipIn,
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    """בודק מה חסר לפני הפקה: שדות חובה וסטטוס החישוב. לא מפיק קובץ."""
    require_company(company_id, user, db, "write")
    res, extras, d, company = _payslip_inputs(db, company_id, employee_id, body)
    _data, missing, reasons = payslip.prepare(res, extras, d, company)
    return {"missing_required_fields": missing, "calculation_notes": reasons,
            "would_be_draft": bool(missing or reasons) and not body.approve}


@app.post("/companies/{company_id}/employees/{employee_id}/payslip")
def payslip_pdf(company_id: str, employee_id: str, body: PayslipIn,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    res, extras, d, company = _payslip_inputs(db, company_id, employee_id, body)
    tpl_missing = []
    if body.template:
        spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", body.template + ".json")
        if not os.path.isfile(spec_path):
            raise HTTPException(404, "תבנית לא נמצאה")
        try:
            spec = templating.load(spec_path)
            data, missing, reasons = payslip.prepare(res, extras, d, company)
            draft = bool(missing or reasons) and not (body.approve and not missing and res.get("net") is not None)
            pdf, tpl_missing = templating.render(spec, data, draft=draft)
        except templating.TemplateError as e:
            raise HTTPException(422, "תבנית לא תקינה: " + str(e))
    else:
        pdf, missing, reasons, draft = payslip.render(res, extras, d, company, approved=body.approve)
    audit(db, user.id, company_id, "payslip_pdf", "employee", employee_id,
          f"{body.month:02d}/{body.year} draft={draft} approved={body.approve} template={body.template}")
    db.commit()
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="payslip-{body.year}-{body.month:02d}.pdf"',
                             "X-Payslip-Draft": str(draft).lower(),
                             "X-Template-Missing": str(len(tpl_missing))})



# ---------------------------------------------------------------------------
# הצעות לאישור: העלאת טופס 101 -> חילוץ (AI אם הופעל) -> אימות -> בדיקה ואישור של חשב השכר
# ---------------------------------------------------------------------------
def _get_proposal(db, company_id, proposal_id):
    pr = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.company_id == company_id).first()
    if not pr:
        raise HTTPException(404, "הצעה לא נמצאה")
    return pr, unseal(db, company_id, pr.payload_enc)


def _proposal_ctx(db, company_id, employee_id):
    emp, d = get_employee(db, company_id, employee_id)
    return emp, {"id_number": d["id_number"], "is_resident": d["is_resident"], "gender": d["gender"]}


@app.post("/companies/{company_id}/proposals/form101")
async def upload_form101(company_id: str, employee_id: str = Form(...), file: UploadFile = File(...),
                         user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    emp, ctx = _proposal_ctx(db, company_id, employee_id)
    data = await file.read(proposals.MAX_FILE_BYTES + 1)   # קריאה חסומה: לא טוענים לזיכרון קובץ ענק
    ext, err = proposals.check_upload(data)
    if err:
        raise HTTPException(400, err)
    try:
        extractor = proposals.get_extractor()
        extraction = extractor.extract(proposals.KIND_FORM101, data, file.filename or "")
    except proposals.ExtractorNotConfigured as e:
        raise HTTPException(422, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception:
        raise HTTPException(502, "החילוץ האוטומטי נכשל. אפשר להזין את השדות ידנית בבדיקת ההצעה")
    prop, val = proposals.build_proposal(proposals.KIND_FORM101, extraction.fields, extraction.source,
                                         extraction.notes, ctx=ctx)
    doc = Document(company_id=company_id, kind=proposals.KIND_FORM101, ext=ext,
                   sha256=proposals.sha256_hex(data), size=len(data),
                   blob_enc=seal(db, company_id, {"b64": __import__("base64").b64encode(data).decode("ascii")}).encode("ascii"),
                   uploaded_by=user.id)
    db.add(doc)
    db.flush()
    year = prop["fields"].get("tax_year")
    pr = Proposal(company_id=company_id, document_id=doc.id, kind=proposals.KIND_FORM101,
                  employee_id=emp.id, year=year, payload_enc=seal(db, company_id, prop), created_by=user.id)
    db.add(pr)
    audit(db, user.id, company_id, "upload_form101", "proposal", pr.id,
          f"source={extraction.source} errors={len(val.errors)}")
    db.commit()
    return {"id": pr.id, "status": pr.status, "extraction_source": extraction.source,
            "fields": prop["fields"], "validation": val.to_dict()}


@app.get("/companies/{company_id}/proposals")
def list_proposals(company_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    rows = db.query(Proposal).filter(Proposal.company_id == company_id).order_by(Proposal.created_at.desc()).all()
    audit(db, user.id, company_id, "list_proposals", "proposal", None, f"count={len(rows)}")
    db.commit()
    return [{"id": r.id, "kind": r.kind, "status": r.status, "year": r.year,
             "created_at": r.created_at.isoformat() if r.created_at else None,
             "usable": proposals.is_usable(r.status)} for r in rows]


@app.get("/companies/{company_id}/proposals/{proposal_id}")
def get_proposal(company_id: str, proposal_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db)
    pr, prop = _get_proposal(db, company_id, proposal_id)
    audit(db, user.id, company_id, "read_proposal", "proposal", pr.id)
    db.commit()
    return {"id": pr.id, "status": pr.status, "year": pr.year, "employee_id": pr.employee_id, **prop}


@app.put("/companies/{company_id}/proposals/{proposal_id}/fields")
def edit_proposal_fields(company_id: str, proposal_id: str, body: dict,
                         user: User = Depends(current_user), db: Session = Depends(get_db)):
    """חשב השכר מתקן/משלים שדות לפני אישור. עובר שוב סכמה ואימות; רק הצעה ממתינה."""
    require_company(company_id, user, db, "write")
    pr, prop = _get_proposal(db, company_id, proposal_id)
    if pr.status != proposals.PENDING:
        raise HTTPException(409, "אפשר לערוך רק הצעה שממתינה לאישור")
    merged = dict(prop["fields"]); merged.update(body or {})
    ctx = {}
    if pr.employee_id:
        _emp, ctx = _proposal_ctx(db, company_id, pr.employee_id)
    new_prop, val = proposals.build_proposal(pr.kind, merged, prop["extraction"]["source"],
                                             prop["extraction"]["notes"] + ["נערך על ידי חשב השכר"], ctx=ctx)
    pr.payload_enc = seal(db, company_id, new_prop)
    pr.year = new_prop["fields"].get("tax_year", pr.year)
    audit(db, user.id, company_id, "edit_proposal", "proposal", pr.id, "fields=" + ",".join(sorted((body or {}).keys())))
    db.commit()
    return {"id": pr.id, "status": pr.status, **new_prop}


class DecisionIn(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    confirm: bool = False
    floor_ack: bool = False


@app.post("/companies/{company_id}/proposals/{proposal_id}/decision")
def decide_proposal(company_id: str, proposal_id: str, body: DecisionIn,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_company(company_id, user, db, "write")
    pr, prop = _get_proposal(db, company_id, proposal_id)
    val = proposals.Validation(errors=dict(prop["validation"]["errors"]),
                               warnings=list(prop["validation"]["warnings"]),
                               checks=dict(prop["validation"]["checks"]),
                               floor_status=prop["validation"]["floor_status"])
    try:
        new_status = proposals.decide(pr.status, body.action, val, body.confirm, body.floor_ack)
    except proposals.TransitionError as e:
        raise HTTPException(409, str(e))
    pr.status = new_status
    pr.decided_by = user.id
    pr.decided_at = datetime.datetime.utcnow()
    if new_status == proposals.APPROVED and pr.kind == proposals.KIND_FORM101 and pr.employee_id:
        emp, _ctx = _proposal_ctx(db, company_id, pr.employee_id)
        year = prop["fields"]["tax_year"]
        payload = proposals.form101_to_employee_year(prop["fields"])
        row = db.query(EmployeeYear).filter(EmployeeYear.employee_id == emp.id, EmployeeYear.year == year).first()
        if row:
            row.payload_enc = seal(db, company_id, payload)
        else:
            db.add(EmployeeYear(company_id=company_id, employee_id=emp.id, year=year,
                                payload_enc=seal(db, company_id, payload)))
    audit(db, user.id, company_id, "proposal_" + body.action, "proposal", pr.id, f"status={new_status}")
    db.commit()
    return {"id": pr.id, "status": new_status}


COLUMN_MAP = {
    "emp_id_number": ["emp_id_number", "תעודת זהות", "ת.ז", "ת\"ז", "מספר עובד"],
    "emp_name": ["emp_name", "שם", "שם עובד", "שם העובד"],
    "base_salary": ["base_salary", "שכר יסוד", "שכר בסיס", "שכר"],
    "ot_hours_125": ["ot_hours_125", "שעות 125", "שעות נוספות 125"],
    "ot_hours_150": ["ot_hours_150", "שעות 150", "שעות נוספות 150"],
    "bonus": ["bonus", "בונוס"],
    "credit_points": ["credit_points", "נקודות זיכוי"],
    "year": ["year", "שנה"],
    "month": ["month", "חודש"],
    "tax_exempt": ["tax_exempt", "פטור ממס", "החזר הוצאות פטור"],
    "pension_employee_rate": ["pension_employee_rate", "אחוז פנסיה עובד"],
    "study_fund_employee_rate": ["study_fund_employee_rate", "אחוז קרן השתלמות עובד"],
    "life_insurance": ["life_insurance", "ביטוח חיים"],
    "tax_mode": ["tax_mode", "שיטת מס"],
    "manual_income_tax": ["manual_income_tax", "מס הכנסה ידני"],
}


def read_rows(filename: str, content: bytes) -> List[dict]:
    name = filename.lower()
    if name.endswith(".csv"):
        text_data = content.decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(text_data)))
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        return [dict(zip(header, r)) for r in rows[1:] if any(v is not None for v in r)]
    raise HTTPException(400, "יש להעלות קובץ .xlsx או .csv")


def pick(row: dict, key: str, default=None):
    for alias in COLUMN_MAP[key]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return default


@app.post("/companies/{company_id}/upload-excel")
async def upload_excel(
    company_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_company(company_id, user, db, "write")
    content = await file.read(5 * 1024 * 1024 + 1)      # קריאה חסומה: לא טוענים לזיכרון קובץ ענק
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "הקובץ גדול מדי (מעל 5MB)")
    rows = read_rows(file.filename or "", content)
    if len(rows) > 2000:
        raise HTTPException(400, "יותר מדי שורות (מעל 2000)")

    results, errors = [], []
    for i, row in enumerate(rows, start=2):
        try:
            _req_mode, _req_points, _req_pension = upload_rules.required_for_row(row)
            p = PaystubIn(
                emp_id_number=str(pick(row, "emp_id_number", "")),
                emp_name=str(pick(row, "emp_name", "")),
                base_salary=float(pick(row, "base_salary", 0)),
                ot_hours_125=float(pick(row, "ot_hours_125", 0)),
                ot_hours_150=float(pick(row, "ot_hours_150", 0)),
                bonus=float(pick(row, "bonus", 0)),
                credit_points=_req_points,
                year=int(pick(row, "year", 0)),
                month=int(pick(row, "month", 0)),
                tax_exempt=float(pick(row, "tax_exempt", 0)),
                pension_employee_rate=_req_pension,
                study_fund_employee_rate=float(pick(row, "study_fund_employee_rate", 0)),
                life_insurance=float(pick(row, "life_insurance", 0)),
                tax_mode=_req_mode,
                manual_income_tax=(float(pick(row, "manual_income_tax"))
                                   if pick(row, "manual_income_tax") is not None else None),
            )
            if not p.emp_id_number or not p.emp_name:
                raise ValueError("חסרים ת.ז או שם")
            res = compute(p, db, company_id)
            save_stub(db, company_id, res)
            results.append(public_res(res))
        except Exception as e:
            errors.append({"row": i, "error": str(e)})
    audit(db, user.id, company_id, "upload_excel", "file", None,
          f"rows={len(rows)} ok={len(results)} errors={len(errors)}")
    db.commit()
    return {"processed": len(results), "errors": errors, "paystubs": results}


COLUMN_MAP["other_deductions"] = ["other_deductions", "ניכויים אחרים", "ניכוי אחר"]


@app.post("/companies/{company_id}/upload-excel-card")
async def upload_excel_card(
    company_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """
    העלאת Excel לפי כרטיס העובד: בקובץ רק ת.ז, שנה, חודש ונתונים משתנים (שעות 125/150, בונוס, פטור ממס, ניכויים אחרים,
    ואופציונלית שכר יסוד לחודש). נקודות זיכוי ושיטת המס נגזרות מטופס 101 של העובד, והפנסיה וההפרשות מכרטיס העובד.
    העובד חייב להיות קיים עם אותה ת.ז. כל שורה עוברת בדיוק את אותו חישוב של /employees/{id}/calculate.
    """
    require_company(company_id, user, db, "write")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "הקובץ גדול מדי (מעל 5MB)")
    rows = read_rows(file.filename or "", content)
    if len(rows) > 2000:
        raise HTTPException(400, "יותר מדי שורות (מעל 2000)")

    results, errors = [], []
    for i, row in enumerate(rows, start=2):
        try:
            id_number = str(pick(row, "emp_id_number", "")).strip()
            if not id_number:
                raise ValueError("חסרה תעודת זהות")
            emp = db.query(Employee).filter(Employee.company_id == company_id,
                                            Employee.id_hash == emp_key(company_id, id_number)).first()
            if not emp:
                raise ValueError("עובד עם ת.ז הזו לא קיים במשרד. יש להוסיף אותו קודם")
            base = pick(row, "base_salary")
            body = CalcFromCardIn(
                year=int(pick(row, "year", 0)), month=int(pick(row, "month", 0)),
                ot_hours_125=float(pick(row, "ot_hours_125", 0)),
                ot_hours_150=float(pick(row, "ot_hours_150", 0)),
                bonus=float(pick(row, "bonus", 0)),
                tax_exempt=float(pick(row, "tax_exempt", 0)),
                other_deductions=float(pick(row, "other_deductions", 0)),
                base_salary=float(base) if base is not None else None)
            out = calculate_from_card(company_id, emp.id, body, user, db)
            results.append(out)
        except HTTPException as e:
            db.rollback()
            errors.append({"row": i, "error": str(e.detail)})
        except Exception as e:
            db.rollback()
            errors.append({"row": i, "error": str(e)})
    audit(db, user.id, company_id, "upload_excel_card", "file", None,
          f"rows={len(rows)} ok={len(results)} errors={len(errors)}")
    db.commit()
    return {"processed": len(results), "errors": errors, "paystubs": results}


@app.post("/companies/{company_id}/parse-hours-pdf")
async def parse_hours_pdf(
    company_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """
    קריאת דוח שעות (כרטיס עובד, PDF) לתצוגה מקדימה בלבד: אינה מחשבת שכר ואינה שומרת דבר.
    מחזירה ימים, שעות לפי עמודות, סיכום, ואימות מול שורת הסיכום של הדוח. אזהרות = דברים שלא נקלטו ודורשים בדיקה.
    """
    require_company(company_id, user, db, "write")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "הקובץ גדול מדי (מעל 5MB)")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "יש להעלות קובץ PDF")
    try:
        result = attendance_pdf.parse_pdf(content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(400, "לא ניתן לקרוא את ה-PDF")
    emp = None
    if result.get("id_number"):
        emp = db.query(Employee).filter(Employee.company_id == company_id,
                                        Employee.id_hash == emp_key(company_id, result["id_number"])).first()
    result["employee_found"] = bool(emp)
    result["employee_id"] = emp.id if emp else None
    result["id_number"] = None            # ת.ז לא מוחזרת ללקוח אחרי ההתאמה
    audit(db, user.id, company_id, "parse_hours_pdf", "file", None, f"warnings={len(result['warnings'])}")
    db.commit()
    return result
