const COLORS=["#3d7bfd","#12a88a","#f59e0b","#8b5cf6","#ef5b5b"];
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
export function lineChart(series,{labels=[],unit="",height=250}={}){
  const all=series.flatMap(s=>s.values).filter(Number.isFinite);if(!all.length)return `<div class="empty">No hay datos suficientes para esta gráfica.</div>`;
  const min=Math.min(0,...all),max=Math.max(...all)*1.08||1,w=760,h=height,p={l:54,r:16,t:16,b:36},pw=w-p.l-p.r,ph=h-p.t-p.b;
  const x=i=>p.l+(series[0].values.length<=1?pw/2:i*pw/(series[0].values.length-1));
  const y=v=>p.t+ph-(v-min)/(max-min||1)*ph;
  let svg=`<svg viewBox="0 0 ${w} ${h}" role="img">`;
  for(let k=0;k<5;k++){const v=min+(max-min)*k/4,yy=y(v);svg+=`<line x1="${p.l}" y1="${yy}" x2="${w-p.r}" y2="${yy}" stroke="#e8edf3"/><text x="${p.l-8}" y="${yy+4}" text-anchor="end" font-size="10" fill="#8491a2">${Math.round(v).toLocaleString("es-MX")}</text>`;}
  labels.forEach((label,i)=>{if(labels.length<=12||i%Math.ceil(labels.length/12)===0)svg+=`<text x="${x(i)}" y="${h-10}" text-anchor="middle" font-size="10" fill="#8491a2">${esc(label)}</text>`;});
  series.forEach((s,j)=>{const pts=s.values.map((v,i)=>`${x(i)},${y(v)}`).join(" ");svg+=`<polyline fill="none" stroke="${COLORS[j%COLORS.length]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${pts}"/>`;s.values.forEach((v,i)=>svg+=`<circle cx="${x(i)}" cy="${y(v)}" r="3" fill="${COLORS[j%COLORS.length]}"/>`);});
  svg+="</svg>";return svg;
}
export function barChart(labels,values,{height=250}={}){
  const good=values.filter(v=>Number.isFinite(v));if(!good.length)return `<div class="empty">No hay datos para graficar.</div>`;
  const w=760,h=height,p={l:48,r:12,t:16,b:44},pw=w-p.l-p.r,ph=h-p.t-p.b,max=Math.max(...good)*1.1||1,bw=Math.min(30,pw/labels.length*.58);
  let svg=`<svg viewBox="0 0 ${w} ${h}">`;
  for(let k=0;k<5;k++){let v=max*k/4,yy=p.t+ph-v/max*ph;svg+=`<line x1="${p.l}" y1="${yy}" x2="${w-p.r}" y2="${yy}" stroke="#e8edf3"/><text x="${p.l-6}" y="${yy+3}" text-anchor="end" font-size="10" fill="#8491a2">${Math.round(v)}</text>`;}
  values.forEach((v,i)=>{if(!Number.isFinite(v))return;const x=p.l+(i+.5)*pw/labels.length,y=p.t+ph-v/max*ph;svg+=`<rect x="${x-bw/2}" y="${y}" width="${bw}" height="${p.t+ph-y}" rx="4" fill="${COLORS[i%COLORS.length]}"/><text x="${x}" y="${h-12}" text-anchor="middle" font-size="10" fill="#8491a2">${esc(labels[i])}</text>`;});
  return svg+"</svg>";
}
