#!/usr/bin/env python3
"""Prepara entradas y evidencia del bloque de datos de consumo residencial."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openpyxl import load_workbook
import pyarrow as pa
import pyarrow.parquet as pq

STATES = frozenset("""AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA
MD ME MI MN MO MS MT NC ND NE NH NJ NM NV NY OH OK OR PA RI SC SD TN TX UT VA
VT WA WI WV WY""".split())
STOCK = (
    "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"
    "end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/"
)
METADATA = STOCK + "metadata_and_annual_results/national/full/parquet/upgrade0.parquet"
EIA = "https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx"
WEATHER = "https://archive-api.open-meteo.com/v1/archive"
AGGREGATE = STOCK + (
    "timeseries_aggregates/by_state/upgrade=0/state=CO/up00-co-single-family_detached.csv"
)
TYPE = "in.geometry_building_type_recs"
ENERGY = "out.electricity.total.energy_consumption..kwh"
STOCK_FIELDS = ["bldg_id", "completed_status", "weight", "in.state", "in.county", TYPE]
STEP = timedelta(minutes=15)
FIRST = datetime(2018, 1, 1, 0, 15)
STOCK_ROWS = 35040
SOURCE_SHEET = "Monthly-States"
POINTS = (
    ("denver_co", "CO", 39.7392, -104.9903),
    ("grand_junction_co", "CO", 39.0639, -108.5506),
)


class RemoteParquet(io.RawIOBase):
    """Lee rangos del mismo objeto S3 para proyectar solo las columnas del índice."""

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.position = 0
        with open_url(url, {"Range": "bytes=0-0"}) as response:
            match = re.fullmatch(r"bytes 0-0/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not match:
                raise ValueError(f"El servidor no admite rangos para {url}")
            self.size = int(match[1])
            self.etag = response.headers.get("ETag")
        self.bytes_read = 1

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, offset, whence=os.SEEK_SET):
        base = {os.SEEK_SET: 0, os.SEEK_CUR: self.position, os.SEEK_END: self.size}[whence]
        self.position = base + offset
        if self.position < 0:
            raise ValueError("Posición de archivo negativa")
        return self.position

    def tell(self):
        return self.position

    def read(self, size=-1):
        start = self.position
        end = self.size if size == -1 else min(start + size, self.size)
        if end <= start:
            return b""
        headers = {"Range": f"bytes={start}-{end - 1}"}
        if self.etag:
            headers["If-Match"] = self.etag
        with open_url(self.url, headers) as response:
            expected = f"bytes {start}-{end - 1}/{self.size}"
            if response.status != 206 or response.headers.get("Content-Range") != expected:
                raise ValueError(f"Rango inesperado de {self.url}")
            data = response.read()
        if len(data) != end - start:
            raise ValueError(f"Rango incompleto de {self.url}")
        self.position = end
        self.bytes_read += len(data)
        return data


def open_url(url, headers=None):
    request = Request(url, headers={"User-Agent": "Proyecto-Big-Data-TecNM/1.0", **(headers or {})})
    for attempt in range(3):
        try:
            return urlopen(request, timeout=45)
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        sleep(2 ** attempt)


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def manifest_record(path, root, source, status, rows=None, **details):
    return {
        "archivo": path.relative_to(root).as_posix(),
        "fuente": source,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "estado": status,
        "bytes": path.stat().st_size if path.exists() else None,
        "filas": rows,
        "sha256": digest(path) if path.exists() else None,
        **details,
    }


def acquire(root, name, url, refresh):
    path = root / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    started = monotonic()
    if path.exists() and not refresh:
        return path, "cache_local", 0.0
    temp = path.with_suffix(path.suffix + ".part")
    try:
        with open_url(url) as response, temp.open("wb") as writer:
            expected = response.headers.get("Content-Length")
            for chunk in iter(lambda: response.read(1 << 20), b""):
                writer.write(chunk)
        if expected is not None and temp.stat().st_size != int(expected):
            raise OSError(f"Descarga incompleta de {url}")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return path, "descargado", round(monotonic() - started, 3)


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prepare_eia(args, records):
    raw, status, duration = acquire(args.output, "eia/sales_revenue.xlsx", EIA, args.refresh)
    data = []
    known_months = set()
    with raw.open("rb") as stream:
        book = load_workbook(stream, read_only=True, data_only=True)
        try:
            table = book[SOURCE_SHEET]
            header = list(table.iter_rows(max_row=3, max_col=6, values_only=True))
            if (header[0][4], header[1][5], header[2][:4], header[2][5]) != (
                "RESIDENTIAL", "Sales", ("Year", "Month", "State", "Data Status"), "Megawatthours"
            ):
                raise ValueError("Cambió el encabezado de la hoja Monthly-States")
            raw_rows = 0
            for year, month, state, quality, _, sales in table.iter_rows(
                min_row=4, max_col=6, values_only=True
            ):
                if state not in STATES or not isinstance(year, int) or not isinstance(month, int):
                    continue
                raw_rows += 1
                if not args.eia_start <= year <= args.eia_end or state not in args.states:
                    continue
                key = (year, month, state)
                if key in known_months or not 1 <= month <= 12:
                    raise ValueError(f"Período EIA duplicado o inválido: {key}")
                if not isinstance(sales, (int, float)) or not math.isfinite(sales) or sales < 0:
                    raise ValueError(f"Ventas EIA inválidas: {key}")
                known_months.add(key)
                data.append(dict(periodo=f"{year}-{month:02d}", estado=state, sector="RES",
                                 estado_dato=quality, ventas_mwh=sales))
        finally:
            book.close()
    records.append(manifest_record(raw, args.output, EIA, status, raw_rows,
                                   alcance_filas="registros mensuales de 50 estados y DC en Monthly-States",
                                   segundos=duration))
    data.sort(key=lambda row: (row["estado"], row["periodo"]))
    path = args.output / "datos/eia_residencial_mensual.csv"
    write_csv(path, ["periodo", "estado", "sector", "estado_dato", "ventas_mwh"], data)
    records.append(manifest_record(path, args.output, EIA, "derivado", len(data)))
    groups = defaultdict(list)
    for row in data:
        groups[int(row["periodo"][:4]), row["estado"]].append(row)
    coverage = []
    for year in range(args.eia_start, args.eia_end + 1):
        for state in sorted(args.states):
            months = groups[year, state]
            final = sum(row["estado_dato"] == "Final" for row in months)
            coverage.append(dict(anio=year, estado=state, sector="RES", meses=len(months),
                                 meses_finales=final, meses_preliminares=sum(
                                     row["estado_dato"] == "Preliminary" for row in months),
                                 meses_faltantes=12-len(months),
                                 ventas_mwh=round(sum(row["ventas_mwh"] for row in months), 4)
                                 if months else None))
    path = args.output / "datos/cobertura_eia.csv"
    write_csv(path, list(coverage[0]), coverage)
    records.append(manifest_record(path, args.output, EIA, "derivado", len(coverage)))
    return data, coverage


def prepare_weather(args, records):
    rows = []
    for name, state, latitude, longitude in POINTS:
        params = dict(latitude=latitude, longitude=longitude, start_date=args.weather_start,
                      end_date=args.weather_end, hourly="temperature_2m", models="era5_land",
                      timezone="GMT", temperature_unit="celsius")
        url = WEATHER + "?" + urlencode(params)
        date_range = f"{args.weather_start}_{args.weather_end}"
        raw, status, duration = acquire(args.output, f"open_meteo/{name}_{date_range}.json", url, args.refresh)
        payload = json.loads(raw.read_bytes())
        times = payload["hourly"]["time"]
        values = payload["hourly"]["temperature_2m"]
        expected = (args.weather_end - args.weather_start).days * 24 + 24
        if (payload["utc_offset_seconds"] != 0 or payload["hourly_units"]["temperature_2m"] != "°C"
                or len(times) != expected or len(values) != expected):
            raise ValueError(f"Cobertura o unidades inesperadas para {name}")
        start = datetime.combine(args.weather_start, datetime.min.time())
        for i, (hour, value) in enumerate(zip(times, values, strict=True)):
            if (datetime.fromisoformat(hour) != start + timedelta(hours=i)
                    or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f"Hora o temperatura inválida en {name}: {hour}")
            rows.append(dict(punto_id=name, estado=state, latitude_solicitada=latitude,
                             longitude_solicitada=longitude, latitude_celda=payload["latitude"],
                             longitude_celda=payload["longitude"], timestamp_utc=hour + ":00Z",
                             temperatura_c=value, modelo="ERA5-Land"))
        records.append(manifest_record(raw, args.output, url, status, expected, segundos=duration))
    path = args.output / "datos/clima_open_meteo_muestra.csv"
    write_csv(path, list(rows[0]), rows)
    records.append(manifest_record(path, args.output, WEATHER, "derivado", len(rows)))
    return rows


def allocate_profiles(strata, goal):
    if not len(strata) <= goal <= sum(map(len, strata.values())):
        raise ValueError("La meta debe cubrir todos los estratos y respetar la capacidad disponible")
    remaining = goal - len(strata)
    available = sum(len(group) - 1 for group in strata.values())
    quotas = {}
    remainders = []
    for key, group in sorted(strata.items()):
        part, remainder = divmod(remaining * (len(group) - 1), available or 1)
        quotas[key] = 1 + part
        remainders.append((remainder, key))
    for _, key in sorted(remainders, key=lambda pair: (-pair[0], pair[1]))[:goal-sum(quotas.values())]:
        quotas[key] += 1
    return quotas


def index_stock(args, records):
    started = monotonic()
    with RemoteParquet(METADATA) as remote:
        dataset = pq.ParquetFile(remote)
        columns = dataset.read(columns=STOCK_FIELDS, use_threads=False).to_pydict()
        transport = dict(bytes_http=remote.bytes_read, bytes_objeto=remote.size,
                         etag_objeto=remote.etag, segundos=round(monotonic() - started, 3))
    strata = defaultdict(list)
    seen = set()
    for bid, state, housing, county, weight, status in zip(
        columns["bldg_id"], columns["in.state"], columns[TYPE],
        columns["in.county"], columns["weight"], columns["completed_status"], strict=True
    ):
        if state not in args.states or status != "Success" or not housing or not weight or weight <= 0:
            continue
        if bid in seen:
            raise ValueError(f"Identificador ResStock duplicado: {bid}")
        seen.add(bid)
        strata[state, housing].append((bid, county, weight))
    records.append({"archivo": None, "fuente": METADATA, "fecha_utc": datetime.now(timezone.utc).isoformat(
        timespec="seconds"), "estado": "lectura_remota_parcial", "filas": len(columns["bldg_id"]),
        "bytes": None, "sha256": None, **transport})
    quotas = allocate_profiles(strata, args.plan_profiles)
    selection = []
    coverage = []
    pilot = []
    rng = random.Random(args.seed)
    for (state, housing), group in sorted(strata.items()):
        count = quotas[state, housing]
        candidates = sorted(group)
        chosen = rng.sample(candidates, count)
        coverage.append(dict(estado=state, tipo_vivienda=housing, candidatos=len(group),
                             cuota_propuesta=count,
                             condados_con_codigo=len({county for _, county, _ in group if county})))
        for i, (bid, county, weight) in enumerate(chosen):
            key = f"timeseries_individual_buildings/by_state/upgrade=0/state={state}/{bid}-0.parquet"
            row = dict(bldg_id=bid, estado=state, tipo_vivienda=housing, condado_codigo=county,
                       peso_viviendas=weight, upgrade=0, url=STOCK+key)
            selection.append(row)
            if state in args.pilot_states and i < args.pilot_per_stratum:
                pilot.append(row)
    for name, rows in (
        ("resstock_cobertura_estratos.csv", coverage),
        ("resstock_seleccion_propuesta.csv", selection),
        ("resstock_seleccion_piloto.csv", pilot),
    ):
        path = args.output / "datos" / name
        write_csv(path, list(rows[0]), rows)
        records.append(manifest_record(path, args.output, METADATA, "derivado", len(rows)))
    return pilot, coverage


def validate_stock_times(times):
    if len(times) != STOCK_ROWS or any(value != FIRST + STEP*i for i, value in enumerate(times)):
        raise ValueError("La serie 2018 no tiene los 35,040 intervalos esperados en orden")


def obtain_profile(args, row):
    bid, state, url = row["bldg_id"], row["estado"], row["url"]
    name = f"resstock/{state}/{bid}-0.parquet"
    raw = args.output / "raw" / name
    started = monotonic()
    try:
        raw, status, duration = acquire(args.output, name, url, args.refresh)
        table = pq.read_table(raw, columns=["bldg_id", "timestamp", ENERGY])
        times, energy = table["timestamp"].to_pylist(), table[ENERGY].to_pylist()
        validate_stock_times(times)
        if (set(table["bldg_id"].to_pylist()) != {bid}
                or any(value is None or not math.isfinite(value) for value in energy)):
            raise ValueError(f"Perfil {bid} con identificador o consumo inválidos")
        table = table.rename_columns(["bldg_id", "timestamp_fin_local", "electricidad_kwh"])
        record = manifest_record(raw, args.output, url, status, table.num_rows,
                                 segundos=duration, bldg_id=bid, estado_eeuu=state)
        return table, record
    except (OSError, ValueError) as exc:
        record = manifest_record(raw, args.output, url, "fallido",
                                 segundos=round(monotonic() - started, 3), bldg_id=bid,
                                 estado_eeuu=state, error=str(exc))
        return None, record


def prepare_profiles(args, pilot, records):
    started = monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda row: obtain_profile(args, row), pilot))
    valid = []
    measured = []
    for table, record in results:
        records.append(record)
        measured.append(record)
        if table is not None:
            valid.append(table)
    path = args.output / "datos/resstock_perfiles_piloto.parquet"
    if valid:
        table = pa.concat_tables(valid)
        pq.write_table(table, path, compression="snappy")
        records.append(manifest_record(
            path,
            args.output,
            METADATA,
            "derivado",
            table.num_rows,
            origen="archivos individuales listados en el manifiesto",
            profile_roster={
                "bldg_ids": sorted({int(row["bldg_id"]) for row in pilot}),
                "intervals_per_profile": STOCK_ROWS,
            },
        ))
    else:
        path.unlink(missing_ok=True)
    sizes = [row["bytes"] for row in measured if row["estado"] != "fallido"]
    return dict(solicitados=len(pilot), obtenidos=len(sizes), fallidos=len(pilot)-len(sizes),
                filas=sum(table.num_rows for table in valid), bytes_total=sum(sizes),
                bytes_min=min(sizes, default=None), bytes_max=max(sizes, default=None),
                bytes_media=round(sum(sizes)/len(sizes), 2) if sizes else None,
                segundos_lote=round(monotonic() - started, 3),
                bytes_estimados_meta=round(args.plan_profiles*sum(sizes)/len(sizes)) if sizes else None,
                perfiles_meta=args.plan_profiles)


def check_demo(args, eia, records):
    raw, status, duration = acquire(args.output, "resstock/co_single_family_detached.csv",
                                   AGGREGATE, args.refresh)
    times = []
    monthly = defaultdict(list)
    models, represented = set(), set()
    with raw.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            time = datetime.fromisoformat(row["timestamp"])
            times.append(time)
            models.add(int(row["models_used"]))
            represented.add(float(row["units_represented"]))
            # El timestamp indica el fin. La medianoche pertenece al intervalo del día anterior.
            monthly[(time-STEP).month].append(float(row[ENERGY]))
    validate_stock_times(times)
    if len(models) != 1 or len(represented) != 1:
        raise ValueError("Modelos o viviendas representadas varían dentro de la serie")
    records.append(manifest_record(raw, args.output, AGGREGATE, status, len(times), segundos=duration))
    co_eia = {int(row["periodo"][-2:]): row["ventas_mwh"] for row in eia
              if row["estado"] == "CO" and row["periodo"].startswith("2018-")}
    rows = []
    for month, values in sorted(monthly.items()):
        stock = math.fsum(values)/1000
        market = co_eia.get(month)
        rows.append(dict(periodo=f"2018-{month:02d}", resstock_co_unifamiliar_aislada_mwh=round(stock, 3),
                         eia_co_res_ventas_mwh=market,
                         razon_descriptiva_pct=round(100*stock/market, 6) if market else None))
    path = args.output / "datos/demo_colorado_2018_verificacion.csv"
    write_csv(path, list(rows[0]), rows)
    records.append(manifest_record(path, args.output, AGGREGATE, "derivado", len(rows), fuente_eia=EIA))
    total = round(sum(row["resstock_co_unifamiliar_aislada_mwh"] for row in rows), 3)
    eia_total = sum(co_eia.values()) if len(co_eia) == 12 else None
    return dict(modelos=models.pop(), viviendas_representadas=represented.pop(),
                intervalos=len(times), resstock_mwh=total, eia_mwh=eia_total,
                razon_descriptiva_pct=round(100*total/eia_total, 6) if eia_total else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/reproduccion-piloto-datos"))
    parser.add_argument("--states", nargs="+", type=str.upper, choices=sorted(STATES),
                        default=sorted(STATES), metavar="ESTADO")
    parser.add_argument("--pilot-states", nargs="+", type=str.upper, choices=sorted(STATES),
                        default=None, metavar="ESTADO")
    parser.add_argument("--pilot-per-stratum", type=int, default=1,
                        help="perfiles por tipo de vivienda en cada estado del piloto")
    parser.add_argument("--eia-start", type=int, default=2018)
    parser.add_argument("--eia-end", type=int, default=2026)
    parser.add_argument("--weather-start", type=date.fromisoformat, default=date(2018, 1, 1))
    parser.add_argument("--weather-end", type=date.fromisoformat, default=date(2018, 1, 7))
    parser.add_argument("--plan-profiles", type=int, default=10000,
                        help="tamaño de la lista propuesta; solo el piloto descarga perfiles")
    parser.add_argument("--seed", type=int, default=22030511)
    parser.add_argument("--refresh", action="store_true", help="volver a consultar archivos crudos")
    args = parser.parse_args()
    args.states = sorted(set(args.states))
    if args.pilot_states is None:
        args.pilot_states = [state for state in ("CO", "NY") if state in args.states] or args.states[:1]
    if (not set(args.pilot_states) <= set(args.states) or not 2010 <= args.eia_start <= args.eia_end
            or args.weather_start > args.weather_end or args.pilot_per_stratum < 1):
        parser.error("El intervalo o la selección de estados es incompatible")
    records = []
    try:
        eia, coverage_eia = prepare_eia(args, records)
        weather = prepare_weather(args, records)
        pilot, coverage_stock = index_stock(args, records)
        summary = prepare_profiles(args, pilot, records)
        demo = check_demo(args, eia, records) if "CO" in args.states else None
        if demo is None:
            (args.output / "datos/demo_colorado_2018_verificacion.csv").unlink(missing_ok=True)
        summary.update(
            eia_filas=len(eia), eia_anios_completos_finales=[
                y for y in range(args.eia_start, args.eia_end+1)
                if all(row["meses_finales"] == 12 for row in coverage_eia if row["anio"] == y)
            ],
            clima_filas=len(weather), resstock_estratos=len(coverage_stock),
            resstock_candidatos=sum(row["candidatos"] for row in coverage_stock),
            demo=demo,
        )
        (args.output / "resumen-ejecucion.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "manifiesto.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return int(summary["fallidos"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
