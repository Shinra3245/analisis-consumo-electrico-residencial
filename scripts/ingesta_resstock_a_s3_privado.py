#!/usr/bin/env python3
"""Ingesta ResStock a un bucket S3 PRIVADO, un perfil por vez (pensada para AWS CloudShell).

Por defecto solo imprime un PLAN y las comprobaciones que haría; no usa red ni AWS.
Con --ejecutar descarga cada perfil de OEDI a un archivo temporal, lo valida (Parquet,
ID, 35,040 intervalos de 15 min, valores) y calcula su SHA-256, lo sube con PUT privado a
raw/resstock/scale10k/<release>/<id>.parquet (SSE-S3, sin ACL, escritura condicional
If-None-Match, checksum SHA-256 validado por S3), verifica con HeadObject y relectura exacta,
y borra el temporal. No guarda datos crudos locales de forma persistente.

Credenciales: solo la cadena por defecto de boto3 (en CloudShell, credenciales temporales de
la sesión). El script no acepta ni imprime llaves ni tokens. No modifica políticas del bucket,
Public Access Block, versionado ni ningún otro recurso: solo lee esa configuración para
demostrar que el bucket es privado y escribe objetos bajo el prefijo fijo.

Atribución: Data includes information from the ResStock(TM) dataset developed by the National
Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).
Licencia CC BY 4.0; datos "as is" y para investigación, sin garantía. Ver
docs/decision-publicacion-datos.md: los crudos van solo a un bucket privado, jamás a Git,
sitio web ni gold/.
"""

import argparse
import base64
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

RELEASE_DEFAULT = "resstock_amy2018_release_1"
STOCK = ("https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/"
         "end-use-load-profiles-for-us-building-stock/2025/")
HOST = "oedi-data-lake.s3.amazonaws.com"
ENERGY = "out.electricity.total.energy_consumption..kwh"
STEP = timedelta(minutes=15)
FIRST = datetime(2018, 1, 1, 0, 15)
STOCK_ROWS = 35040
EXPECTED_IDS = 10_000
DEFAULT_SELECTION = Path("datos/resstock_seleccion_propuesta.csv")
SELECTION_FIELDS = ("bldg_id", "estado", "tipo_vivienda", "upgrade", "url")
REPO = Path(__file__).resolve().parent.parent
MAX_COST_CAP = 5.0  # umbral operativo (USD); --max-costo-usd no puede superarlo
FORMAT = "resstock-s3-privado-v1"
ATTRIBUTION = (
    "Data includes information from the ResStock(TM) dataset developed by the National "
    "Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy "
    "(DOE). CC BY 4.0. As is, para investigacion, sin garantia."
)
# Precios de lista de referencia (USD, S3 Standard); son ESTIMACIONES y se pueden sobrescribir.
PRICE_PUT_1000 = 0.005
PRICE_GET_1000 = 0.0004
PRICE_GB_MONTH = 0.023
PRICE_INTERREGION_GB = 0.02
STATES_OK = {"aceptado", "rechazado", "fallido", "conflicto"}
FATAL_CODES = {"AccessDenied", "NoSuchBucket", "InvalidAccessKeyId", "ExpiredToken",
               "SignatureDoesNotMatch", "AllAccessDisabled", "InvalidToken", "AccountProblem"}


class Fatal(Exception):
    """Condición que detiene la ejecución completa (falla cerrada)."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def b64_sha256(hex_digest):
    return base64.b64encode(bytes.fromhex(hex_digest)).decode()


# ---------------------------------------------------------------- selección

def load_selection(path, expected_rows):
    """Lee y valida la selección: sin duplicados, release/URL exactos y tamaño esperado."""
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
            expected = (f"{STOCK}resstock_amy2018_release_1/timeseries_individual_buildings/"
                        f"by_state/upgrade=0/state={state}/{bid}-0.parquet")
            if bid <= 0 or bid in seen or not re.fullmatch(r"[A-Z]{2}", state):
                raise ValueError(f"Línea {line}: ID duplicado/no positivo o estado inválido")
            if row["upgrade"] != "0" or row["url"] != expected:
                raise ValueError(f"Línea {line}: URL/upgrade distinto del release esperado")
            seen.add(bid)
            rows.append(dict(bldg_id=bid, estado=state, tipo_vivienda=row["tipo_vivienda"],
                             url=row["url"]))
    if len(rows) != expected_rows:
        raise ValueError(f"La selección tiene {len(rows)} IDs; se esperaban {expected_rows}")
    return rows


def order_selection(rows, seed):
    """Mismo orden determinista que scripts/ingesta_resstock_lotes.py (estratos intercalados)."""
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


def selection_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------ prefijo y llave

def safe_release(release):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", release) or ".." in release:
        raise ValueError("--release inválido")
    return release


def prefix_for(release):
    prefix = f"raw/resstock/scale10k/{safe_release(release)}/"
    if not prefix.startswith("raw/") or any(w in prefix for w in ("gold", "website", "public")):
        raise ValueError("Prefijo no seguro")
    return prefix


def key_for(prefix, bid):
    key = f"{prefix}{int(bid)}.parquet"
    if not key.startswith("raw/resstock/scale10k/"):
        raise ValueError("Llave fuera del prefijo raw/ permitido")
    return key


# ------------------------------------------------------------------- costos

def estimate_cost(n_profiles, mean_bytes, args, same_region=True):
    """Costo adicional de la PRIMERA ventana de 30 días del lote (umbral duro) y mensual recurrente.

    El umbral incluye solicitudes, transferencia (si aplicara) y el almacenamiento del lote de
    esos 30 días (se cobra como un mes completo, conservador). Con --max-bytes se calcula además
    una cota superior (bytes descargables como máximo) para el mismo concepto.
    """
    puts = n_profiles + 1  # perfiles + diario de auditoría
    gets = n_profiles * 2 + 4  # relectura + HEAD previo/posterior
    requests = puts / 1000 * args.precio_put_1000 + gets / 1000 * args.precio_get_1000

    def block(gb):
        transfer = 0.0 if same_region else gb * 2 * PRICE_INTERREGION_GB
        storage = gb * args.precio_gb_mes
        return {"gb": round(gb, 3), "usd_transferencia_entre_regiones": round(transfer, 4),
                "usd_almacenamiento_primeros_30_dias": round(storage, 4),
                "usd_adicional_primeros_30_dias": round(requests + transfer + storage, 4)}

    expected = block(n_profiles * mean_bytes / 1e9)
    out = {"perfiles": n_profiles, "usd_solicitudes_put_get_head": round(requests, 4),
           "estimado": expected, "umbral_usd": args.max_costo_usd,
           "usd_almacenamiento_mensual_recurrente": expected["usd_almacenamiento_primeros_30_dias"],
           "nota": "Estimación con precios de lista S3 Standard (sobrescribibles). El umbral cubre "
                   "solicitudes + transferencia + almacenamiento de los primeros 30 días del lote. "
                   "El costo mensual recurrente se informa aparte tras ese periodo. Excluye "
                   "impuestos, descuentos y otros servicios."}
    cap = None
    if args.max_bytes:
        cap = block(min(n_profiles * args.max_bytes_archivo, args.max_bytes + args.max_bytes_archivo) / 1e9)
        out["cota_superior_por_max_bytes"] = cap
    worst = max(expected["usd_adicional_primeros_30_dias"],
                cap["usd_adicional_primeros_30_dias"] if cap else 0.0)
    out["usd_adicional_umbral_evaluado"] = worst
    per_profile = (args.precio_put_1000 + 2 * args.precio_get_1000) / 1000 + \
        mean_bytes / 1e9 * (args.precio_gb_mes + (0 if same_region else 2 * PRICE_INTERREGION_GB))
    out["perfiles_maximos_bajo_umbral"] = int(max(args.max_costo_usd - 0.01, 0) / per_profile)
    return out


# --------------------------------------------------------------- validación

def validate_profile(path, bid):
    """Devuelve el número de filas o lanza ValueError con la causa del rechazo."""
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
                raise ValueError("Timestamps no válidos, fuera de orden o con paso distinto de 15 min")
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


def http_open(request, timeout=45):
    return urlopen(request, timeout=timeout)  # inyectable en pruebas con mocks


def download(url, dest, max_bytes, opener=http_open):
    """Streaming a `dest` (nuevo); devuelve (bytes, sha256 hex). Respeta el máximo por archivo."""
    if urlparse(url).hostname != HOST or not url.startswith("https://"):
        raise ValueError("URL fuera del host OEDI esperado")
    request = Request(url, headers={"User-Agent": "Proyecto-Big-Data-TecNM/1.0"})
    declared = None
    try:
        with opener(request) as response, dest.open("xb") as writer:
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
        raise Transient(type(exc).__name__) from exc
    if declared is not None and size != int(declared):
        raise Transient("Descarga incompleta")
    return size, sha.hexdigest()


def fetch_text(url, opener=http_open, limit=1 << 16):
    request = Request(url, headers={"User-Agent": "Proyecto-Big-Data-TecNM/1.0"})
    with opener(request) as response:
        if urlparse(response.geturl()).hostname != HOST:
            raise ValueError("Redirección a un host no esperado")
        return response.read(limit).decode("utf-8", "replace")


# ------------------------------------------------------------------- diario

def check_record(record, rows_by_id):
    bid = record.get("bldg_id")
    if not isinstance(bid, int) or isinstance(bid, bool) or bid not in rows_by_id:
        raise ValueError(f"bldg_id ajeno a la selección: {bid!r}")
    if record.get("estado_proceso") not in STATES_OK:
        raise ValueError(f"estado_proceso inválido para {bid}")
    digest = record.get("sha256")
    if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise ValueError(f"sha256 inválido para {bid}")
    if record["estado_proceso"] == "aceptado" and (
            not digest or record.get("filas") != STOCK_ROWS or not record.get("s3_key")):
        raise ValueError(f"registro aceptado incompleto para {bid}")


def read_journal(path, rows_by_id):
    """Último registro por ID. Una última línea truncada (caída) se ignora; otra corrupción falla."""
    records = {}
    if not path.exists():
        return records
    lines = path.read_bytes().split(b"\n")
    last_partial = lines[-1] != b""
    if not last_partial:
        lines.pop()
    for i, line in enumerate(lines, start=1):
        try:
            record = json.loads(line.decode("utf-8"))
            check_record(record, rows_by_id)
        except (ValueError, UnicodeDecodeError) as exc:
            if last_partial and i == len(lines):
                continue  # fragmento sin LF: escritura truncada, no cuenta como registro
            raise ValueError(f"Diario inválido en la línea {i}: {exc}") from None
        records[record["bldg_id"]] = record
    return records


class Journal:
    def __init__(self, path):
        if path.exists() and path.stat().st_size:
            data = path.read_bytes()
            if not data.endswith(b"\n"):  # recorta la cola truncada antes de agregar
                keep = data.rfind(b"\n") + 1
                with path.open("r+b") as stream:
                    stream.truncate(keep)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        self.path = path
        self.stream = os.fdopen(os.open(path, flags, 0o600), "a", encoding="utf-8")

    def append(self, record):
        self.stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


def check_journal_path(path):
    if path.is_symlink():
        raise ValueError("El diario no puede ser un enlace simbólico")
    resolved = path.resolve()
    if REPO in resolved.parents and not (REPO / "data" / "raw") in resolved.parents:
        raise ValueError("Dentro del repositorio solo se permite data/raw/ (ignorado por Git)")
    return path


# ---------------------------------------------------------------------- AWS

def code_of(exc):
    response = getattr(exc, "response", None) or {}
    err = response.get("Error", {})
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return str(err.get("Code", type(exc).__name__)), status


def make_session():
    """Cadena de credenciales por defecto de boto3; sin parámetros de llaves."""
    if os.environ.get("AWS_SECRET_ACCESS_KEY") and not os.environ.get("AWS_SESSION_TOKEN"):
        raise Fatal("Hay llaves AWS de larga duración en el entorno (sin token de sesión); "
                    "usa credenciales temporales (CloudShell). Abortado.")
    try:
        import boto3
    except ImportError as exc:
        raise Fatal("Falta boto3: verifica la sesión e instálalo en un venv (ver la guía)") from exc
    session = boto3.session.Session()
    if session.get_credentials() is None:
        raise Fatal("boto3 no encontró credenciales en la cadena por defecto")
    return session


def preflight(s3, sts, bucket, session_region, args):
    """Demuestra o aborta: operación PutObject condicional, región, bucket privado, identidad."""
    shape = s3.meta.service_model.operation_model("PutObject").input_shape.members
    for needed in ("IfNoneMatch", "ChecksumSHA256", "ServerSideEncryption"):
        if needed not in shape:
            raise Fatal(f"boto3/botocore demasiado antiguo: PutObject sin {needed}; actualiza")
    try:
        ident = sts.get_caller_identity()
    except Exception as exc:  # noqa: BLE001 - se traduce a un código sin detalles sensibles
        raise Fatal(f"No se pudo validar la identidad (STS): {code_of(exc)[0]}") from None
    try:
        head = s3.head_bucket(Bucket=bucket)
    except Exception as exc:  # noqa: BLE001
        raise Fatal(f"No se pudo acceder al bucket (HeadBucket): {code_of(exc)[0]}") from None
    bucket_region = head.get("ResponseMetadata", {}).get("HTTPHeaders", {}).get(
        "x-amz-bucket-region") or head.get("BucketRegion")
    if not bucket_region or bucket_region != session_region:
        raise Fatal(f"Región del bucket ({bucket_region}) distinta de la de la sesión "
                    f"({session_region}): evita transferencia entre regiones. Abortado.")
    try:
        pab = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    except Exception as exc:  # noqa: BLE001
        raise Fatal("No se pudo demostrar que el bucket es privado (GetPublicAccessBlock: "
                    f"{code_of(exc)[0]}). Se requiere s3:GetBucketPublicAccessBlock.") from None
    needed = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
    if not all(pab.get(k) is True for k in needed):
        raise Fatal("Public Access Block incompleto: el bucket no está demostrablemente privado. "
                    "Este script NO lo modifica; corrígelo fuera del script.")
    try:
        if s3.get_bucket_policy_status(Bucket=bucket)["PolicyStatus"]["IsPublic"]:
            raise Fatal("La política del bucket lo hace público. Abortado.")
    except Fatal:
        raise
    except Exception as exc:  # noqa: BLE001
        code = code_of(exc)[0]
        if code != "NoSuchBucketPolicy":
            print(f"AVISO: no se pudo leer PolicyStatus ({code}); se confía en Public Access Block.",
                  file=sys.stderr)
    # La identidad solo se valida; ni la cuenta ni el ARN se conservan ni se imprimen.
    return {"identidad_validada": bool(ident.get("Account") or ident.get("Arn")),
            "region": bucket_region}


def check_license(opener, release):
    text = fetch_text(f"{STOCK}{release}/citation.txt", opener)
    if not re.search(r"CC[- ]?BY[- ]?4\.0", text, re.I):
        raise Fatal("citation.txt del release no declara CC BY 4.0; no se puede demostrar la licencia")
    return hashlib.sha256(text.encode()).hexdigest()


def put_private(s3, bucket, key, path, size, digest, row, release):
    """PUT condicional privado. Devuelve 'subido', 'existia' o 'conflicto409'.

    412 = el objeto ya existe (se acepta solo tras verify_object). 409 (ConditionalRequestConflict)
    = otra solicitud concurrente sobre la misma llave: se reintenta UNA vez de forma condicional;
    si persiste, se devuelve 'conflicto409' y quien llama registra conflicto y detiene.
    """
    for attempt in range(2):
        with path.open("rb") as body:
            try:
                s3.put_object(
                    Bucket=bucket, Key=key, Body=body, ContentLength=size,
                    ContentType="application/vnd.apache.parquet",
                    ServerSideEncryption="AES256", ChecksumAlgorithm="SHA256",
                    ChecksumSHA256=b64_sha256(digest), IfNoneMatch="*",
                    Metadata={"sha256": digest, "bldg-id": str(row["bldg_id"]),
                              "release": release, "license": "CC-BY-4.0",
                              "source": "NREL-ResStock-OEDI"})
                return "subido"
            except Exception as exc:  # noqa: BLE001
                code, status = code_of(exc)
                if status == 412 or code == "PreconditionFailed":
                    return "existia"
                if status == 409 or code == "ConditionalRequestConflict":
                    if attempt == 0:
                        sleep(1)
                        continue
                    return "conflicto409"
                raise
    return "conflicto409"


def verify_object(s3, bucket, key, size, digest, readback):
    """HeadObject (tamaño, checksum, SSE) y relectura exacta en streaming; lanza ValueError."""
    head = s3.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED")
    if head.get("ContentLength") != size:
        raise ValueError(f"tamaño en S3 {head.get('ContentLength')} != {size}")
    if head.get("ChecksumSHA256") != b64_sha256(digest):
        raise ValueError("checksum SHA-256 en S3 no coincide")
    if head.get("ServerSideEncryption") != "AES256":
        raise ValueError(f"cifrado en S3 {head.get('ServerSideEncryption')!r}; se esperaba AES256")
    if readback:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"]
        sha, total = hashlib.sha256(), 0
        for chunk in iter(lambda: body.read(1 << 20), b""):
            sha.update(chunk)
            total += len(chunk)
        if total != size or sha.hexdigest() != digest:
            raise ValueError("la relectura de S3 no coincide byte a byte (tamaño/SHA-256)")


# ---------------------------------------------------------------- por perfil

def process(ctx, row, previous):
    args, s3 = ctx["args"], ctx["s3"]
    record = dict(bldg_id=row["bldg_id"], estado_eeuu=row["estado"], url=row["url"],
                  estado_proceso=None, s3_key=None, bytes=None, sha256=None, filas=None,
                  segundos=None, error=None, intentos=(previous or {}).get("intentos", 0) + 1,
                  capturado_utc=now(), run_id=ctx["run_id"])
    started = monotonic()
    key = key_for(ctx["prefix"], row["bldg_id"])
    tmp = Path(tempfile.mkdtemp(prefix="resstock-", dir=args.tmp))
    try:
        part = tmp / f"{row['bldg_id']}-0.parquet"
        last = None
        for attempt in range(args.reintentos + 1):
            try:
                size, digest = download(row["url"], part, args.max_bytes_archivo, ctx["opener"])
                last = None
                break
            except Transient as exc:
                last = str(exc)
                part.unlink(missing_ok=True)
                sleep(min(2 ** attempt, 30) * ctx["sleep_scale"])
        if last is not None:
            record.update(estado_proceso="fallido", error=f"red: {last}")
            return record
        record.update(bytes=size, sha256=digest, s3_key=key)
        try:
            record["filas"] = validate_profile(part, row["bldg_id"])
        except ValueError as exc:
            record.update(estado_proceso="rechazado", error=str(exc)[:300], s3_key=None)
            return record
        outcome = put_private(s3, args.bucket, key, part, size, digest, row, args.release)
        ctx["puts"] += 1
        if outcome == "conflicto409":
            record.update(estado_proceso="conflicto",
                          error="ConditionalRequestConflict (409) persistente tras un reintento; "
                                "no se verificó ni se sobrescribió el objeto")
            return record
        try:  # 412 solo se acepta si tamaño, SHA-256 y SSE coinciden (relectura forzada)
            verify_object(s3, args.bucket, key, size, digest,
                          readback=outcome == "existia" or ctx["n_done"] % args.readback_cada == 0)
        except ValueError as exc:
            record.update(estado_proceso="conflicto",
                          error=("objeto preexistente distinto" if outcome == "existia"
                                 else "verificación fallida tras PUT") + f": {exc}")
            return record
        record.update(estado_proceso="aceptado", error=None if outcome == "subido"
                      else "ya existía con idéntico SHA-256/tamaño; no se sobrescribió")
        return record
    except OSError as exc:
        record.update(estado_proceso="fallido", error=f"origen/local: {exc}"[:300])
        return record
    except ValueError as exc:
        record.update(estado_proceso="rechazado", error=str(exc)[:300])
        return record
    except Exception as exc:  # noqa: BLE001 - errores AWS: fatales o fallo por perfil sin detalles
        code, _ = code_of(exc)
        if code in FATAL_CODES:
            record.update(estado_proceso="fallido", error=f"AWS {code} (fatal)")
            raise Fatal(f"AWS {code}: permisos/credenciales/bucket. Detenido sin reintentar.") from None
        record.update(estado_proceso="fallido", error=f"AWS {code}")
        return record
    finally:
        record["segundos"] = round(monotonic() - started, 3)
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------- ejecución

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bucket", help="Bucket PRIVADO destino (nunca se guarda en Git)")
    p.add_argument("--release", default=RELEASE_DEFAULT)
    p.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    p.add_argument("--esperados", type=int, default=EXPECTED_IDS)
    p.add_argument("--seed", type=int, default=22030511)
    p.add_argument("--offset", type=int, default=0, help="Inicio de la ventana en el orden estable")
    p.add_argument("--limite", type=int, help="IDs máximos de esta ejecución (obligatorio con --ejecutar)")
    p.add_argument("--max-bytes", type=int, help="Tope de bytes descargados por ejecución (obligatorio)")
    p.add_argument("--max-bytes-archivo", type=int, default=25_000_000)
    p.add_argument("--max-costo-usd", type=float, default=MAX_COST_CAP)
    p.add_argument("--media-bytes", type=float, default=6_168_532.0,
                   help="Bytes medios por perfil para estimar (observado en 250 perfiles)")
    p.add_argument("--precio-put-1000", type=float, default=PRICE_PUT_1000)
    p.add_argument("--precio-get-1000", type=float, default=PRICE_GET_1000)
    p.add_argument("--precio-gb-mes", type=float, default=PRICE_GB_MONTH)
    p.add_argument("--diario", type=Path, default=Path("resstock_s3_diario.jsonl"))
    p.add_argument("--tmp", type=Path, default=None, help="Carpeta de temporales (se limpian por perfil)")
    p.add_argument("--reintentos", type=int, default=3)
    p.add_argument("--max-fallos-seguidos", type=int, default=5)
    p.add_argument("--max-anomalias", type=int, default=5, help="Rechazos+conflictos antes de detener")
    p.add_argument("--readback-cada", type=int, default=1, help="Relectura completa cada N perfiles")
    p.add_argument("--reintentar", action="store_true", help="Reintenta fallidos/rechazados previos")
    p.add_argument("--ejecutar", action="store_true", help="OPT-IN: usa red y AWS")
    args = p.parse_args(argv)
    if args.max_costo_usd <= 0 or args.max_costo_usd > MAX_COST_CAP:
        p.error(f"--max-costo-usd debe estar en (0, {MAX_COST_CAP}]")
    for name in ("esperados", "readback_cada", "max_fallos_seguidos", "max_anomalias",
                 "max_bytes_archivo"):
        if getattr(args, name) < 1:
            p.error(f"--{name.replace('_', '-')} debe ser >= 1")
    if args.offset < 0 or args.reintentos < 0 or args.seed < 0:
        p.error("--offset, --reintentos y --seed no pueden ser negativos")
    if args.limite is not None and args.limite < 1:
        p.error("--limite debe ser >= 1")
    if args.max_bytes is not None and args.max_bytes < 1:
        p.error("--max-bytes debe ser >= 1")
    if args.ejecutar and not (args.bucket and args.limite and args.max_bytes):
        p.error("--ejecutar exige --bucket, --limite y --max-bytes explícitos")
    if args.bucket and not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,62}", args.bucket):
        p.error("--bucket inválido")
    return args


def window(ordered, records, args):
    """IDs de esta ejecución: ventana [offset, offset+limite) sin aceptados; omite no reintentables."""
    chosen = []
    for row in ordered[args.offset:]:
        prev = records.get(row["bldg_id"])
        if prev and prev["estado_proceso"] == "aceptado":
            continue
        if prev and prev["estado_proceso"] == "conflicto":
            continue  # requiere decisión manual
        if prev and prev["estado_proceso"] in {"fallido", "rechazado"} and not args.reintentar:
            continue
        chosen.append(row)
        if args.limite and len(chosen) >= args.limite:
            break
    return chosen


def run(args, session=None, opener=http_open, sleep_scale=1.0):
    selection = load_selection(args.selection, args.esperados)
    ordered = order_selection(selection, args.seed)
    rows_by_id = {r["bldg_id"]: r for r in selection}
    prefix = prefix_for(args.release)
    check_journal_path(args.diario)
    records = read_journal(args.diario, rows_by_id)
    chosen = window(ordered, records, args)
    accepted = sum(1 for r in records.values() if r["estado_proceso"] == "aceptado")
    plan = {
        "formato": FORMAT, "modo": "ejecutar" if args.ejecutar else "plan",
        "seleccion_sha256": selection_sha(args.selection), "ids_en_seleccion": len(selection),
        "aceptados_en_diario": accepted, "ids_esta_ejecucion": len(chosen),
        "prefijo_s3": prefix, "atribucion": ATTRIBUTION,
        "costo": estimate_cost(len(chosen), args.media_bytes, args),
        "costo_bloque_completo_restante": estimate_cost(
            len(selection) - accepted, args.media_bytes, args),
    }
    if plan["costo"]["usd_adicional_umbral_evaluado"] > args.max_costo_usd:
        raise Fatal(
            f"Costo adicional de los primeros 30 días (USD {plan['costo']['usd_adicional_umbral_evaluado']}) "
            f"supera el umbral USD {args.max_costo_usd}; exige un lote menor: --limite <= "
            f"{plan['costo']['perfiles_maximos_bajo_umbral']} y/o --max-bytes menor")
    if not args.ejecutar:
        plan["siguiente"] = ("repetir con --ejecutar --bucket B --limite N --max-bytes BYTES "
                             "(solo en CloudShell autorizado)")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return plan

    args.tmp = args.tmp or Path(tempfile.gettempdir())
    free = shutil.disk_usage(args.tmp).free
    if free < 4 * args.max_bytes_archivo:
        raise Fatal(f"Espacio temporal insuficiente: {free} bytes libres")
    session = session or make_session()
    s3, sts = session.client("s3"), session.client("sts")
    info = preflight(s3, sts, args.bucket, session.region_name, args)
    license_sha = check_license(opener, args.release)
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    ctx = dict(args=args, s3=s3, prefix=prefix, opener=opener, run_id=run_id, puts=0,
               n_done=0, sleep_scale=sleep_scale)
    journal = Journal(args.diario)
    counts = {"aceptado": 0, "rechazado": 0, "fallido": 0, "conflicto": 0}
    used, streak, stop = 0, 0, None
    t0 = monotonic()
    try:
        for row in chosen:
            if used >= args.max_bytes:
                stop = "límite de bytes por ejecución alcanzado"
                break
            record = process(ctx, row, records.get(row["bldg_id"]))
            journal.append(record)
            ctx["n_done"] += 1
            counts[record["estado_proceso"]] += 1
            used += record["bytes"] or 0
            streak = streak + 1 if record["estado_proceso"] == "fallido" else 0
            if streak >= args.max_fallos_seguidos:
                stop = "demasiados fallos seguidos"
                break
            if counts["rechazado"] + counts["conflicto"] >= args.max_anomalias or \
                    record["estado_proceso"] == "conflicto":
                stop = "anomalía (rechazo/conflicto); revisar el diario antes de continuar"
                break
    except Fatal as exc:
        stop = f"FATAL: {exc}"
    finally:
        journal.close()
    summary = dict(plan, run_id=run_id, region=info["region"],
                   identidad_validada=info["identidad_validada"],
                   licencia_citation_sha256=license_sha, procesados=ctx["n_done"], **counts,
                   bytes_descargados=used, segundos=round(monotonic() - t0, 1),
                   motivo_parada=stop)
    audit_key = f"{prefix}_audit/{run_id}.json"
    try:  # manifiesto de auditoría de esta ejecución (no sobrescribe; mismo prefijo privado raw/)
        body = json.dumps(summary, ensure_ascii=False, indent=2).encode()
        s3.put_object(Bucket=args.bucket, Key=audit_key, Body=body, IfNoneMatch="*",
                      ServerSideEncryption="AES256", ContentType="application/json")
        summary["auditoria_s3_key"] = audit_key
    except Exception as exc:  # noqa: BLE001
        summary["auditoria_s3_key"] = f"no escrita ({code_of(exc)[0]}); ver diario local"
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main(argv=None):
    args = parse_args(argv)
    try:
        summary = run(args)
    except (Fatal, ValueError) as exc:
        print(f"ERROR (falla cerrada): {exc}", file=sys.stderr)
        return 2
    if summary.get("motivo_parada") and str(summary["motivo_parada"]).startswith("FATAL"):
        return 3
    return 0 if not summary.get("rechazado") and not summary.get("fallido") \
        and not summary.get("conflicto") else 1


if __name__ == "__main__":
    sys.exit(main())
