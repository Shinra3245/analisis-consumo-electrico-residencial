#!/usr/bin/env python3
"""Cruza población y superficie del Censo con doce meses de ventas residenciales finales."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import tempfile
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
YEARS = range(2020, 2026)
MONTHS = set(range(1, 13))
SQ_METERS_PER_SQ_MILE = Decimal("2589988.110336")
POP_FILE = "NST-EST2025-ALLDATA.csv"
AREA_FILE = "tigerweb_tab20_state_2020_us.html"
POP_URL = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/" + POP_FILE
AREA_URL = "https://tigerweb.geo.census.gov/tigerwebmain/Files/tab20/" + AREA_FILE
EIA_URL = "https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx"
EIA_CSV_AT_CUTOFF = (
    "https://github.com/Shinra3245/analisis-consumo-electrico-residencial/blob/"
    "bbf2b4f02f4bcd498f17d3554dd2e9a2e45545f8/datos/eia_residencial_mensual.csv"
)
EIA_SHA_AT_CUTOFF = "dff80ba19688732949ef340046e1257eab4bb1e206b0480162b7ed61fba9f93a"
CSV_NAME = "energy_demography_state_year_v1.csv"
FIELDS = (
    "state_fips", "state_code", "year", "population_estimate", "land_area_sq_mi_2020",
    "population_density_per_sq_mi", "residential_sales_mwh", "residential_kwh_per_capita",
    "eia_data_status", "census_vintage", "source_version",
)


class CensusTable(HTMLParser):
    """Lee encabezados y celdas de la tabla HTML estática de TIGERweb."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


def census_bytes(name, url, directory):
    if directory is not None:
        return (directory / name).read_bytes()
    request = Request(url, headers={"User-Agent": "DemografiaEstatal/1.0"})
    with urlopen(request, timeout=45) as response:
        return response.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def csv_reader(data, required):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    missing = set(required).difference(reader.fieldnames or [])
    if missing:
        raise ValueError("Faltan columnas: " + ", ".join(sorted(missing)))
    return reader


def state_fips(value):
    if not re.fullmatch(r"[0-9]{1,2}", value.strip()):
        raise ValueError(f"FIPS estatal inválido: {value!r}")
    return value.strip().zfill(2)


def land_areas(data):
    table = CensusTable()
    table.feed(data.decode("utf-8-sig"))
    table.close()
    if not table.rows or not {"STATE", "STUSAB", "AREALAND"}.issubset(table.rows[0]):
        raise ValueError("TIGERweb no contiene las columnas estatales esperadas.")
    areas = {}
    for cells in table.rows[1:]:
        row = dict(zip(table.rows[0], cells, strict=True))
        fips = state_fips(row["STATE"])
        if not "01" <= fips <= "56":  # Los territorios tienen códigos superiores a 56.
            continue
        code = row["STUSAB"].strip().upper()
        area = int(row["AREALAND"])
        if fips in areas or not re.fullmatch(r"[A-Z]{2}", code) or area <= 0:
            raise ValueError(f"Geografía duplicada o inválida: {fips} {code}")
        areas[fips] = (code, Decimal(area) / SQ_METERS_PER_SQ_MILE)
    codes = {code for code, _ in areas.values()}
    if len(areas) != 51 or len(codes) != 51 or areas.get("11", (None,))[0] != "DC":
        raise ValueError("Se esperaban 50 estados y el Distrito de Columbia con claves únicas.")
    return areas


def population_by_year(data, areas):
    fields = [f"POPESTIMATE{year}" for year in YEARS]
    population = {}
    for row in csv_reader(data, ["SUMLEV", "STATE", *fields]):
        if row["SUMLEV"].strip().zfill(3) != "040":
            continue
        fips = state_fips(row["STATE"])
        if fips not in areas:
            continue
        for year in YEARS:
            key = (fips, year)
            value = int(row[f"POPESTIMATE{year}"])
            if key in population or value <= 0:
                raise ValueError(f"Población duplicada o inválida: {key}")
            population[key] = value
    missing = {(fips, year) for fips in areas for year in YEARS}.difference(population)
    if missing:
        raise ValueError(f"Faltan estimaciones de población: {sorted(missing)}")
    return population


def read_sales(data, codes):
    records = defaultdict(dict)
    scanned = 0
    for row in csv_reader(data, ("periodo", "estado", "sector", "estado_dato", "ventas_mwh")):
        scanned += 1
        code = row["estado"].strip().upper()
        if row["sector"].strip().upper() != "RES" or code not in codes:
            continue
        period = row["periodo"].strip()
        if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", period):
            raise ValueError(f"Periodo inválido en EIA: {code} {period!r}")
        year, month = map(int, period.split("-"))
        if year not in YEARS:
            continue
        monthly = records[code, year]
        status = row["estado_dato"].strip().lower()
        if month in monthly:
            raise ValueError(f"Mes residencial duplicado en EIA: {code} {period}")
        if status not in {"final", "preliminary"}:
            raise ValueError(f"Estado del dato desconocido: {code} {period} {status!r}")
        value = None
        if status == "final":
            value = Decimal(row["ventas_mwh"].strip())
            if not value.is_finite() or value < 0:
                raise ValueError(f"Venta final inválida: {code} {period}")
        monthly[month] = value
    return records, scanned


def six_decimals(value):
    return format(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP), "f")


def build(eia_file, census_dir, snapshot_date):
    pop_data = census_bytes(POP_FILE, POP_URL, census_dir)
    area_data = census_bytes(AREA_FILE, AREA_URL, census_dir)
    eia_data = eia_file.read_bytes()
    sources = {}
    for key, name, url, data, vintage in (
        ("population", POP_FILE, POP_URL, pop_data, "Census PEP Vintage 2025"),
        ("land_area", AREA_FILE, AREA_URL, area_data, "Geografía del Censo 2020, BVP20"),
    ):
        sources[key] = {"file": name, "url": url, "version": vintage,
                        "bytes": len(data), "sha256": sha256(data)}
    electricity = {"file": eia_file.name, "version": "Serie mensual residencial del equipo",
                   "bytes": len(eia_data), "sha256": sha256(eia_data),
                   "upstream_dataset": "EIA-861M, hoja Monthly-States", "upstream_url": EIA_URL}
    if electricity["sha256"] == EIA_SHA_AT_CUTOFF:
        electricity.update(url=EIA_CSV_AT_CUTOFF, upstream_access_date="2026-11-17")
    sources["electricity"] = electricity
    signature = "\n".join(source["sha256"] for source in sources.values()).encode("ascii")
    version = "v1-" + sha256(signature)[:16]
    areas = land_areas(area_data)
    population = population_by_year(pop_data, areas)
    codes = {code for code, _ in areas.values()}
    sales, scanned = read_sales(eia_data, codes)

    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(FIELDS)
    yearly = {str(year): 0 for year in YEARS}
    excluded = []
    for fips, (code, land) in sorted(areas.items()):
        for year in YEARS:
            monthly = sales.get((code, year), {})
            missing = sorted(MONTHS.difference(monthly))
            preliminary = sorted(month for month, value in monthly.items() if value is None)
            if missing or preliminary:
                excluded.append({"state_code": code, "year": year,
                                 "missing_months": missing, "preliminary_months": preliminary})
                continue
            total = sum(monthly.values(), Decimal(0))
            people = population[fips, year]
            writer.writerow((fips, code, year, people, six_decimals(land),
                             six_decimals(people / land), format(total, "f"),
                             six_decimals(total * 1000 / people), "Final", 2025, version))
            yearly[str(year)] += 1

    output = stream.getvalue().encode("utf-8")
    count = sum(yearly.values())
    if count == 0:
        raise ValueError("Ningún estado-año reúne doce meses finales. Revise la entrada EIA.")
    artifact = {"file": CSV_NAME, "rows": count, "bytes": len(output), "sha256": sha256(output)}
    manifest = {
        "manifest_version": 1, "source_version": version, "snapshot_access_date": snapshot_date.isoformat(),
        "artifact": artifact, "grain": ["state_fips", "year"], "fields": list(FIELDS),
        "units": {"population_estimate": "personas al 1 de julio",
                  "land_area_sq_mi_2020": "mi² terrestres",
                  "population_density_per_sq_mi": "personas/mi² terrestre, estimación calculada",
                  "residential_sales_mwh": "MWh/año", "residential_kwh_per_capita": "kWh/persona/año"},
        "coverage": {"geography": "50 estados de EE. UU. y el Distrito de Columbia",
                     "years": list(YEARS), "expected_jurisdictions": len(areas),
                     "expected_state_years": len(areas) * len(YEARS),
                     "state_years_by_year": yearly, "monthly_eia_rows_read": scanned,
                     "final_months_used": count * 12, "excluded_state_years": excluded},
        "sources": sources,
    }
    metadata = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {CSV_NAME: output, "manifest.json": metadata}, artifact


def publish(files, directory):
    """Publica la pareja completa por renombrado e identifica repeticiones idénticas."""
    if directory.is_dir() and any(directory.iterdir()):
        if all((directory / name).is_file() and (directory / name).read_bytes() == data
               for name, data in files.items()):
            return
        raise ValueError(f"Hay archivos distintos en {directory}. Use --output con otra carpeta.")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent) as tmp:
        staged = Path(tmp) / "salida"
        staged.mkdir()
        for name, data in files.items():
            (staged / name).write_bytes(data)
        if directory.is_dir():
            directory.rmdir()  # En Windows el destino del renombrado debe estar libre.
        staged.rename(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eia", type=Path, default=ROOT / "datos/eia_residencial_mensual.csv",
                        help="CSV mensual versionado del equipo")
    parser.add_argument("--census-dir", type=Path,
                        help="Carpeta con el CSV de población y el HTML de superficie para uso sin red")
    parser.add_argument("--output", type=Path, default=ROOT / "datos/demografia_estatal",
                        help="Carpeta de salida")
    parser.add_argument("--fecha-consulta", type=date.fromisoformat, default=date.today(),
                        help="Fecha de consulta de los insumos del corte (AAAA-MM-DD)")
    parser.add_argument("--comparar-con", type=Path, metavar="CARPETA",
                        help="Verificar el CSV y el manifiesto contra una entrega existente")
    args = parser.parse_args()
    try:
        files, artifact = build(args.eia, args.census_dir, args.fecha_consulta)
        if args.comparar_con:
            for name, data in files.items():
                if (args.comparar_con / name).read_bytes() != data:
                    raise ValueError(f"La reproducción difiere en {name}. Revise las fuentes y la fecha.")
        publish(files, args.output)
    except (OSError, ValueError, InvalidOperation, csv.Error) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"{artifact['rows']} filas | {artifact['bytes']} bytes | SHA-256 {artifact['sha256']}")
    if args.comparar_con:
        print("El CSV y el manifiesto coinciden byte por byte con la entrega.")


if __name__ == "__main__":
    main()
