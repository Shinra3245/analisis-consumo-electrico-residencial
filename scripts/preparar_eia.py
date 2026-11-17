#!/usr/bin/env python3
"""Genera las tablas residenciales del proyecto desde un XLSX EIA-861M."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook


STATES = """AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA
MD ME MI MN MO MS MT NC ND NE NH NJ NM NV NY OH OK OR PA RI SC SD TN TX UT VA
VT WA WI WV WY""".split()
SHEET = "Monthly-States"
EXPECTED_HEADER = (
    "RESIDENTIAL",
    "Sales",
    ("Year", "Month", "State", "Data Status"),
    "Megawatthours",
)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prepare(input_path: Path, output_dir: Path, start_year: int, end_year: int,
            overwrite: bool) -> tuple[int, int]:
    if not input_path.is_file():
        raise FileNotFoundError(f"No existe el XLSX de entrada: {input_path}")
    if start_year > end_year:
        raise ValueError("El año inicial debe ser menor o igual al año final")

    monthly_path = output_dir / "eia_residencial_mensual.csv"
    coverage_path = output_dir / "cobertura_eia.csv"
    existing = [path for path in (monthly_path, coverage_path) if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Las salidas ya existen; usa --overwrite para reemplazarlas: "
            + ", ".join(str(path) for path in existing)
        )

    workbook = load_workbook(input_path, read_only=True, data_only=True)
    try:
        if SHEET not in workbook.sheetnames:
            raise ValueError(f"Falta la hoja esperada {SHEET!r}")
        sheet = workbook[SHEET]
        header = list(sheet.iter_rows(max_row=3, max_col=6, values_only=True))
        observed = (header[0][4], header[1][5], header[2][:4], header[2][5])
        if observed != EXPECTED_HEADER:
            raise ValueError(f"Cambió el encabezado esperado de EIA-861M: {observed!r}")

        records = []
        seen = set()
        for year, month, state, status, _revenue, sales in sheet.iter_rows(
            min_row=4, max_col=6, values_only=True
        ):
            if state not in STATES or not isinstance(year, int) or not isinstance(month, int):
                continue
            if not start_year <= year <= end_year:
                continue
            if not 1 <= month <= 12:
                raise ValueError(f"Mes inválido en EIA: {year}-{month}, {state}")
            if status not in {"Final", "Preliminary"}:
                raise ValueError(f"Estado del dato desconocido: {status!r} en {year}-{month}, {state}")
            if isinstance(sales, bool) or not isinstance(sales, (int, float)):
                raise ValueError(f"Venta no numérica en {year}-{month}, {state}: {sales!r}")
            if not math.isfinite(sales) or sales < 0:
                raise ValueError(f"Venta fuera de rango en {year}-{month}, {state}: {sales!r}")

            key = (year, month, state)
            if key in seen:
                raise ValueError(f"Periodo estatal duplicado: {key}")
            seen.add(key)
            records.append({
                "periodo": f"{year}-{month:02d}",
                "estado": state,
                "sector": "RES",
                "estado_dato": status,
                "ventas_mwh": sales,
            })
    finally:
        workbook.close()

    records.sort(key=lambda row: (row["estado"], row["periodo"]))
    monthly_fields = ["periodo", "estado", "sector", "estado_dato", "ventas_mwh"]
    write_csv(monthly_path, monthly_fields, records)

    groups = defaultdict(list)
    for row in records:
        year, month = map(int, row["periodo"].split("-"))
        groups[year, row["estado"]].append((month, row["estado_dato"], row["ventas_mwh"]))

    coverage = []
    for year in range(start_year, end_year + 1):
        for state in STATES:
            months = groups[year, state]
            final = sum(status == "Final" for _, status, _ in months)
            preliminary = sum(status == "Preliminary" for _, status, _ in months)
            coverage.append({
                "anio": year,
                "estado": state,
                "sector": "RES",
                "meses": len(months),
                "meses_finales": final,
                "meses_preliminares": preliminary,
                "meses_faltantes": 12 - len(months),
                "ventas_mwh": round(sum(value for _, _, value in months), 4) if months else None,
            })
    coverage_fields = [
        "anio", "estado", "sector", "meses", "meses_finales",
        "meses_preliminares", "meses_faltantes", "ventas_mwh",
    ]
    write_csv(coverage_path, coverage_fields, coverage)
    return len(records), len(coverage)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="XLSX oficial de EIA-861M")
    parser.add_argument("--output", required=True, type=Path, help="Directorio destino de las dos tablas")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--overwrite", action="store_true", help="Permitir reemplazar los CSV de salida")
    args = parser.parse_args()
    monthly, coverage = prepare(args.input, args.output, args.start_year, args.end_year, args.overwrite)
    print(f"Generado: {args.output / 'eia_residencial_mensual.csv'} ({monthly} filas)")
    print(f"Generado: {args.output / 'cobertura_eia.csv'} ({coverage} filas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
