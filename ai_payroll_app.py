import streamlit as st
import pandas as pd
import io
import os
import json
import html as html_lib
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time
import streamlit.components.v1 as components
 
# ===========================================================================
# 🤖 אפליקציית AI Payroll - תהליך 5 שלבים
# גרסה מתוקנת לאחר ביקורת מקצועית (Payroll Audit) - 23/09/2026
# ===========================================================================
#
# רשימת התיקונים העיקריים שבוצעו בגרסה זו (ראו דו"ח הביקורת המלא לפרטים):
#   1. תוקנה שגיאת תחביר קריטית (SyntaxError) בפונקציית פענוח הקבצים
#      שמנעה מהאפליקציה לרוץ בכלל.
#   2. מדרגות מס ההכנסה עודכנו לערכים הנכונים לשנת 2026 (לאחר חוק
#      ההתייעלות הכלכלית מיום 31.3.2026 - ריווח מדרגות המס).
#   3. תקרת/שיעורי הביטוח הלאומי עודכנו לפי טבלת המוסד לביטוח לאומי
#      התקפה מ-1.1.2026, כולל הוספת תקרת הכנסה מרבית חייבת בדמי ביטוח.
#   4. נוספה תמיכה במס יסף (3%) על הכנסה חודשית העולה על 60,130 ₪.
#   5. פרמטרי המס/ביטוח לאומי הוצאו לקובץ קונפיגורציה חיצוני
#      (payroll_config_2026.json) שניתן לעדכן בלי לגעת בקוד - ראו
#      הפונקציה load_regulatory_config() למטה.
#   6. תוקנה לוגיקת ברירת המחדל השגויה של נקודות זיכוי: "0 נקודות"
#      שהוזן במפורש (למשל תושב חוץ) כבר לא נדרס ל-2.25 - רק שדה
#      שבאמת חסר (עמודה לא קיימת בקובץ) מקבל את ברירת המחדל.
#   7. זיהוי שורת הכותרות האמיתית באקסל הורחב גם לקבצי CSV (בעבר
#      עבד רק על xlsx/xls).
#   8. הפרשת הפנסיה מחושבת כעת על בסיס שכר פנסיוני (בסיס + ש"נ) ולא
#      כולל בונוסים חד-פעמיים, בהתאם לנוהג המקובל.
#   9. כל טקסט המגיע מהמשתמש/מהקובץ (שם עובד, שם קובץ תבנית) עובר
#      HTML-escaping לפני הזרקה לתלוש, כדי למנוע הזרקת קוד HTML.
#   10. הועלמו מרשימת סוגי הקבצים הנתמכים סוגים שלא נתמכים בפועל
#       (PDF/תמונה בהעלאת קובץ השכר הראשי) כדי לא להטעות את המשתמש.
# ===========================================================================
 
st.set_page_config(
    page_title="AI Payroll - אפליקציית חישוב שכר אוטונומית",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)
 
# עיצוב CSS מודרני: RTL מלא, תוך הגנה על הפונט של האייקונים (Material Icons)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&display=swap');
    
    /* הגדרת גופן עברי כללי */
    html, body, [data-testid="stAppViewContainer"], .main, .stApp {
        direction: rtl;
        text-align: right;
        font-family: 'Rubik', sans-serif;
        background-color: #F8FAFC;
    }
    
    /* החלת Rubik רק על טקסטים ולא על אייקונים מובנים של Streamlit */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, caption {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Rubik', sans-serif !important;
    }
    
    /* מניעת דריסת הפונט של אייקוני החצים (מונע הופעת keyboard_arrow_down כטקסט) */
    [data-testid="stExpanderToggleIcon"], .material-symbols-outlined, [class*="material-"] {
        font-family: 'Material Symbols Outlined', 'Material Icons' !important;
        direction: ltr !important;
    }
    
    .clean-card {
        background-color: #FFFFFF;
        padding: 22px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    
    .stButton button {
        direction: rtl !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 8px 20px !important;
    }
    
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
 
# ניהול מצב המסכים והנתונים (Session State)
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
        TaxBracket(to_dec('19000.00'), to_dec('0.20')),
        TaxBracket(to_dec('25100.00'), to_dec('0.31')),
        TaxBracket(to_dec('46690.00'), to_dec('0.35')),
        TaxBracket(None, to_dec('0.47')),
    ])
    # מס יסף לפי סעיף 121ב לפקודה - 3% על החלק העולה על התקרה החודשית
    surtax_monthly_threshold: Decimal = to_dec('60130.00')
    surtax_rate: Decimal = to_dec('0.03')
    # ביטוח לאומי + מס בריאות, עובד שכיר רגיל (טבלת המל"ל, בתוקף מ-1.1.2026)
    national_insurance_reduced_rate: Decimal = to_dec('0.0427')   # 1.04% ב"ל + 3.23% בריאות
    national_insurance_full_rate: Decimal = to_dec('0.1217')      # 7.00% ב"ל + 5.17% בריאות
    bituach_leumi_threshold: Decimal = to_dec('7703.00')          # מדרגת גביה מופחתת
    bituach_leumi_ceiling: Decimal = to_dec('51910.00')           # הכנסה מרבית חייבת בדמי ביטוח
    pension_employee_rate: Decimal = to_dec('0.06')
    # האם הפרשת הפנסיה כוללת בונוסים חד-פעמיים (ברוב ההסכמים - לא)
    pension_base_includes_bonus: bool = False
 
 
CONFIG_FILENAME = "payroll_config_2026.json"
 
 
def load_regulatory_config() -> RegulatoryData2026:
    """
    טוען את פרמטרי המס/ביטוח הלאומי מקובץ קונפיגורציה חיצוני
    (payroll_config_2026.json) אם קיים, כדי שחשב שכר מוסמך יוכל לעדכן
    מדרגות מס/תקרות מבלי לגעת בקוד ומבלי לפרוס גרסה חדשה של האפליקציה.
    אם הקובץ לא נמצא או פגום - נופלים חזרה לערכי ברירת המחדל המעודכנים
    שמוטמעים בקוד (RegulatoryData2026 למעלה).
    """
    default_rules = RegulatoryData2026()
    candidate_paths = [
        CONFIG_FILENAME,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME),
    ]
    for path in candidate_paths:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                brackets = [
                    TaxBracket(
                        to_dec(b["upper_limit"]) if b.get("upper_limit") is not None else None,
                        to_dec(b["rate"])
                    )
                    for b in cfg["tax_brackets"]
                ]
                return RegulatoryData2026(
                    year=cfg.get("year", default_rules.year),
                    credit_point_value_monthly=to_dec(cfg.get("credit_point_value_monthly", default_rules.credit_point_value_monthly)),
                    tax_brackets=brackets,
                    surtax_monthly_threshold=to_dec(cfg.get("surtax_monthly_threshold", default_rules.surtax_monthly_threshold)),
                    surtax_rate=to_dec(cfg.get("surtax_rate", default_rules.surtax_rate)),
                    national_insurance_reduced_rate=to_dec(cfg.get("national_insurance_reduced_rate", default_rules.national_insurance_reduced_rate)),
                    national_insurance_full_rate=to_dec(cfg.get("national_insurance_full_rate", default_rules.national_insurance_full_rate)),
                    bituach_leumi_threshold=to_dec(cfg.get("bituach_leumi_threshold", default_rules.bituach_leumi_threshold)),
                    bituach_leumi_ceiling=to_dec(cfg.get("bituach_leumi_ceiling", default_rules.bituach_leumi_ceiling)),
                    pension_employee_rate=to_dec(cfg.get("pension_employee_rate", default_rules.pension_employee_rate)),
                    pension_base_includes_bonus=bool(cfg.get("pension_base_includes_bonus", default_rules.pension_base_includes_bonus)),
                )
        except Exception as e:
            st.warning(f"⚠️ לא ניתן היה לטעון את קובץ הקונפיגורציה ({path}): {e}. נעשה שימוש בערכי ברירת המחדל המוטמעים בקוד.")
            break
    return default_rules
 
 
class EasyPayrollEngine:
    def __init__(self):
        self.rules = load_regulatory_config()
 
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
 
        # --- נקודות זיכוי ---
        # יש להבחין בין "לא סופק נתון" (None -> נופלים לברירת המחדל של
        # תושב ישראל, 2.25) לבין "סופק במפורש הערך 0" (למשל תושב חוץ
        # ללא זכאות לנקודות בסיס) - במקרה הזה חובה לכבד את ה-0 ולא
        # לדרוס אותו.
        raw_pts = emp.get('credit_points', None)
        if raw_pts is None:
            pts = Decimal('2.25')
        else:
            pts = to_dec(raw_pts)
 
        # --- מס הכנסה: מדרגות פרוגרסיביות ---
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
 
        # --- מס יסף (סעיף 121ב) על הכנסה חודשית מעל התקרה ---
        if gross > self.rules.surtax_monthly_threshold:
            tax_gross += (gross - self.rules.surtax_monthly_threshold) * self.rules.surtax_rate
 
        tax_credit = pts * self.rules.credit_point_value_monthly
        tax_final = to_dec(max(Decimal('0.00'), tax_gross - tax_credit))
 
        # --- ביטוח לאומי + מס בריאות, כולל תקרת הכנסה מרבית חייבת ---
        t = self.rules.bituach_leumi_threshold
        ceiling = self.rules.bituach_leumi_ceiling
        ni_base = min(gross, ceiling)  # מעל התקרה - אין ניכוי נוסף
        if ni_base <= t:
            ni = ni_base * self.rules.national_insurance_reduced_rate
        else:
            ni = (t * self.rules.national_insurance_reduced_rate) + ((ni_base - t) * self.rules.national_insurance_full_rate)
        ni_final = to_dec(ni)
 
        # --- הפרשת פנסיה: לפי בסיס פנסיוני (ברירת מחדל: בלי בונוס חד-פעמי) ---
        pension_base = (base + ot_pay + bonus) if self.rules.pension_base_includes_bonus else (base + ot_pay)
        pension = to_dec(pension_base * self.rules.pension_employee_rate)
 
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
            'income_tax': tax_final,
            'ni': ni_final,
            'pension': pension,
            'total_ded': total_ded,
            'net': net,
            'credit_pts': pts
        }
 
# ===========================================================================
# 🧠 פונקציית קליטה ופענוח אקסל/CSV מתוחכמת (קוראת 100% מהשמות והנתונים)
# ===========================================================================
 
# מילות המפתח המשמשות לניקוד שורת הכותרות האמיתית - משותפות ל-Excel ול-CSV
_HEADER_KEYWORDS = ['שם', 'עובד', 'name', 'תז', 'ת.ז', 'id', 'בסיס', 'salary',
                     'משכורת', 'ברוטו', 'תפקיד', 'מחלקה', 'בונוס', 'bonus', 'שעות']
 
# ניסוחים שונים לשורות "סה\"כ/סיכום" שיש לסנן - כדי לא לקלוט אותן כעובד
_SUMMARY_ROW_MARKERS = ['סה"כ', 'סיכום', 'עובדים', 'סה״כ', 'סך הכל', 'סך הכול', 'total', 'sum']
 
 
def _find_header_row(df_raw: pd.DataFrame) -> int:
    """
    סורק עד 20 השורות הראשונות של DataFrame גולמי (ללא כותרות) ומנקד כל
    שורה לפי כמות מילות המפתח שמופיעות בה + כמות התאים הטקסטואליים בה,
    כדי לאתר את שורת הכותרות האמיתית גם כשהיא לא בשורה הראשונה
    (למשל כשיש שורות לוגו/כותרת/רווח מעל טבלת הנתונים).
    משמש הן לקבצי Excel והן לקבצי CSV - כדי שההתנהגות תהיה עקבית בין
    הפורמטים (בגרסה הקודמת זיהוי זה בוצע רק עבור Excel).
    """
    best_row_idx = 0
    max_score = -1
    for r_idx in range(min(20, len(df_raw))):
        row_vals = [str(v).strip() for v in df_raw.iloc[r_idx].values if pd.notna(v) and str(v).strip() != '']
        if len(row_vals) < 2:
            continue
        row_str_lower = ' '.join(row_vals).lower()
        matches = sum(1 for k in _HEADER_KEYWORDS if k in row_str_lower)
        text_cols = sum(1 for v in row_vals if not str(v).replace('.', '').replace('-', '').replace('₪', '').strip().isdigit())
        score = matches * 10 + text_cols
        if score > max_score and matches >= 1:
            max_score = score
            best_row_idx = r_idx
    return best_row_idx
 
 
def parse_uploaded_file(uploaded_file) -> List[Dict[str, Any]]:
    parsed_records = []
    try:
        filename = uploaded_file.name.lower()
        file_bytes = uploaded_file.getvalue()
 
        if filename.endswith('.csv'):
            # קריאה גולמית לפי שורות (csv.reader) ולא pd.read_csv הישיר:
            # שורות "רעש" מעל הכותרת האמיתית (למשל כותרת חברה) מכילות
            # פחות עמודות מהטבלה עצמה, ו-pd.read_csv נכשל על כך (ParserError).
            # csv.reader סובלני לשורות לא-אחידות, בדיוק כמו שקריאת ה-Excel
            # למטה סובלנית לכך דרך header=None.
            raw_text = None
            for enc in ['utf-8-sig', 'utf-8', 'cp1255', 'iso-8859-8']:
                try:
                    raw_text = file_bytes.decode(enc)
                    break
                except Exception:
                    continue
            if raw_text is None or not raw_text.strip():
                st.error("⚠️ לא ניתן היה לקרוא את קובץ ה-CSV (בעיית קידוד או קובץ ריק).")
                return []
 
            import csv as _csv_module
            sample = "\n".join(raw_text.splitlines()[:5])
            try:
                delimiter = _csv_module.Sniffer().sniff(sample, delimiters=",;\t").delimiter
            except Exception:
                delimiter = ","
 
            raw_rows = [row for row in _csv_module.reader(io.StringIO(raw_text), delimiter=delimiter) if row]
            if not raw_rows:
                st.error("⚠️ קובץ ה-CSV ריק.")
                return []
 
            max_cols = max(len(r) for r in raw_rows)
            padded_rows = [r + [""] * (max_cols - len(r)) for r in raw_rows]
            df_raw = pd.DataFrame(padded_rows).replace("", pd.NA)
 
            best_row_idx = _find_header_row(df_raw)
            header_vals = padded_rows[best_row_idx]
            data_rows = padded_rows[best_row_idx + 1:]
            df = pd.DataFrame(data_rows, columns=header_vals).replace("", pd.NA)
 
        elif filename.endswith(('.xlsx', '.xls')):
            df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None)
            if df_raw.empty:
                return []
 
            best_row_idx = _find_header_row(df_raw)
            df = pd.read_excel(io.BytesIO(file_bytes), header=best_row_idx)
        else:
            st.error(f"⚠️ סוג הקובץ '{filename}' אינו נתמך לקליטה אוטומטית. יש להעלות קובץ Excel (xlsx/xls) או CSV בלבד.")
            return []
 
        df = df.dropna(how='all')
        df.columns = [str(c).strip() for c in df.columns]
 
        full_name_col = None
        first_name_col = None
        last_name_col = None
        id_col = None
        base_col = None
        ot125_col = None
        ot150_col = None
        bonus_col = None
        credit_col = None
 
        for col in df.columns:
            c_clean = str(col).strip().lower()
            if 'unnamed' in c_clean:
                continue
            
            if 'שם פרטי' in c_clean or 'first' in c_clean:
                first_name_col = col
            elif 'שם משפחה' in c_clean or 'last' in c_clean:
                last_name_col = col
            elif ('שם' in c_clean or 'name' in c_clean or 'עובד' in c_clean) and not full_name_col and 'מס' not in c_clean and 'תז' not in c_clean and 'ת.ז' not in c_clean:
                full_name_col = col
            elif ('שם' in c_clean or 'name' in c_clean or 'עובד' in c_clean) and not full_name_col and 'מס' not in c_clean and 'תז' not in c_clean:
                full_name_col = col
 
            if ('תז' in c_clean or 'ת.ז' in c_clean or 'id' in c_clean or 'זהות' in c_clean or 'מס' in c_clean) and not id_col:
                id_col = col
            elif ('בסיס' in c_clean or 'base' in c_clean or 'שכר' in c_clean or 'salary' in c_clean or 'יסוד' in c_clean) and not base_col:
                base_col = col
            elif '125' in c_clean:
                ot125_col = col
            elif '150' in c_clean:
                ot150_col = col
            elif ('בונוס' in c_clean or 'bonus' in c_clean or 'עמלה' in c_clean or 'תוספת' in c_clean) and not bonus_col:
                bonus_col = col
            elif ('זיכוי' in c_clean or 'credit' in c_clean or 'נז' in c_clean or 'נ"ז' in c_clean) and not credit_col:
                credit_col = col
 
        if not full_name_col and not (first_name_col and last_name_col):
            for col in df.columns:
                if 'unnamed' in str(col).lower(): continue
                sample_vals = df[col].dropna().astype(str).tolist()
                if any(any('\u0590' <= ch <= '\u05ff' for ch in s) for s in sample_vals[:10]):
                    full_name_col = col
                    break
 
        def clean_num(v, default=0.0):
            if pd.isna(v) or v == '' or v is None:
                return default
            try:
                s = str(v).replace('₪', '').replace(',', '').strip()
                return float(s)
            except Exception:
                return default
 
        for idx, row in df.iterrows():
            emp_name = ""
            if first_name_col and last_name_col:
                fn = str(row.get(first_name_col, '')).strip() if pd.notna(row.get(first_name_col)) else ""
                ln = str(row.get(last_name_col, '')).strip() if pd.notna(row.get(last_name_col)) else ""
                emp_name = f"{fn} {ln}".strip()
            
            if not emp_name and full_name_col:
                val = row.get(full_name_col)
                if pd.notna(val) and str(val).strip() and str(val).strip().lower() != 'nan':
                    emp_name = str(val).strip()
 
            emp_name_lower = emp_name.lower()
            if not emp_name or emp_name_lower == 'nan' or any(k in emp_name or k in emp_name_lower for k in _SUMMARY_ROW_MARKERS):
                continue
 
            emp_id = ""
            if id_col:
                val = row.get(id_col)
                if pd.notna(val) and str(val).strip() and str(val).strip().lower() != 'nan':
                    id_str = str(val).strip()
                    if id_str.endswith('.0'):
                        id_str = id_str[:-2]
                    emp_id = id_str
            if not emp_id or 'סה' in emp_id:
                emp_id = str(idx + 101)
 
            # נקודות זיכוי: אם לא נמצאה בקובץ עמודת נקודות זיכוי כלל,
            # משאירים None כדי שמנוע החישוב יידע להשלים ברירת מחדל של
            # 2.25 (תושב ישראל). אם העמודה כן קיימת - מכבדים את הערך
            # שבתא, כולל 0 (למשל תושב חוץ ללא זכאות לנקודות בסיס).
            if credit_col is None:
                credit_points_value = None
            else:
                raw_credit_val = row.get(credit_col)
                credit_points_value = clean_num(raw_credit_val, default=None)
                if credit_points_value is None and pd.notna(raw_credit_val):
                    credit_points_value = 2.25  # ערך לא-תקין בתא -> נופלים לברירת מחדל
 
            record = {
                'id': emp_id,
                'name': emp_name,
                'base_salary': clean_num(row.get(base_col, 0)),
                'ot_125': clean_num(row.get(ot125_col, 0)),
                'ot_150': clean_num(row.get(ot150_col, 0)),
                'bonus': clean_num(row.get(bonus_col, 0)),
                'credit_points': credit_points_value
            }
            parsed_records.append(record)
 
    except Exception as e:
        st.error(f"שגיאה בפענוח הקובץ: {str(e)}")
    return parsed_records
 
# המרת נתוני עובדים לטבלה מעוצבת בעברית
def get_hebrew_display_df(records_list):
    display_rows = []
    for r in records_list:
        display_rows.append({
            "מספר עובד / ת.ז": str(r.get('id', '')),
            "שם העובד/ת": str(r.get('name', '')),
            "שכר בסיס (₪)": f"₪{to_dec(r.get('base_salary', 0)):,.2f}",
            "שעות 125%": r.get('ot_125', 0),
            "שעות 150%": r.get('ot_150', 0),
            "בונוס / עמלה (₪)": f"₪{to_dec(r.get('bonus', 0)):,.2f}",
            "נקודות זיכוי מס": (r.get('credit_points') if r.get('credit_points') is not None else "2.25 (ברירת מחדל)")
        })
    return pd.DataFrame(display_rows)
 
# רשימת עובדי דמו משותפת (נוצרה פעם אחת כדי למנוע שכפול קוד בין השלבים)
DEFAULT_DEMO_EMPLOYEES = [
    {"id": "101", "name": "דנה לוי", "base_salary": 16000, "ot_125": 5, "ot_150": 2, "bonus": 4500, "credit_points": 2.75},
    {"id": "102", "name": "ישראל ישראלי", "base_salary": 12500, "ot_125": 15, "ot_150": 5, "bonus": 1200, "credit_points": 2.25},
    {"id": "103", "name": "משה כהן", "base_salary": 9500, "ot_125": 0, "ot_150": 0, "bonus": 0, "credit_points": 2.25},
    {"id": "104", "name": "אלישבע מור", "base_salary": 14500, "ot_125": 12, "ot_150": 6, "bonus": 1200, "credit_points": 3.25},
    {"id": "105", "name": "אביתר אברהם", "base_salary": 18500, "ot_125": 4, "ot_150": 0, "bonus": 3000, "credit_points": 4.25},
]
 
# --- כותרת ראשית וסרגל התקדמות ---
st.title("🤖 מערכת חישוב שכר אוטונומית — AI Payroll")
st.caption("מערכת שכר חכמה לחשבי שכר | קליטת נתונים, חישוב מדויק, סקירת חריגות והפקת תלושים מעוצבים")
 
step_names = {
    1: "1. קליטת קבצים ושכר",
    2: "2. חישוב AI ומיסוי",
    3: "3. בדיקה ואישור חשב",
    4: "4. התאמת תבנית ארגונית",
    5: "5. הפקת תלושים מעוצבים"
}
 
progress_val = st.session_state.step / 5
st.progress(progress_val)
st.markdown(f"**שלב נוכחי:** {step_names[st.session_state.step]}")
 
# ===========================================================================
# שלב 1: קליטת קבצים
# ===========================================================================
if st.session_state.step == 1:
    st.subheader("📁 שלב 1: העלאת קבצי שכר וטפסים")
    st.write("העלי את קובץ האקסל או ה-CSV עם נתוני השכר של העובדים:")
 
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        # הוסרו png/jpg/jpeg/pdf מרשימת הסוגים הנתמכים: parse_uploaded_file
        # אינו יודע לפענח אותם, וקבלתם כאן הייתה יוצרת אשליית פונקציונליות
        # (קובץ "מתקבל" ע"י הממשק אך לא נטען אף רשומה ממנו, בלי הודעת שגיאה).
        uploaded_files = st.file_uploader(
            "לחצי להעלאת קובצי אקסל / CSV:",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            help="נתמכים כרגע קבצי Excel (xlsx/xls) ו-CSV בלבד."
        )
        if uploaded_files:
            all_records = []
            for f in uploaded_files:
                records = parse_uploaded_file(f)
                if records:
                    all_records.extend(records)
            if all_records:
                st.session_state.uploaded_employees_data = all_records
                st.success(f"✨ נקלטו בהצלחה {len(all_records)} עובדים מתוך הקובץ שהועלה!")
 
    with col_up2:
        st.write("📸 **צילום טפסי 101 / מסמכים בלייב:**")
        cam_image = st.camera_input("לחצי לצילום מסמך במצלמה")
        if cam_image:
            # שים לב: בשלב זה הצילום נשמר לתיעוד בלבד. פענוח אוטומטי (OCR)
            # של תוכן הטופס וקישורו לנתוני העובד טרם מומש - ראו דו"ח
            # הביקורת, תרחיש קצה י'. יש להימנע מהודעה שמרמזת ש"פוענח".
            st.info("📸 המסמך צולם ונשמר להצגה בלבד. פענוח אוטומטי (OCR) של טופס 101 אינו מיושם עדיין במערכת - יש להזין את הנתונים ידנית.")
 
    if st.session_state.uploaded_employees_data:
        st.markdown(f"### 📋 נקלטו {len(st.session_state.uploaded_employees_data)} עובדים מתוך הקובץ:")
        df_preview = get_hebrew_display_df(st.session_state.uploaded_employees_data)
        st.dataframe(df_preview, use_container_width=True, height=400)
 
    st.markdown("---")
    if st.button("➡️ המשך לשלב החישוב", type="primary", use_container_width=True):
        st.session_state.step = 2
        st.rerun()
 
# ===========================================================================
# שלב 2: חישוב AI
# ===========================================================================
elif st.session_state.step == 2:
    st.subheader("🧮 שלב 2: הרצת חישוב AI וסנכרון חוקי מיסוי 2026")
 
    current_employees_input = st.session_state.uploaded_employees_data
    if not current_employees_input:
        current_employees_input = DEFAULT_DEMO_EMPLOYEES
 
    st.write(f"המערכת מוכנה להריץ חישוב פיננסי מדויק עבור **{len(current_employees_input)} עובדים**:")
 
    if not st.session_state.payroll_calculated:
        if st.button("🧮 הרץ חישוב שכר עכשיו", type="primary", use_container_width=True):
            with st.spinner(f"⏳ מנוע ה-AI מחשב שכר ומיסוי עבור {len(current_employees_input)} עובדים..."):
                time.sleep(1.5)
            st.session_state.payroll_calculated = True
            st.rerun()
    else:
        st.balloons()
        st.success(f"🎉 **החישוב הושלם בהצלחה!** נתוני השכר של כל {len(current_employees_input)} העובדים מחושבים ומעודכנים.")
        st.markdown("---")
        if st.button("➡️ המשך לסקירת חשב השכר", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
 
# ===========================================================================
# שלב 3: סקירת חשב שכר
# ===========================================================================
elif st.session_state.step == 3:
    st.subheader("📋 שלב 3: סקירת נתונים מפורטת ואישור חשב שכר")
 
    current_employees_input = st.session_state.uploaded_employees_data
    if not current_employees_input:
        current_employees_input = DEFAULT_DEMO_EMPLOYEES
 
    engine = EasyPayrollEngine()
    calculated_data = [engine.process(e) for e in current_employees_input]
 
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("סה\"כ עובדים במחזור", len(calculated_data))
    col_m2.metric("תלושים שאושרו", len(st.session_state.approved_stubs))
    col_m3.metric("תלושים לתיקון", len(st.session_state.rejected_stubs))
 
    search_query = st.text_input("🔍 חיפוש מהיר לפי שם עובד/ת או תעודת זהות:", value="")
 
    st.markdown("---")
 
    for emp in calculated_data:
        if search_query and search_query.strip() not in emp['name'] and search_query.strip() not in emp['id']:
            continue
 
        is_app = emp['id'] in st.session_state.approved_stubs
        is_rej = emp['id'] in st.session_state.rejected_stubs
        status_text = "✅ אושר" if is_app else ("❌ נדחה" if is_rej else "⏳ ממתין לבדיקה")
 
        with st.expander(f"👤 {emp['name']} (ת.ז {emp['id']}) — סטטוס: [{status_text}] — 💰 נטו לבנק: ₪{emp['net']:,.2f}", expanded=(not is_app and not is_rej)):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **💵 פירוט רכיבי ברוטו:**
                * שכר בסיס: ₪{emp['base']:,.2f}
                * תעריף שעתי: ₪{emp['hourly']:,.2f}
                * שעות נוספות: ₪{emp['ot_pay']:,.2f}
                * בונוסים ועמלות: ₪{emp['bonus']:,.2f}
                * **סה"כ שכר ברוטו:** **₪{emp['gross']:,.2f}**
                """)
            with col2:
                st.markdown(f"""
                **📉 פירוט ניכויי חובה ומיסוי:**
                * מס הכנסה: ₪{emp['income_tax']:,.2f}
                * ביטוח לאומי ומס בריאות: ₪{emp['ni']:,.2f}
                * הפרשת פנסיה עובד (6%): ₪{emp['pension']:,.2f}
                * **סה"כ ניכויי חובה:** ₪{emp['total_ded']:,.2f}
                """)
 
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button(f"✅ אשר תלוש עבור {emp['name']}", key=f"app_{emp['id']}"):
                    st.session_state.approved_stubs.add(emp['id'])
                    st.session_state.rejected_stubs.discard(emp['id'])
                    st.rerun()
            with b_col2:
                if st.button(f"❌ דחה תלוש עבור {emp['name']}", key=f"rej_{emp['id']}"):
                    st.session_state.rejected_stubs.add(emp['id'])
                    st.session_state.approved_stubs.discard(emp['id'])
                    st.rerun()
 
    st.markdown("---")
    if st.button("➡️ המשך להתאמת תבנית התלוש", type="primary", use_container_width=True):
        st.session_state.step = 4
        st.rerun()
 
# ===========================================================================
# שלב 4: התאמת תבנית
# ===========================================================================
elif st.session_state.step == 4:
    st.subheader("📄 שלב 4: התאמת תבנית תלוש השכר של הארגון")
    st.write("העלי קובץ תלוש לדוגמה של הארגון (PDF / תמונה). ה-AI ילמד את המבנה והעיצוב שלו:")
 
    sample_file = st.file_uploader(
        "לחצי להעלאת תלוש לדוגמה (PDF / תמונה):",
        type=["pdf", "png", "jpg", "jpeg"],
        key="template_uploader"
    )
 
    if sample_file:
        st.session_state.sample_template_bytes = sample_file.getvalue()
        st.session_state.sample_template_name = sample_file.name
        st.session_state.sample_template_type = sample_file.type
        st.success(f"✨ התלוש לדוגמה **{sample_file.name}** נשמר בהצלחה כקובץ ייחוס.")
        st.caption("שימו לב: הקובץ נשמר לצפייה/תיעוד בלבד. התאמה אוטומטית של עיצוב התלוש המופק למבנה הקובץ שהועלה אינה מיושמת עדיין.")
 
        if sample_file.type.startswith("image/"):
            st.image(sample_file, caption="תצוגה מקדימה של תבנית הארגון", use_container_width=True)
 
    st.markdown("---")
    if st.button("➡️ המשך להפקת התלושים המעוצבים", type="primary", use_container_width=True):
        st.session_state.step = 5
        st.rerun()
 
# ===========================================================================
# שלב 5: הפקת תלושים
# ===========================================================================
elif st.session_state.step == 5:
    st.subheader("🎉 שלב 5: הפקת תלושי שכר מעוצבים והורדה למחשב")
 
    current_employees_input = st.session_state.uploaded_employees_data
    if not current_employees_input:
        current_employees_input = DEFAULT_DEMO_EMPLOYEES
 
    engine = EasyPayrollEngine()
    calculated_data = [engine.process(e) for e in current_employees_input]
 
    template_label = st.session_state.sample_template_name or 'תבנית ארגונית רשמית'
    
    # חילוץ בטוח של שם החברה ללא שום שגיאה
    clean_label_str = str(template_label)
    if '.' in clean_label_str:
        company_name = clean_label_str.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
    else:
        company_name = clean_label_str.replace('_', ' ').replace('-', ' ')
 
    st.info(f"✨ **התלושים מופקים בהתאמה לתבנית הארגון:** `{template_label}`")
 
    selected_name = st.selectbox("בחרי עובד/ת להצגה והורדה:", options=[e['name'] for e in calculated_data])
    emp = next(e for e in calculated_data if e['name'] == selected_name)
 
    # HTML-escaping לכל מחרוזת שמקורה בקלט חיצוני (שם עובד, שם קובץ תבנית)
    # לפני הזרקה ל-HTML של התלוש, כדי למנוע הזרקת תגיות/קוד HTML (XSS)
    # דרך שם עובד או שם קובץ עם תווים כמו < > &.
    safe_company_name = html_lib.escape(company_name)
    safe_template_label = html_lib.escape(str(template_label))
    safe_emp_name = html_lib.escape(emp['name'])
    safe_emp_id = html_lib.escape(emp['id'])
 
    # בילד קובץ HTML מעוצב ונקי של התלוש בעברית מלאה
    official_paystub_html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="utf-8">
    <title>תלוש שכר - {safe_emp_name}</title>
 
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #FFFFFF;
            padding: 15px;
            direction: rtl;
            text-align: right;
            color: #0F172A;
        }}
        .paystub-card {{
            max-width: 850px;
            margin: 0 auto;
            background: #FFFFFF;
            border: 2px solid #1E3A8A;
            border-radius: 8px;
            padding: 20px;
        }}
        .top-header {{
            display: flex;
            justify-content: space-between;
            border-bottom: 2px solid #0F172A;
            padding-bottom: 8px;
            margin-bottom: 12px;
            font-size: 13px;
        }}
        .header-title {{
            font-size: 18px;
            font-weight: bold;
            color: #1E3A8A;
        }}
        .section-box {{
            border: 1px solid #CBD5E1;
            margin-bottom: 12px;
            border-radius: 4px;
            overflow: hidden;
        }}
        .section-header {{
            background-color: #F1F5F9;
            padding: 6px 12px;
            font-weight: bold;
            font-size: 13px;
            color: #1E293B;
            border-bottom: 1px solid #CBD5E1;
        }}
        .details-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding: 10px;
            font-size: 12px;
            background-color: #FAFAFA;
        }}
        .tables-row {{
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
        }}
        .table-col {{ flex: 1; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th, td {{
            padding: 6px 8px;
            border: 1px solid #CBD5E1;
            text-align: right;
        }}
        th {{
            background-color: #0F172A;
            color: white;
        }}
        .total-row {{
            background-color: #F8FAFC;
            font-weight: bold;
        }}
        .net-pay-banner {{
            background-color: #DCFCE7;
            border: 2px solid #16A34A;
            padding: 12px;
            text-align: center;
            font-size: 20px;
            font-weight: bold;
            color: #15803D;
            border-radius: 6px;
            margin-bottom: 12px;
        }}
        .bottom-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            font-size: 11px;
        }}
        .bottom-box {{
            border: 1px solid #CBD5E1;
            padding: 8px;
            background-color: #FAFAFA;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="paystub-card">
        <div class="top-header">
            <div>
                <div class="header-title">תלוש משכורת רשמי — ספטמבר 2026</div>
                <div>הודפס בתאריך 23/09/2026 | דף 1 מתוך 1</div>
            </div>
            <div style="text-align: left;">
                <b>ארגון / מעסיק:</b> {safe_company_name}<br/>
                <b>תבנית ייחוס:</b> {safe_template_label}
            </div>
        </div>
 
        <div class="section-box">
            <div class="section-header">פרטים אישיים והעסקה</div>
            <div class="details-grid">
                <div><b>מספר עובד:</b> {safe_emp_id}</div>
                <div><b>תעודת זהות:</b> {safe_emp_id}</div>
                <div><b>שם העובד/ת:</b> {safe_emp_name}</div>
                <div><b>בסיס השכר:</b> חודשי / שעתי</div>
                <div><b>תושב:</b> כן</div>
                <div><b>משרה:</b> 100%</div>
                <div><b>נקודות זיכוי:</b> {emp['credit_pts']} נ"ז</div>
                <div><b>תחילת עבודה:</b> 01/01/2024</div>
            </div>
        </div>
 
        <div class="tables-row">
            <div class="table-col">
                <div class="section-box">
                    <div class="section-header">פירוט תשלומים (ברוטו)</div>
                    <table>
                        <thead>
                            <tr>
                                <th>קוד</th>
                                <th>תאור התשלום</th>
                                <th>סכום (₪)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>001</td><td>משכורת בסיס</td><td>₪{emp['base']:,.2f}</td></tr>
                            {'<tr><td>002</td><td>גמול שעות נוספות</td><td>₪' + f"{emp['ot_pay']:,.2f}" + '</td></tr>' if emp['ot_pay'] > 0 else ''}
                            {'<tr><td>003</td><td>בונוס / עמלה</td><td>₪' + f"{emp['bonus']:,.2f}" + '</td></tr>' if emp['bonus'] > 0 else ''}
                            <tr class="total-row">
                                <td colspan="2"><b>סה"כ שכר ברוטו</b></td>
                                <td><b>₪{emp['gross']:,.2f}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
 
            <div class="table-col">
                <div class="section-box">
                    <div class="section-header">פירוט ניכויי חובה</div>
                    <table>
                        <thead>
                            <tr>
                                <th>קוד</th>
                                <th>תאור הניכוי</th>
                                <th>סכום (₪)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>101</td><td>מס הכנסה (מדרגות 2026)</td><td>₪{emp['income_tax']:,.2f}</td></tr>
                            <tr><td>102</td><td>ביטוח לאומי ומס בריאות</td><td>₪{emp['ni']:,.2f}</td></tr>
                            <tr><td>103</td><td>הפרשת פנסיה עובד (6%)</td><td>₪{emp['pension']:,.2f}</td></tr>
                            <tr class="total-row">
                                <td colspan="2"><b>סה"כ ניכויי חובה</b></td>
                                <td><b>₪{emp['total_ded']:,.2f}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
 
        <div class="net-pay-banner">
            💵 שכר נטו לתשלום לבנק: ₪{emp['net']:,.2f}
        </div>
 
        <div class="bottom-grid">
            <div class="bottom-box">
                <b>📊 נתונים נוספים:</b><br/>
                • ימי עבודה בפועל: 22 ימים<br/>
                • שעות עבודה בפועל: 182 שעות
            </div>
            <div class="bottom-box">
                <b>📈 נתונים מצטברים:</b><br/>
                • מצטבר חייב מס: ₪{emp['gross']:,.2f}<br/>
                • מצטבר מס הכנסה: ₪{emp['income_tax']:,.2f}
            </div>
            <div class="bottom-box">
                <b>🏖️ יתרות חופשה ומחלה:</b><br/>
                • יתרת חופשה: 13.5 ימים<br/>
                • יתרת מחלה: 25.25 ימים
            </div>
        </div>
    </div>
</body>
</html>"""
 
    # ניקוי שם הקובץ מתווים שאינם חוקיים במערכות קבצים (שם עובד/מספר עובד
    # מגיעים מקובץ שהועלה ע"י המשתמש ואינם באחריותנו לוודא שהם "נקיים")
    _unsafe_chars = '<>:"/\\|?*'
    safe_filename_part = "".join(c for c in f"{emp['id']}_{emp['name']}" if c not in _unsafe_chars).strip()
 
    st.download_button(
        label=f"📥 הורד תלוש שכר מעוצב עבור {emp['name']} למחשב",
        data=official_paystub_html,
        file_name=f"paystub_{safe_filename_part}.html",
        mime="text/html",
        type="primary",
        use_container_width=True
    )
 
    st.markdown("---")
 
    tab1, tab2 = st.tabs(["📄 תצוגת התלוש המעוצב", "🖼️ תבנית המקור שהועלתה"])
 
    with tab1:
        components.html(official_paystub_html, height=560, scrolling=True)
 
    with tab2:
        if st.session_state.sample_template_bytes:
            st.write(f"**תבנית המקור שהועלתה:** `{st.session_state.sample_template_name}`")
            if st.session_state.sample_template_type and st.session_state.sample_template_type.startswith("image/"):
                st.image(st.session_state.sample_template_bytes, caption="תבנית הארגון המקורית", use_container_width=True)
            else:
                st.info("קובץ התבנית הועלה ונשמר במערכת בפורמט מסמך.")
        else:
            st.info("לא הועלה קובץ תבנית במסך 4. נעשה שימוש בתבנית הדיגיטלית המובנית.")
 
    st.markdown("---")
    if st.button("🔄 התחל תהליך חדש (חזרה לשלב 1)", use_container_width=True):
        st.session_state.step = 1
        st.session_state.payroll_calculated = False
        st.rerun()
