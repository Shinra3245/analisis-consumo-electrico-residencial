#!/usr/bin/env python3
"""Analiza una muestra acotada de ResStock, EIA y Open-Meteo para el MVP.

Con --descargar obtiene únicamente un agregado de Colorado, el libro público
mensual de EIA y una serie meteorológica horaria de Denver para 2018. Los
archivos originales se guardan en data/raw/ (ignorada por Git). El análisis
no trata estos productos como mediciones equivalentes ni ejecuta una unión
horaria de las tres fuentes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESSTOCK_NAME = "up00-co-single-family_detached.csv"
EIA_NAME = "eia_sales_revenue.xlsx"
WEATHER_NAME = "openmeteo_denver_2018.json"
RESSTOCK_URL = (
    "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"
    "end-use-load-profiles-for-us-building-stock/2025/"
    "resstock_amy2018_release_1/timeseries_aggregates/by_state/"
    "upgrade=0/state=CO/up00-co-single-family_detached.csv"
)
EIA_URL = "https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx"
WEATHER_PARAMS = {
    "latitude": "39.7392",
    "longitude": "-104.9903",
    "start_date": "2018-01-01",
    "end_date": "2018-12-31",
    "hourly": "temperature_2m",
    "timezone": "GMT",
}
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(
    WEATHER_PARAMS
)
ENERGY_COLUMN = "out.electricity.total.energy_consumption..kwh"
MONTH_NAMES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "BigDataAcademicProject/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response, path.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)


def ensure_inputs(download_sources: bool) -> tuple[Path, Path, Path]:
    paths = (RAW / RESSTOCK_NAME, RAW / EIA_NAME, RAW / WEATHER_NAME)
    urls = (RESSTOCK_URL, EIA_URL, WEATHER_URL)
    if download_sources:
        for url, path in zip(urls, paths):
            if not path.exists():
                print(f"Descargando {path.relative_to(ROOT)}")
                download(url, path)
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    if missing:
        raise SystemExit(
            "Faltan archivos fuente locales: " + ", ".join(missing)
            + ". Ejecute con --descargar o coloque las fuentes en data/raw/."
        )
    return paths


def analyze_resstock(path: Path) -> dict:
    required = {
        "upgrade", "in.state", "in.geometry_building_type_recs", "timestamp",
        "models_used", "units_represented", ENERGY_COLUMN,
    }
    monthly_kwh: dict[int, float] = defaultdict(float)
    timestamps: list[datetime] = []
    first_identity: tuple[str, str, str] | None = None
    first_models: str | None = None
    first_units: str | None = None
    rows = 0
    null_cells = 0
    negative_total = 0
    minimum_kwh = math.inf
    maximum_kwh = -math.inf

    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("La cabecera ResStock no contiene todos los campos esperados.")
        for row in reader:
            rows += 1
            null_cells += sum(value in (None, "") for value in row.values())
            identity = (row["upgrade"], row["in.state"], row["in.geometry_building_type_recs"])
            if first_identity is None:
                first_identity = identity
                first_models = row["models_used"]
                first_units = row["units_represented"]
            elif identity != first_identity:
                raise ValueError("La muestra contiene más de un escenario, estado o tipo de vivienda.")
            if row["models_used"] != first_models or row["units_represented"] != first_units:
                raise ValueError("Los campos de ponderación no son constantes en el agregado.")
            timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            timestamps.append(timestamp)
            kwh = float(row[ENERGY_COLUMN])
            minimum_kwh = min(minimum_kwh, kwh)
            maximum_kwh = max(maximum_kwh, kwh)
            negative_total += kwh < 0
            # La marca temporal es el final del intervalo. Restar 15 min
            # asigna correctamente el intervalo 23:45–00:00 al mes anterior.
            month = (timestamp - timedelta(minutes=15)).month
            monthly_kwh[month] += kwh

    deltas = [(b - a).total_seconds() / 60 for a, b in zip(timestamps, timestamps[1:])]
    if rows != 35040:
        raise ValueError(f"Se esperaban 35040 intervalos para 2018 y se encontraron {rows}.")
    if len(set(timestamps)) != rows:
        raise ValueError("La muestra tiene timestamps duplicados.")
    if deltas and set(deltas) != {15.0}:
        raise ValueError(f"La secuencia no mantiene intervalos de 15 minutos: {sorted(set(deltas))}.")
    if null_cells:
        raise ValueError(f"La muestra tiene {null_cells} celdas vacías.")
    if negative_total:
        raise ValueError(f"La energía total tiene {negative_total} valores negativos.")
    total_mwh = sum(monthly_kwh.values()) / 1000
    return {
        "source_url": RESSTOCK_URL,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "rows": rows,
        "columns": len(reader.fieldnames or []),
        "identity": {"upgrade": first_identity[0], "state": first_identity[1], "dwelling_type": first_identity[2]},
        "models_used": int(first_models),
        "units_represented": float(first_units),
        "first_timestamp": timestamps[0].isoformat(sep=" "),
        "last_timestamp": timestamps[-1].isoformat(sep=" "),
        "unique_timestamps": len(set(timestamps)),
        "interval_minutes": sorted(set(deltas)),
        "null_cells": null_cells,
        "negative_total_energy_values": negative_total,
        "total_electricity_kwh_min": minimum_kwh,
        "total_electricity_kwh_max": maximum_kwh,
        "annual_total_electricity_mwh": total_mwh,
        "monthly_electricity_mwh": {month: monthly_kwh[month] / 1000 for month in range(1, 13)},
    }


def analyze_eia(path: Path) -> dict:
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise SystemExit("Instale dependencias con `python -m pip install -r requirements.txt`.") from error

    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["Monthly-States"]
    records: dict[int, tuple[float, str]] = {}
    for row in sheet.iter_rows(min_row=4, values_only=True):
        if row[0] == 2018 and row[2] == "CO":
            month = int(row[1])
            records[month] = (float(row[5]), str(row[3]))
    workbook.close()
    if set(records) != set(range(1, 13)):
        raise ValueError("La hoja Monthly-States no contiene los 12 meses de Colorado para 2018.")
    if {status for _, status in records.values()} != {"Final"}:
        raise ValueError("Los registros EIA de 2018 no aparecen todos como Final.")
    values = {month: records[month][0] for month in range(1, 13)}
    return {
        "source_url": EIA_URL,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "sheet": "Monthly-States",
        "state": "CO",
        "sector": "RESIDENTIAL",
        "period": "2018-01..2018-12",
        "status": "Final",
        "unit": "MWh",
        "rows": len(values),
        "annual_sales_mwh": sum(values.values()),
        "monthly_sales_mwh": values,
    }


def analyze_weather(path: Path) -> dict:
    raw = path.read_bytes()
    data = json.loads(raw)
    hourly = data["hourly"]
    times = hourly["time"]
    values = hourly["temperature_2m"]
    numeric = [float(value) for value in values if value is not None]
    if len(times) != 8760 or len(numeric) != 8760:
        raise ValueError("La consulta Open-Meteo no contiene las 8760 horas completas de 2018.")
    monthly_values: dict[int, list[float]] = defaultdict(list)
    for time_value, temperature in zip(times, values):
        monthly_values[int(time_value[5:7])].append(float(temperature))
    return {
        "source_url": WEATHER_URL,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "latitude": WEATHER_PARAMS["latitude"],
        "longitude": WEATHER_PARAMS["longitude"],
        "timezone": data["timezone"],
        "elevation_m": data.get("elevation"),
        "rows": len(times),
        "first_timestamp": times[0],
        "last_timestamp": times[-1],
        "missing_values": sum(value is None for value in values),
        "unit": data["hourly_units"]["temperature_2m"],
        "min": min(numeric),
        "max": max(numeric),
        "mean": statistics.fmean(numeric),
        "monthly_mean": {month: statistics.fmean(monthly_values[month]) for month in range(1, 13)},
    }


def svg_chart(resstock: dict, eia: dict, path: Path) -> None:
    width, height = 960, 520
    left, right, top, bottom = 90, 30, 105, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    r_values = [resstock["monthly_electricity_mwh"][m] for m in range(1, 13)]
    e_values = [eia["monthly_sales_mwh"][m] for m in range(1, 13)]
    max_val = max(max(r_values), max(e_values)) * 1.08
    x = lambda i: left + (i - 1) * plot_w / 11
    y = lambda v: top + plot_h * (1 - v / max_val)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="90" y="25" font-family="sans-serif" font-size="19" font-weight="bold">Colorado 2018: ResStock modelado y ventas EIA</text>',
        '<text x="90" y="44" font-family="sans-serif" font-size="12" fill="#555">Agregado de vivienda unifamiliar separada frente a todo el sector residencial (MWh/mes)</text>',
    ]
    for tick in range(0, 5):
        value = max_val * tick / 4
        yy = y(value)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#d9e0e8"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11" fill="#555">{value/1_000_000:.1f}M</text>')
    for i, label in enumerate(MONTH_NAMES, start=1):
        parts.append(f'<text x="{x(i):.1f}" y="{height-47}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#555">{label}</text>')
    for values, color in ((r_values, "#147D64"), (e_values, "#3658A6")):
        points = " ".join(f"{x(i):.1f},{y(value):.1f}" for i, value in enumerate(values, start=1))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        for i, value in enumerate(values, start=1):
            parts.append(f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="3.5" fill="{color}"/>')
    parts.extend([
        '<line x1="550" y1="74" x2="580" y2="74" stroke="#147D64" stroke-width="3"/><text x="586" y="78" font-family="sans-serif" font-size="12">ResStock baseline · CO · detached</text>',
        '<line x1="780" y1="74" x2="810" y2="74" stroke="#3658A6" stroke-width="3"/><text x="816" y="78" font-family="sans-serif" font-size="12">EIA · CO residencial</text>',
        '<text x="90" y="500" font-family="sans-serif" font-size="11" fill="#666">Comparación exploratoria: coberturas distintas; no equivale a validación hogar-a-hogar.</text>',
        '</svg>',
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def write_report(resstock: dict, eia: dict, weather: dict, output: Path) -> None:
    analysis_date = datetime.now().date().isoformat()
    lines = [
        "# Resultados de la primera muestra de datos",
        "",
        f"**Fecha de análisis:** {analysis_date}  ",
        "**Estado:** muestra exploratoria validada; no es resultado representativo de todo el consumo residencial.  ",
        "**Reproducibilidad:** `python -m pip install -r requirements.txt` y `python scripts/analizar_muestra_inicial.py --descargar`.",
        "",
        "## Alcance y datos observados",
        "",
        f"- **ResStock:** `{resstock['identity']['state']}`, `{resstock['identity']['dwelling_type']}`, escenario `{resstock['identity']['upgrade']}`; {resstock['rows']:,} intervalos y {resstock['columns']} columnas. Archivo de {resstock['bytes']:,} bytes; SHA-256 `{resstock['sha256']}`.",
        f"- **EIA:** Colorado, sector residencial, enero-diciembre de 2018; {eia['rows']} registros mensuales con estado `{eia['status']}`. Libro de {eia['bytes']:,} bytes; SHA-256 `{eia['sha256']}`.",
        f"- **Open-Meteo:** temperatura horaria en un punto de Denver ({weather['latitude']}, {weather['longitude']}), 2018 en UTC; {weather['rows']:,} horas y {weather['missing_values']} valores faltantes. Respuesta de {weather['bytes']:,} bytes; SHA-256 `{weather['sha256']}`.",
        "",
        "## Perfil ResStock y controles iniciales",
        "",
        f"- Los 35,040 timestamps son únicos y consecutivos, separados por {', '.join(str(x) for x in resstock['interval_minutes'])} minutos; cubren `{resstock['first_timestamp']}` a `{resstock['last_timestamp']}`. El timestamp marca el final del intervalo, por lo que se restaron 15 minutos para asignar cada intervalo a su mes.",
        f"- No se encontraron celdas vacías ({resstock['null_cells']:,}) ni valores negativos en `out.electricity.total.energy_consumption..kwh` ({resstock['negative_total_energy_values']}). El rango observado por intervalo fue {resstock['total_electricity_kwh_min']:,.2f}–{resstock['total_electricity_kwh_max']:,.2f} kWh agregados.",
        f"- El agregado indica {resstock['models_used']:,} modelos y {resstock['units_represented']:,.3f} unidades representadas. No equivale a {resstock['models_used']:,} medidores reales: son resultados modelados y ponderados.",
        "",
        "## Comparación mensual exploratoria con EIA",
        "",
        "ResStock aquí cubre solo vivienda unifamiliar separada modelada; EIA cubre las ventas de todo el sector residencial estatal. Las unidades se expresaron en MWh para comparar escala y estacionalidad, no para afirmar igualdad de poblaciones.",
        "",
        "| Mes | ResStock CO detached (MWh) | EIA CO residencial (MWh) | Razón exploratoria |",
        "|---|---:|---:|---:|",
    ]
    for month in range(1, 13):
        r_value = resstock["monthly_electricity_mwh"][month]
        e_value = eia["monthly_sales_mwh"][month]
        lines.append(f"| {MONTH_NAMES[month-1]} | {r_value:,.2f} | {e_value:,.2f} | {100*r_value/e_value:.2f}% |")
    ratio = 100 * resstock["annual_total_electricity_mwh"] / eia["annual_sales_mwh"]
    lines.extend([
        f"| **Año** | **{resstock['annual_total_electricity_mwh']:,.2f}** | **{eia['annual_sales_mwh']:,.2f}** | **{ratio:.2f}%** |",
        "",
        "![Comparación mensual exploratoria ResStock y EIA](evidencia/comparacion-resstock-eia-co-2018.svg)",
        "",
        "Esta razón no es una métrica de precisión: compara una categoría residencial modelada con ventas de todo el sector, sin reconciliar cobertura, definiciones ni incertidumbre. El patrón sirve para plantear análisis posterior, no para afirmar validación o causalidad.",
        "",
        "## Clima y alineación pendiente",
        "",
        f"La serie puntual de Denver tuvo temperatura entre {weather['min']:.1f} y {weather['max']:.1f} °C y media horaria de {weather['mean']:.2f} °C. Es un producto de reanálisis, no una lectura de una estación. La consulta dejó el modelo en `Best Match` (valor predeterminado, combinación de modelos), no en un único modelo fijado. Se conserva como capa climática independiente: el punto no representa necesariamente todo Colorado y está en UTC, mientras ResStock publica timestamps en EST. No se hizo una unión ni correlación con el perfil estatal.",
        "",
        "## Fuentes y atribución",
        "",
        f"- ResStock 2025.1 (OEDI): [archivo agregado](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/timeseries_aggregates/by_state/upgrade=0/state=CO/{RESSTOCK_NAME}), [FAQ oficial de ResStock](https://natlabrockies.github.io/ResStock.github.io/docs/FAQ.html), [registro OEDI](https://registry.opendata.aws/oedi-data-lake/). Atribuir a ResStock/NLR y DOE, y conservar la cita recomendada en el README del release. El registro general de OEDI declara CC BY 3.0 US; cualquier aviso específico del release prevalece.",
        f"- EIA: [archivo mensual oficial](https://www.eia.gov/electricity/data/eia861m/), [definición de datos EIA-861M](https://www.eia.gov/electricity/data/detail-data.php). Ventas residenciales en MWh; API no usada, no se solicitó clave.",
        f"- Clima: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), [términos](https://open-meteo.com/en/terms). El API histórico usa reanálisis; la documentación señala que `Best Match` combina modelos. Atribución Open-Meteo pendiente de mantener en cualquier figura/publicación; uso académico no comercial asumido para esta prueba.",
        "",
        "Los originales descargados quedan localmente bajo `data/raw/`, ignorados por Git; no se publicaron en este repositorio. El script obtiene únicamente estos tres objetos y genera esta tabla y el SVG.",
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descargar", action="store_true", help="Descarga solo las tres fuentes acotadas a data/raw/.")
    args = parser.parse_args()
    resstock_path, eia_path, weather_path = ensure_inputs(args.descargar)
    resstock = analyze_resstock(resstock_path)
    eia = analyze_eia(eia_path)
    weather = analyze_weather(weather_path)
    report_path = ROOT / "docs" / "resultados-muestra-inicial.md"
    svg_path = ROOT / "docs" / "evidencia" / "comparacion-resstock-eia-co-2018.svg"
    svg_chart(resstock, eia, svg_path)
    write_report(resstock, eia, weather, report_path)
    print(json.dumps({"report": str(report_path.relative_to(ROOT)), "chart": str(svg_path.relative_to(ROOT)), "resstock": resstock, "eia": eia, "weather": weather}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
