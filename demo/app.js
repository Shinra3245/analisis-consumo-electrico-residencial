/**
 * Visor de consumo eléctrico residencial en Colorado - JavaScript Vanilla
 * Sin dependencias externas, sin llamadas a red, 100% autónomo.
 * Cifras y hechos obtenidos exclusivamente de los documentos del proyecto.
 */

// Datos documentados verificados (2018, Colorado)
const MONTHLY_DATA = [
  {
    month: "Ene",
    monthName: "Enero",
    resstockMwh: 1812597.23,
    eiaMwh: 1653911.40,
    ratio: 109.59,
    season: "Invierno",
    notes: "ResStock registra 1,812,597.23 MWh y EIA 1,653,911.40 MWh. La razón mensual es 109.59%; este análisis no atribuye la diferencia a una causa."
  },
  {
    month: "Feb",
    monthName: "Febrero",
    resstockMwh: 1667852.33,
    eiaMwh: 1452241.20,
    ratio: 114.85,
    season: "Invierno",
    notes: "Es la razón mensual más alta observada (114.85%). La comparación es descriptiva y no explica por qué difieren las fuentes."
  },
  {
    month: "Mar",
    monthName: "Marzo",
    resstockMwh: 1322864.87,
    eiaMwh: 1456725.50,
    ratio: 90.81,
    season: "Primavera",
    notes: "La razón mensual es 90.81%. ResStock registra 1,322,864.87 MWh y EIA 1,456,725.50 MWh."
  },
  {
    month: "Abr",
    monthName: "Abril",
    resstockMwh: 1147907.04,
    eiaMwh: 1297995.10,
    ratio: 88.44,
    season: "Primavera",
    notes: "EIA registra 1,297,995.10 MWh, su menor total mensual del año dentro de esta serie."
  },
  {
    month: "May",
    monthName: "Mayo",
    resstockMwh: 1114155.94,
    eiaMwh: 1429900.70,
    ratio: 77.92,
    season: "Primavera",
    notes: "ResStock registra su menor total mensual de la serie: 1,114,155.94 MWh."
  },
  {
    month: "Jun",
    monthName: "Junio",
    resstockMwh: 1343082.37,
    eiaMwh: 1783312.10,
    ratio: 75.31,
    season: "Verano",
    notes: "EIA registra 1,783,312.10 MWh y ResStock 1,343,082.37 MWh. La gráfica muestra su diferencia mensual."
  },
  {
    month: "Jul",
    monthName: "Julio",
    resstockMwh: 1512931.30,
    eiaMwh: 2042863.00,
    ratio: 74.06,
    season: "Verano",
    notes: "EIA alcanza su mayor total mensual de la serie: 2,042,863.00 MWh. La razón mensual es 74.06%."
  },
  {
    month: "Ago",
    monthName: "Agosto",
    resstockMwh: 1362359.35,
    eiaMwh: 1994351.80,
    ratio: 68.31,
    season: "Verano",
    notes: "Es la razón mensual más baja observada (68.31%). La diferencia entre fuentes no se atribuye a una causa."
  },
  {
    month: "Sep",
    monthName: "Septiembre",
    resstockMwh: 1212696.57,
    eiaMwh: 1658108.00,
    ratio: 73.14,
    season: "Otoño",
    notes: "La razón mensual es 73.14%. Es una comparación entre fuentes con coberturas distintas, no un análisis causal."
  },
  {
    month: "Oct",
    monthName: "Octubre",
    resstockMwh: 1138391.12,
    eiaMwh: 1404371.80,
    ratio: 81.06,
    season: "Otoño",
    notes: "ResStock registra su segundo menor total mensual de la serie: 1,138,391.12 MWh."
  },
  {
    month: "Nov",
    monthName: "Noviembre",
    resstockMwh: 1401276.70,
    eiaMwh: 1448118.50,
    ratio: 96.77,
    season: "Otoño",
    notes: "La razón mensual es 96.77%. La cercanía numérica no implica que las coberturas de ambas fuentes sean equivalentes."
  },
  {
    month: "Dic",
    monthName: "Diciembre",
    resstockMwh: 1773538.48,
    eiaMwh: 1665052.90,
    ratio: 106.52,
    season: "Invierno",
    notes: "ResStock registra 1,773,538.48 MWh y EIA 1,665,052.90 MWh. La razón mensual es 106.52%."
  }
];

// Totales anuales documentados
const ANNUAL_TOTALS = {
  resstockMwh: 16809653.30,
  eiaMwh: 19286952.00,
  ratio: 87.16
};

// Estado interactivo de la aplicación
const state = {
  currentView: "lines", // 'lines', 'bars', 'ratio'
  selectedSeason: "all",
  activeMonthIndex: 0 // Enero por defecto
};

// Inicialización cuando carga el DOM
document.addEventListener("DOMContentLoaded", () => {
  renderTable();
  renderChart();
  updateMonthInspector(state.activeMonthIndex);
  setupEventListeners();
  updateChartGuide();
});

function setupEventListeners() {
  // Tabs de vistas
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-pressed", String(b === btn));
      });
      state.currentView = btn.getAttribute("data-view");
      updateChartGuide();
      renderChart();
    });
  });

  // Filtros de temporada
  document.querySelectorAll(".chip-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".chip-btn").forEach(b => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-pressed", String(b === btn));
      });
      state.selectedSeason = btn.getAttribute("data-season");
      filterData();
    });
  });

  // Selección de mes desde la tabla (delegado)
  const tbody = document.getElementById("data-tbody");
  if (tbody) {
    tbody.addEventListener("click", (e) => {
      const tr = e.target.closest("tr[data-index]");
      if (tr) selectMonth(parseInt(tr.getAttribute("data-index"), 10));
    });
  }
}

function isInSeason(d) {
  return state.selectedSeason === "all" || d.season === state.selectedSeason;
}

function filterData() {
  const filtered = MONTHLY_DATA.filter(isInSeason);

  // Recalcular subtotal seleccionado
  let sumRes = 0;
  let sumEia = 0;
  filtered.forEach(d => {
    sumRes += d.resstockMwh;
    sumEia += d.eiaMwh;
  });
  const subRatio = sumEia > 0 ? ((sumRes / sumEia) * 100).toFixed(2) : "0.00";

  const summaryEl = document.getElementById("filter-summary");
  if (summaryEl) {
    if (state.selectedSeason === "all") {
      summaryEl.innerHTML = `Mostrando: <strong>12 meses (Año completo)</strong> | Relación anual: <strong>87.16%</strong>`;
    } else {
      summaryEl.innerHTML = `Filtro <strong>${state.selectedSeason}</strong> (${filtered.length} meses): ResStock <strong>${formatNumber(sumRes)} MWh</strong> · EIA <strong>${formatNumber(sumEia)} MWh</strong> · Relación: <strong>${subRatio}%</strong>`;
    }
  }

  // Atenuar filas fuera de la temporada
  document.querySelectorAll("#data-tbody tr").forEach((tr, index) => {
    tr.classList.toggle("dimmed", !isInSeason(MONTHLY_DATA[index]));
  });

  renderChart();
}

function updateChartGuide() {
  const guide = document.getElementById("chart-guide");
  const ratioLegend = document.getElementById("legend-ratio");
  const explanations = {
    lines: "El eje horizontal muestra los meses y el vertical, el consumo mensual en MWh. En cada mes, la línea verde muestra el perfil de viviendas unifamiliares de ResStock; la azul, las ventas de todo el sector residencial reportadas por EIA.",
    bars: "Cada par de barras corresponde a un mes. El eje vertical muestra MWh: verde representa el consumo modelado de ResStock y azul, las ventas residenciales de EIA.",
    ratio: "El eje horizontal muestra los meses y el vertical, el porcentaje ResStock/EIA. Cada punto es ResStock ÷ EIA × 100. El 100% indica el mismo valor numérico; por sus coberturas distintas, no representa la participación real de las viviendas unifamiliares."
  };
  if (guide) {
    guide.innerHTML = `<strong>Cómo leer la gráfica:</strong> ${explanations[state.currentView]}`;
  }
  if (ratioLegend) ratioLegend.hidden = state.currentView !== "ratio";
}

function selectMonth(index, opts = {}) {
  state.activeMonthIndex = index;

  document.querySelectorAll("#data-tbody tr").forEach((tr, idx) => {
    const active = idx === index;
    tr.classList.toggle("selected-row", active);
    const btn = tr.querySelector(".row-btn");
    if (btn) btn.setAttribute("aria-pressed", String(active));
  });

  updateMonthInspector(index);
  renderChart();

  if (opts.focusChart) {
    const col = document.querySelector(`.chart-month-col[data-index="${index}"]`);
    if (col) col.focus();
  }
}

function ratioClass(ratio) {
  return ratio >= 100 ? "ratio-high" : ratio >= 80 ? "ratio-mid" : "ratio-low";
}

function updateMonthInspector(index) {
  const item = MONTHLY_DATA[index];
  if (!item) return;

  const diffMwh = item.resstockMwh - item.eiaMwh;
  const diffSign = diffMwh >= 0 ? "+" : "";

  const container = document.getElementById("month-inspector");
  if (!container) return;

  container.innerHTML = `
    <div class="inspector-title">
      <span>Detalle del mes: <strong>${item.monthName} 2018</strong></span>
      <span class="ratio-pill ${ratioClass(item.ratio)}">
        Relación: ${item.ratio.toFixed(2)}%
      </span>
    </div>
    <div class="inspector-stats">
      <div class="inspector-stat-item">
        <span class="inspector-stat-label">Perfil modelado (ResStock)</span>
        <span class="inspector-stat-val c-res">${formatNumber(item.resstockMwh)} MWh</span>
      </div>
      <div class="inspector-stat-item">
        <span class="inspector-stat-label">Estadística oficial (EIA)</span>
        <span class="inspector-stat-val c-eia">${formatNumber(item.eiaMwh)} MWh</span>
      </div>
      <div class="inspector-stat-item">
        <span class="inspector-stat-label">Diferencia entre fuentes</span>
        <span class="inspector-stat-val">${diffSign}${formatNumber(diffMwh)} MWh</span>
      </div>
      <div class="inspector-stat-item">
        <span class="inspector-stat-label">Temporada</span>
        <span class="inspector-stat-val">${item.season}</span>
      </div>
    </div>
    <div class="inspector-notes">
      <strong>Lectura:</strong> ${item.notes}
    </div>
  `;
}

function renderTable() {
  const tbody = document.getElementById("data-tbody");
  if (!tbody) return;

  let html = "";
  MONTHLY_DATA.forEach((item, index) => {
    const diff = item.resstockMwh - item.eiaMwh;
    const diffSign = diff >= 0 ? "+" : "";
    const active = index === state.activeMonthIndex;

    html += `
      <tr data-index="${index}" class="${active ? "selected-row" : ""}">
        <td>
          <button type="button" class="row-btn" aria-pressed="${active}" aria-label="Ver detalle de ${item.monthName}">${item.month}</button>
          <span class="season">(${item.season})</span>
        </td>
        <td class="text-right"><span class="c-res">${formatNumber(item.resstockMwh)}</span></td>
        <td class="text-right"><span class="c-eia">${formatNumber(item.eiaMwh)}</span></td>
        <td class="text-center">
          <span class="ratio-pill ${ratioClass(item.ratio)}">${item.ratio.toFixed(2)}%</span>
        </td>
        <td class="text-right c-muted">${diffSign}${formatNumber(diff)}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;

  const tfoot = document.getElementById("data-tfoot");
  if (tfoot) {
    const totalDiff = ANNUAL_TOTALS.resstockMwh - ANNUAL_TOTALS.eiaMwh;
    tfoot.innerHTML = `
      <tr class="total-row">
        <td>Total Anual 2018</td>
        <td class="text-right c-res">${formatNumber(ANNUAL_TOTALS.resstockMwh)}</td>
        <td class="text-right c-eia">${formatNumber(ANNUAL_TOTALS.eiaMwh)}</td>
        <td class="text-center">
          <span class="ratio-pill ratio-mid">${ANNUAL_TOTALS.ratio.toFixed(2)}%</span>
        </td>
        <td class="text-right">${formatNumber(totalDiff)}</td>
      </tr>
    `;
  }
}

function renderChart() {
  const container = document.getElementById("chart-svg-container");
  if (!container) return;

  const width = 960;
  const height = 400;
  const margin = { top: 35, right: 35, bottom: 50, left: 80 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  let svgContent = "";
  let label = "";

  if (state.currentView === "lines") {
    svgContent = generateLineChartSvg(innerWidth, innerHeight, margin);
    label = "Gráfica de líneas mensuales ResStock frente a EIA";
  } else if (state.currentView === "bars") {
    svgContent = generateBarChartSvg(innerWidth, innerHeight, margin);
    label = "Gráfica de barras mensuales ResStock frente a EIA";
  } else if (state.currentView === "ratio") {
    svgContent = generateRatioChartSvg(innerWidth, innerHeight, margin);
    label = "Gráfica de la relación mensual ResStock/EIA";
  }

  container.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="group" aria-label="${label}. Cada mes es un botón seleccionable.">
      <defs>
        <pattern id="hatch-eia" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect class="hatch-bg" width="6" height="6" />
          <line class="hatch-ln" x1="0" y1="0" x2="0" y2="6" />
        </pattern>
      </defs>
      ${svgContent}
    </svg>
  `;

  attachSvgInteractions();
}

// Atributos comunes de la columna interactiva de un mes
function monthColAttrs(d, i) {
  const classes = ["chart-month-col"];
  if (i === state.activeMonthIndex) classes.push("selected");
  if (!isInSeason(d)) classes.push("dimmed");
  const aria = `${d.monthName} 2018: ResStock ${formatNumber(d.resstockMwh)} MWh, EIA ${formatNumber(d.eiaMwh)} MWh, razón ${d.ratio.toFixed(2)}%`;
  return `class="${classes.join(" ")}" data-index="${i}" tabindex="0" role="button" aria-pressed="${i === state.activeMonthIndex}" aria-label="${aria}"`;
}

function yAxisMwh(w, h, margin, maxVal) {
  let gridSvg = "";
  [0, 500000, 1000000, 1500000, 2000000].forEach(tick => {
    const y = margin.top + h - (tick / maxVal) * h;
    const label = (tick / 1000000).toFixed(1) + "M";
    gridSvg += `
      <line class="grid-line" x1="${margin.left}" y1="${y}" x2="${margin.left + w}" y2="${y}" />
      <text class="ax-text" x="${margin.left - 12}" y="${y + 4}" text-anchor="end">${label}</text>
    `;
  });
  return gridSvg;
}

// Zona seleccionable recortada al área de trazado para no tapar las etiquetas de los ejes
function hitRect(x0, width, margin, w, h) {
  const x1 = Math.max(x0, margin.left);
  const x2 = Math.min(x0 + width, margin.left + w);
  return `<rect class="hit" x="${x1}" y="${margin.top}" width="${x2 - x1}" height="${h}" rx="4" />`;
}

function monthLabel(d, i, x, y) {
  return `<text class="ax-text${i === state.activeMonthIndex ? " sel" : ""}" x="${x}" y="${y}" text-anchor="middle">${d.month}</text>`;
}

function generateLineChartSvg(w, h, margin) {
  const maxVal = 2200000; // 2.2M MWh
  const stepX = w / (MONTHLY_DATA.length - 1);

  const pointsRes = [];
  const pointsEia = [];
  let xLabels = "";
  let interactionSvg = "";

  MONTHLY_DATA.forEach((d, i) => {
    const x = margin.left + i * stepX;
    const yRes = margin.top + h - (d.resstockMwh / maxVal) * h;
    const yEia = margin.top + h - (d.eiaMwh / maxVal) * h;
    const sel = i === state.activeMonthIndex;
    const r = sel ? 7 : 5;

    pointsRes.push(`${x},${yRes}`);
    pointsEia.push(`${x},${yEia}`);
    xLabels += monthLabel(d, i, x, margin.top + h + 22);

    interactionSvg += `
      <g ${monthColAttrs(d, i)}>
        ${hitRect(x - stepX / 2, stepX, margin, w, h)}
        <circle class="pt-res" cx="${x}" cy="${yRes}" r="${r}" />
        <rect class="pt-eia" x="${x - r}" y="${yEia - r}" width="${r * 2}" height="${r * 2}" rx="1.5" />
      </g>
    `;
  });

  return `
    <text class="chart-title" x="${margin.left}" y="20">Comparación mensual temporal: ResStock (modelado) vs EIA (ventas oficiales) [MWh]</text>
    ${yAxisMwh(w, h, margin, maxVal)}
    <polyline class="ln-res" points="${pointsRes.join(" ")}" />
    <polyline class="ln-eia" points="${pointsEia.join(" ")}" />
    ${xLabels}
    ${interactionSvg}
  `;
}

function generateBarChartSvg(w, h, margin) {
  const maxVal = 2200000;
  const groupWidth = w / MONTHLY_DATA.length;
  const barWidth = groupWidth * 0.35;

  let barsSvg = "";
  let xLabels = "";

  MONTHLY_DATA.forEach((d, i) => {
    const groupX = margin.left + i * groupWidth;
    const xRes = groupX + groupWidth * 0.12;
    const xEia = xRes + barWidth + 3;

    const barHRes = (d.resstockMwh / maxVal) * h;
    const barHEia = (d.eiaMwh / maxVal) * h;

    xLabels += monthLabel(d, i, groupX + groupWidth / 2, margin.top + h + 22);

    barsSvg += `
      <g ${monthColAttrs(d, i)}>
        ${hitRect(groupX, groupWidth, margin, w, h)}
        <rect class="bar-res" x="${xRes}" y="${margin.top + h - barHRes}" width="${barWidth}" height="${barHRes}" rx="2" />
        <rect class="bar-eia" x="${xEia}" y="${margin.top + h - barHEia}" width="${barWidth}" height="${barHEia}" rx="2" />
      </g>
    `;
  });

  return `
    <text class="chart-title" x="${margin.left}" y="20">Comparación en barras apareadas por mes (MWh)</text>
    ${yAxisMwh(w, h, margin, maxVal)}
    ${barsSvg}
    ${xLabels}
  `;
}

function generateRatioChartSvg(w, h, margin) {
  const maxVal = 130; // 130%
  const minVal = 50;  // 50%
  const stepX = w / (MONTHLY_DATA.length - 1);
  const yOf = v => margin.top + h - ((v - minVal) / (maxVal - minVal)) * h;

  let gridSvg = "";
  [60, 80, 100, 120].forEach(tick => {
    const y = yOf(tick);
    gridSvg += `
      <line class="${tick === 100 ? "base-line" : "grid-line"}" x1="${margin.left}" y1="${y}" x2="${margin.left + w}" y2="${y}" />
      <text class="${tick === 100 ? "base-text" : "ax-text"}" x="${margin.left - 12}" y="${y + 4}" text-anchor="end">${tick}%</text>
    `;
  });

  // Línea de referencia 100% etiqueta
  gridSvg += `
    <text class="base-text" x="${margin.left + w - 5}" y="${yOf(100) - 6}" text-anchor="end">Línea base de igualdad de escala (100%)</text>
  `;

  const pointsRatio = [];
  let xLabels = "";
  let interactionSvg = "";

  MONTHLY_DATA.forEach((d, i) => {
    const x = margin.left + i * stepX;
    const yRatio = yOf(d.ratio);
    pointsRatio.push(`${x},${yRatio}`);
    xLabels += monthLabel(d, i, x, margin.top + h + 22);

    interactionSvg += `
      <g ${monthColAttrs(d, i)}>
        ${hitRect(x - stepX / 2, stepX, margin, w, h)}
        <circle class="pt-ratio" cx="${x}" cy="${yRatio}" r="${i === state.activeMonthIndex ? 7 : 5}" />
        <text class="ratio-label" x="${x}" y="${yRatio - 11}" text-anchor="middle">${d.ratio.toFixed(1)}%</text>
      </g>
    `;
  });

  return `
    <text class="chart-title" x="${margin.left}" y="20">Relación mensual ResStock/EIA (%)</text>
    ${gridSvg}
    <polyline class="ln-ratio" points="${pointsRatio.join(" ")}" />
    ${xLabels}
    ${interactionSvg}
  `;
}

function attachSvgInteractions() {
  const tooltip = document.getElementById("chart-tooltip");
  const chartBox = document.querySelector(".chart-container");
  if (!tooltip || !chartBox) return;

  const show = (col) => {
    const d = MONTHLY_DATA[parseInt(col.getAttribute("data-index"), 10)];
    tooltip.innerHTML = `
      <div><strong>${d.monthName} 2018 (${d.season})</strong></div>
      <div>ResStock: ${formatNumber(d.resstockMwh)} MWh</div>
      <div>EIA: ${formatNumber(d.eiaMwh)} MWh</div>
      <div><strong>Relación: ${d.ratio.toFixed(2)}%</strong></div>
    `;
    tooltip.style.opacity = "1";
  };
  const hide = () => { tooltip.style.opacity = "0"; };

  document.querySelectorAll(".chart-month-col").forEach(col => {
    const index = parseInt(col.getAttribute("data-index"), 10);

    col.addEventListener("click", () => selectMonth(index, { focusChart: true }));

    col.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectMonth(index, { focusChart: true });
      } else if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        const next = Math.min(MONTHLY_DATA.length - 1, Math.max(0, index + (e.key === "ArrowRight" ? 1 : -1)));
        selectMonth(next, { focusChart: true });
      } else if (e.key === "Escape") {
        hide();
      }
    });

    col.addEventListener("mouseenter", () => show(col));
    col.addEventListener("mouseleave", hide);
    col.addEventListener("mousemove", (e) => {
      const rect = chartBox.getBoundingClientRect();
      const tipW = tooltip.offsetWidth;
      let x = e.clientX - rect.left + 15;
      if (x + tipW > rect.width) x = e.clientX - rect.left - tipW - 15;
      tooltip.style.left = `${Math.max(0, x)}px`;
      tooltip.style.top = `${e.clientY - rect.top + 15}px`;
    });

    col.addEventListener("focus", () => {
      show(col);
      const rect = chartBox.getBoundingClientRect();
      const c = col.getBoundingClientRect();
      const tipW = tooltip.offsetWidth;
      const x = Math.min(Math.max(0, c.left - rect.left + c.width / 2 - tipW / 2), Math.max(0, rect.width - tipW));
      tooltip.style.left = `${x}px`;
      tooltip.style.top = `${Math.max(0, c.top - rect.top + 8)}px`;
    });
    col.addEventListener("blur", hide);
  });
}

function formatNumber(num) {
  return new Intl.NumberFormat("es-MX", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
}
