// Gráficas SVG sin dependencias. Cada función devuelve una cadena HTML.
export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export const nf = (v, d = 0) => (v == null || Number.isNaN(v) ? '—' : Number(v).toLocaleString('es-MX', { minimumFractionDigits: d, maximumFractionDigits: d }));

export function niceTicks(min, max, n = 5) {
  if (!(max > min)) { max = min + 1; }
  const raw = (max - min) / n;
  const p = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw);
  const t = [];
  for (let v = Math.floor(min / step) * step; v <= max + step * 0.001; v += step) t.push(+v.toFixed(10));
  return t;
}

const M = { l: 62, r: 14, t: 12, b: 38 };

// series: [{name,color,dash,points:[{x,y,tip}], markers}]  xTicks: [{x,label}]
export function lineChart({ width, height = 300, series, xTicks, xDomain, yLabel, xLabel, aria, yFmt = (v) => nf(v), zeroBase = false }) {
  const w = Math.max(280, width), iw = w - M.l - M.r, ih = height - M.t - M.b;
  const all = series.flatMap((s) => s.points);
  if (!all.length) return '';
  let [x0, x1] = xDomain || [Math.min(...all.map((p) => p.x)), Math.max(...all.map((p) => p.x))];
  if (x1 === x0) x1 = x0 + 1;
  let y0 = zeroBase ? 0 : Math.min(...all.map((p) => p.y)), y1 = Math.max(...all.map((p) => p.y));
  const yt = niceTicks(y0, y1, 5); y0 = Math.min(y0, yt[0]); y1 = yt[yt.length - 1];
  const X = (x) => M.l + ((x - x0) / (x1 - x0)) * iw, Y = (y) => M.t + ih - ((y - y0) / (y1 - y0 || 1)) * ih;
  let g = '';
  for (const t of yt) g += `<line class="grid" x1="${M.l}" x2="${w - M.r}" y1="${Y(t)}" y2="${Y(t)}"/><text class="tick" x="${M.l - 8}" y="${Y(t) + 4}" text-anchor="end">${esc(yFmt(t))}</text>`;
  for (const t of xTicks) g += `<text class="tick" x="${X(t.x)}" y="${height - M.b + 18}" text-anchor="middle">${esc(t.label)}</text>`;
  g += `<line class="axis" x1="${M.l}" x2="${w - M.r}" y1="${M.t + ih}" y2="${M.t + ih}"/>`;
  for (const s of series) {
    const pts = [...s.points].sort((a, b) => a.x - b.x);
    // Un hueco (y nulo) corta la línea
    let d = '', pen = false;
    for (const p of pts) {
      if (p.y == null) { pen = false; continue; }
      d += `${pen ? 'L' : 'M'}${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`; pen = true;
    }
    g += `<path class="ln" d="${d}" stroke="${s.color}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''} fill="none"/>`;
    if (s.markers) for (const p of pts) if (p.y != null) g += `<circle class="pt" cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="3.5" fill="${s.color}"><title>${esc(p.tip || `${s.name}: ${yFmt(p.y)}`)}</title></circle>`;
    else if (pts.length < 400) for (const p of pts) if (p.y != null) g += `<circle class="pt hit" cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="5" fill="${s.color}"><title>${esc(p.tip || `${s.name}: ${yFmt(p.y)}`)}</title></circle>`;
  }
  if (yLabel) g += `<text class="axl" transform="translate(14 ${M.t + ih / 2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text>`;
  if (xLabel) g += `<text class="axl" x="${M.l + iw / 2}" y="${height - 4}" text-anchor="middle">${esc(xLabel)}</text>`;
  return `<svg class="chart" viewBox="0 0 ${w} ${height}" role="img" aria-label="${esc(aria)}">${g}</svg>${legend(series)}`;
}

export function legend(items) {
  return `<ul class="legend">${items.map((s) => `<li><svg width="26" height="10" aria-hidden="true"><line x1="1" x2="25" y1="5" y2="5" stroke="${s.color}" stroke-width="3" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''}/></svg>${esc(s.name)}</li>`).join('')}</ul>`;
}

// groups: [{label, bars:[{name,color,value,tip}]}]
export function barChart({ width, height = 300, groups, yLabel, aria, yFmt = (v) => nf(v) }) {
  const w = Math.max(280, width), iw = w - M.l - M.r, ih = height - M.t - M.b - 14;
  const max = Math.max(...groups.flatMap((g) => g.bars.map((b) => b.value)), 1);
  const yt = niceTicks(0, max, 5), ymax = yt[yt.length - 1];
  const Y = (v) => M.t + ih - (v / ymax) * ih;
  let g = '';
  for (const t of yt) g += `<line class="grid" x1="${M.l}" x2="${w - M.r}" y1="${Y(t)}" y2="${Y(t)}"/><text class="tick" x="${M.l - 8}" y="${Y(t) + 4}" text-anchor="end">${esc(yFmt(t))}</text>`;
  const gw = iw / groups.length;
  groups.forEach((gr, gi) => {
    const bw = Math.min(46, (gw * 0.8) / gr.bars.length), x0 = M.l + gi * gw + (gw - bw * gr.bars.length) / 2;
    gr.bars.forEach((b, bi) => {
      g += `<rect class="bar" x="${x0 + bi * bw + 1}" y="${Y(b.value)}" width="${bw - 2}" height="${M.t + ih - Y(b.value)}" fill="${b.color}" rx="2"><title>${esc(b.tip || `${b.name}: ${yFmt(b.value)}`)}</title></rect>`;
    });
    g += `<text class="tick" x="${M.l + gi * gw + gw / 2}" y="${M.t + ih + 18}" text-anchor="middle">${esc(gr.label)}</text>`;
  });
  g += `<line class="axis" x1="${M.l}" x2="${w - M.r}" y1="${M.t + ih}" y2="${M.t + ih}"/>`;
  if (yLabel) g += `<text class="axl" transform="translate(14 ${M.t + ih / 2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text>`;
  const names = [...new Map(groups.flatMap((gr) => gr.bars).map((b) => [b.name, b])).values()];
  return `<svg class="chart" viewBox="0 0 ${w} ${height}" role="img" aria-label="${esc(aria)}">${g}</svg><ul class="legend">${names.map((b) => `<li><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" rx="2" fill="${b.color}"/></svg>${esc(b.name)}</li>`).join('')}</ul>`;
}

// cells: Map "row|col" -> {v, partial}; rows: periodos; cols: 0..23
export function heatmap({ width, rows, cells, aria, unit, rowLabel = (r) => r }) {
  const w = Math.max(300, width), lm = 74, rm = 12, tm = 8, cw = (w - lm - rm) / 24, rh = 22;
  const vals = [...cells.values()].map((c) => c?.v).filter(Number.isFinite);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const color = (v) => { const t = hi > lo ? (v - lo) / (hi - lo) : 0; return `hsl(168 ${35 + t * 45}% ${95 - t * 68}%)`; };
  let g = '';
  rows.forEach((r, ri) => {
    const part = cells.get(`${r}|partial`);
    g += `<text class="tick" x="${lm - 8}" y="${tm + ri * rh + 15}" text-anchor="end">${esc(rowLabel(r))}${part ? ' ◩' : ''}</text>`;
    for (let h = 0; h < 24; h++) {
      const c = cells.get(`${r}|${h}`);
      if (!c) { g += `<rect x="${lm + h * cw}" y="${tm + ri * rh}" width="${cw - 1}" height="${rh - 1}" class="hm-empty"/>`; continue; }
      g += `<rect x="${lm + h * cw}" y="${tm + ri * rh}" width="${cw - 1}" height="${rh - 1}" fill="${color(c.v)}" ${c.partial ? 'class="hm-partial"' : ''}><title>${esc(`${rowLabel(r)} · ${String(h).padStart(2, '0')}:00 · ${nf(c.v, 3)} ${unit}${c.partial ? ' · periodo parcial' : ''}`)}</title></rect>`;
    }
  });
  const hh = tm + rows.length * rh;
  for (let h = 0; h < 24; h += 3) g += `<text class="tick" x="${lm + h * cw + cw / 2}" y="${hh + 16}" text-anchor="middle">${String(h).padStart(2, '0')}</text>`;
  const bar = `<div class="scale" aria-hidden="true"><span>${nf(lo, 2)}</span><i style="background:linear-gradient(90deg,${color(lo)},${color((lo + hi) / 2)},${color(hi)})"></i><span>${nf(hi, 2)} ${esc(unit)}</span></div>`;
  return `<svg class="chart" viewBox="0 0 ${w} ${hh + 26}" role="img" aria-label="${esc(aria)}">${g}</svg>${bar}`;
}

// points: [{x, y, r, label, state_code, tip, color, isDc, isSelected, showLabel}]
export function scatterChart({
  width,
  height = 340,
  points,
  xLabel = 'Densidad estimada (hab./mi²)',
  yLabel = 'Ventas por habitante (kWh/hab)',
  aria = 'Dispersión de ventas por habitante frente a densidad poblacional',
  xDomain,
  yDomain,
  yFmt = (v) => nf(v),
  xFmt = (v) => nf(v),
}) {
  const w = Math.max(300, width), iw = w - M.l - M.r, ih = height - M.t - M.b;
  if (!points || !points.length) return '';
  let [x0, x1] = xDomain || [0, Math.max(...points.map((p) => p.x)) * 1.05];
  if (x1 === x0) x1 = x0 + 1;
  let [y0, y1] = yDomain || [0, Math.max(...points.map((p) => p.y)) * 1.08];
  if (y1 === y0) y1 = y0 + 1;

  // Extiende los ticks hasta cubrir el máximo para que ningún punto quede fuera del área.
  const cover = (t, hi) => { const st = t[1] - t[0]; while (st > 0 && t[t.length - 1] < hi) t.push(+(t[t.length - 1] + st).toFixed(10)); return t; };
  const xt = cover(niceTicks(x0, x1, 5), x1);
  x0 = xt[0]; x1 = xt[xt.length - 1];
  const yt = cover(niceTicks(y0, y1, 5), y1);
  y0 = yt[0]; y1 = yt[yt.length - 1];

  const X = (x) => M.l + ((x - x0) / (x1 - x0 || 1)) * iw;
  const Y = (y) => M.t + ih - ((y - y0) / (y1 - y0 || 1)) * ih;

  let g = '';
  for (const t of yt) {
    g += `<line class="grid" x1="${M.l}" x2="${w - M.r}" y1="${Y(t)}" y2="${Y(t)}"/><text class="tick" x="${M.l - 8}" y="${Y(t) + 4}" text-anchor="end">${esc(yFmt(t))}</text>`;
  }
  for (const t of xt) {
    g += `<line class="grid" x1="${X(t)}" x2="${X(t)}" y1="${M.t}" y2="${M.t + ih}" stroke-dasharray="3 3"/><text class="tick" x="${X(t)}" y="${height - M.b + 18}" text-anchor="middle">${esc(xFmt(t))}</text>`;
  }
  g += `<line class="axis" x1="${M.l}" x2="${w - M.r}" y1="${M.t + ih}" y2="${M.t + ih}"/>`;
  g += `<line class="axis" x1="${M.l}" x2="${M.l}" y1="${M.t}" y2="${M.t + ih}"/>`;

  for (const p of points) {
    const cx = X(p.x);
    const cy = Y(p.y);
    const baseRad = p.r || 5;
    const rad = p.isSelected ? baseRad + 3 : (p.isDc ? baseRad + 1 : baseRad);
    const fill = p.color || (p.isSelected ? '#0f8a6d' : (p.isDc ? '#d98a1f' : '#2b8fc4'));
    const stroke = p.isSelected ? '#0b6f58' : (p.isDc ? '#92400e' : '#1e3a8a');
    const strokeWidth = p.isSelected ? 2.5 : 1.2;

    if (p.isDc) {
      g += `<polygon points="${cx},${cy - rad - 2} ${cx + rad + 2},${cy} ${cx},${cy + rad + 2} ${cx - rad - 2},${cy}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" opacity="0.95"><title>${esc(p.tip)}</title></polygon>`;
      g += `<text x="${cx + rad + 4}" y="${cy + 4}" font-size="11" font-weight="700" fill="${stroke}">${esc(p.label || p.state_code)}</text>`;
    } else {
      g += `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${rad}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" opacity="0.85"><title>${esc(p.tip)}</title></circle>`;
      if (p.isSelected || p.showLabel) {
        g += `<text x="${cx + rad + 3}" y="${cy + 4}" font-size="11" font-weight="${p.isSelected ? '700' : '600'}" fill="${stroke}">${esc(p.label || p.state_code)}</text>`;
      }
    }
  }

  if (yLabel) g += `<text class="axl" transform="translate(14 ${M.t + ih / 2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text>`;
  if (xLabel) g += `<text class="axl" x="${M.l + iw / 2}" y="${height - 4}" text-anchor="middle">${esc(xLabel)}</text>`;

  return `<svg class="chart" viewBox="0 0 ${w} ${height}" role="img" aria-label="${esc(aria)}">${g}</svg>`;
}
