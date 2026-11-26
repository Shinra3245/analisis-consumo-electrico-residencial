#!/usr/bin/env python3
"""Ingesta ResStock por lotes, reanudable e idempotente.

Por defecto solo imprime un PLAN a partir de la selección de candidatos; no
escribe nada ni usa la red. Descargar exige --descargar y un --limite explícito.
Los IDs de la selección son candidatos, no perfiles descargados ni aceptados.
Los archivos crudos quedan bajo --output y no deben copiarse a Git ni a S3 sin
la decisión de publicación (docs/decision-publicacion-datos.md).

Atribución: Data includes information from the ResStock(TM) dataset developed by
the National Renewable Energy Laboratory (NREL) with funding from the U.S.
Department of Energy (DOE). Licencia CC BY 4.0; los datos se proporcionan
"as is" y para investigación, sin garantía.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Constantes duplicadas a propósito de scripts/preparar_datos.py (que exige openpyxl).
STOCK = (
    "https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"
    "end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/"
)
HOST = "oedi-data-lake.s3.amazonaws.com"
ENERGY = "out.electricity.total.energy_consumption..kwh"
STEP = timedelta(minutes=15)
FIRST = datetime(2018, 1, 1, 0, 15)
STOCK_ROWS = 35040
FORMAT = "resstock-ingesta-v1"
MARKER = "ingesta_resstock.json"
JOURNAL = "roster.jsonl"
SUMMARY = "resumen.json"
DEFAULT_SELECTION = Path("datos/resstock_seleccion_propuesta.csv")
SELECTION_FIELDS = ("bldg_id", "estado", "tipo_vivienda", "upgrade", "url")
MEAN_BYTES_PILOT = 6_450_949.7  # media de 10 perfiles piloto: proyección, no medición del lote
REPO = Path(__file__).resolve().parent.parent
ATTRIBUTION = (
    "Data includes information from the ResStock(TM) dataset developed by the National "
    "Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy "
    "(DOE). CC BY 4.0. Datos 'as is' para investigación, sin garantía. Redistribución de "
    "crudos sujeta a docs/decision-publicacion-datos.md."
)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def safe_path(out, rel):
    """Ruta bajo `out` sin componentes simbólicos ni escape; `rel` debe ser relativa y sin '..'."""
    parts = Path(rel).parts
    if not parts or Path(rel).is_absolute() or ".." in parts:
        raise ValueError(f"Ruta interna inválida: {rel}")
    path = out
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Enlace simbólico en la ruta interna: {path}")
    resolved = path.resolve()
    if out not in resolved.parents:
        raise ValueError(f"La ruta interna escapa de la salida: {rel}")
    return path


def safe_mkdir(out, rel):
    path = out
    for part in Path(rel).parts:
        path = safe_path(out, (path / part).relative_to(out).as_posix())
        path.mkdir(exist_ok=True)
    return path


def atomic_write_json(path, payload):
    temp = path.with_name(path.name + ".tmp")
    temp.unlink(missing_ok=True)  # un .tmp preexistente (incluso un enlace) se descarta, no se sigue
    with temp.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


# ---------------------------------------------------------------- selección

def load_selection(path):
    """Lee y valida la selección; la URL debe ser exactamente la del release esperado."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(SELECTION_FIELDS) <= set(reader.fieldnames or ()):
            raise ValueError(f"La selección debe tener las columnas {SELECTION_FIELDS}")
        rows, seen = [], set()
        for line, row in enumerate(reader, start=2):
            try:
                bid = int(row["bldg_id"])
            except ValueError:
                raise ValueError(f"Línea {line}: bldg_id inválido") from None
            state = row["estado"]
            expected = (f"{STOCK}timeseries_individual_buildings/by_state/upgrade=0/"
                        f"state={state}/{bid}-0.parquet")
            if bid <= 0 or bid in seen or not re.fullmatch(r"[A-Z]{2}", state):
                raise ValueError(f"Línea {line}: ID duplicado/no positivo o estado inválido")
            if row["upgrade"] != "0" or row["url"] != expected:
                raise ValueError(f"Línea {line}: URL/upgrade distinto del release esperado")
            seen.add(bid)
            rows.append(dict(bldg_id=bid, estado=state, tipo_vivienda=row["tipo_vivienda"],
                             url=row["url"]))
    if not rows:
        raise ValueError("La selección está vacía")
    return rows


def order_selection(rows, seed):
    """Orden determinista que intercala estratos: cualquier prefijo cubre varios estratos."""
    strata = {}
    for row in rows:
        strata.setdefault((row["estado"], row["tipo_vivienda"]), []).append(row)
    keyed = []
    for stratum, group in strata.items():
        ranked = sorted(group, key=lambda r: hashlib.sha256(
            f"{seed}:{r['bldg_id']}".encode()).hexdigest())
        for i, row in enumerate(ranked):
            keyed.append(((i / len(ranked), stratum, row["bldg_id"]), row))
    return [row for _, row in sorted(keyed, key=lambda pair: pair[0])]


# ---------------------------------------------------------- salida y diario

def check_output(output, selection):
    """Devuelve la ruta resuelta y si ya es una salida propia reconocida."""
    if output.is_symlink():
        raise ValueError("La salida no puede ser un enlace simbólico")
    out = output.resolve()
    sel_dir = selection.resolve().parent
    protected = [sel_dir, REPO / "datos", REPO / "tablero", REPO / "docs", REPO / "scripts"]
    for base in protected:
        if out == base or base in out.parents or out in base.parents:
            raise ValueError(f"La salida se solapa con entradas o código del repositorio: {base}")
    if out == Path(out.anchor) or out == Path.home():
        raise ValueError("Ruta de salida insegura")
    if REPO in out.parents and not (out == REPO / "data" / "raw" or REPO / "data" / "raw" in out.parents):
        raise ValueError("Dentro del repositorio solo se permite /data/raw/ (ignorado por Git)")
    if not out.exists():
        return out, False
    if not out.is_dir():
        raise ValueError("La salida existe y no es un directorio")
    marker = out / MARKER
    if any(out.iterdir()) and not marker.is_file():
        raise ValueError("La salida existe, no está vacía y no es una salida de esta herramienta")
    return out, marker.is_file()


STATES_OK = {"aceptado", "rechazado", "fallido", "conflicto"}


def check_record(record, rows_by_id, out):
    """Valida un registro del diario contra la selección; lanza ValueError si es inválido."""
    def opt(key, kind):
        value = record.get(key)
        if value is not None and (not isinstance(value, kind) or isinstance(value, bool)):
            raise ValueError(f"campo {key} con tipo inválido")
        return value

    if not isinstance(record, dict):
        raise ValueError("el registro no es un objeto")
    bid = record.get("bldg_id")
    row = rows_by_id.get(bid) if isinstance(bid, int) and not isinstance(bid, bool) else None
    if row is None:
        raise ValueError(f"bldg_id ajeno a la selección: {bid!r}")
    if (record.get("estado_proceso") not in STATES_OK or record.get("estado_eeuu") != row["estado"]
            or record.get("url") != row["url"]):
        raise ValueError(f"estado/estado_eeuu/url inválidos para {bid}")
    intentos = opt("intentos", int)
    size, filas = opt("bytes", int), opt("filas", int)
    digest, ruta, error = opt("sha256", str), opt("ruta", str), opt("error", str)
    if intentos is None or intentos < 0 or any(v is not None and v < 0 for v in (size, filas)):
        raise ValueError(f"contadores inválidos para {bid}")
    if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"sha256 inválido para {bid}")
    if ruta is not None:
        safe_path(out, ruta)
    if record["estado_proceso"] == "aceptado" and (
            size is None or digest is None or filas != STOCK_ROWS
            or ruta != f"raw/resstock/{row['estado']}/{bid}-0.parquet"):
        raise ValueError(f"registro aceptado incompleto para {bid}")


def read_journal(out, rows_by_id):
    """Devuelve (último registro por ID, tail).

    tail es None o (bytes, completo): el último fragmento sin salto de línea. Si es un JSON
    completo se valida con check_record y SE INCLUYE en los registros (solo falta el LF); si
    no es JSON, es una escritura truncada por una caída y se descarta de los registros. Un
    JSON completo pero inválido, o cualquier otra línea corrupta, es un error.
    """
    path = safe_path(out, JOURNAL)
    records, tail = {}, None
    if not path.exists():
        return records, tail
    data = path.read_bytes()
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    elif lines:
        tail = (lines.pop(), False)
    for i, line in enumerate(lines, start=1):
        try:
            record = json.loads(line.decode("utf-8"))
            check_record(record, rows_by_id, out)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"Diario inválido en la línea {i}: {exc}") from None
        records[record["bldg_id"]] = record
    if tail is not None:
        try:
            record = json.loads(tail[0].decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return records, tail  # fragmento incompleto: repair_journal lo aparta y recorta
        try:
            check_record(record, rows_by_id, out)
        except ValueError as exc:
            raise ValueError(f"Último registro del diario (sin salto de línea) inválido: {exc}. "
                             "Revisa o corrige roster.jsonl a mano") from None
        records[record["bldg_id"]] = record
        tail = (tail[0], True)
    return records, tail


def repair_journal(out, tail):
    """Antes de agregar: completa el LF de un último registro íntegro, o aparta y recorta un fragmento."""
    if tail is None:
        return
    data, complete = tail
    path = safe_path(out, JOURNAL)
    if complete:  # ya validado e incluido en el roster por read_journal
        with path.open("ab") as stream:
            stream.write(b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        return
    keep = path.stat().st_size - len(data)
    side = path.with_name(f"{JOURNAL}.truncado-{now().replace(':', '')}")
    with side.open("xb") as stream:
        stream.write(data)
    with path.open("r+b") as stream:
        stream.truncate(keep)
        stream.flush()
        os.fsync(stream.fileno())


class Journal:
    def __init__(self, path):
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        self.stream = os.fdopen(os.open(path, flags, 0o644), "a", encoding="utf-8")
        self.lock = threading.Lock()

    def append(self, record):
        with self.lock:
            self.stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.stream.flush()
            os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


# --------------------------------------------------------------- validación

def validate_profile(path, bid):
    """Devuelve el número de filas o lanza ValueError con la causa del rechazo.

    Todo error de esquema, tipo o valor del archivo se convierte en ValueError; los errores
    de sistema (OSError, MemoryError, etc.) no se ocultan.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    bad = (pa.ArrowException, ValueError, TypeError, AttributeError, KeyError, OverflowError)
    try:
        parquet = pq.ParquetFile(path)
        if parquet.metadata.num_rows != STOCK_ROWS:
            raise ValueError(f"{parquet.metadata.num_rows} filas; se esperaban {STOCK_ROWS}")
        if not {"bldg_id", "timestamp", ENERGY} <= set(parquet.schema_arrow.names):
            raise ValueError("Faltan columnas bldg_id/timestamp/energía total")
        table = parquet.read(columns=["bldg_id", "timestamp", ENERGY])
        if any(table[name].null_count for name in ("bldg_id", "timestamp", ENERGY)):
            raise ValueError("Valores nulos en bldg_id, timestamp o energía")
        ids = table["bldg_id"].to_pylist()
        if any(isinstance(v, bool) or not isinstance(v, int) for v in ids) or set(ids) != {bid}:
            raise ValueError("bldg_id no entero o distinto del esperado")
        for i, value in enumerate(table["timestamp"].to_pylist()):
            if not isinstance(value, datetime) or value.replace(tzinfo=None) != FIRST + STEP * i:
                raise ValueError("Timestamps no válidos, fuera de orden, con paso distinto de "
                                 "15 min o fuera de 2018")
        for value in table[ENERGY].to_pylist():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError("Energía no numérica, no finita o negativa")
    except bad as exc:
        if isinstance(exc, ValueError) and not isinstance(exc, pa.ArrowException):
            raise
        raise ValueError(f"Parquet ilegible o con esquema inesperado: {exc}") from exc
    return table.num_rows


# ---------------------------------------------------------------- descarga

class Transient(Exception):
    pass


def download(url, part, max_bytes):
    """Descarga en streaming a `part`; devuelve (bytes, sha256). Respeta el máximo por archivo."""
    request = Request(url, headers={"User-Agent": "Proyecto-Big-Data-TecNM/1.0"})
    try:
        with urlopen(request, timeout=45) as response, part.open("xb") as writer:
            if urlparse(response.geturl()).hostname != HOST:
                raise ValueError("Redirección a un host no esperado")
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > max_bytes:
                raise ValueError(f"Content-Length {declared} excede el máximo {max_bytes}")
            sha, size = hashlib.sha256(), 0
            for chunk in iter(lambda: response.read(1 << 20), b""):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f"El archivo excede el máximo {max_bytes} bytes")
                sha.update(chunk)
                writer.write(chunk)
    except HTTPError as exc:
        if exc.code in {429, 500, 502, 503, 504}:
            raise Transient(f"HTTP {exc.code}") from exc
        raise OSError(f"HTTP {exc.code}") from exc
    except (URLError, TimeoutError, ConnectionError) as exc:
        raise Transient(str(exc)) from exc
    if declared is not None and size != int(declared):
        raise Transient("Descarga incompleta")
    return size, sha.hexdigest()


class Run:
    def __init__(self, args, out, journal):
        self.args, self.out, self.journal = args, out, journal
        self.lock = threading.Lock()
        self.bytes_used = 0

    def reserve(self):
        with self.lock:
            return self.bytes_used < self.args.max_bytes_lote

    def add_bytes(self, size):
        with self.lock:
            self.bytes_used += size


def base_record(row, previous):
    return dict(bldg_id=row["bldg_id"], estado_eeuu=row["estado"], tipo_vivienda=row["tipo_vivienda"],
                url=row["url"], estado_proceso=None, bytes=None, sha256=None, filas=None,
                segundos=None, error=None, intentos=(previous or {}).get("intentos", 0),
                capturado_utc=now(), ruta=None)


def reuse_or_conflict(run, row, previous, record):
    """Valida un archivo ya aceptado antes de reutilizarlo; nunca lo reemplaza."""
    try:
        path = safe_path(run.out, previous["ruta"])
        if (not path.is_file() or path.stat().st_size != previous["bytes"]
                or sha256_file(path) != previous["sha256"]):
            raise ValueError("el archivo local no coincide con el roster (bytes/SHA-256)")
        if run.args.revalidar:
            validate_profile(path, row["bldg_id"])
    except ValueError as exc:
        record.update(estado_proceso="conflicto", error=str(exc), ruta=previous["ruta"])
        return record
    record.update({k: previous[k] for k in ("bytes", "sha256", "filas", "ruta")},
                  estado_proceso="aceptado", segundos=0.0)
    return record


def process(run, row, previous):
    record = base_record(row, previous)
    rel = f"raw/resstock/{row['estado']}/{row['bldg_id']}-0.parquet"
    if previous and previous["estado_proceso"] == "aceptado":
        return reuse_or_conflict(run, row, previous, record)
    try:
        final = safe_path(run.out, rel)
        safe_path(run.out, rel + ".part")
        if final.exists() or final.is_symlink():
            raise FileExistsError
    except ValueError as exc:
        record.update(estado_proceso="conflicto", ruta=None, error=f"ruta interna insegura: {exc}")
        return record
    except FileExistsError:
        record.update(estado_proceso="conflicto", ruta=rel,
                      error="existe un archivo sin registro aceptado; no se sobrescribe")
        return record
    if not run.reserve():
        return None  # presupuesto de bytes agotado: queda pendiente, sin registro
    started = monotonic()
    part = final.with_name(final.name + ".part")
    try:
        safe_mkdir(run.out, Path(rel).parent.as_posix())
        part.unlink(missing_ok=True)  # un .part previo (o enlace) se descarta; "xb" no lo sigue
        for attempt in range(run.args.reintentos + 1):
            record["intentos"] += 1
            try:
                size, digest = download(row["url"], part, run.args.max_bytes_archivo)
                break
            except Transient as exc:
                part.unlink(missing_ok=True)
                if attempt == run.args.reintentos:
                    record.update(estado_proceso="fallido", error=f"transitorio: {exc}")
                    return record
                sleep(2 ** attempt)
        run.add_bytes(size)
        record.update(bytes=size, sha256=digest)
        try:
            record["filas"] = validate_profile(part, row["bldg_id"])
        except ValueError as exc:
            qrel = (f"cuarentena/{row['estado']}/"
                    f"{row['bldg_id']}-0.intento{record['intentos']}.parquet")
            safe_mkdir(run.out, Path(qrel).parent.as_posix())
            os.replace(part, safe_path(run.out, qrel))
            record.update(estado_proceso="rechazado", error=str(exc), ruta=qrel)
            return record
        os.replace(part, final)
        record.update(estado_proceso="aceptado", ruta=rel)
        return record
    except (OSError, ValueError) as exc:  # validate_profile ya convierte los errores de contenido
        record.update(estado_proceso="fallido" if record["bytes"] is None else "rechazado",
                      error=str(exc))
        return record
    finally:
        part.unlink(missing_ok=True)
        record["segundos"] = round(monotonic() - started, 3)
        record["capturado_utc"] = now()


# ------------------------------------------------------------ plan y resumen

def select_batch(ordered, journal, args):
    if args.continuar:
        pending = []
        for row in ordered:
            prev = journal.get(row["bldg_id"])
            retry = (prev and args.reintentar and prev["estado_proceso"] in {"fallido", "rechazado"}
                     and prev["intentos"] < args.max_intentos)
            if prev is None or retry:
                pending.append(row)
        return pending[:args.limite]
    return ordered[args.offset:args.offset + args.limite]


def summarize(selection, journal, run_bytes=None):
    """Todo se calcula sobre la misma selección; el diario ya se validó contra sus IDs."""
    ids = {row["bldg_id"] for row in selection}
    if not set(journal) <= ids:
        raise ValueError("El roster contiene IDs ajenos a la selección")
    counts = {}
    for record in journal.values():
        counts[record["estado_proceso"]] = counts.get(record["estado_proceso"], 0) + 1
    downloaded = sum(1 for r in journal.values() if r["bytes"] is not None)
    accepted = counts.get("aceptado", 0)
    if sum(counts.values()) != len(journal) or not (accepted <= downloaded <= len(journal) <= len(ids)):
        raise ValueError("Conteos inconsistentes entre selección y roster")
    return {
        "formato": FORMAT,
        "generado_utc": now(),
        "candidatos_en_seleccion": len(ids),
        "intentados_en_roster": len(journal),
        "descargados_con_bytes": downloaded,
        "aceptados": accepted,
        "rechazados": counts.get("rechazado", 0),
        "fallidos": counts.get("fallido", 0),
        "conflictos": counts.get("conflicto", 0),
        "pendientes_sin_intentar": len(ids) - len(journal),
        "meta_perfiles": 10000,
        "aceptados_sobre_meta": f"{accepted}/10000",
        "bytes_aceptados": sum(r["bytes"] for r in journal.values()
                               if r["estado_proceso"] == "aceptado"),
        "bytes_descargados_esta_ejecucion": run_bytes,
        "aviso": "Candidatos, descargados y aceptados son conjuntos distintos; solo "
                 "'aceptados' cuenta como procesado. " + ATTRIBUTION,
    }


def print_plan(args, selection, ordered, journal, batch, recognized):
    strata = {}
    for row in batch:
        strata[row["estado"]] = strata.get(row["estado"], 0) + 1
    plan = {
        "modo": "PLAN (sin descarga, sin escritura, sin red)",
        "selección": str(args.selection),
        "candidatos": len(selection),
        "semilla": args.seed,
        "lote": {"modo": "continuar" if args.continuar else "ventana", "offset": args.offset,
                 "limite": args.limite, "perfiles_en_lote": len(batch),
                 "primeros_ids": [r["bldg_id"] for r in batch[:5]],
                 "perfiles_por_estado": dict(sorted(strata.items()))},
        "estimacion_bytes_proyeccion_piloto": round(len(batch) * MEAN_BYTES_PILOT),
        "salida": str(args.output) if args.output else None,
        "salida_reconocida": recognized,
        "roster_actual": summarize(selection, journal) if recognized else None,
        "para_descargar": "repetir con --descargar --limite N (y --output)",
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))


# ------------------------------------------------------------ consolidación

def consolidate(out, selection_rows, journal):
    """Une los perfiles ACEPTADOS en consolidado/; adaptador previo a preparar_entrada_spark.py.

    Cada raw aceptado se revalida (ruta interna, bytes, SHA-256 y validate_profile) antes de
    leerlo. Todo se escribe en un staging hermano y se renombra al final; ante cualquier fallo
    se elimina el staging y no queda salida parcial. Un consolidado/ preexistente se rechaza.
    """
    import pyarrow.parquet as pq

    accepted = sorted(r["bldg_id"] for r in journal.values() if r["estado_proceso"] == "aceptado")
    if not accepted:
        raise ValueError("No hay perfiles aceptados para consolidar")
    final = safe_path(out, "consolidado")
    if os.path.lexists(final):
        raise FileExistsError(f"{final} ya existe; muévelo o elige otra salida (no se borra)")
    staging = Path(tempfile.mkdtemp(prefix=".consolidado.stage-", dir=out))
    try:
        os.chmod(staging, 0o755)
        parquet = staging / "resstock_perfiles_lote.parquet"
        writer = None
        try:
            for bid in accepted:
                record = journal[bid]
                try:
                    raw = safe_path(out, record["ruta"])
                    if (not raw.is_file() or raw.stat().st_size != record["bytes"]
                            or sha256_file(raw) != record["sha256"]):
                        raise ValueError("bytes/SHA-256 distintos del registro aceptado")
                    if validate_profile(raw, bid) != STOCK_ROWS:
                        raise ValueError("número de filas distinto de 35,040")
                except ValueError as exc:
                    raise ValueError(f"El perfil aceptado {bid} ya no es válido ({exc}); no se "
                                     "consolida. Revisa el raw y reejecuta el ingestor") from None
                table = pq.read_table(raw, columns=["bldg_id", "timestamp", ENERGY])
                table = table.rename_columns(["bldg_id", "timestamp_fin_local", "electricidad_kwh"])
                writer = writer or pq.ParquetWriter(parquet, table.schema, compression="snappy")
                writer.write_table(table)
        finally:
            if writer:
                writer.close()
        by_id = {r["bldg_id"]: r for r in selection_rows}
        with (staging / "resstock_seleccion_aceptada.csv").open("x", encoding="utf-8", newline="") as s:
            w = csv.DictWriter(s, fieldnames=["bldg_id", "estado", "tipo_vivienda", "upgrade", "url"])
            w.writeheader()
            for bid in accepted:
                r = by_id[bid]
                w.writerow(dict(bldg_id=bid, estado=r["estado"], tipo_vivienda=r["tipo_vivienda"],
                                upgrade=0, url=r["url"]))
        handle = pq.ParquetFile(parquet)
        ids = handle.read(columns=["bldg_id"])["bldg_id"].to_pylist()
        if handle.metadata.num_rows != len(accepted) * STOCK_ROWS or sorted(set(ids)) != accepted \
                or any(count != STOCK_ROWS for count in Counter(ids).values()):
            raise ValueError("El Parquet consolidado no coincide con los perfiles aceptados")
        atomic_write_json(staging / "consolidado.json", {
            "formato": FORMAT, "generado_utc": now(), "perfiles": len(accepted),
            "filas": len(accepted) * STOCK_ROWS, "sha256_parquet": sha256_file(parquet),
            "profile_roster": {"bldg_ids": accepted, "intervals_per_profile": STOCK_ROWS},
            "atribucion": ATTRIBUTION})
        if os.path.lexists(final):
            raise FileExistsError(f"{final} apareció durante la consolidación; no se sobrescribe")
        os.rename(staging, final)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return len(accepted)


# --------------------------------------------------------------------- main

def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    p.add_argument("--output", type=Path, help="Carpeta nueva o salida propia a reanudar")
    p.add_argument("--seed", type=int, default=22030511, help="Semilla del orden de lotes")
    p.add_argument("--offset", type=int, default=None,
                   help="Inicio de la ventana en el orden estable (0 por defecto; incompatible con --continuar)")
    p.add_argument("--limite", type=int, help="Perfiles del lote (obligatorio con --descargar)")
    p.add_argument("--continuar", action="store_true",
                   help="Toma los primeros --limite perfiles aún sin registro en el roster")
    p.add_argument("--reintentar", action="store_true",
                   help="Con --continuar, reintenta fallidos/rechazados hasta --max-intentos")
    p.add_argument("--max-intentos", type=int, default=3)
    p.add_argument("--reintentos", type=int, default=2, help="Reintentos transitorios por ejecución")
    p.add_argument("--descargar", action="store_true", help="OPT-IN: realiza descargas de red")
    p.add_argument("--concurrencia", type=int, default=2, help="Descargas simultáneas (máx. 4)")
    p.add_argument("--max-bytes-archivo", type=int, default=25_000_000)
    p.add_argument("--max-bytes-lote", type=int, default=2_000_000_000,
                   help="Tope aproximado de bytes por ejecución (puede excederse por la concurrencia)")
    p.add_argument("--revalidar", action="store_true", help="Revalida el Parquet de perfiles ya aceptados")
    p.add_argument("--consolidar", action="store_true",
                   help="Une los aceptados en consolidado/ (sin red; requiere --output)")
    return p.parse_args()


def check_args(args):
    """Valida los límites antes de tocar disco o red; devuelve el mensaje de error o None."""
    if args.limite is not None and args.limite < 1:
        return "--limite debe ser >= 1"
    if not 1 <= args.concurrencia <= 4:
        return "--concurrencia debe estar entre 1 y 4"
    if args.max_bytes_archivo < 1 or args.max_bytes_lote < 1:
        return "--max-bytes-archivo y --max-bytes-lote deben ser positivos"
    if args.reintentos < 0 or args.max_intentos < 1:
        return "--reintentos debe ser >= 0 y --max-intentos >= 1"
    if args.seed < 0:
        return "--seed debe ser >= 0"
    if args.offset is not None and args.offset < 0:
        return "--offset debe ser >= 0"
    if args.continuar and args.offset is not None:
        return "--continuar toma los siguientes pendientes y no admite --offset"
    if args.reintentar and not args.continuar:
        return "--reintentar solo aplica con --continuar"
    if args.descargar and (args.limite is None or args.output is None):
        return "--descargar exige --limite y --output explícitos"
    if args.consolidar and (args.output is None or args.descargar):
        return "--consolidar exige --output y no se combina con --descargar"
    return None


def main():
    args = parse_args()
    error = check_args(args)
    if error:
        sys.exit(error)
    try:
        return run_main(args)
    except (ValueError, FileExistsError) as exc:
        sys.exit(f"Error: {exc}")


def run_main(args):
    if args.limite is None:
        args.limite = 50  # solo para la previsualización
    selection = load_selection(args.selection)
    if args.offset is not None and args.offset >= len(selection):
        sys.exit("--offset está fuera de la selección")
    args.offset = args.offset or 0
    rows_by_id = {row["bldg_id"]: row for row in selection}
    ordered = order_selection(selection, args.seed)
    out, recognized = (check_output(args.output, args.selection) if args.output else (None, False))
    journal, tail = ({}, None)
    if recognized:
        marker = safe_path(out, MARKER)
        meta = json.loads(marker.read_text(encoding="utf-8"))
        if (not isinstance(meta, dict) or meta.get("formato") != FORMAT
                or meta.get("seleccion_sha256") != sha256_file(args.selection)
                or meta.get("semilla") != args.seed):
            sys.exit("La salida existente fue creada con otra selección/semilla; usa una salida nueva")
        journal, tail = read_journal(out, rows_by_id)

    if args.consolidar:
        if not recognized:
            sys.exit("--consolidar requiere una salida existente de esta herramienta")
        print(f"Consolidados {consolidate(out, selection, journal)} perfiles aceptados en {out}/consolidado")
        return 0

    batch = select_batch(ordered, journal, args)
    if not args.descargar:
        print_plan(args, selection, ordered, journal, batch, recognized)
        return 0

    out.mkdir(parents=True, exist_ok=True)
    if not recognized:
        atomic_write_json(safe_path(out, MARKER), {
            "formato": FORMAT, "creado_utc": now(), "semilla": args.seed,
            "seleccion": str(args.selection), "seleccion_sha256": sha256_file(args.selection),
            "candidatos": len(selection), "atribucion": ATTRIBUTION})
    repair_journal(out, tail)  # aparta/recorta una cola truncada antes de agregar
    diary = Journal(safe_path(out, JOURNAL))
    run = Run(args, out, diary)

    def work(row):
        record = process(run, row, journal.get(row["bldg_id"]))
        if record is not None:
            diary.append(record)  # un registro durable por perfil
        return record

    try:
        with ThreadPoolExecutor(max_workers=args.concurrencia) as pool:
            results = [r for r in pool.map(work, batch) if r is not None]
    finally:
        diary.close()
        final_journal, _ = read_journal(out, rows_by_id)
        atomic_write_json(safe_path(out, SUMMARY), summarize(selection, final_journal,
                                                   run_bytes=run.bytes_used))
    print(json.dumps({"solicitados_en_lote": len(batch), "procesados_esta_ejecucion": len(results),
                      **{k: v for k, v in json.loads(safe_path(out, SUMMARY).read_text()).items()
                         if k != "aviso"}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
