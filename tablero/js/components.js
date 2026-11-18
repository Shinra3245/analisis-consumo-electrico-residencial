export const card=(title,body,subtitle="")=>`<article class="card"><div class="card-head"><div><h2 class="card-title">${title}</h2>${subtitle?`<div class="card-subtitle">${subtitle}</div>`:""}</div></div>${body}</article>`;
export const metric=(label,value,note="")=>`<article class="card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-note">${note}</div></article>`;
export const notice=(text,type="info")=>`<div class="notice ${type}">${text}</div>`;
export const table=(headers,rows)=>`<div class="table-wrap"><table class="table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((v,i)=>`<td class="${i>0?"numeric":""}">${v}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
