import { DATA_BASE, SCHEMA_VERSION, TABLES } from './config.js';
import { loadAll, store, rowsOf, statusOf, ensureTable } from './data.js';
import { esc, nf, lineChart, barChart, heatmap } from './charts.js';
import { isoHouse } from './iso.js';

/* ---------- vistas ---------- */
const ico = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const VIEWS = [
  { id: 'resumen', label: 'Resumen', icon: ico('<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'), q: '¿Qué datos hay, de qué fuente y qué tan grande es el consumo residencial?' },
  { id: 'patrones', label: 'Patrones', icon: ico('<path d="M3 17l5-6 4 3 5-8 4 5"/><path d="M3 21h18"/>'), q: '¿Cómo varía el consumo por mes, hora y tipo de vivienda?' },
  { id: 'clima', label: 'Clima', icon: ico('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>'), q: '¿Qué información climática hay y por qué todavía no se une al consumo?' },
  { id: 'anomalias', label: 'Anomalías', icon: ico('<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.5"/>'), q: '¿Qué es un comportamiento atípico, cómo se detecta y qué tan bien funciona el método?' },
  { id: 'estimaciones', label: 'Estimaciones', icon: ico('<path d="M3 20V8M9 20V4M15 20v-9M21 20V12"/>'), q: '¿Cuánto consumo residencial se esperaría y qué error tuvo el método en meses ya conocidos?' },
  { id: 'calidad', label: 'Flujo/Calidad', icon: ico('<path d="M5 4h14v6H5zM5 14h14v6H5z"/><path d="M8 7h.01M8 17h.01"/>'), q: '¿De dónde viene cada cifra, qué cobertura tiene y qué controles pasó?' },
];
const state = { view: 'resumen', st: 'CO', from: null, to: null, type: 'ALL', source: 'ALL', gran: 'monthly', prelim: true, profile: null, day: 'weekday', tz: null };
const $ = (s) => document.querySelector(s);
const SRC = {
  eia: { cls: 'eia', name: 'EIA-861M', kind: 'oficial' },
  res: { cls: 'res', name: 'ResStock AMY 2018', kind: 'modelado' },
  clim: { cls: 'clim', name: 'Open-Meteo ERA5-Land', kind: 'reanálisis' },
};
const chip = (src, parts) => { const s = SRC[src]; return `<span class="chip ${s.cls}"><i></i><b>${esc(s.name)}</b> · ${esc(s.kind)}${parts.map((p) => ` · ${esc(p)}`).join('')} · esquema ${SCHEMA_VERSION}</span>`; };
const preChip = (t) => `<span class="chip pre"><b>Preliminar</b> · ${esc(t)}</span>`;
const stateName = (s) => (s === 'ALL' ? 'Suma 51 jurisdicciones' : s);
const cmp = (v) => (Math.abs(v) >= 1e6 ? `${nf(v / 1e6, v % 1e6 ? 1 : 0)} M` : Math.abs(v) >= 1e4 ? `${nf(v / 1e3)} mil` : nf(v));
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const inRange = (p) => p >= state.from && p <= state.to; // p = 'YYYY-MM'

/* ---------- datos derivados ---------- */
let eiaIdx = null; // Map state -> Map period -> {mwh, status}
function buildEia() {
  const rows = rowsOf('gold_eia_monthly');
  if (!rows) return (eiaIdx = null);
  eiaIdx = new Map();
  const all = new Map();
  for (const r of rows) {
    if (!eiaIdx.has(r.state_code)) eiaIdx.set(r.state_code, new Map());
    eiaIdx.get(r.state_code).set(r.period, { mwh: +r.sales_mwh, status: r.data_status });
    const a = all.get(r.period) || { mwh: 0, status: 'Final', n: 0 };
    a.mwh += +r.sales_mwh; a.n++;
    if (r.data_status !== 'Final') a.status = 'Preliminary';
    all.set(r.period, a);
  }
  eiaIdx.set('ALL', all);
}
const eiaStates = () => (eiaIdx ? [...eiaIdx.keys()].filter((k) => k !== 'ALL').sort() : []);
/** Serie EIA del estado seleccionado, respetando periodo y el conmutador de preliminares. */
function eiaSeries() {
  const m = eiaIdx?.get(state.st);
  if (!m) return [];
  return [...m.entries()].filter(([p, v]) => inRange(p) && (state.prelim || v.status === 'Final'))
    .map(([period, v]) => ({ period, ...v })).sort((a, b) => (a.period < b.period ? -1 : 1));
}
const resSummary = () => rowsOf('gold_resstock_profile_summary');
const resStates = () => [...new Set((resSummary() || []).map((r) => r.state_code))].sort();
const resTypes = () => [...new Set((resSummary() || []).filter((r) => state.st === 'ALL' || r.state_code === state.st).map((r) => r.housing_type))].sort();
const profiles = () => (resSummary() || []).filter((r) => (state.st === 'ALL' || r.state_code === state.st) && (state.type === 'ALL' || r.housing_type === state.type))
  .sort((a, b) => (a.state_code + a.housing_type < b.state_code + b.housing_type ? -1 : 1));
function currentProfile() {
  const ps = profiles();
  if (state.profile && state.profile !== 'ALL') {
    return ps.find((p) => String(p.bldg_id) === String(state.profile)) || ps[0] || null;
  }
  return ps[0] || null;
}
const climRows = () => (rowsOf('gold_climate') || []).filter((r) => (state.st === 'ALL' || r.state_code === state.st) && inRange(r.timestamp_utc.slice(0, 7)));
const periodBounds = () => {
  const ps = eiaIdx ? [...eiaIdx.get('ALL').keys()].sort() : [];
  return ps.length ? [ps[0], ps[ps.length - 1]] : ['2018-01', '2026-08'];
};

/* ---------- componentes ---------- */
const charts = [];
let uid = 0;
function slot(fn, aria) {
  const id = `ch${uid++}`;
  charts.push({ id, fn });
  return `<div class="chart-slot" id="${id}"><div class="skel" role="status" aria-label="Cargando gráfica"></div></div>`;
}
function dataTable(head, rows, max = 80) {
  const body = rows.slice(0, max).map((r) => `<tr>${r.map((c, i) => `<td${typeof c === 'number' ? ' class="n"' : ''}>${typeof c === 'number' ? nf(c, 2) : esc(c)}</td>`).join('')}</tr>`).join('');
  return `<details class="data"><summary>Ver datos de la gráfica (${rows.length} filas${rows.length > max ? `, primeras ${max}` : ''})</summary><div class="tbl-wrap"><table class="t"><thead><tr>${head.map((h) => `<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></div></details>`;
}
const card = ({ id, q, accent = 'none', body, chips = '', limit = '', cls = '' }) => `<section class="card accent-${accent} ${cls}" ${id ? `aria-labelledby="h-${id}"` : ''}>${id ? `<span class="cid">${id}</span>` : ''}<h2 id="h-${id}">${esc(q)}</h2>${body}${chips ? `<div class="chips">${chips}</div>` : ''}${limit ? `<p class="limit">${limit}</p>` : ''}</section>`;
const empty = (title, text, extra = '', err = false) => `<div class="empty ${err ? 'err' : ''}" role="status"><strong>${esc(title)}</strong>${text}${extra}</div>`;
const pendingTables = (names) => `<ul>${names.map((n) => `<li><code>${n}</code> — ${statusLabel(n)}</li>`).join('')}</ul>`;
function statusLabel(n) {
  const s = store.tables[n];
  if (!s) return store.entries?.[n] ? 'listada en el manifiesto; esta versión del tablero aún no la grafica' : 'no entregada todavía';
  if (s.status === 'lazy') return 'bajo demanda (inspección individual)';
  if (s.status === 'loading') return 'cargando…';
  return { ok: 'cargada', pending: 'no entregada todavía', error: s.message }[s.status] || s.status;
}
/** Estado vacío/err de una o varias tablas requeridas. Devuelve null si todo está disponible. */
function needTables(names, what) {
  const bad = names.filter((n) => statusOf(n) !== 'ok');
  if (!bad.length) return null;
  const loading = bad.some((n) => statusOf(n) === 'loading');
  if (loading) return empty(`Cargando datos de ${what}…`, 'Descargando datos y verificando integridad contra manifiesto.');
  const err = bad.some((n) => statusOf(n) === 'error');
  return empty(err ? `No se pudo cargar los datos de ${what}` : `${what[0].toUpperCase()}${what.slice(1)}: esperando datos`,
    err ? 'Falló la lectura o validación; no se muestran cifras.' : 'El bloque de datos aún no entrega esta tabla; no se muestran cifras de relleno.', pendingTables(bad), err);
}
const noResState = () => empty(`No hay perfiles ResStock para ${state.st === 'ALL' ? 'este filtro' : state.st}${state.type !== 'ALL' ? ` · ${state.type}` : ''} en el piloto`,
  `Disponibles: ${resStates().join(', ') || '—'}${state.type !== 'ALL' ? '. Prueba con “Todos” en tipo de vivienda.' : '.'}`);

/* ---------- Resumen ---------- */
function viewResumen() {
  const showAll = state.source === 'ALL';
  const out = [];
  // Hero isométrico
  const p = currentProfile();
  const ht = p?.housing_type;
  const heroMeta = p
    ? `<p class="eyebrow">Perfil modelado ResStock · #${esc(p.bldg_id)}</p><h2 style="margin:0;font-size:22px">${esc(p.housing_type)} · ${esc(p.state_code)}</h2>
       <p class="sub">Año fuente ${esc(p.source_year)} (calendario EST fijo) · ${nf(p.n_hours)} horas.</p>
       <dl class="kv"><div><dt>Consumo anual</dt><dd>${nf(p.annual_kwh)} kWh</dd></div><div><dt>Promedio horario</dt><dd>${nf(p.mean_hour_kwh, 2)} kWh</dd></div><div><dt>Pico horario</dt><dd>${nf(p.peak_hour_kwh, 2)} kWh</dd></div></dl>
       <div class="chips">${chip('res', ['kWh', `${p.source_year}`, 'modelo de 1 vivienda'])}</div>`
    : `<p class="eyebrow">Ilustración conceptual</p><h2 style="margin:0;font-size:20px">Sin perfil ResStock para este filtro</h2>
       <p class="sub">${statusOf('gold_resstock_profile_summary') === 'ok' ? `El piloto solo incluye ${esc(resStates().join(', '))}. ` : 'La tabla de perfiles aún no está disponible. '}Se muestra una vivienda genérica sin cifras.</p>`;
  out.push(`<section class="card hero grid" style="margin:0 0 16px;display:grid" aria-label="Vivienda ilustrativa"><div class="iso-wrap" key="${esc(ht || 'x')}${esc(p?.bldg_id || '')}">${isoHouse(ht)}<p class="sub" style="text-align:center;margin:0">Ilustración conceptual del tipo de vivienda: no es un plano ni muestra consumo por habitación.</p></div><div class="meta">${heroMeta}</div></section>`);

  const cards = [];
  if (showAll || state.source === 'eia') {
    const s = eiaSeries();
    const e = needTables(['gold_eia_monthly'], 'ventas EIA');
    if (e) cards.push(card({ id: 'R1a', q: 'Ventas residenciales EIA', accent: 'eia', body: e }));
    else if (!s.length) cards.push(card({ id: 'R1a', q: 'Ventas residenciales EIA', accent: 'eia', body: empty('Sin datos EIA para el filtro', `No hay meses de ${esc(stateName(state.st))} entre ${state.from} y ${state.to}${state.prelim ? '' : ' con preliminares ocultos'}.`) }));
    else {
      const byYear = new Map();
      for (const r of s) { const y = r.period.slice(0, 4); (byYear.get(y) || byYear.set(y, []).get(y)).push(r); }
      const years = [...byYear.keys()].sort();
      const full = years.filter((y) => byYear.get(y).length === 12);
      const y = full.length ? full[full.length - 1] : years[years.length - 1];
      const rows = byYear.get(y), tot = rows.reduce((a, r) => a + r.mwh, 0), pre = rows.filter((r) => r.status !== 'Final').length;
      cards.push(card({
        id: 'R1a', q: `Ventas residenciales EIA ${y}`, accent: 'eia',
        body: `<div class="big">${nf(tot)}<span class="unit">MWh</span></div><p class="sub">${esc(stateName(state.st))} · ${rows.length === 12 ? 'año completo' : `<strong>parcial: ${rows.length} de 12 meses</strong>`}${pre ? ` · incluye ${pre} meses preliminares` : ''}</p>`,
        chips: chip('eia', ['MWh', `${rows[0].period}…${rows[rows.length - 1].period}`, state.st === 'ALL' ? '51 jurisdicciones' : state.st]) + (pre ? preChip('puede cambiar') : ''),
        limit: 'Ventas de electricidad al sector residencial (todo el estado), no consumo medido por hogar.',
      }));
      const fin = s.filter((r) => r.status === 'Final').length, prel = s.length - fin;
      cards.push(card({
        id: 'R1b', q: 'Cobertura de meses EIA', accent: 'eia',
        body: `<div class="big">${nf(fin)}<span class="unit">finales</span></div><p class="sub">${nf(prel)} preliminares en el rango ${state.from}…${state.to}${state.prelim ? '' : ' (ocultos por el filtro)'}.</p>`,
        chips: chip('eia', ['meses', `${state.from}…${state.to}`]), limit: 'Los meses faltantes por año están en Flujo/Calidad (Q1).',
      }));
    }
  }
  if (showAll || state.source === 'res') {
    const e = needTables(['gold_resstock_profile_summary'], 'perfiles ResStock');
    if (e) cards.push(card({ id: 'R1c', q: 'Perfiles ResStock en el piloto', accent: 'res', body: e }));
    else {
      const total = rowsOf('gold_resstock_profile_summary').length, ps = profiles();
      cards.push(card({
        id: 'R1c', q: 'Perfiles ResStock en el piloto', accent: 'res',
        body: `<div class="big">${nf(ps.length)}<span class="unit">de ${nf(total)} perfiles</span></div><p class="sub">${esc(state.st === 'ALL' ? 'Todos los estados del piloto' : state.st)}${state.type === 'ALL' ? '' : ` · ${esc(state.type)}`}. Perfiles descargados, no un conteo de viviendas.</p>`,
        chips: chip('res', ['perfiles', resStates().join('/')]), limit: 'Son perfiles modelados exploratorios; no representan al estado ni al país.',
      }));
    }
  }
  if (showAll || state.source === 'clim') {
    const e = needTables(['gold_climate'], 'clima');
    if (e) cards.push(card({ id: 'R1d', q: 'Clima disponible', accent: 'clim', body: e }));
    else {
      const all = rowsOf('gold_climate'), pts = new Set(all.map((r) => r.point_id)), ts = all.map((r) => r.timestamp_utc).sort();
      cards.push(card({
        id: 'R1d', q: 'Clima disponible', accent: 'clim',
        body: `<div class="big">${pts.size}<span class="unit">puntos</span></div><p class="sub">${ts[0].slice(0, 10)} a ${ts[ts.length - 1].slice(0, 10)} (UTC), ${nf(all.length)} lecturas horarias. Solo ${[...new Set(all.map((r) => r.state_code))].join(', ')}.</p>`,
        chips: chip('clim', ['°C', 'horario UTC']), limit: 'Celdas de reanálisis, no estaciones. No se une al consumo.',
      }));
    }
  }
  if (showAll) {
    const fc = store.manifest?.analytics?.forecast;
    cards.push(card({
      id: 'R1e', q: 'Error del mejor pronóstico (sMAPE)', accent: 'none',
      body: fc ? `<div class="big">${nf(fc.median_model_smape_pct, 2)}<span class="unit">%</span></div><p class="sub">Mediana en ${nf(fc.state_count)} estados; gana a la línea base estacional en ${nf(fc.states_model_beats_naive)} estados.</p>` : empty('Pendiente', 'No hay un backtest Gold disponible.'),
      chips: fc ? chip('eia', ['sMAPE', `${fc.holdout[0]}…${fc.holdout[1]}`, 'backtest']) : '',
      limit: 'Resultado histórico de evaluación; no es una proyección del consumo futuro.',
    }));
  }
  out.push(`<div class="grid g4">${cards.join('')}</div>`);

  // R2: cobertura, sin razón
  if (showAll || state.source === 'eia' || state.source === 'res') {
    const co = eiaIdx?.get('CO');
    const tot = co ? [...co.entries()].filter(([p]) => p.startsWith('2018')) : [];
    out.push(card({
      id: 'R2', q: '¿Se pueden comparar ResStock y EIA en Colorado 2018?', accent: 'none',
      body: `${empty('Razón descriptiva no calculada', 'La cifra 87.16 % no se ha reproducido desde su agregado fuente y no se publica como resultado. ResStock contiene perfiles modelados de muestra; EIA informa ventas del sector residencial completo. Son coberturas distintas y la razón no es una medida de precisión.')}
      <div class="tbl-wrap" style="max-height:none"><table class="t"><caption class="sr">Cobertura de cada fuente</caption><thead><tr><th scope="col">Fuente</th><th scope="col">Población</th><th scope="col">Periodo</th><th scope="col">Cobertura</th></tr></thead><tbody>
      <tr><td>${chip('eia', [])}</td><td>Ventas de todo el estado (CO)</td><td>2018</td><td>${tot.length ? `${tot.length} meses · ${nf(tot.reduce((a, [, v]) => a + v.mwh, 0))} MWh` : 'sin datos'}</td></tr>
      <tr><td>${chip('res', [])}</td><td>${(() => { const n = (resSummary() || []).filter((r) => r.state_code === 'CO').length; return n ? `${n} perfiles modelados de CO (no solo unifamiliar aislada)` : 'perfiles piloto no disponibles'; })()}</td><td>2018 (EST fijo)</td><td>Piloto exploratorio; sin ponderación válida</td></tr></tbody></table></div>`,
      limit: 'Poblaciones y definiciones distintas: no se comparan sumas de los dos conjuntos.',
    }));
  }
  return out.join('');
}

/* ---------- Patrones ---------- */
const YCOL = ['#c9dcf7', '#a8c5f0', '#86addf', '#6595d3', '#437dc4', '#2b67b5', '#1e55a0', '#16427e', '#0c2d5a'];
const TYPE_COL = { 'Single-Family Detached': '#0f8a6d', 'Single-Family Attached': '#6d4fd1', 'Mobile Home': '#d98a1f', 'Multi-Family with 2 - 4 Units': '#2b8fc4', 'Multi-Family with 5+ Units': '#6b7280' };
const typeCol = (t) => TYPE_COL[t] || '#6b7280';

function viewPatrones() {
  const out = [];
  const isIndividual = Boolean(state.profile && state.profile !== 'ALL');
  const p = currentProfile();
  const heroHt = isIndividual ? p?.housing_type : (state.type !== 'ALL' ? state.type : p?.housing_type);
  const heroTitle = isIndividual
    ? `${esc(p?.housing_type || '')} · ${esc(p?.state_code || '')}`
    : (state.type !== 'ALL' ? `${esc(state.type)} · ${esc(state.st === 'ALL' ? 'Muestra general' : state.st)}` : `Patrones horarios agregados · ${esc(state.st === 'ALL' ? 'Todos los estados' : state.st)}`);
  const heroSub = isIndividual
    ? `Inspección individual: perfil modelado #${esc(p?.bldg_id)}. Mostrando datos específicos de este edificio.`
    : `Agregado Gold de la muestra por estrato físico. Mantiene acotado el volumen en el navegador al escalar la muestra. Selecciona un perfil para inspección individual.`;
  const heroChip = isIndividual
    ? (p ? chip('res', ['kWh', 'perfil piloto', 'inspección individual']) : '')
    : chip('res', ['kWh', 'agregado Gold', 'muestra modelada']);
  const hero = `<section class="card hero" style="margin-bottom:16px" aria-label="Vivienda ilustrativa"><div class="iso-wrap">${isoHouse(heroHt)}</div><div class="meta"><p class="eyebrow">${isIndividual ? 'Inspección individual de perfil' : 'Ilustración conceptual · Agregado Gold'}</p><h2 style="margin:0;font-size:20px">${heroTitle}</h2><p class="sub">${heroSub}</p><div class="chips">${heroChip}</div></div></section>`;
  out.push(hero);
  if (state.gran === 'monthly') {
    out.push('<div class="grid g2">' + patternP1() + patternP1b() + '</div>' + patternP3());
  } else out.push(patternP2());
  return out.join('');
}

function patternP1() {
  const e = needTables(['gold_eia_monthly'], 'ventas EIA');
  const base = { id: 'P1', q: '¿Cómo es la estacionalidad de las ventas residenciales y cómo cambió por año?', accent: 'eia' };
  if (e) return card({ ...base, body: e });
  const s = eiaSeries();
  if (!s.length) return card({ ...base, body: empty('Sin datos EIA para el filtro', `No hay meses de ${esc(stateName(state.st))} entre ${state.from} y ${state.to}.`) });
  const by = new Map();
  for (const r of s) (by.get(r.period.slice(0, 4)) || by.set(r.period.slice(0, 4), []).get(r.period.slice(0, 4))).push(r);
  const years = [...by.keys()].sort();
  const series = years.map((y, i) => {
    const rows = by.get(y), pre = rows.some((r) => r.status !== 'Final');
    return { name: `${y}${pre ? ' (preliminar)' : ''}`, color: YCOL[Math.min(YCOL.length - 1, Math.round((i / Math.max(1, years.length - 1)) * (YCOL.length - 1)))], dash: pre ? '6 4' : '',
      points: rows.map((r) => ({ x: +r.period.slice(5), y: r.mwh, tip: `${r.period} · ${nf(r.mwh)} MWh · ${r.status === 'Final' ? 'Final' : 'Preliminar, puede cambiar'}` })) };
  });
  const peak = s.reduce((a, r) => (r.mwh > a.mwh ? r : a));
  const aria = `Líneas de ventas mensuales en MWh por año para ${stateName(state.st)}; el máximo es ${nf(peak.mwh)} MWh en ${peak.period}.`;
  const pre = s.some((r) => r.status !== 'Final');
  return card({
    ...base,
    body: slot((w) => lineChart({ width: w, series, xTicks: MES.map((m, i) => ({ x: i + 1, label: m })), xDomain: [1, 12], yLabel: 'MWh', aria, yFmt: cmp })) + `<p class="sub">${esc(aria)}</p>` + dataTable(['Periodo', 'Estado', 'MWh', 'Publicación'], s.map((r) => [r.period, state.st, r.mwh, r.status])),
    chips: chip('eia', ['MWh', `${s[0].period}…${s[s.length - 1].period}`, state.st === 'ALL' ? '51 jurisdicciones' : state.st]) + (pre ? preChip('línea punteada') : ''),
    limit: 'Muestra ventas, no consumo medido por hogar.',
  });
}

function patternP1b() {
  const base = { id: 'P1b', q: '¿Cómo varía por mes el consumo de cada perfil modelado?', accent: 'res' };
  const e = needTables(['gold_resstock_monthly', 'gold_resstock_profile_summary'], 'perfiles ResStock');
  if (e) return card({ ...base, body: e });
  const ps = profiles();
  if (!ps.length) return card({ ...base, body: noResState() });
  const ids = new Set(ps.map((x) => String(x.bldg_id)));
  const rows = rowsOf('gold_resstock_monthly').filter((r) => ids.has(String(r.bldg_id)) && inRange(r.source_period));
  if (!rows.length) return card({ ...base, body: empty('Sin datos ResStock en el periodo', `El piloto cubre 2018; el rango ${state.from}…${state.to} no lo intersecta.`) });
  const series = ps.map((x) => ({ name: `${x.housing_type} (${x.state_code})`, color: typeCol(x.housing_type), markers: true,
    points: rows.filter((r) => String(r.bldg_id) === String(x.bldg_id)).map((r) => ({ x: +r.source_period.slice(5), y: +r.kwh_month, tip: `#${x.bldg_id} · ${r.source_period} · ${nf(r.kwh_month)} kWh` })) })).filter((s) => s.points.length);
  const aria = `Consumo mensual modelado en kWh de ${series.length} perfil(es) de ${state.st === 'ALL' ? 'los estados del piloto' : state.st}, calendario fuente EST.`;
  return card({
    ...base,
    body: slot((w) => lineChart({ width: w, series, xTicks: MES.map((m, i) => ({ x: i + 1, label: m })), xDomain: [1, 12], yLabel: 'kWh por mes', aria, yFmt: cmp })) + `<p class="sub">${esc(aria)}</p>` + dataTable(['Perfil', 'Mes fuente', 'kWh'], rows.map((r) => [`#${r.bldg_id} ${r.housing_type}`, r.source_period, +r.kwh_month])),
    chips: chip('res', ['kWh', 'mensual', `${ps.length} perfiles`, 'calendario fuente EST']),
    limit: 'Un perfil por tipo y estado: exploratorio. El mes sigue el calendario del release, no el mes civil local.',
  });
}

function patternP3() {
  const base = { id: 'P3', q: '¿Cómo difiere el consumo anual entre tipos de vivienda?', accent: 'res' };
  const e = needTables(['gold_resstock_profile_summary'], 'perfiles ResStock');
  if (e) return card({ ...base, body: e });
  const ps = profiles();
  if (!ps.length) return card({ ...base, body: noResState() });
  if (state.to < '2018-01' || state.from > '2018-12') return card({ ...base, body: empty('Sin datos ResStock en el periodo', `El resumen anual corresponde a 2018; el rango ${state.from}…${state.to} no lo incluye.`) });
  const sts = [...new Set(ps.map((x) => x.state_code))].sort();
  const groups = sts.map((s) => ({ label: s, bars: ps.filter((x) => x.state_code === s).map((x) => ({ name: x.housing_type, color: typeCol(x.housing_type), value: +x.annual_kwh, tip: `${s} · ${x.housing_type} · #${x.bldg_id} · ${nf(x.annual_kwh)} kWh` })) }));
  const aria = `Barras de consumo anual modelado en kWh por tipo de vivienda en ${sts.join(' y ')}.`;
  return card({
    ...base,
    body: slot((w) => barChart({ width: w, groups, yLabel: 'kWh al año', aria, yFmt: cmp })) + `<p class="sub">${esc(aria)}</p>` + dataTable(['Estado', 'Tipo', 'Perfil', 'kWh anual'], ps.map((x) => [x.state_code, x.housing_type, `#${x.bldg_id}`, +x.annual_kwh])),
    chips: chip('res', ['kWh', 'anual 2018', `${ps.length} perfiles`]),
    limit: 'Un perfil por tipo y estado: <strong>exploratorio</strong>, no una comparación estadística. <code>profile_weight</code> es idéntico en todos y no se usa como estimador.',
  });
}

function patternP2() {
  const isIndividual = Boolean(state.profile && state.profile !== 'ALL');
  const ps = profiles();
  if (!ps.length) return card({ id: 'P2', q: 'Patrones horarios ResStock', accent: 'res', body: noResState() });

  const p = isIndividual ? (ps.find((x) => String(x.bldg_id) === String(state.profile)) || ps[0]) : null;
  const base = {
    id: 'P2',
    q: isIndividual
      ? `¿A qué horas y en qué meses consume más el perfil #${esc(p?.bldg_id)}?`
      : '¿A qué horas y en qué meses se concentra el consumo agregado de la muestra?',
    accent: 'res',
  };

  const tableNeeded = isIndividual ? 'gold_resstock_pattern' : 'gold_resstock_pattern_aggregate';
  if (['lazy', 'pending'].includes(statusOf(tableNeeded))) {
    ensureTable(tableNeeded).then(() => render());
  }

  const e = needTables([tableNeeded, 'gold_resstock_profile_summary'], isIndividual ? 'patrones horarios individuales' : 'patrones horarios agregados');
  if (e) return card({ ...base, body: e });

  const selProfile = `<div class="ctl"><label>Vista de patrones <select id="sel-profile">
    <option value="ALL" ${!isIndividual ? 'selected' : ''}>Agregado general de la muestra (Gold)</option>
    <optgroup label="Inspección individual de perfiles">
      ${ps.map((x) => `<option value="${x.bldg_id}" ${(isIndividual && String(x.bldg_id) === String(p?.bldg_id)) ? 'selected' : ''}>#${x.bldg_id} · ${esc(x.housing_type)} · ${esc(x.state_code)}</option>`).join('')}
    </optgroup>
  </select></label>
    <div class="seg" role="group" aria-label="Tipo de día"><button type="button" data-day="weekday" aria-pressed="${state.day === 'weekday'}">Día laboral</button><button type="button" data-day="weekend" aria-pressed="${state.day === 'weekend'}">Fin de semana</button></div></div>`;

  let rows;
  if (isIndividual) {
    rows = (rowsOf('gold_resstock_pattern') || []).filter((r) => String(r.bldg_id) === String(p.bldg_id) && r.day_type === state.day && inRange(r.period_local));
  } else {
    rows = (rowsOf('gold_resstock_pattern_aggregate') || []).filter((r) => (state.st === 'ALL' || r.state_code === state.st) && (state.type === 'ALL' || r.housing_type === state.type) && r.day_type === state.day && inRange(r.period_local));
  }

  if (!rows.length) return card({ ...base, body: selProfile + empty('Sin patrones para el filtro', `No hay filas de ${state.day === 'weekday' ? 'día laboral' : 'fin de semana'} para este filtro entre ${state.from} y ${state.to}.`) });

  const allTzs = [...new Set(rows.map((r) => r.time_zone))];
  const activeTz = state.tz && allTzs.includes(state.tz) ? state.tz : allTzs[0];
  const tzRows = isIndividual ? rows : rows.filter((r) => r.time_zone === activeTz);

  const tzSwitcher = (!isIndividual && allTzs.length > 1)
    ? `<div class="ctl" style="margin-top:6px"><label>Zona horaria <select id="sel-tz">${allTzs.map((z) => `<option value="${esc(z)}" ${z === activeTz ? 'selected' : ''}>${esc(z)}</option>`).join('')}</select></label><span class="sub" style="font-size:12px;color:var(--c-sub)">El agregado distingue zona horaria IANA para no mezclar ciclos solares distintos.</span></div>`
    : '';

  const sel = selProfile + tzSwitcher;
  const tz = activeTz;
  const cells = new Map(), acc = new Map(), periods = [...new Set(tzRows.map((r) => r.period_local))].sort();
  for (const r of tzRows) {
    const k = `${r.period_local}|${r.hour_local}`, a = acc.get(k) || { s: 0, n: 0, part: false };
    a.s += +r.median_kwh; a.n++; a.part ||= !!r.is_partial_period; acc.set(k, a);
    if (r.is_partial_period) cells.set(`${r.period_local}|partial`, true);
  }
  for (const [k, a] of acc) cells.set(k, { v: a.s / a.n, partial: a.part });
  const nPart = periods.filter((x) => cells.get(`${x}|partial`)).length;
  const hourAvg = Array.from({ length: 24 }, (_, h) => { const v = periods.map((x) => cells.get(`${x}|${h}`)?.v).filter((v) => v != null); return v.length ? v.reduce((a, b) => a + b) / v.length : -1; });
  const pk = hourAvg.indexOf(Math.max(...hourAvg));

  const aria = isIndividual
    ? `Mapa de calor de la mediana horaria en kWh, hora local ${tz}, ${periods.length} periodos; la hora con mayor mediana promedio es ${String(pk).padStart(2, '0')}:00.`
    : `Mapa de calor del patrón horario agregado en kWh, hora local ${tz}, ${periods.length} periodos; la hora con mayor consumo promedio es ${String(pk).padStart(2, '0')}:00.`;

  const tableHead = isIndividual
    ? ['Periodo local', 'Hora local', 'Zona IANA', 'Mediana kWh', 'Parcial', 'Fuente NOAA']
    : ['Periodo local', 'Hora local', 'Estado', 'Tipo vivienda', 'Zona IANA', 'Mediana kWh', 'Media kWh', 'P10', 'P90', 'Perfiles', 'Parcial', 'Fuente NOAA'];

  const tableRows = isIndividual
    ? tzRows.map((r) => [r.period_local, r.hour_local, r.time_zone, +r.median_kwh, r.is_partial_period ? 'sí' : 'no', r.source_version || 'NOAA c_16ap26'])
    : tzRows.map((r) => [r.period_local, r.hour_local, r.state_code, r.housing_type, r.time_zone, +r.median_kwh, +r.mean_kwh, +r.p10_kwh, +r.p90_kwh, r.n_profiles, r.is_partial_period ? 'sí' : 'no', r.source_version || 'NOAA c_16ap26']);

  const chips = isIndividual
    ? chip('res', ['kWh por hora', `hora local ${tz}`, `#${p.bldg_id}`, 'inspección individual (lazy-load)'])
    : chip('res', ['kWh por hora', `hora local ${tz}`, 'agregado Gold', `${state.type === 'ALL' ? 'todos los tipos' : state.type}`]);

  const limit = isIndividual
    ? 'Inspección individual cargada bajo demanda desde <code>gold_resstock_pattern.json</code>. Cambia a «Agregado general de la muestra» para ver el comportamiento consolidado por estrato sin transferir datos edificio por edificio.'
    : 'Agregado Gold por estrato <code>(state_code, housing_type, time_zone, periodo local, tipo de día, hora local, offset UTC)</code>. Distingue zona IANA por condado (NOAA/NWS c_16ap26) para no mezclar ciclos solares. Estadísticas calculadas sobre horas completas (4 cuartos de hora): mediana, media, p10, p90, min, max y conteo de perfiles. <strong>La muestra modelada no representa a la población general ni a los totales residenciales de facturación.</strong>';

  return card({
    ...base,
    body: sel + slot((w) => heatmap({ width: w, rows: periods, cells, unit: 'kWh/h', aria })) + `<p class="sub"><strong>Hora local · ${esc(tz)}</strong>. ${esc(aria)}${nPart ? ` \u25e9 ${nPart} periodo(s) parcial(es) con borde punteado: no se comparan como meses completos.` : ''}</p>` + dataTable(tableHead, tableRows),
    chips,
    limit,
  });
}

/* ---------- Clima ---------- */
function viewClima() {
  const e = needTables(['gold_climate'], 'clima');
  const out = [];
  if (e) out.push(card({ id: 'C1', q: '¿Qué temperatura hubo en los puntos consultados?', accent: 'clim', body: e }));
  else {
    const rows = climRows();
    if (!rows.length) {
      const have = [...new Set(rowsOf('gold_climate').map((r) => r.state_code))].join(', ');
      out.push(card({ id: 'C1', q: '¿Qué temperatura hubo en los puntos consultados?', accent: 'clim', body: empty(`No hay clima para ${stateName(state.st)} en ${state.from}…${state.to}`, `La muestra solo cubre ${esc(have)} y 1–7 ene 2018.`) }));
    } else {
      const by = new Map();
      for (const r of rows) (by.get(r.point_id) || by.set(r.point_id, []).get(r.point_id)).push(r);
      const t0 = Date.parse(rows.map((r) => r.timestamp_utc).sort()[0]);
      const COL = ['#b45f06', '#7a4fd1', '#2b8fc4', '#c2410c'];
      const series = [...by.entries()].map(([id, rs], i) => ({ name: id, color: COL[i % COL.length], points: rs.map((r) => ({ x: (Date.parse(r.timestamp_utc) - t0) / 36e5, y: +r.temperature_c, tip: `${id} · ${r.timestamp_utc.replace('T', ' ').replace('Z', ' UTC')} · ${r.temperature_c} °C` })) }));
      const maxH = Math.max(...series.flatMap((s) => s.points.map((p) => p.x)));
      const ticks = []; for (let d = 0; d * 24 <= maxH; d++) ticks.push({ x: d * 24, label: new Date(t0 + d * 864e5).toISOString().slice(5, 10) });
      const all = rows.map((r) => +r.temperature_c);
      const aria = `Temperatura horaria en °C de ${by.size} puntos (${[...by.keys()].join(', ')}); mínimo ${nf(Math.min(...all), 1)} °C y máximo ${nf(Math.max(...all), 1)} °C.`;
      out.push(card({
        id: 'C1', q: '¿Qué temperatura hubo en los puntos consultados?', accent: 'clim',
        body: slot((w) => lineChart({ width: w, series, xTicks: ticks, yLabel: '°C', xLabel: 'Fecha UTC (mes-día)', aria, yFmt: (v) => nf(v) })) + `<p class="sub">${esc(aria)}</p>` + dataTable(['Punto', 'UTC', '°C'], rows.map((r) => [r.point_id, r.timestamp_utc, +r.temperature_c]), 60),
        chips: chip('clim', ['°C', 'horario UTC', `${by.size} puntos`, `${rows[0].timestamp_utc.slice(0, 10)}…`]),
        limit: 'Celdas de reanálisis ERA5-Land, no estaciones.',
      }));
    }
  }
  const all = rowsOf('gold_climate');
  const days = all ? new Set(all.map((r) => r.timestamp_utc.slice(0, 10))).size : null;
  out.push(card({
    id: 'C2', q: '¿Se puede relacionar clima y consumo?', accent: 'none',
    body: empty('Dato no comparable', `Clima y consumo no se unen: ${days ? `${days} días` : '7 días'}, ${all ? new Set(all.map((r) => r.point_id)).size : 2} puntos, y husos horarios distintos (ResStock en EST fijo; clima en UTC).<ul><li>No existe una regla de unión geográfica y horaria documentada.</li><li>Por eso no hay gráfica de correlación ni se sugiere causalidad.</li></ul>`),
  }));
  return out.join('');
}

/* ---------- Anomalías: candidatos estadísticos y prueba sintética ---------- */
function viewAnomalias() {
  const err = needTables(['gold_anomaly_candidates', 'gold_anomaly_synthetic_eval'], 'salidas de detección');
  if (err) return card({ id: 'A1–A3', q: 'Cambios inusuales en EIA mensual', accent: 'syn', body: err });
  const all = rowsOf('gold_anomaly_candidates');
  const rows = all.filter((r) => (state.st === 'ALL' || r.state_code === state.st) && inRange(r.period))
    .sort((a, b) => Math.abs(+b.robust_z) - Math.abs(+a.robust_z));
  const evals = rowsOf('gold_anomaly_synthetic_eval');
  const counts = store.manifest?.analytics?.anomaly_counts || {};
  const table = dataTable(['Periodo', 'Estado', 'Cambio interanual (%)', 'Estación', 'Puntuación robusta', 'Partición', 'Etiqueta'],
    rows.map((r) => [r.period, r.state_code, +r.yoy_change_pct, r.season, +r.robust_z, r.partition, 'Candidato estadístico']), 60);
  const metrics = dataTable(['Cambio inyectado', 'Recall', 'Precisión', 'Falsos positivos', 'Casos positivos'],
    evals.map((r) => [`±${nf(+r.injection_pct)}%`, `${nf(+r.recall * 100, 1)}%`, `${nf(+r.precision * 100, 1)}%`, `${nf(+r.false_positive_rate * 100, 1)}%`, `${r.tp}/${r.tp + r.fn}`]));
  return `<div class="banner syn" role="note">La evaluación marcada como sintética usa cambios inyectados. Los candidatos observados no están confirmados como eventos reales.</div>`
    + `<div class="grid g3">${card({ id: 'A1', q: 'Candidatos en datos Final', accent: 'eia', body: `<div class="big">${nf(counts.candidatos_entrenamiento + counts.candidatos_prueba)}<span class="unit">candidatos</span></div><p class="sub">${nf(counts.candidatos_entrenamiento)} en ajuste · ${nf(counts.candidatos_prueba)} en prueba.</p>`, chips: chip('eia', ['51 estados', '2018–2025']), limit: 'Son cambios que superan un umbral estadístico; requieren revisión humana.' })}
    ${card({ id: 'A2', q: 'Cambios en meses preliminares', accent: 'eia', body: `<div class="big">${nf(counts.candidatos_preliminares_2026)}<span class="unit">candidatos</span></div><p class="sub">Se puntúan aparte y no entran al ajuste.</p>`, chips: preChip('2026, corte enero–agosto'), limit: 'Los valores preliminares de EIA pueden actualizarse.' })}
    ${card({ id: 'A3', q: 'Sensibilidad en prueba sintética', accent: 'syn', body: metrics, chips: '<span class="chip syn"><i></i><b>Sintético</b> · cambios inyectados</span>', limit: 'La detección es conservadora ante cambios pequeños. Estas métricas no estiman el desempeño ante eventos reales.' })}</div>`
    + card({ id: 'A4', q: `Candidatos para revisar (${rows.length})`, accent: 'eia', body: table, chips: chip('eia', ['variación interanual', `k = 3.5 MAD`, `${state.from}…${state.to}`]), limit: 'Se compara cada mes con el mismo mes del año anterior; el umbral usa mediana y MAD por estado y estación, ajustado en el periodo de entrenamiento.' });
}

/* ---------- Estimaciones: backtest temporal, no proyección futura ---------- */
function viewEstimaciones() {
  const err = needTables(['gold_forecast_metrics', 'gold_forecast_series'], 'backtest EIA');
  if (err) return card({ id: 'E1–E4', q: 'Evaluación temporal de una línea base', body: err });
  const metrics = rowsOf('gold_forecast_metrics');
  const all = rowsOf('gold_forecast_series');
  const byState = state.st === 'ALL' ? metrics : metrics.filter((r) => r.state_code === state.st);
  const picked = state.st === 'ALL' ? all : all.filter((r) => r.state_code === state.st);
  const periods = [...new Set(picked.map((r) => r.period))].sort();
  const monthTicks = periods.filter((p) => ['01', '04', '07', '10'].includes(p.slice(5, 7)));
  const toSeries = (key, name, color, dash) => ({
    name, color, dash, markers: false,
    points: periods.map((p, i) => {
      const rr = picked.filter((r) => r.period === p);
      const y = rr.length ? rr.reduce((s, r) => s + +r[key], 0) : null;
      return { x: i, y, tip: `${p} · ${name}: ${nf(y)} MWh` };
    }),
  });
  const chart = slot((w) => lineChart({
    width: w, height: 330,
    series: [toSeries('actual_mwh', 'EIA observado', 'var(--eia)'), toSeries('naive_mwh', 'Naive estacional', 'var(--ink-2)', '6 4'), toSeries('model_mwh', 'Log-lineal + mes', 'var(--res)')],
    xTicks: monthTicks.map((p) => ({ x: periods.indexOf(p), label: p })), xDomain: [0, periods.length - 1],
    yLabel: 'Ventas EIA (MWh)', xLabel: 'Mes del holdout', aria: 'Backtest mensual de ventas EIA: observado, naive estacional y modelo log-lineal con mes.', zeroBase: false,
    yFmt: (v) => cmp(v),
  }));
  const smapeN = byState.map((r) => +r.naive_smape_pct).sort((a,b) => a-b);
  const smapeM = byState.map((r) => +r.model_smape_pct).sort((a,b) => a-b);
  const median = (a) => a.length ? (a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2) : null;
  const selectedMetrics = state.st === 'ALL' ? null : byState[0];
  const modelMetric = selectedMetrics ? +selectedMetrics.model_smape_pct : median(smapeM);
  const naiveMetric = selectedMetrics ? +selectedMetrics.naive_smape_pct : median(smapeN);
  const nWins = state.st === 'ALL' ? byState.filter((r) => +r.model_smape_pct < +r.naive_smape_pct).length : Number(modelMetric < naiveMetric);
  const detail = picked.map((r) => [r.period, +r.actual_mwh, +r.naive_mwh, +r.model_mwh]);
  const lineTable = dataTable(['Periodo', 'EIA observado (MWh)', 'Naive estacional (MWh)', 'Modelo (MWh)'], detail, 48);
  const stateLabel = state.st === 'ALL' ? 'suma de 51 jurisdicciones' : state.st;
  return `<div class="banner warn" role="note">Esto es un backtest sobre meses conocidos, no una proyección futura. Entrenamiento: 2018–2023; evaluación: 2024–2025. Los meses preliminares de 2026 se excluyeron.</div>`
    + `<div class="grid g3">${card({ id: 'E1', q: 'sMAPE del modelo', accent: 'eia', body: `<div class="big">${nf(modelMetric, 2)}<span class="unit">%</span></div><p class="sub">${state.st === 'ALL' ? 'Mediana entre estados' : `Estado ${state.st}`}</p>`, chips: chip('eia', ['2018–2025', 'periodos separados']), limit: 'Error porcentual simétrico medio en el holdout; menor es mejor.' })}
    ${card({ id: 'E2', q: 'Comparación con baseline', accent: 'none', body: `<div class="big">${nf(naiveMetric, 2)}<span class="unit">% naive</span></div><p class="sub">El modelo mejora en ${nf(nWins)} de ${nf(byState.length)} estados del filtro.</p>`, chips: chip('eia', ['naive estacional']), limit: 'La baseline repite el último ciclo anual de entrenamiento.' })}
    ${card({ id: 'E3', q: 'Cobertura del backtest', accent: 'none', body: `<div class="big">24<span class="unit">meses</span></div><p class="sub">${stateLabel} · 2024-01 a 2025-12.</p>`, chips: chip('eia', ['sin preliminares']), limit: 'Un solo corte temporal; los resultados pueden cambiar con otros periodos de evaluación.' })}</div>`
    + card({ id: 'E4', q: `Ventas observadas y estimadas · ${stateLabel}`, accent: 'eia', body: chart + lineTable, chips: chip('eia', ['MWh', 'backtest']), limit: 'Modelo log-lineal con tendencia y mes estacional, ajustado solo con datos de entrenamiento. No se extrapola a 2026 ni a años futuros.' });
}

/* ---------- Flujo / Calidad ---------- */
const short = (h) => (h ? `${h.slice(0, 8)}…${h.slice(-6)}` : '—');
function viewCalidad() {
  const out = [];
  const showEia = state.source === 'ALL' || state.source === 'eia';
  const e = needTables(['gold_eia_monthly'], 'cobertura EIA');
  if (showEia) {
    if (e) out.push(card({ id: 'Q1', q: '¿Qué cobertura temporal tiene EIA?', accent: 'eia', body: e }));
    else {
      const rows = rowsOf('gold_eia_monthly'), years = [...new Set(rows.map((r) => r.period.slice(0, 4)))].sort();
      const cnt = new Map();
      for (const r of rows) { const k = `${r.state_code}|${r.period.slice(0, 4)}`, c = cnt.get(k) || { f: 0, p: 0 }; r.data_status === 'Final' ? c.f++ : c.p++; cnt.set(k, c); }
      const sts = eiaStates();
      const cell = (s, y) => { const c = cnt.get(`${s}|${y}`) || { f: 0, p: 0 }; const m = 12 - c.f - c.p; return `<td aria-label="${s} ${y}: ${c.f} finales, ${c.p} preliminares, ${m} faltantes"><span class="cell12" title="${c.f} finales · ${c.p} prelim. · ${m} faltantes">${'<i></i>'.repeat(c.f)}${'<i class="p"></i>'.repeat(c.p)}${'<i class="m"></i>'.repeat(m)}</span></td>`; };
      const tot = years.map((y) => rows.filter((r) => r.period.startsWith(y) && r.data_status !== 'Final').length);
      out.push(card({
        id: 'Q1', q: '¿Qué cobertura temporal tiene EIA?', accent: 'eia',
        body: `<ul class="legend"><li><span class="cell12"><i></i></span>mes final</li><li><span class="cell12"><i class="p"></i></span>mes preliminar</li><li><span class="cell12"><i class="m"></i></span>mes faltante</li></ul>
        <div class="tbl-wrap" style="max-height:420px"><table class="t"><caption class="sr">Meses finales, preliminares y faltantes por estado y año</caption><thead><tr><th scope="col">Estado</th>${years.map((y) => `<th scope="col">${y}</th>`).join('')}</tr></thead><tbody>${sts.map((s) => `<tr class="${s === state.st ? 'sel' : ''}"><th scope="row">${s}</th>${years.map((y) => cell(s, y)).join('')}</tr>`).join('')}</tbody></table></div>
        <p class="sub">${sts.length} jurisdicciones · ${nf(rows.length)} registros. Meses preliminares por año: ${years.map((y, i) => `${y}: ${tot[i] / sts.length || 0}`).filter((_, i) => tot[i]).join(', ') || 'ninguno'} (por estado).</p>`,
        chips: chip('eia', ['meses por año', `${years[0]}…${years[years.length - 1]}`, `${sts.length} jurisdicciones`]),
        limit: 'Un año incompleto (p. ej. 2026) muestra meses faltantes por diseño de la publicación, no errores de carga.',
      }));
    }
  }
  // Q2 manifiesto
  const man = store.manifest, ent = store.entries || {};
  const names = [...new Set([...Object.keys(TABLES), ...Object.keys(ent)])];
  const srcOf = (n) => ({ eia: 'EIA', resstock: 'ResStock', climate: 'Open-Meteo' }[TABLES[n]?.source] || (ent[n]?.source ?? '—'));
  const keep = names.filter((n) => state.source === 'ALL' || (state.source === 'eia' && TABLES[n]?.source === 'eia') || (state.source === 'res' && TABLES[n]?.source === 'resstock') || (state.source === 'clim' && TABLES[n]?.source === 'climate'));
  const trs = keep.map((n) => {
    const s = store.tables[n], en = ent[n];
    const st = s ? ({ ok: `✔ cargada · ${s.validated}`, pending: '… pendiente de entrega', error: `✖ ${s.message}` }[s.status]) : 'listada; sin lector en esta versión';
    return `<tr><th scope="row"><code>${esc(n)}</code></th><td>${esc(srcOf(n))}</td><td class="n">${s?.status === 'ok' ? nf(s.rows.length) : '—'}${en?.rows != null ? ` / ${nf(en.rows)} manifiesto` : ''}</td><td class="n">${en?.bytes != null ? nf(en.bytes) : '—'}</td><td><code title="${esc(en?.sha256 || '')}">${short(en?.sha256)}</code></td><td>${Array.isArray(en?.inputs) ? `${en.inputs.length} entradas` : '—'}</td><td style="white-space:normal">${esc(st)}</td></tr>`;
  }).join('');
  out.push(card({
    id: 'Q2', q: '¿De dónde viene cada tabla?', accent: 'none',
    body: `<p class="sub">Manifiesto: ${man ? `esquema ${esc(man.schema_version ?? man.manifest_version)} · base <code>${esc(DATA_BASE)}</code>` : esc(store.manifestMessage || 'no disponible')}</p><div class="tbl-wrap"><table class="t"><caption class="sr">Tablas Gold consumidas y su validación</caption><thead><tr><th scope="col">Tabla</th><th scope="col">Fuente</th><th class="n" scope="col">Filas</th><th class="n" scope="col">Bytes</th><th scope="col">SHA-256</th><th scope="col">Entradas</th><th scope="col">Estado</th></tr></thead><tbody>${trs}</tbody></table></div>`,
    limit: 'Al cargar se comparan filas, bytes y SHA-256 con el manifiesto; una tabla que no coincide no se usa.',
  }));
  out.push(`<div class="grid g2">${card({ id: 'Q3', q: '¿Qué estado tiene el replay y el pipeline?', body: empty('No disponible todavía', 'Aún no existe salida de replay/pipeline (<code>replay_id</code>, <code>ingested_at_utc</code>). No se simula un estado «en vivo».') })}
  ${card({ id: 'Q4', q: '¿Qué controles de calidad se pasaron?', body: empty('No disponible todavía', 'Se llenará con <code>quality_status</code> y <code>quality_flags</code> del Gold de Spark cuando se exporten al manifiesto.') })}</div>`);
  return out.join('');
}

/* ---------- filtros ---------- */
function rules() {
  const v = state.view, on = { on: true }, off = (why) => ({ on: false, why });
  const nothing = (why) => ({ st: off(why), period: off(why), type: off(why), source: off(why), gran: off(why), prelim: off(why), profile: off(why) });
  if (v === 'anomalias') {
    const R = nothing('Los filtros de estado y periodo se aplican a los candidatos EIA.');
    R.st = on; R.period = on;
    return R;
  }
  if (v === 'estimaciones') {
    const R = nothing('El backtest conserva su periodo de evaluación 2024–2025; solo cambia el estado.');
    R.st = on;
    return R;
  }
  const R = { st: on, period: on, type: on, source: on, gran: on, prelim: on, profile: on };
  if (v === 'resumen') R.gran = off('El resumen no tiene gráficas con granularidad variable.');
  if (v === 'patrones') { R.source = off('Cada gráfica de Patrones ya está ligada a una fuente.'); R.prelim = off('Solo aplica a P1 (EIA); se ve en la leyenda cuando hay meses preliminares.'); if (state.gran === 'monthly') R.prelim = on; }
  if (v === 'clima') { R.type = off('Sin efecto: el clima no tiene tipo de vivienda.'); R.source = off('Esta vista ya es solo clima.'); R.prelim = off('Sin efecto: el clima no tiene estado Final/Preliminary.'); R.profile = off('Sin efecto en clima.'); }
  if (v === 'calidad') { R.type = off('Sin efecto en la cobertura ni el manifiesto.'); R.gran = off('Sin efecto en Calidad.'); R.prelim = off('La cuadrícula muestra siempre finales y preliminares.'); R.profile = off('Sin efecto en Calidad.'); R.period = off('La cobertura se muestra siempre completa.'); }
  if (v === 'patrones' && state.gran === 'monthly') R.profile = off('El perfil se elige en P2 (granularidad horaria).');
  // Estado: si la vista depende de ResStock/clima y el estado no existe, se explica, no se oculta
  return R;
}
const fld = (id, label, control, why) => `<div class="fld"><label for="${id}">${label}</label>${control}${why ? `<span class="why" id="why-${id}">${esc(why)}</span>` : ''}</div>`;
function renderFilters() {
  const focus = document.activeElement?.id;
  const R = rules(), [lo, hi] = periodBounds();
  if (!state.from) { state.from = lo; state.to = hi; }
  const months = []; for (let [y, m] = lo.split('-').map(Number); `${y}-${String(m).padStart(2, '0')}` <= hi; m === 12 ? (y++, m = 1) : m++) months.push(`${y}-${String(m).padStart(2, '0')}`);
  const sel = (id, opts, val, r, extra = '') => `<select id="${id}" ${r.on ? '' : 'disabled'} ${r.on ? '' : `aria-describedby="why-${id}"`} ${extra}>${opts.map(([v, l, d]) => `<option value="${esc(v)}" ${String(v) === String(val) ? 'selected' : ''} ${d ? 'disabled' : ''}>${esc(l)}</option>`).join('')}</select>`;
  const sts = [['ALL', 'Suma 51 jurisdicciones'], ...eiaStates().map((s) => [s, s + (resStates().includes(s) ? ' · EIA + ResStock' : '')])];
  if (sts.length === 1) for (const s of ['CO', 'NY']) sts.push([s, s]);
  const stWhy = !R.st.on ? R.st.why : ((w) => (w === 'patrones' || w === 'clima' || w === 'resumen') ? `ResStock: ${resStates().join(', ') || '—'} · Clima: ${[...new Set((rowsOf('gold_climate') || []).map((r) => r.state_code))].join(', ') || '—'}. Fuera de esas fuentes se muestra estado vacío.` : '')(state.view);
  const types = resTypes();
  const typeWhy = R.type.on ? (statusOf('gold_resstock_profile_summary') === 'ok' ? 'Solo afecta a ResStock.' : 'Esperando la tabla de perfiles.') : R.type.why;
  const ps = profiles(), cp = currentProfile();
  const html = [
    fld('f-st', 'Estado', sel('f-st', sts, state.st, R.st), stWhy),
    fld('f-from', 'Periodo: desde', `<div class="row2">${sel('f-from', months.map((m) => [m, m]), state.from, R.period)}</div>`, R.period.on ? `Rango de EIA ${lo}…${hi}; ResStock solo 2018; clima 1–7 ene 2018.` : R.period.why),
    fld('f-to', 'Periodo: hasta', sel('f-to', months.map((m) => [m, m]), state.to, R.period), ''),
    fld('f-type', 'Tipo de vivienda', sel('f-type', [['ALL', 'Todos'], ...types.map((t) => [t, t])], state.type, R.type), typeWhy),
    fld('f-profile', 'Perfil ResStock', sel('f-profile', [
      ['ALL', 'Agregado general de la muestra (Gold)'],
      ...ps.map((p) => [p.bldg_id, `#${p.bldg_id} · ${p.housing_type} · ${p.state_code}`])
    ], state.profile || 'ALL', R.profile), R.profile.on ? 'Agregado general o inspección individual de perfil.' : R.profile.why),
    fld('f-source', 'Fuente', sel('f-source', [['ALL', 'Todas'], ['eia', 'EIA'], ['res', 'ResStock'], ['clim', 'Open-Meteo']].filter(([v]) => state.view !== 'calidad' || v !== 'clim' || true), state.source, R.source), R.source.on ? '' : R.source.why),
    fld('f-gran', 'Granularidad', sel('f-gran', [['monthly', 'Mensual' + (state.view === 'clima' ? ' (no aplica: 7 días)' : ''), state.view === 'clima'], ['hourly', 'Horaria']], state.view === 'clima' ? 'hourly' : state.gran, R.gran), R.gran.on ? (state.view === 'clima' ? 'Solo hay serie horaria.' : 'Mensual: P1, P1b, P3 · Horaria: P2.') : R.gran.why),
    fld('f-prelim', 'Datos preliminares', `<label class="tog"><input type="checkbox" id="f-prelim" ${state.prelim ? 'checked' : ''} ${R.prelim.on ? '' : 'disabled aria-describedby="why-f-prelim"'}> Mostrar preliminares</label>`, R.prelim.on ? 'Solo EIA.' : R.prelim.why),
  ].join('');
  $('#filters').innerHTML = html;
  if (focus && $('#' + focus)) $('#' + focus).focus();
}

function onFilter(e) {
  const id = e.target.id, val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
  const map = { 'f-st': 'st', 'f-from': 'from', 'f-to': 'to', 'f-type': 'type', 'f-source': 'source', 'f-gran': 'gran', 'f-prelim': 'prelim', 'f-profile': 'profile' };
  if (!map[id]) return;
  state[map[id]] = val;
  if (state.from > state.to) { if (id === 'f-from') state.to = state.from; else state.from = state.to; }
  if (id === 'f-st' || id === 'f-type') state.profile = null;
  render();
}

/* ---------- render ---------- */
const BUILD = { resumen: viewResumen, patrones: viewPatrones, clima: viewClima, anomalias: viewAnomalias, estimaciones: viewEstimaciones, calidad: viewCalidad };
function renderRail() {
  $('#rail').innerHTML = `<div class="brand"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3l12 7v12l-12 7-12-7V10z" fill="#0f8a6d"/><path d="M16 3l12 7-12 7-12-7z" fill="#62d2b3"/><path d="M16 17v12l12-7V10z" fill="#0b6f58"/></svg><span>Consumo residencial</span></div>`
    + VIEWS.map((x) => `<a href="#${x.id}" ${x.id === state.view ? 'aria-current="page"' : ''}>${x.icon}<span>${x.label}</span>${x.pending ? '<span class="dot" title="Espera datos" role="img" aria-label="espera datos"></span>' : ''}</a>`).join('')
    + `<div class="legend-src"><b>Fuentes</b>Azul · EIA oficial<br>Verde · ResStock modelado<br>Ámbar · Clima<br>Magenta · Sintético<br>Rayado · Preliminar</div>`;
}
function renderStatus() {
  const n = Object.keys(TABLES).length;
  const available = Object.entries(store.tables).filter(([name, t]) =>
    t.status === 'ok' || t.status === 'loading' || (t.status === 'lazy' && Boolean(store.entries?.[name]))
  ).length;
  $('#load-status').innerHTML = store.manifestStatus === 'loading' ? '<span>Cargando datos…</span>' : `<span>Tablas disponibles: ${available}/${n}</span><span>Manifiesto: ${{ ok: 'validado', missing: 'ausente', error: 'con error' }[store.manifestStatus]}</span>`;
  const profileCount = rowsOf('gold_resstock_profile_summary')?.length;
  const note = $('#project-note');
  if (note) note.textContent = `Exploratorio: ResStock incluye ${profileCount == null ? 'perfiles modelados' : `${nf(profileCount)} perfiles modelados`} y no representa hogares ni población general. Ilustración conceptual, sin datos por habitación.`;
  const b = [];
  if (store.manifestStatus === 'missing') b.push(`<div class="banner warn" role="status">${esc(store.manifestMessage)}</div>`);
  if (store.manifestStatus === 'error') b.push(`<div class="banner err" role="alert">${esc(store.manifestMessage)}</div>`);
  for (const [n2, t] of Object.entries(store.tables)) if (t.status === 'error' && store.manifestStatus !== 'error') b.push(`<div class="banner err" role="alert"><strong>Error de carga:</strong> ${esc(t.message)}</div>`);
  $('#banners').innerHTML = b.join('');
}
function drawCharts() {
  for (const c of charts) { const el = document.getElementById(c.id); if (el) el.innerHTML = c.fn(el.clientWidth || 600); }
}
let ready = false;
function render() {
  const V = VIEWS.find((x) => x.id === state.view);
  document.title = `${V.label} · Consumo eléctrico residencial`;
  $('#view-title').textContent = V.label; $('#view-question').textContent = V.q;
  renderRail(); renderFilters(); renderStatus();
  charts.length = 0; uid = 0;
  const main = $('#main');
  if (!ready) { main.innerHTML = '<div class="grid g4"><div class="skel"></div><div class="skel"></div><div class="skel"></div><div class="skel"></div></div>'; return; }
  const prevView = main.dataset.view;
  main.innerHTML = `<div class="view" ${prevView === state.view ? 'style="animation:none"' : ''}>${BUILD[state.view]()}</div>`;
  main.dataset.view = state.view;
  drawCharts();
  main.querySelector('#sel-profile')?.addEventListener('change', (e) => { state.profile = e.target.value; render(); });
  main.querySelector('#sel-tz')?.addEventListener('change', (e) => { state.tz = e.target.value; render(); });
  main.querySelectorAll('[data-day]').forEach((b) => b.addEventListener('click', () => { state.day = b.dataset.day; render(); }));
}
function route() {
  const id = location.hash.slice(1);
  if (VIEWS.some((x) => x.id === id)) state.view = id;
  render();
  if (location.hash && ready) $('#main').focus({ preventScroll: true });
}
const mq = matchMedia('(max-width:900px)');
const fw = $('#filters-wrap'); const syncFilters = () => { fw.open = !mq.matches; }; syncFilters(); mq.addEventListener('change', syncFilters);
$('#filters').addEventListener('change', onFilter);
window.addEventListener('hashchange', route);
let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(drawCharts, 120); }).observe(document.body);
route();
loadAll().then(() => { buildEia(); ready = true; state.from = null; render(); }).catch((e) => { $('#banners').innerHTML = `<div class="banner err" role="alert">Error inesperado: ${esc(e.message)}</div>`; });
