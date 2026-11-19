# ממשק מעסיקים – דיווח שוטף (גרסה 006): הערות מקור

מקור: דף "קבצי דיווח לגופים מוסדיים" באתר רשות שוק ההון, ביטוח וחיסכון (gov.il/he/departments/dynamiccollectors/gufimmosadiimfiles), נקרא 19.11.2026 בדפדפן.
קבצים רשמיים (גרסה 006), כולם תחת https://www.gov.il/BlobFolder/dynamiccollectorresultitem/info_0030/he/ :
- Employer%20interface%20V%206.xlsx (Excel, סכימת הנתונים)
- mimshak_maasikim_shotef_xsd_schema_006.xsd (דיווח שוטף - הרלוונטי)
- mimshak_maasikim_shliliim_xsd_schema_006.xsd (שלילי), mimshak_maasikim_mesakem_xsd_schema_006.xsd (מסכם), mimshak_maasikim_mesakem_shnati_xsd_schema_006.xsd (מסכם שנתי)

## מבנה ה-XML השוטף (מתוך ה-XSD, שורש MimshakMaasikim)
1. KoteretKovetz: SUG-MIMSHAK=12, MISPAR-GIRSAT-XML=006, TAARICH-BITZUA (YYYYMMDD), KOD-SVIVAT-AVODA (1/2), MISPAR-HAKOVETZ (עד 34), MISPAR-SIDURI, NetuneiGoremSholech (פרטי השולח + איש קשר), NetuneiGoremNimaan (הגוף המוסדי הנמען).
2. GufHamimshak > YeshutGoremPoneLemislaka (חוזר) > PirteiHaavaratKsafim (חוזר): קוד מזהה קופה (30 ספרות), פרטי מפקיד/מעסיק, סכום הפקדה כולל, אמצעי תשלום, תאריך ערך, מספר מזהה (GUID), פרטי חשבון בנק של המעסיק והקולט, ואז PirteiKupa > PirteiOved (חוזר): ת"ז, שם, תאריך לידה, כתובת, מין, מועד תחילת העסקה, סעיף 14, ואז ChodeshMaskoretVestatusOved: חודש משכורת, שכר מדווח, חלקיות משרה, ימי עבודה, ו-PizulHafrashot (סוג הפרשה, שיעור, סכום).
3. ReshumatSgira: סיכומים (מספר קופות, מעסיקים, רשומות, עמיתים, סך הפרשות והפקדות).

## מה חסר במערכת כדי לבנות את הקובץ (לא ממציאים)
קוד מזהה קופה בן 30 ספרות לכל עובד, מספר תיק ניכויים/מזהה מעסיק אצל הגוף המוסדי, פרטי חשבון בנק של המעסיק והקולט, מספר פוליסה/חשבון, מזהה סלקה (GUID), סעיף 14, מין, תאריך תחילת העסקה, וסוגי הפרשה (קוד לכל רכיב). אלה נתונים שהמעסיק מקבל מהגוף המוסדי; יש להוסיף להם שדות בכרטיס העובד/הקופה ולסמן "נדרש טיפול ידני" כשהם חסרים.
