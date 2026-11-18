export const fmtNumber=(v,d=0)=>Number.isFinite(Number(v))?Number(v).toLocaleString("es-MX",{maximumFractionDigits:d,minimumFractionDigits:d}):"—";
export const fmtMWh=v=>`${fmtNumber(v,0)} MWh`;
export const fmtPct=v=>`${fmtNumber(v,2)}%`;
export const monthLabel=p=>{const [y,m]=String(p).split("-");return `${["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][Number(m)-1]||m} ${y}`;};
export const escapeHTML=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
