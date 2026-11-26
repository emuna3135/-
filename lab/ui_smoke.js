// בדיקת ציור מסך "הצג חישוב" ב-jsdom: CALC_JSON=קובץ שנוצר ע"י DUMP_CALC ב-e2e_smoke.py; דורש npm i jsdom
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
const data=JSON.parse(fs.readFileSync(process.env.CALC_JSON,'utf8'));
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",beforeParse(w){
  w.fetch=async(u,o)=>{const j=u.includes('/calculation')?data.calc:u.includes('/employees')?data.emps:{};return {ok:true,status:200,headers:{get:()=>null},json:async()=>j}};
}});
const w=dom.window;
setTimeout(async()=>{
  try{
    w.eval('state.token="x";state.user="בדיקה";state.companies=[{id:"c1",name:"בדיוני"}];state.companyId="c1";render("showcalc")');
    await new Promise(r=>setTimeout(r,200));
    const sel=w.document.querySelector('select'); sel.value=sel.options[1].value;
    [...w.document.querySelectorAll('button')].find(b=>b.textContent==='הצג חישוב'&&!b.classList.contains('nav')).click();
    await new Promise(r=>setTimeout(r,300));
    const t=w.document.body.textContent;
    const navs=[...w.document.querySelectorAll('nav .nav')].map(b=>b.textContent).slice(0,5);
    console.log('NAV',navs.join(' | '));
    for(const k of ['עובד בדיוני 0','1. שכר ברוטו','מס הכנסה','עפ"י החוק','תיקון ידני','7. הערות ומקורות','8,144.69','3.25']) console.log(t.includes(k)?'OK ':'MISSING',k);
  }catch(e){console.log('ERR',e.message)}
  process.exit(0);
},300);
