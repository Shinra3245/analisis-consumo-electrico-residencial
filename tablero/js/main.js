import { DATA_BASE, SCHEMA_VERSION, TABLES } from './config.js';
import { loadAll, store, rowsOf, statusOf, ensureTable } from './data.js';
import { esc, nf, lineChart, barChart, heatmap, scatterChart } from './charts.js';
import { isoHouse } from './iso.js';

/* ---------- vistas ---------- */
const ico = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const VIEWS = [
  { id: 'resumen', label: 'Resumen', short: 'Resumen', icon: ico('<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'), q: '¿Cuánta electricidad se vende a los hogares, de dónde salen los datos y cómo se leen?' },
  { id: 'patrones', label: 'Patrones de consumo', short: 'Patrones', icon: ico('<path d="M3 17l5-6 4 3 5-8 4 5"/><path d="M3 21h18"/>'), q: '¿En qué meses, horas y tipos de vivienda se usa más electricidad, y cómo cambia entre estados?' },
  { id: 'clima', label: 'Clima', short: 'Clima', icon: ico('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>'), q: '¿Qué datos de temperatura tenemos y por qué todavía no se cruzan con el consumo?' },
  { id: 'anomalias', label: 'Meses atípicos', short: 'Atípicos', icon: ico('<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.5"/>'), q: '¿Qué meses cambiaron mucho más de lo habitual y qué tan confiable es esa detección?' },
  { id: 'estimaciones', label: 'Estimaciones', short: 'Estimar', icon: ico('<path d="M3 20V8M9 20V4M15 20v-9M21 20V12"/>'), q: '¿Qué tan bien habría acertado un modelo sencillo en meses que ya conocemos?' },
  { id: 'calidad', label: 'Calidad de datos', short: 'Calidad', icon: ico('<path d="M9 12l2 2 4-4"/><path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/>'), q: '¿De dónde viene cada dato, qué periodo cubre y cómo se comprobó que no cambió?' },
];
const state = {
  view: 'resumen',
  st: 'CO',
  from: null,
  to: null,
  type: 'ALL',
  source: 'ALL',
  gran: 'monthly',
  prelim: true,
  profile: null,
  day: 'weekday',
  tz: null,
  demoYear: 2025,
  demoSortCol: 'residential_kwh_per_capita',
  demoSortAsc: false,
  demoIncludeDc: false,
};
const $ = (s) => document.querySelector(s);
const SRC = {
  eia: { cls: 'eia', name: 'EIA-861M', kind: 'ventas oficiales agregadas' },
  res: { cls: 'res', name: 'ResStock 2018', kind: 'simulación (modelado)' },
  clim: { cls: 'clim', name: 'Open-Meteo ERA5-Land', kind: 'reanálisis' },
  demo: { cls: 'demo', name: 'Census PEP + EIA', kind: 'oficial anual' },
};

const STATE_NAMES = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
  CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', DC: 'Distrito de Columbia',
  FL: 'Florida', GA: 'Georgia', HI: 'Hawái', ID: 'Idaho', IL: 'Illinois',
  IN: 'Indiana', IA: 'Iowa', KS: 'Kansas', KY: 'Kentucky', LA: 'Luisiana',
  ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota',
  MS: 'Misisipi', MO: 'Misuri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada',
  NH: 'Nuevo Hampshire', NJ: 'Nueva Jersey', NM: 'Nuevo México', NY: 'Nueva York',
  NC: 'Carolina del Norte', ND: 'Dakota del Norte', OH: 'Ohio', OK: 'Oklahoma',
  OR: 'Oregón', PA: 'Pensilvania', RI: 'Rhode Island', SC: 'Carolina del Sur',
  SD: 'Dakota del Sur', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
  VA: 'Virginia', WA: 'Washington', WV: 'Virginia Occidental', WI: 'Wisconsin',
  WY: 'Wyoming',
};
const jurisdictionName = (c) => STATE_NAMES[c] || c;
const HOUSING_TYPE_LABELS = {
  'Mobile Home': 'Casa móvil (Mobile Home)',
  'Single-Family Detached': 'Unifamiliar aislada (Single-Family Detached)',
  'Single-Family Attached': 'Unifamiliar adosada (Single-Family Attached)',
  'Multi-Family with 2 - 4 Units': 'Multifamiliar (2 a 4 unidades de vivienda)',
  'Multi-Family with 5+ Units': 'Multifamiliar (5 o más unidades de vivienda)',
};
const housingTypeName = (t) => HOUSING_TYPE_LABELS[t] || t;
const chip = (src, parts) => { const s = SRC[src]; return `<span class="chip ${s.cls}"><i></i><b>${esc(s.name)}</b> · ${esc(s.kind)}${parts.map((p) => ` · ${esc(p)}`).join('')}</span>`; };
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
const demoRows = () => rowsOf('gold_demography_state_year') || [];
const demoByYear = (y) => {
  const yNum = Number(y);
  return demoRows().filter((r) => Number(r.year) === yNum);
};
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
const card = ({ id, q, accent = 'none', body, chips = '', limit = '', cls = '' }) => `<section class="card accent-${accent} ${cls}" ${id ? `aria-labelledby="h-${id}"` : ''}><header class="card-h"><h2 id="h-${id}">${esc(q)}</h2>${id ? `<span class="cid" title="Referencia del requisito">${id}</span>` : ''}</header><div class="card-b">${body}</div>${limit ? `<p class="limit"><span class="limit-i" aria-hidden="true">i</span><span>${limit}</span></p>` : ''}${chips ? `<div class="chips" aria-label="Fuente y unidades">${chips}</div>` : ''}</section>`;
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

/* ---------- Selector visual de tipo de vivienda ---------- */
const TYPE_SHORT = { 'Mobile Home': 'Móvil', 'Single-Family Detached': 'Aislada', 'Single-Family Attached': 'Adosada', 'Multi-Family with 2 - 4 Units': '2–4 unid.', 'Multi-Family with 5+ Units': '5+ unid.' };
function typePicker() {
  const types = resTypes();
  if (!types.length) return '';
  const b = (v, l, t) => `<button type="button" data-pick-type="${esc(v)}" aria-pressed="${state.type === v}" title="${esc(t)}">${esc(l)}</button>`;
  return `<div class="type-pick" role="group" aria-label="Filtrar por tipo de vivienda">${b('ALL', 'Todos', 'Todos los tipos')}${types.map((t) => b(t, TYPE_SHORT[t] || t, housingTypeName(t))).join('')}</div>`;
}

/* ---------- Resumen ---------- */
function viewResumen() {
  const showAll = state.source === 'ALL';
  const out = [];
  // Hero isométrico
  const p = currentProfile();
  const ht = p?.housing_type;
  const heroMeta = p
    ? `<p class="eyebrow">Vivienda simulada · ResStock #${esc(p.bldg_id)}</p><h2 class="hero-t">${esc(housingTypeName(p.housing_type))} · ${esc(jurisdictionName(p.state_code))}</h2>
       <p class="sub">Un ejemplo de vivienda <strong>modelada</strong> por computadora para el año ${esc(p.source_year)}; no es una casa real medida.</p>
       <dl class="kv"><div><dt>Al año</dt><dd>${nf(p.annual_kwh)} <small>kWh</small></dd></div><div><dt>Por hora, en promedio</dt><dd>${nf(p.mean_hour_kwh, 2)} <small>kWh</small></dd></div><div><dt>Hora de mayor uso</dt><dd>${nf(p.peak_hour_kwh, 2)} <small>kWh</small></dd></div></dl>
       <div class="chips">${chip('res', ['kWh', `${p.source_year}`, '1 vivienda simulada'])}</div>`
    : `<p class="eyebrow">Ilustración de referencia</p><h2 class="hero-t">No hay viviendas simuladas para este filtro</h2>
       <p class="sub">${statusOf('gold_resstock_profile_summary') === 'ok' ? `Las simulaciones solo cubren ${esc(resStates().map(jurisdictionName).join(' y '))}. ` : 'La tabla de viviendas simuladas aún no está disponible. '}La ilustración no muestra cifras.</p>`;
  out.push(`<section class="card hero" aria-label="Tipo de vivienda"><div class="iso-wrap">${isoHouse(ht)}${typePicker()}<p class="iso-cap">Exterior ilustrativo del tipo de vivienda. No muestra habitaciones ni consumo por cuarto.</p></div><div class="meta">${heroMeta}</div></section>`);

  const cards = [];
  if (showAll || state.source === 'eia') {
    const s = eiaSeries();
    const e = needTables(['gold_eia_monthly'], 'ventas EIA');
    if (e) cards.push(card({ id: 'R1a', q: 'Electricidad vendida a hogares', accent: 'eia', body: e }));
    else if (!s.length) cards.push(card({ id: 'R1a', q: 'Electricidad vendida a hogares', accent: 'eia', body: empty('Sin datos EIA para el filtro', `No hay meses de ${esc(stateName(state.st))} entre ${state.from} y ${state.to}${state.prelim ? '' : ' con preliminares ocultos'}.`) }));
    else {
      const byYear = new Map();
      for (const r of s) { const y = r.period.slice(0, 4); (byYear.get(y) || byYear.set(y, []).get(y)).push(r); }
      const years = [...byYear.keys()].sort();
      const full = years.filter((y) => byYear.get(y).length === 12);
      const y = full.length ? full[full.length - 1] : years[years.length - 1];
      const rows = byYear.get(y), tot = rows.reduce((a, r) => a + r.mwh, 0), pre = rows.filter((r) => r.status !== 'Final').length;
      cards.push(card({
        id: 'R1a', q: `Electricidad vendida a hogares en ${y}`, accent: 'eia',
        body: `<div class="big">${nf(tot)}<span class="unit">MWh</span></div><p class="sub">${esc(stateName(state.st))} · ${rows.length === 12 ? 'año completo' : `<strong>parcial: ${rows.length} de 12 meses</strong>`}${pre ? ` · incluye ${pre} meses preliminares` : ''}</p>`,
        chips: chip('eia', ['MWh', `${rows[0].period}…${rows[rows.length - 1].period}`, state.st === 'ALL' ? '51 jurisdicciones' : state.st]) + (pre ? preChip('puede cambiar') : ''),
        limit: 'Total vendido a los hogares del estado por las compañías eléctricas. 1 MWh = 1,000 kWh. No es una medición por hogar.',
      }));
      const fin = s.filter((r) => r.status === 'Final').length, prel = s.length - fin;
      cards.push(card({
        id: 'R1b', q: 'Meses con datos en el periodo', accent: 'eia',
        body: `<div class="big">${nf(fin)}<span class="unit">definitivos</span></div><p class="sub">${nf(prel)} preliminares (EIA aún puede corregirlos) entre ${state.from}…${state.to}${state.prelim ? '' : ' (ocultos por el filtro)'}.</p>`,
        chips: chip('eia', ['meses', `${state.from}…${state.to}`]), limit: 'El detalle por año está en Calidad de datos.',
      }));
    }
  }
  if (showAll || state.source === 'res') {
    const e = needTables(['gold_resstock_profile_summary'], 'perfiles ResStock');
    if (e) cards.push(card({ id: 'R1c', q: 'Viviendas simuladas disponibles', accent: 'res', body: e }));
    else {
      const total = rowsOf('gold_resstock_profile_summary').length, ps = profiles();
      cards.push(card({
        id: 'R1c', q: 'Viviendas simuladas disponibles', accent: 'res',
        body: `<div class="big">${nf(ps.length)}<span class="unit">de ${nf(total)} simulaciones</span></div><p class="sub">${esc(state.st === 'ALL' ? 'Todos los estados del piloto' : state.st)}${state.type === 'ALL' ? '' : ` · ${esc(state.type)}`}. Es el tamaño de la muestra simulada, no un conteo de viviendas reales.</p>`,
        chips: chip('res', ['perfiles', resStates().join('/')]), limit: 'Datos modelados: no representan al estado ni al país.',
      }));
    }
  }
  if (showAll || state.source === 'clim') {
    const e = needTables(['gold_climate'], 'clima');
    if (e) cards.push(card({ id: 'R1d', q: 'Datos de clima disponibles', accent: 'clim', body: e }));
    else {
      const all = rowsOf('gold_climate'), pts = new Set(all.map((r) => r.point_id)), ts = all.map((r) => r.timestamp_utc).sort();
      cards.push(card({
        id: 'R1d', q: 'Datos de clima disponibles', accent: 'clim',
        body: `<div class="big">${pts.size}<span class="unit">puntos</span></div><p class="sub">${ts[0].slice(0, 10)} a ${ts[ts.length - 1].slice(0, 10)} (UTC), ${nf(all.length)} lecturas horarias. Solo ${[...new Set(all.map((r) => r.state_code))].join(', ')}.</p>`,
        chips: chip('clim', ['°C', 'horario UTC']), limit: 'Temperatura de un modelo de reanálisis, no de estaciones. Se muestra aparte del consumo.',
      }));
    }
  }
  if (showAll) {
    const fc = store.manifest?.analytics?.forecast;
    cards.push(card({
      id: 'R1e', q: 'Error típico del modelo de estimación', accent: 'none',
      body: fc ? `<div class="big">${nf(fc.median_model_smape_pct, 2)}<span class="unit">%</span></div><p class="sub">Error porcentual (sMAPE) mediano en ${nf(fc.state_count)} jurisdicciones; supera a la referencia simple en ${nf(fc.states_model_beats_naive)}.</p>` : empty('Pendiente', 'No hay un backtest Gold disponible.'),
      chips: fc ? chip('eia', ['sMAPE', `${fc.holdout[0]}…${fc.holdout[1]}`, 'backtest']) : '',
      limit: 'Evaluado con meses ya conocidos; no es un pronóstico del futuro.',
    }));
  }
  if (showAll || state.source === 'demo') {
    const demErr = needTables(['gold_demography_state_year'], 'demografía');
    if (demErr) {
      cards.push(card({ id: 'R1f', q: 'Población y ventas por habitante', accent: 'demo', body: demErr }));
    } else {
      const d25 = demoByYear(2025);
      const isAll = state.st === 'ALL';
      const stRow = d25.find((r) => r.state_code === state.st);
      if (isAll) {
        const totPop = d25.reduce((a, r) => a + Number(r.population_estimate), 0);
        const totMwh = d25.reduce((a, r) => a + Number(r.residential_sales_mwh), 0);
        const avgKwh = totPop > 0 ? (totMwh * 1000) / totPop : 0;
        cards.push(card({
          id: 'R1f', q: 'Electricidad por habitante, 2025', accent: 'demo',
          body: `<div class="big">${nf(avgKwh, 1)}<span class="unit">kWh/hab</span></div><p class="sub">50 estados + DC en conjunto (${nf(totPop)} residentes al 1 de julio de 2025).</p>`,
          chips: chip('demo', ['2025', 'Vintage 2025', '51 jurisdicciones', 'EIA-861M']),
          limit: 'Ventas anuales a hogares divididas entre la población. Es un promedio agregado, no la factura de un hogar.',
        }));
      } else if (stRow) {
        cards.push(card({
          id: 'R1f', q: `Electricidad por habitante, 2025 · ${stRow.state_code}`, accent: 'demo',
          body: `<div class="big">${nf(stRow.residential_kwh_per_capita, 1)}<span class="unit">kWh/hab</span></div><p class="sub">${jurisdictionName(stRow.state_code)}: ${nf(stRow.population_estimate)} hab. · ${nf(stRow.population_density_per_sq_mi, 1)} hab./mi² (año 2025).</p>`,
          chips: chip('demo', ['2025', stRow.state_code, `${nf(stRow.residential_sales_mwh)} MWh`]),
          limit: 'Ventas anuales a hogares divididas entre la población. Es descriptivo: no explica por qué un estado consume más.',
        }));
      }
    }
  }
  out.push(`<div class="grid g4">${cards.join('')}</div>`);

  // R2: cobertura, sin razón
  if (showAll || state.source === 'eia' || state.source === 'res') {
    const co = eiaIdx?.get('CO');
    const tot = co ? [...co.entries()].filter(([p]) => p.startsWith('2018')) : [];
    out.push(card({
      id: 'R2', q: '¿Se pueden comparar las simulaciones con las ventas reales?', accent: 'none',
      body: `${empty('No directamente', 'ResStock simula unas pocas viviendas; EIA reporta las ventas de todo el estado. Por eso no se publica una razón entre ambas (la cifra preliminar 87.16 % no se reprodujo y no mide precisión).')}
      <div class="tbl-wrap" style="max-height:none"><table class="t"><caption class="sr">Cobertura de cada fuente</caption><thead><tr><th scope="col">Fuente</th><th scope="col">Población</th><th scope="col">Periodo</th><th scope="col">Cobertura</th></tr></thead><tbody>
      <tr><td>${chip('eia', [])}</td><td>Ventas de todo el estado (CO)</td><td>2018</td><td>${tot.length ? `${tot.length} meses · ${nf(tot.reduce((a, [, v]) => a + v.mwh, 0))} MWh` : 'sin datos'}</td></tr>
      <tr><td>${chip('res', [])}</td><td>${(() => { const n = (resSummary() || []).filter((r) => r.state_code === 'CO').length; return n ? `${n} perfiles modelados de CO (no solo unifamiliar aislada)` : 'perfiles piloto no disponibles'; })()}</td><td>2018 (EST fijo)</td><td>Piloto exploratorio; sin ponderación válida</td></tr></tbody></table></div>`,
      limit: 'Se usa Colorado 2018 como ejemplo porque ahí coinciden ambas fuentes.',
    }));
  }

  // R3: cómo leer las fuentes y unidades (definiciones; las cifras por estado están en Patrones)
  out.push(card({
    id: 'R3', q: '¿Cómo leer estas cifras?', accent: 'none',
    body: `<div class="dim-grid">
      <div class="dim-card"><span class="dot eia"></span><b>Ventas EIA (MWh)</b><div class="sub">Electricidad vendida a todos los hogares de un estado en un mes. 1 MWh = 1,000 kWh. Son totales oficiales, no mediciones por hogar.</div></div>
      <div class="dim-card"><span class="dot res"></span><b>Viviendas simuladas ResStock (kWh)</b><div class="sub">Consumo calculado por un modelo para viviendas tipo de 2018. Sirven para ver formas y horarios, no para representar al estado.</div></div>
      <div class="dim-card"><span class="dot demo"></span><b>Por habitante (kWh/hab)</b><div class="sub">Ventas anuales del estado divididas entre su población. Permite comparar estados de distinto tamaño; no es la factura de un hogar.</div></div>
      <div class="dim-card"><span class="dot clim"></span><b>Clima (°C)</b><div class="sub">Temperatura horaria de un modelo de reanálisis para pocos puntos y días. Se muestra aparte del consumo.</div></div>
    </div>`,
    limit: 'Las fuentes cubren periodos distintos (EIA 2018–2026, ResStock 2018, clima 1–7 ene 2018) y no se suman entre sí. Washington D.C. (DC) es un distrito federal, no un estado. Ninguna comparación implica causa.',
  }));
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
    ? `${esc(housingTypeName(p?.housing_type || ''))} · ${esc(p?.state_code || '')}`
    : (state.type !== 'ALL' ? `${esc(housingTypeName(state.type))} · ${esc(state.st === 'ALL' ? 'Muestra general' : state.st)}` : `Todos los tipos de vivienda · ${esc(state.st === 'ALL' ? 'Todos los estados' : jurisdictionName(state.st))}`);
  const heroSub = isIndividual
    ? `Viendo una sola vivienda simulada (#${esc(p?.bldg_id)}). Elige «Promedio de la muestra» para volver al conjunto.`
    : `Promedio de las viviendas simuladas para el filtro elegido. Cambia a «Por hora» para ver una vivienda concreta.`;
  const heroChip = isIndividual
    ? (p ? chip('res', ['kWh', '1 vivienda simulada']) : '')
    : chip('res', ['kWh', 'promedio de la muestra']);
  const hero = `<section class="card hero" aria-label="Tipo de vivienda"><div class="iso-wrap">${isoHouse(heroHt)}${isIndividual ? '' : typePicker()}<p class="iso-cap">Exterior ilustrativo; no muestra habitaciones ni consumo por cuarto.</p></div><div class="meta"><p class="eyebrow">${isIndividual ? 'Una vivienda simulada' : 'Viviendas simuladas · promedio'}</p><h2 class="hero-t">${heroTitle}</h2><p class="sub">${heroSub}</p><div class="chips">${heroChip}</div></div></section>`;
  out.push(hero);
  if (state.gran === 'monthly') {
    out.push('<div class="grid g2">' + patternP1() + patternP1b() + '</div>' + patternP3() + patternP4());
  } else out.push(patternP2());
  return out.join('');
}

function patternP1() {
  const e = needTables(['gold_eia_monthly'], 'ventas EIA');
  const base = { id: 'P1', q: '¿En qué meses se vende más electricidad a los hogares?', accent: 'eia' };
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
    limit: 'Cada línea es un año; la punteada tiene meses preliminares. Son ventas totales, no consumo medido por hogar.',
  });
}

function patternP1b() {
  const base = { id: 'P1b', q: '¿Cómo cambia mes a mes cada vivienda simulada?', accent: 'res' };
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
    limit: 'Una vivienda simulada por tipo y estado: sirve para explorar, no para generalizar.',
  });
}

function patternP3() {
  const base = { id: 'P3', q: '¿Qué tipo de vivienda simulada usa más electricidad al año?', accent: 'res' };
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
    limit: 'Una vivienda simulada por tipo y estado: es un ejemplo, no una comparación estadística entre tipos.',
  });
}

function patternP4() {
  const base = { id: 'P4', q: '¿Los estados más densos usan más o menos electricidad por persona?', accent: 'demo' };
  const e = needTables(['gold_demography_state_year'], 'demografía y ventas estatales');
  if (e) return card({ ...base, body: e });

  const activeYear = Number(state.demoYear || 2025);
  const allYearRows = demoByYear(activeYear);
  if (!allYearRows.length) {
    return card({ ...base, body: empty('Sin datos demográficos para el año', `No se encontraron registros para el año ${activeYear}.`) });
  }

  // Líderes del año
  const popLeader = [...allYearRows].sort((a, b) => b.population_estimate - a.population_estimate)[0];
  const salesLeader = [...allYearRows].sort((a, b) => b.residential_sales_mwh - a.residential_sales_mwh)[0];
  const kwhLeader = [...allYearRows].sort((a, b) => b.residential_kwh_per_capita - a.residential_kwh_per_capita)[0];
  const stateDensities = allYearRows.filter((r) => r.state_code !== 'DC');
  const densLeader = [...stateDensities].sort((a, b) => b.population_density_per_sq_mi - a.population_density_per_sq_mi)[0];
  const dcRow = allYearRows.find((r) => r.state_code === 'DC');

  // Selector de año 2020-2025
  const years = [2020, 2021, 2022, 2023, 2024, 2025];
  const yearTabs = `<div class="year-tabs" role="group" aria-label="Año de análisis demográfico">${years.map((y) => `<button type="button" class="year-tab ${y === activeYear ? 'active' : ''}" data-demo-year="${y}" aria-pressed="${y === activeYear}">${y}</button>`).join('')}</div>`;

  // Resumen de las 4 dimensiones y líderes
  const summaryStrip = `
  <div class="dim-grid">
    <div class="dim-card">
      <span class="eyebrow">Población</span>
      <b>Mayor población</b>
      <div style="font-size:18px;font-weight:700;color:var(--demo);margin:4px 0">${esc(jurisdictionName(popLeader.state_code))} (${esc(popLeader.state_code)})</div>
      <div>${nf(popLeader.population_estimate)} residentes al 1 de julio</div>
    </div>
    <div class="dim-card">
      <span class="eyebrow">Densidad</span>
      <b>Estado más denso (sin DC)</b>
      <div style="font-size:18px;font-weight:700;color:var(--demo);margin:4px 0">${esc(jurisdictionName(densLeader.state_code))} (${esc(densLeader.state_code)})</div>
      <div>${nf(densLeader.population_density_per_sq_mi, 1)} hab./mi² <span class="badge-dc" title="Distrito federal urbano censal (Washington D.C.), no un estado">DC: ${nf(dcRow?.population_density_per_sq_mi, 1)} hab./mi² (distrito urbano)</span></div>
    </div>
    <div class="dim-card">
      <span class="eyebrow">Ventas totales</span>
      <b>Mayores ventas totales</b>
      <div style="font-size:18px;font-weight:700;color:var(--demo);margin:4px 0">${esc(jurisdictionName(salesLeader.state_code))} (${esc(salesLeader.state_code)})</div>
      <div>${nf(salesLeader.residential_sales_mwh)} MWh/año</div>
    </div>
    <div class="dim-card">
      <span class="eyebrow">Por habitante</span>
      <b>Mayores ventas por habitante</b>
      <div style="font-size:18px;font-weight:700;color:var(--demo);margin:4px 0">${esc(jurisdictionName(kwhLeader.state_code))} (${esc(kwhLeader.state_code)})</div>
      <div>${nf(kwhLeader.residential_kwh_per_capita, 1)} kWh/hab/año</div>
    </div>
  </div>`;

  // Gráfica de dispersión
  const includeDc = Boolean(state.demoIncludeDc);
  const chartRows = includeDc ? allYearRows : allYearRows.filter((r) => r.state_code !== 'DC');
  const minPop = Math.min(...chartRows.map((r) => Number(r.population_estimate)));
  const maxPop = Math.max(...chartRows.map((r) => Number(r.population_estimate)));
  const sqrtMin = Math.sqrt(minPop || 1);
  const sqrtMax = Math.sqrt(maxPop || 1);

  const points = chartRows.map((r) => {
    const pop = Number(r.population_estimate);
    // Escala cuadrática acotada perceptible entre 4px y 14px
    const popRadius = 4 + ((Math.sqrt(pop) - sqrtMin) / (sqrtMax - sqrtMin || 1)) * 10;
    return {
      x: Number(r.population_density_per_sq_mi),
      y: Number(r.residential_kwh_per_capita),
      r: Number(popRadius.toFixed(1)),
      state_code: r.state_code,
      label: r.state_code,
      isDc: r.state_code === 'DC',
      isSelected: r.state_code === state.st,
      showLabel: ['CA', 'TX', 'FL', 'NY', 'NJ', 'LA', 'DC', 'HI', 'WY', 'AK'].includes(r.state_code) || r.state_code === state.st,
      tip: `${jurisdictionName(r.state_code)} (${r.state_code}) · Año ${r.year}
· Población residente: ${nf(r.population_estimate)} hab. (radio proporcional)
· Ventas por habitante: ${nf(r.residential_kwh_per_capita, 2)} kWh/hab/año
· Densidad estimada: ${nf(r.population_density_per_sq_mi, 2)} hab./mi²
· Ventas residenciales: ${nf(r.residential_sales_mwh, 2)} MWh
· Superficie terrestre: ${nf(r.land_area_sq_mi_2020, 2)} mi²`,
    };
  });

  const chartCtl = `
  <div class="ctl" style="justify-content:space-between;margin-top:14px">
    <label class="tog"><input type="checkbox" id="chk-demo-dc" ${includeDc ? 'checked' : ''}> Incluir Washington D.C. (DC)</label>
    <span class="sub" style="font-size:12px;color:var(--ink-2)">${includeDc ? 'DC es un distrito urbano con densidad muy superior a cualquier estado; comprime la escala.' : 'DC se oculta en la gráfica para poder ver la diferencia entre los 50 estados. Sigue en la tabla.'}</span>
  </div>`;

  const ariaChart = `Gráfica de dispersión de ventas por habitante (kWh/hab) frente a densidad poblacional (hab./mi²) para el año ${activeYear}. El tamaño de los círculos representa la población residente.`;
  const chartHtml = slot((w) => scatterChart({
    width: w,
    height: 350,
    points,
    xLabel: 'Densidad poblacional estimada (personas/mi² terrestre)',
    yLabel: 'Ventas residenciales por habitante (kWh/persona/año)',
    aria: ariaChart,
    xFmt: (v) => nf(v),
    yFmt: (v) => nf(v),
  })) + `<p class="sub how"><strong>Cómo leerla:</strong> cada círculo es un estado. Más a la derecha = más personas por milla cuadrada; más arriba = más electricidad por persona al año; círculo más grande = más población. Pasa el cursor o toca un punto para ver el detalle.</p>`;

  // Tabla interactiva ordenable
  const sortCol = state.demoSortCol || 'residential_kwh_per_capita';
  const sortAsc = Boolean(state.demoSortAsc);

  const sortedRows = [...allYearRows].sort((a, b) => {
    let va = a[sortCol];
    let vb = b[sortCol];
    if (typeof va === 'string') {
      return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }
    va = Number(va);
    vb = Number(vb);
    return sortAsc ? va - vb : vb - va;
  });

  const cols = [
    { key: 'state_code', label: 'Jurisdicción', numeric: false },
    { key: 'population_estimate', label: 'Población (hab.)', numeric: true },
    { key: 'population_density_per_sq_mi', label: 'Densidad (hab./mi²)', numeric: true },
    { key: 'residential_sales_mwh', label: 'Ventas totales (MWh)', numeric: true },
    { key: 'residential_kwh_per_capita', label: 'Ventas por hab. (kWh/hab)', numeric: true },
    { key: 'land_area_sq_mi_2020', label: 'Superficie (mi²)', numeric: true },
  ];

  const thHtml = cols.map((c) => {
    const isSorted = sortCol === c.key;
    const ariaSort = isSorted ? (sortAsc ? 'ascending' : 'descending') : 'none';
    const sortIcon = isSorted ? (sortAsc ? '▲' : '▼') : '↕';
    return `<th scope="col" aria-sort="${ariaSort}" class="${c.numeric ? 'n' : ''}">
      <button type="button" class="btn-sort" data-demo-sort="${c.key}">
        <span>${c.label}</span>
        <span class="sort-icon" aria-hidden="true">${sortIcon}</span>
      </button>
    </th>`;
  }).join('');

  const tableHeader = `
  <thead>
    <tr>
      <th scope="col" style="width:40px">#</th>
      ${thHtml}
    </tr>
  </thead>`;

  const tableBody = sortedRows.map((r, i) => {
    const isSel = r.state_code === state.st;
    const isDc = r.state_code === 'DC';
    const name = jurisdictionName(r.state_code);
    return `<tr class="${isSel ? 'sel' : ''}">
      <td class="sub">${i + 1}</td>
      <th scope="row"><strong>${esc(name)}</strong> <span class="sub">(${esc(r.state_code)})</span>${isDc ? '<span class="badge-dc" title="Distrito federal urbano censal (Washington D.C.)">DC: distrito urbano</span>' : ''}</th>
      <td class="n">${nf(r.population_estimate)}</td>
      <td class="n">${nf(r.population_density_per_sq_mi, 2)}</td>
      <td class="n">${nf(r.residential_sales_mwh, 2)}</td>
      <td class="n"><strong>${nf(r.residential_kwh_per_capita, 2)}</strong></td>
      <td class="n">${nf(r.land_area_sq_mi_2020, 2)}</td>
    </tr>`;
  }).join('');

  const tableHtml = `
  <div style="margin-top:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
      <h3 class="h3">50 estados + DC · ${activeYear}</h3>
      <span class="sub" style="font-size:12px;margin:0">Pulsa un encabezado para ordenar</span>
    </div>
    <div class="tbl-wrap" style="max-height:360px">
      <table class="t">
        <caption class="sr">Clasificación demográfica y eléctrica por estado, año ${activeYear}</caption>
        ${tableHeader}
        <tbody>${tableBody}</tbody>
      </table>
    </div>
  </div>`;

  const limitText = `<strong>Descriptivo, no causal.</strong> Que dos medidas se muevan juntas no significa que una cause la otra: el consumo también depende del clima, del uso de gas para calefacción, de las tarifas y del tipo de hogar. Son cifras oficiales agregadas (EIA-861M + Census PEP Vintage 2025), independientes de las simulaciones ResStock.`;

  return card({
    ...base,
    body: yearTabs + summaryStrip + chartCtl + chartHtml + tableHtml,
    chips: chip('demo', [`Año ${activeYear}`, '50 estados + DC', 'kWh/hab · hab./mi²']),
    limit: limitText,
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
      ? `¿A qué hora del día usa más electricidad la vivienda simulada #${esc(p?.bldg_id)}?`
      : '¿A qué hora del día se usa más electricidad en las viviendas simuladas?',
    accent: 'res',
  };

  const tableNeeded = isIndividual ? 'gold_resstock_pattern' : 'gold_resstock_pattern_aggregate';
  if (['lazy', 'pending'].includes(statusOf(tableNeeded))) {
    ensureTable(tableNeeded).then(() => render());
  }

  const e = needTables([tableNeeded, 'gold_resstock_profile_summary'], isIndividual ? 'patrones horarios individuales' : 'patrones horarios agregados');
  if (e) return card({ ...base, body: e });

  const selProfile = `<div class="ctl"><label>Viviendas <select id="sel-profile">
    <option value="ALL" ${!isIndividual ? 'selected' : ''}>Promedio de la muestra</option>
    <optgroup label="Una vivienda simulada">
      ${ps.map((x) => `<option value="${x.bldg_id}" ${(isIndividual && String(x.bldg_id) === String(p?.bldg_id)) ? 'selected' : ''}>${esc(housingTypeName(x.housing_type))} · ${esc(x.state_code)} (#${x.bldg_id})</option>`).join('')}
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
    ? `<div class="ctl" style="margin-top:6px"><label>Zona horaria <select id="sel-tz">${allTzs.map((z) => `<option value="${esc(z)}" ${z === activeTz ? 'selected' : ''}>${esc(z)}</option>`).join('')}</select></label><span class="sub" style="font-size:12px;margin:0">Se separa por zona horaria para no mezclar horas locales distintas.</span></div>`
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
    ? chip('res', ['kWh por hora', `hora local ${tz}`, `#${p.bldg_id}`])
    : chip('res', ['kWh por hora', `hora local ${tz}`, 'promedio', `${state.type === 'ALL' ? 'todos los tipos' : housingTypeName(state.type)}`]);

  const limit = isIndividual
    ? 'Filas: meses; columnas: horas del día; color más intenso = más consumo (mediana). Es una sola vivienda simulada.'
    : 'Filas: meses; columnas: horas del día; color más intenso = más consumo (mediana por estado, tipo y zona horaria). <strong>Muestra simulada: no representa a la población ni a las ventas totales.</strong>';

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
  if (e) out.push(card({ id: 'C1', q: '¿Qué temperatura hubo en los puntos medidos?', accent: 'clim', body: e }));
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
        limit: 'Valores de un modelo de reanálisis (ERA5-Land) para celdas de terreno, no de estaciones meteorológicas.',
      }));
    }
  }
  const all = rowsOf('gold_climate');
  const days = all ? new Set(all.map((r) => r.timestamp_utc.slice(0, 10))).size : null;
  out.push(card({
    id: 'C2', q: '¿Se puede relacionar el clima con el consumo?', accent: 'none',
    body: empty('Todavía no', `Hay solo ${days ? `${days} días` : '7 días'} y ${all ? new Set(all.map((r) => r.point_id)).size : 2} puntos de clima, con un horario distinto al de las simulaciones (UTC frente a hora fija EST). Sin una regla de unión documentada no se dibuja una correlación ni se sugiere causa.`),
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
  const table = dataTable(['Periodo', 'Estado', 'Cambio vs. año anterior (%)', 'Estación', 'Puntuación robusta', 'Periodo', 'Etiqueta'],
    rows.map((r) => [r.period, r.state_code, +r.yoy_change_pct, r.season, +r.robust_z, r.partition, 'Candidato estadístico']), 60);
  const metrics = dataTable(['Cambio inyectado', 'Recall', 'Precisión', 'Falsos positivos', 'Casos positivos'],
    evals.map((r) => [`±${nf(+r.injection_pct)}%`, `${nf(+r.recall * 100, 1)}%`, `${nf(+r.precision * 100, 1)}%`, `${nf(+r.false_positive_rate * 100, 1)}%`, `${r.tp}/${r.tp + r.fn}`]));
  return `<div class="banner syn" role="note"><strong>Cómo leer esta vista:</strong> un «mes atípico» es un candidato estadístico que pide revisión, no un evento confirmado. La prueba de sensibilidad usa cambios artificiales (sintéticos) inyectados a propósito.</div>`
    + `<div class="grid g3">${card({ id: 'A1', q: 'Meses atípicos en datos definitivos', accent: 'eia', body: `<div class="big">${nf(counts.candidatos_entrenamiento + counts.candidatos_prueba)}<span class="unit">candidatos</span></div><p class="sub">${nf(counts.candidatos_entrenamiento)} en el periodo de ajuste · ${nf(counts.candidatos_prueba)} en el de prueba.</p>`, chips: chip('eia', ['51 estados', '2018–2025']), limit: 'Cambios que superan un umbral estadístico; requieren revisión humana.' })}
    ${card({ id: 'A2', q: 'Meses atípicos en datos preliminares', accent: 'eia', body: `<div class="big">${nf(counts.candidatos_preliminares_2026)}<span class="unit">candidatos</span></div><p class="sub">Se evalúan aparte y no se usan para fijar el umbral.</p>`, chips: preChip('2026, corte enero–agosto'), limit: 'Los valores preliminares de EIA pueden actualizarse.' })}
    ${card({ id: 'A3', q: '¿Detecta cambios artificiales? (prueba sintética)', accent: 'syn', body: metrics, chips: '<span class="chip syn"><i></i><b>Sintético</b> · cambios inyectados</span>', limit: 'Recall = cambios artificiales detectados; precisión = alertas que eran correctas. Detecta poco los cambios pequeños y no mide el desempeño ante eventos reales.' })}</div>`
    + card({ id: 'A4', q: `Lista de meses atípicos para revisar (${rows.length})`, accent: 'eia', body: table, chips: chip('eia', ['variación interanual', `k = 3.5 MAD`, `${state.from}…${state.to}`]), limit: 'Cada mes se compara con el mismo mes del año anterior. Se marca si el cambio se aleja más de 3.5 desviaciones robustas (MAD) de lo habitual para ese estado y estación, según el periodo de ajuste.' });
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
    series: [toSeries('actual_mwh', 'Real (EIA)', 'var(--eia)'), toSeries('naive_mwh', 'Referencia simple', 'var(--ink-2)', '6 4'), toSeries('model_mwh', 'Modelo', 'var(--res)')],
    xTicks: monthTicks.map((p) => ({ x: periods.indexOf(p), label: p })), xDomain: [0, periods.length - 1],
    yLabel: 'Ventas EIA (MWh)', xLabel: 'Mes evaluado', aria: 'Backtest mensual de ventas EIA: observado, naive estacional y modelo log-lineal con mes.', zeroBase: false,
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
  return `<div class="banner warn" role="note"><strong>Esto no es un pronóstico del futuro.</strong> El modelo aprendió con 2018–2023 y se comparó contra los meses reales de 2024–2025 (backtest). Los meses preliminares de 2026 no se usan.</div>`
    + `<div class="grid g3">${card({ id: 'E1', q: 'Error del modelo', accent: 'eia', body: `<div class="big">${nf(modelMetric, 2)}<span class="unit">%</span></div><p class="sub">${state.st === 'ALL' ? 'Mediana entre estados' : `Estado ${state.st}`}</p>`, chips: chip('eia', ['2018–2025', 'periodos separados']), limit: 'sMAPE: diferencia porcentual promedio entre lo estimado y lo real en 2024–2025. Menor es mejor.' })}
    ${card({ id: 'E2', q: 'Error de la referencia simple', accent: 'none', body: `<div class="big">${nf(naiveMetric, 2)}<span class="unit">%</span></div><p class="sub">El modelo mejora en ${nf(nWins)} de ${nf(byState.length)} estados del filtro.</p>`, chips: chip('eia', ['naive estacional']), limit: 'La referencia simple («naive estacional») repite los valores del último año de ajuste.' })}
    ${card({ id: 'E3', q: 'Meses evaluados', accent: 'none', body: `<div class="big">24<span class="unit">meses</span></div><p class="sub">${stateLabel} · 2024-01 a 2025-12.</p>`, chips: chip('eia', ['sin preliminares']), limit: 'Un solo corte temporal; los resultados pueden cambiar con otros periodos de evaluación.' })}</div>`
    + card({ id: 'E4', q: `Real frente a estimado · ${stateLabel}`, accent: 'eia', body: chart + lineTable, chips: chip('eia', ['MWh', 'backtest']), limit: 'Modelo log-lineal con tendencia y efecto del mes, ajustado solo con 2018–2023. No se extiende a 2026 ni a años futuros.' });
}

/* ---------- Flujo / Calidad ---------- */
const short = (h) => (h ? `${h.slice(0, 8)}…${h.slice(-6)}` : '—');
function viewCalidad() {
  const out = [];
  const showEia = state.source === 'ALL' || state.source === 'eia';
  const e = needTables(['gold_eia_monthly'], 'cobertura EIA');
  if (showEia) {
    if (e) out.push(card({ id: 'Q1', q: '¿Qué meses tiene cada estado en EIA?', accent: 'eia', body: e }));
    else {
      const rows = rowsOf('gold_eia_monthly'), years = [...new Set(rows.map((r) => r.period.slice(0, 4)))].sort();
      const cnt = new Map();
      for (const r of rows) { const k = `${r.state_code}|${r.period.slice(0, 4)}`, c = cnt.get(k) || { f: 0, p: 0 }; r.data_status === 'Final' ? c.f++ : c.p++; cnt.set(k, c); }
      const sts = eiaStates();
      const cell = (s, y) => { const c = cnt.get(`${s}|${y}`) || { f: 0, p: 0 }; const m = 12 - c.f - c.p; return `<td aria-label="${s} ${y}: ${c.f} finales, ${c.p} preliminares, ${m} faltantes"><span class="cell12" title="${c.f} finales · ${c.p} prelim. · ${m} faltantes">${'<i></i>'.repeat(c.f)}${'<i class="p"></i>'.repeat(c.p)}${'<i class="m"></i>'.repeat(m)}</span></td>`; };
      const tot = years.map((y) => rows.filter((r) => r.period.startsWith(y) && r.data_status !== 'Final').length);
      out.push(card({
        id: 'Q1', q: '¿Qué meses tiene cada estado en EIA?', accent: 'eia',
        body: `<ul class="legend"><li><span class="cell12"><i></i></span>mes definitivo</li><li><span class="cell12"><i class="p"></i></span>mes preliminar</li><li><span class="cell12"><i class="m"></i></span>mes faltante</li></ul>
        <div class="tbl-wrap" style="max-height:420px"><table class="t"><caption class="sr">Meses finales, preliminares y faltantes por estado y año</caption><thead><tr><th scope="col">Estado</th>${years.map((y) => `<th scope="col">${y}</th>`).join('')}</tr></thead><tbody>${sts.map((s) => `<tr class="${s === state.st ? 'sel' : ''}"><th scope="row">${s}</th>${years.map((y) => cell(s, y)).join('')}</tr>`).join('')}</tbody></table></div>
        <p class="sub">${sts.length} jurisdicciones · ${nf(rows.length)} registros. Meses preliminares por año: ${years.map((y, i) => `${y}: ${tot[i] / sts.length || 0}`).filter((_, i) => tot[i]).join(', ') || 'ninguno'} (por estado).</p>`,
        chips: chip('eia', ['meses por año', `${years[0]}…${years[years.length - 1]}`, `${sts.length} jurisdicciones`]),
        limit: 'En el año en curso (2026) faltan meses porque EIA aún no los publica; no es un error.',
      }));
    }
  }
  // Q2 manifiesto
  const man = store.manifest, ent = store.entries || {};
  const names = [...new Set([...Object.keys(TABLES), ...Object.keys(ent)])];
  const srcOf = (n) => ({ eia: 'EIA', resstock: 'ResStock', climate: 'Open-Meteo', demography: 'Census PEP + EIA' }[TABLES[n]?.source] || (ent[n]?.source ?? '—'));
  const keep = names.filter((n) => state.source === 'ALL' || (state.source === 'eia' && TABLES[n]?.source === 'eia') || (state.source === 'res' && TABLES[n]?.source === 'resstock') || (state.source === 'clim' && TABLES[n]?.source === 'climate') || (state.source === 'demo' && TABLES[n]?.source === 'demography'));
  const trs = keep.map((n) => {
    const s = store.tables[n], en = ent[n];
    const st = s ? ({ ok: `✔ cargada · ${s.validated}`, pending: '… pendiente de entrega', error: `✖ ${s.message}` }[s.status]) : 'listada; sin lector en esta versión';
    return `<tr><th scope="row"><code>${esc(n)}</code></th><td>${esc(srcOf(n))}</td><td class="n">${s?.status === 'ok' ? nf(s.rows.length) : '—'}${en?.rows != null ? ` / ${nf(en.rows)} manifiesto` : ''}</td><td class="n">${en?.bytes != null ? nf(en.bytes) : '—'}</td><td><code title="${esc(en?.sha256 || '')}">${short(en?.sha256)}</code></td><td>${Array.isArray(en?.inputs) ? `${en.inputs.length} entradas` : '—'}</td><td style="white-space:normal">${esc(st)}</td></tr>`;
  }).join('');
  out.push(card({
    id: 'Q2', q: '¿De dónde viene cada tabla y se verificó?', accent: 'none',
    body: `<p class="sub">Índice de datos (manifiesto): ${man ? `esquema ${esc(man.schema_version ?? man.manifest_version)} · origen ${/^[a-z]+:/i.test(DATA_BASE) ? 'externo configurado (dirección oculta)' : `local <code>${esc(DATA_BASE)}</code>`}` : esc(store.manifestMessage || 'no disponible')}</p><div class="tbl-wrap"><table class="t"><caption class="sr">Tablas Gold consumidas y su validación</caption><thead><tr><th scope="col">Tabla</th><th scope="col">Fuente</th><th class="n" scope="col">Filas</th><th class="n" scope="col">Bytes</th><th scope="col">SHA-256</th><th scope="col">Entradas</th><th scope="col">Estado</th></tr></thead><tbody>${trs}</tbody></table></div>`,
    limit: 'Al abrir el tablero se comparan filas, tamaño y huella SHA-256 de cada tabla con el manifiesto; si no coinciden, la tabla no se usa.',
  }));
  out.push(`<div class="grid g2">${card({ id: 'Q3', q: '¿Hay un flujo de datos en vivo?', body: empty('No', 'El tablero lee una copia local de datos ya procesados. Aún no hay salida de reproducción del pipeline (<code>replay_id</code>, <code>ingested_at_utc</code>) y no se simula un estado «en vivo».') })}
  ${card({ id: 'Q4', q: '¿Qué controles de calidad se aplicaron?', body: empty('Pendiente', 'Se mostrarán cuando el procesamiento en Spark exporte <code>quality_status</code> y <code>quality_flags</code> al manifiesto.') })}</div>`);
  return out.join('');
}

/* ---------- filtros ---------- */
function rules() {
  const v = state.view, on = { on: true }, off = (why) => ({ on: false, why });
  const nothing = (why) => ({ st: off(why), period: off(why), type: off(why), source: off(why), gran: off(why), prelim: off(why), profile: off(why) });
  if (v === 'anomalias') {
    const R = nothing('Esta vista solo se filtra por estado y periodo.');
    R.st = on; R.period = on;
    return R;
  }
  if (v === 'estimaciones') {
    const R = nothing('El periodo evaluado es fijo (2024–2025); solo cambia el estado.');
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
// Los filtros que no aplican a la vista se ocultan (su valor se conserva) y se listan en una nota.
const fld = (id, label, control, why, r = { on: true }) => (r.on ? `<div class="fld"><label for="${id}">${label}</label>${control}${why ? `<span class="why" id="why-${id}">${esc(why)}</span>` : ''}</div>` : '');
function renderFilters() {
  const focus = document.activeElement?.id;
  const R = rules(), [lo, hi] = periodBounds();
  if (!state.from) { state.from = lo; state.to = hi; }
  const months = []; for (let [y, m] = lo.split('-').map(Number); `${y}-${String(m).padStart(2, '0')}` <= hi; m === 12 ? (y++, m = 1) : m++) months.push(`${y}-${String(m).padStart(2, '0')}`);
  const sel = (id, opts, val, r, extra = '') => `<select id="${id}" ${r.on ? '' : 'disabled'} ${r.on ? '' : `aria-describedby="why-${id}"`} ${extra}>${opts.map(([v, l, d]) => `<option value="${esc(v)}" ${String(v) === String(val) ? 'selected' : ''} ${d ? 'disabled' : ''}>${esc(l)}</option>`).join('')}</select>`;
  const sts = [['ALL', 'Todo EE. UU. (50 estados + DC)'], ...eiaStates().map((s) => [s, `${jurisdictionName(s)} (${s})${resStates().includes(s) ? ' ★' : ''}`])];
  if (sts.length === 1) for (const s of ['CO', 'NY']) sts.push([s, s]);
  const stWhy = !R.st.on ? R.st.why : ((w) => (w === 'patrones' || w === 'clima' || w === 'resumen') ? `Simulaciones: ${resStates().join(', ') || '—'} · Clima: ${[...new Set((rowsOf('gold_climate') || []).map((r) => r.state_code))].join(', ') || '—'}. En otros estados esas tarjetas aparecen vacías.` : 'Elige un estado o el total del país. ★ = tiene viviendas simuladas.')(state.view);
  const types = resTypes();
  const typeWhy = R.type.on ? (statusOf('gold_resstock_profile_summary') === 'ok' ? 'Solo cambia las viviendas simuladas.' : 'Esperando la tabla de viviendas simuladas.') : R.type.why;
  const ps = profiles(), cp = currentProfile();
  const html = [
    fld('f-st', 'Estado', sel('f-st', sts, state.st, R.st), stWhy, R.st),
    fld('f-from', 'Desde (mes)', sel('f-from', months.map((m) => [m, m]), state.from, R.period), `Ventas EIA: ${lo} a ${hi}. Simulaciones: solo 2018.`, R.period),
    fld('f-to', 'Hasta (mes)', sel('f-to', months.map((m) => [m, m]), state.to, R.period), 'Clima: solo 1–7 ene 2018.', R.period),
    fld('f-type', 'Tipo de vivienda', sel('f-type', [['ALL', 'Todos los tipos'], ...types.map((t) => [t, housingTypeName(t)])], state.type, R.type), typeWhy, R.type),
    fld('f-profile', 'Vivienda simulada', sel('f-profile', [
      ['ALL', 'Promedio de la muestra'],
      ...ps.map((p) => [p.bldg_id, `${housingTypeName(p.housing_type)} · ${p.state_code} (#${p.bldg_id})`])
    ], state.profile || 'ALL', R.profile), 'El promedio o una vivienda concreta.', R.profile),
    fld('f-source', 'Fuente de datos', sel('f-source', [['ALL', 'Todas las fuentes'], ['eia', 'Ventas EIA (oficial)'], ['res', 'Simulaciones ResStock'], ['clim', 'Clima (Open-Meteo)'], ['demo', 'Población (Census + EIA)']], state.source, R.source), 'Muestra solo las tarjetas de esa fuente.', R.source),
    fld('f-gran', 'Detalle de tiempo', sel('f-gran', [['monthly', 'Por mes' + (state.view === 'clima' ? ' (no aplica: 7 días)' : ''), state.view === 'clima'], ['hourly', 'Por hora del día']], state.view === 'clima' ? 'hourly' : state.gran, R.gran), state.view === 'clima' ? 'El clima solo tiene datos por hora.' : 'Por mes: meses y estados. Por hora: horario de uso.', R.gran),
    fld('f-prelim', 'Meses preliminares', `<label class="tog"><input type="checkbox" id="f-prelim" ${state.prelim ? 'checked' : ''}> Incluir</label>`, 'Meses recientes que EIA aún puede corregir.', R.prelim),
  ].join('');
  const NAMES = { st: 'estado', period: 'periodo', type: 'tipo de vivienda', profile: 'vivienda simulada', source: 'fuente', gran: 'detalle de tiempo', prelim: 'preliminares' };
  const offs = Object.entries(R).filter(([, r]) => !r.on);
  const note = offs.length ? `<p class="filters-note">No aplican aquí: ${offs.map(([k]) => NAMES[k]).join(', ')}. ${new Set(offs.map(([, r]) => r.why)).size === 1 ? esc(offs[0][1].why || '') : ''}</p>` : '';
  $('#filters').innerHTML = html + note;
  $('#filters-count').textContent = `${Object.values(R).filter((r) => r.on).length} disponibles`;
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
  $('#rail').innerHTML = `<div class="brand"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3l12 7v12l-12 7-12-7V10z" fill="#2453c7"/><path d="M16 3l12 7-12 7-12-7z" fill="#7aa2f7"/><path d="M16 17v12l12-7V10z" fill="#1b3f9c"/></svg><span><b>Consumo eléctrico</b><small>residencial · EE. UU.</small></span></div>`
    + `<p class="rail-h">Vistas</p><ul class="nav">${VIEWS.map((x) => `<li><a href="#${x.id}" ${x.id === state.view ? 'aria-current="page"' : ''} aria-label="${esc(x.label)}">${x.icon}<span class="rail-lbl"><span class="lbl-full">${esc(x.label)}</span><span class="lbl-short">${esc(x.short || x.label)}</span></span></a></li>`).join('')}</ul>`
    + `<div class="legend-src"><p class="rail-h">Colores por fuente</p><ul><li><i class="eia"></i>Ventas EIA · oficial</li><li><i class="res"></i>ResStock · simulado</li><li><i class="demo"></i>Población · oficial</li><li><i class="clim"></i>Clima · reanálisis</li><li><i class="syn"></i>Prueba sintética</li><li><i class="pre"></i>Preliminar</li></ul></div>`;
}
function renderStatus() {
  const n = Object.keys(TABLES).length;
  const available = Object.entries(store.tables).filter(([name, t]) =>
    t.status === 'ok' || t.status === 'loading' || (t.status === 'lazy' && Boolean(store.entries?.[name]))
  ).length;
  const ms = store.manifestStatus;
  $('#load-status').innerHTML = ms === 'loading' ? '<span class="pill">Cargando datos…</span>' : `<span class="pill ${ms === 'ok' ? 'ok' : 'bad'}" title="Copia local de datos procesados; no es una conexión en vivo"><i></i>Datos locales ${{ ok: 'verificados', missing: 'sin manifiesto', error: 'con error' }[ms]}</span><span class="pill">${available} de ${n} tablas</span>`;
  const profileCount = rowsOf('gold_resstock_profile_summary')?.length;
  const note = $('#project-note');
  if (note) note.textContent = `Proyecto académico exploratorio. Datos de una copia local, no en vivo. ResStock aporta ${profileCount == null ? 'viviendas simuladas' : `${nf(profileCount)} viviendas simuladas`} que no representan hogares reales ni a la población. EIA son ventas agregadas por estado. Las ilustraciones son exteriores conceptuales.`;
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
  main.querySelectorAll('[data-pick-type]').forEach((b) => b.addEventListener('click', () => { state.type = b.dataset.pickType; state.profile = null; render(); }));
  main.querySelectorAll('[data-day]').forEach((b) => b.addEventListener('click', () => { state.day = b.dataset.day; render(); }));
  main.querySelectorAll('[data-demo-year]').forEach((b) => b.addEventListener('click', () => {
    state.demoYear = Number(b.dataset.demoYear);
    render();
  }));
  main.querySelector('#chk-demo-dc')?.addEventListener('change', (e) => {
    state.demoIncludeDc = e.target.checked;
    render();
  });
  main.querySelectorAll('[data-demo-sort]').forEach((th) => th.addEventListener('click', () => {
    const col = th.dataset.demoSort;
    if (state.demoSortCol === col) {
      state.demoSortAsc = !state.demoSortAsc;
    } else {
      state.demoSortCol = col;
      state.demoSortAsc = false;
    }
    render();
  }));
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
