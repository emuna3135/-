
import streamlit as st
import pandas as pd

# הגדרת עמוד האפליקציה
st.set_page_config(
    page_title="Autonomous AI Payroll",
    page_icon="🤖",
    layout="wide"
)

# כותרת ראשית ותיאור
st.title("🤖 אפליקציית חישוב שכר אוטונומית (AI Payroll)")
st.caption("סריקת נתונים אוטומטית, זיהוי חריגות בזמן אמת ואישור חשב שכר (Human-in-the-Loop)")
st.markdown("---")

# סרגל צד לטעינת קבצים ומידע
st.sidebar.header("📁 טעינת נתוני שכר")
uploaded_file = st.sidebar.file_uploader("גררי לכאן קובץ אקסל/נוכחות", type=["xlsx", "csv"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ סטטוס רגולציה ומיסוי")
st.sidebar.success("🟢 מסונכרן בזמן אמת לרגולציית 2026")
st.sidebar.info("• מדרגות מס הכנסה מעודכנות\n• תקרות ביטוח לאומי 2026\n• נקודת זיכוי: ₪242.00")

# נתוני דוגמה לתלושים וחריגות
employees_data = [
    {
        "id": "101",
        "name": "ישראל ישראלי",
        "gross": 18161.81,
        "net": 13069.28,
        "status": "FLAGGED",
        "flags": [
            {"level": "HIGH", "icon": "🔴", "msg": "קפיצה חריגה של 179% בשעות נוספות ביחס לממוצע ההיסטורי."},
            {"level": "MEDIUM", "icon": "🟠", "msg": "בונוס/עמלה בגובה ₪1,850.00 חורג מהנורמה החודשית."}
        ]
    },
    {
        "id": "102",
        "name": "דנה לוי",
        "gross": 21049.45,
        "net": 14662.98,
        "status": "FLAGGED",
        "flags": [
            {"level": "MEDIUM", "icon": "🟠", "msg": "בונוס חורג בגובה ₪4,500.00."},
            {"level": "LOW", "icon": "🟡", "msg": "עודכן טופס 101 חדש - יש לוודא התאמת נקודות זיכוי."}
        ]
    },
    {
        "id": "103",
        "name": "משה כהן",
        "gross": 9630.49,
        "net": 7975.39,
        "status": "CLEAN",
        "flags": []
    }
]

# מדדים מרכזיים
col1, col2, col3 = st.columns(3)
total_emp = len(employees_data)
flagged_emp = len([e for e in employees_data if e["status"] == "FLAGGED"])
clean_emp = total_emp - flagged_emp

col1.metric("סה\"כ תלושים במחזור", total_emp)
col2.metric("מאושרים אוטומטית (תקינים)", clean_emp, delta="🟢 מוכנים לסגירה")
col3.metric("ממתינים לבדיקת חשב", flagged_emp, delta="-⚠️ חריגות לבדיקה", delta_color="inverse")

st.markdown("---")

# לוח בדיקות ואישורים
st.subheader("📋 לוח בדיקות ואישורים (Human-in-the-Loop)")
st.write("ה-AI סרק את הנתונים, חישב את השכר והציף את החריגות. החלטת האישור הסופית היא שלך:")

for emp in employees_data:
    if emp["status"] == "FLAGGED":
        with st.expander(f"⚠️ **{emp['name']}** (ת.ז: {emp['id']}) — ברוטו: ₪{emp['gross']:,.2f} | נטו לתשלום: ₪{emp['net']:,.2f}", expanded=True):
            st.markdown("##### 🔍 ממצאי ה-AI לבדיקת החשב:")
            for flag in emp["flags"]:
                if flag["level"] == "HIGH":
                    st.error(f"{flag['icon']} **[{flag['level']}]** {flag['msg']}")
                elif flag["level"] == "MEDIUM":
                    st.warning(f"{flag['icon']} **[{flag['level']}]** {flag['msg']}")
                else:
                    st.info(f"{flag['icon']} **[{flag['level']}]** {flag['msg']}")
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button(f"✅ אשר תלוש", key=f"approve_{emp['id']}"):
                    st.success(f"תלוש השכר של {emp['name']} אושר בהצלחה!")
            with btn_col2:
                if st.button(f"❌ דחה / תחקור", key=f"reject_{emp['id']}"):
                    st.error(f"התלוש הועבר לתיקון מול מנהל המחלקה.")
    else:
        st.success(f"🟢 **{emp['name']}** (ת.ז: {emp['id']}) — ברוטו: ₪{emp['gross']:,.2f} | נטו לתשלום: ₪{emp['net']:,.2f} (✅ התלוש תקין לחלוטין ואושר אוטומטית במנוע החישוב)")

st.markdown("---")

if st.button("🚀 אישור גורף לכל התלושים התקינים", type="primary"):
    st.balloons()
    st.success("התלושים נסגרו, הופקו ונשלחו אוטומטית לעובדים!")
