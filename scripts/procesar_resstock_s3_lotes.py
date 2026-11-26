#!/usr/bin/env python3
"""Procesa por lotes (<= 200 perfiles) los perfiles ResStock de un bucket S3 PRIVADO con el job
Spark existente, sin EMR, y publica Silver/Gold por lote bajo prefijos nuevos.

Por defecto solo imprime un PLAN (sin red ni AWS). Con --ejecutar, para cada lote:
 1. verifica el lote en S3 (si ya existe su marca de commit, lo omite: idempotente);
 2. descarga en streaming cada perfil desde raw/resstock/scale10k/<release>/ a un directorio
    temporal, comprobando tamaño, checksum SHA-256 de S3, SSE-S3 y el contrato Parquet;
 3. arma, en el temporal, una salida con el mismo formato que el ingestor local (marca, roster,
    consolidado) y ejecuta SIN modificarlos adaptar_lote_resstock_spark.py,
    preparar_entrada_spark.py y job_spark_piloto.py (EIA y clima entran solo como contexto
    verificado contra datos/manifiesto-integracion.json, no se republican por lote);
 4. verifica el reporte (21/21 reglas, roster exacto, filas, hashes de cada archivo);
 5. publica en silver/resstock/scale10k/<processing-release>/<lote>/<run>/ y gold/resstock/scale10k/<processing-release>/
    <lote>/<run>/ con SSE-S3, ChecksumSHA256, IfNoneMatch (no sobrescribe), HEAD y relectura exacta;
 6. escribe al final la marca de commit gold/.../_commit/<lote>.json (IfNoneMatch). Solo entonces el
    lote cuenta como completo y se borra el temporal.
Un fallo en cualquier etapa deja el lote SIN declarar completo (los objetos huérfanos de ese intento
quedan bajo su <run> y se listan en el diario; este script nunca borra objetos de S3).

Credenciales: solo la cadena por defecto de boto3. No acepta ni imprime llaves, tokens, cuenta,
ARN ni el nombre del bucket. No toca el dashboard, Gold v2, el piloto ni los raw.

Atribución: Data includes information from the ResStock(TM) dataset developed by the National
Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE). CC BY 4.0,
"as is", para investigación. Ver docs/decision-publicacion-datos.md.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingesta_resstock_a_s3_privado as raw3  # noqa: E402  (validación, preflight y verificación S3)
import ingesta_resstock_lotes as ing  # noqa: E402  (contrato del ingestor local)

REPO = Path(__file__).resolve().parent.parent
FORMAT = "resstock-procesamiento-s3-v2"
MAX_BATCH = 200
WORKDIR_MARK = ".procesamiento-resstock"
CONTRACT_FILES = ("manifiesto-integracion.json", "resstock_seleccion_propuesta.csv",
                  "eia_residencial_mensual.csv", "clima_open_meteo_muestra.csv")
PUBLISH_TABLES = {  # tabla del job -> (capa, carpeta). EIA/clima no se republican por lote.
    "silver.resstock_profile_interval": ("silver", "resstock_profile_interval"),
    "gold_resstock_monthly": ("gold", "gold_resstock_monthly"),
}
LIMITATIONS = [
    "gold_resstock_pattern_aggregate del tablero (mediana/p10/p90 por estrato) NO se genera por lote: "
    "los percentiles no son componibles entre lotes disjuntos y generar_datos_tablero.py carga todo el "
    "Parquet en memoria. Este script produce gold_resstock_monthly, que sí es una unión exacta.",
    "El cierre de 10,000 perfiles exige que todos los lotes tengan marca de commit y una "
    "consolidación/QC global posterior; este script no declara esa meta.",
]


class Stop(Exception):
    """Falla de un lote o de la ejecución: se registra y se detiene sin declarar éxito."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_path(path):
    return ing.sha256_file(Path(path))


# ------------------------------------------------------------------- diario

class Diary:
    """JSONL durable (fsync por evento). Sin bucket, cuenta, ARN ni credenciales."""

    def __init__(self, path):
        if path.is_symlink():
            raise ValueError("El diario no puede ser un enlace simbólico")
        resolved = path.resolve()
        if REPO in resolved.parents and (REPO / "data" / "raw") not in resolved.parents:
            raise ValueError("Dentro del repositorio solo se permite data/raw/ (ignorado por Git)")
        if path.exists() and path.stat().st_size and not path.read_bytes().endswith(b"\n"):
            keep = path.read_bytes().rfind(b"\n") + 1  # cola truncada por una caída
            with path.open("r+b") as stream:
                stream.truncate(keep)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        self.stream = os.fdopen(os.open(path, flags, 0o600), "a", encoding="utf-8")

    def event(self, lote, etapa, estado, **extra):
        self.stream.write(json.dumps(dict(capturado_utc=now(), lote=lote, etapa=etapa,
                                          estado=estado, **extra), ensure_ascii=False) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


# -------------------------------------------------------------------- lotes

def plan_batches(ordered, offset, size, first, count):
    """Ventanas deterministas del orden estable: lote k = ordered[offset + k*size : ... + size]."""
    batches = []
    for k in range(first, first + count):
        start = offset + k * size
        rows = ordered[start:start + size]
        if not rows:
            break
        batches.append(dict(lote=f"b{k:05d}", indice=k, inicio=start, rows=rows))
    return batches


SEGMENT = re.compile(r"[A-Za-z0-9_=][A-Za-z0-9_.=\-]*")  # sin punto inicial: ni '.', ni '..', ni ocultos
AUX_NAMES = {"reporte_calidad.json", "manifiesto_ejecucion.json"}
COMMIT_MAX_BYTES = 4_000_000


def safe_relpath(rel, folder=None, suffix=None):
    """Ruta relativa POSIX estricta: sin '..', '.', absolutos, '\\', segmentos vacíos u ocultos."""
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel:
        raise Stop(f"ruta relativa no segura: {rel!r}")
    parts = rel.split("/")
    for seg in parts:
        if seg in {"", ".", ".."} or ".." in seg or not SEGMENT.fullmatch(seg):
            raise Stop(f"segmento no seguro en la ruta: {rel!r}")
    if folder and parts[:2] != folder.split("/"):
        raise Stop(f"{rel!r} no está bajo {folder}/")
    if suffix and not rel.endswith(suffix):
        raise Stop(f"{rel!r} no termina en {suffix}")
    return rel


def safe_key(key, layer=None, release=None, lote=None, run_id=None):
    """Llave S3 <capa>/resstock/scale10k/<release>/<lote>/<run>/<ruta> con segmentos estrictos."""
    parts = key.split("/") if isinstance(key, str) else []
    if len(parts) < 7 or parts[0] not in {"silver", "gold"} or parts[1:3] != ["resstock", "scale10k"]:
        raise Stop(f"llave fuera de los prefijos permitidos: {key!r}")
    if any(seg in {"", ".", ".."} or ".." in seg or not SEGMENT.fullmatch(seg) for seg in parts):
        raise Stop(f"segmento no seguro en la llave: {key!r}")
    if not re.fullmatch(r"b\d{5}", parts[4]):
        raise Stop(f"lote inválido en la llave: {key!r}")
    for got, want in ((parts[0], layer), (parts[3], release), (parts[4], lote), (parts[5], run_id)):
        if want is not None and got != want:
            raise Stop(f"la llave no pertenece al lote/intento esperado: {key!r}")
    return key


def commit_key(release, lote):
    return f"gold/resstock/scale10k/{raw3.safe_release(release)}/_commit/{lote}.json"


def layer_prefix(layer, release, lote, run_id):
    return f"{layer}/resstock/scale10k/{raw3.safe_release(release)}/{lote}/{run_id}/"


def not_found(exc):
    code, status = raw3.code_of(exc)
    return status == 404 or code in {"404", "NoSuchKey", "NotFound"}


def exists(s3, bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as exc:  # noqa: BLE001
        if not_found(exc):
            return False
        code = raw3.code_of(exc)[0]
        if code in raw3.FATAL_CODES:
            raise raw3.Fatal(f"AWS {code}: permisos/credenciales/bucket") from None
        raise Stop(f"No se pudo comprobar la marca de commit ({code})") from None


def verify_commit(ctx, batch, ckey):
    """Cierra el gate de 'lote ya completo': lee y valida la marca de commit y sus artefactos.

    Cualquier discrepancia (otra selección/semilla/ventana/roster, marca alterada, objeto faltante o
    distinto) lanza Stop: nunca se omite un lote por la mera existencia de la llave.
    """
    args, s3 = ctx["args"], ctx["s3"]
    lote, release = batch["lote"], args.processing_release
    ids = sorted(r["bldg_id"] for r in batch["rows"])

    def fail(msg):
        raise Stop(f"marca de commit {lote} existente pero NO verificable: {msg}. No se omite ni se "
                   "sobrescribe; requiere decisión manual")

    try:
        head = s3.head_object(Bucket=args.bucket, Key=ckey, ChecksumMode="ENABLED")
        size = head.get("ContentLength")
        if not isinstance(size, int) or not 0 < size <= COMMIT_MAX_BYTES:
            fail(f"tamaño {size!r} fuera de rango")
        body = s3.get_object(Bucket=args.bucket, Key=ckey)["Body"].read(COMMIT_MAX_BYTES + 1)
    except Stop:
        raise
    except Exception as exc:  # noqa: BLE001
        code = raw3.code_of(exc)[0]
        if code in raw3.FATAL_CODES:
            raise raw3.Fatal(f"AWS {code}: permisos/credenciales/bucket") from None
        fail(f"AWS {code}")
    digest = hashlib.sha256(body).hexdigest()
    meta = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
    if len(body) != size or head.get("ChecksumSHA256") != raw3.b64_sha256(digest):
        fail("bytes/SHA-256 de S3 no coinciden con el contenido leído")
    if head.get("ServerSideEncryption") != "AES256" or meta.get("sha256") != digest:
        fail("cifrado o metadato sha256 de la marca inválidos")
    try:
        doc = json.loads(body.decode("utf-8"))
    except ValueError:
        fail("JSON ilegible")
    if not isinstance(doc, dict):
        fail("la marca no es un objeto JSON")
    expected = dict(formato=FORMAT, estado="completo", lote=lote, release=release,
                    raw_release=args.release,
                    seleccion_sha256=ctx["selection_sha"], semilla=args.seed)
    for key, want in expected.items():
        if doc.get(key) != want:
            fail(f"campo {key} distinto del esperado")
    if doc.get("ventana") != dict(inicio=batch["inicio"], tamano=len(ids)):
        fail("ventana distinta")
    roster = doc.get("roster")
    if (not isinstance(roster, dict) or roster.get("bldg_ids") != ids
            or roster.get("intervals_per_profile") != ing.STOCK_ROWS
            or roster.get("filas") != len(ids) * ing.STOCK_ROWS):
        fail("roster distinto del lote esperado")
    spark = doc.get("spark")
    if (not isinstance(spark, dict) or spark.get("estado") not in {"VALID", "VALID_WITH_WARNINGS"}
            or spark.get("silver_filas") != len(ids) * ing.STOCK_ROWS):
        fail("QC/filas de Spark no aprobados en la marca")
    run_id = doc.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", run_id):
        fail("run_id inválido")
    raw_items = doc.get("raw")
    if (not isinstance(raw_items, list) or [r.get("bldg_id") for r in raw_items] != ids
            or any(not re.fullmatch(r"[0-9a-f]{64}", str(r.get("sha256"))) for r in raw_items)):
        fail("raw de la marca distinto del roster")
    published = doc.get("publicado")
    if not isinstance(published, list) or not published:
        fail("sin objetos publicados")
    tables = {item.get("tabla") for item in published if isinstance(item, dict)}
    if not {"silver.resstock_profile_interval", "gold_resstock_monthly", "reporte"} <= tables:
        fail("faltan tablas/reportes publicados")
    for item in published:
        try:
            key = safe_key(item.get("key"), run_id=run_id, release=release, lote=lote)
        except Stop as exc:
            fail(str(exc))
        if (not isinstance(item.get("bytes"), int) or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256")))):
            fail(f"registro de objeto inválido: {key}")
        try:
            raw3.verify_object(s3, args.bucket, key, item["bytes"], item["sha256"],
                               readback=args.readback_commit)
        except ValueError as exc:
            fail(f"{key}: {exc}")
        except Exception as exc:  # noqa: BLE001
            fail(f"{key}: AWS {raw3.code_of(exc)[0]}")
    # La marca y Silver/Gold pertenecen al namespace de salida, pero los perfiles
    # fuente conservan siempre el release raw de OEDI.
    prefix = raw3.prefix_for(args.release)
    for item in raw_items:  # el raw sigue siendo el mismo (checksum S3 de cada objeto)
        try:
            h = s3.head_object(Bucket=args.bucket, Key=raw3.key_for(prefix, item["bldg_id"]),
                               ChecksumMode="ENABLED")
        except Exception as exc:  # noqa: BLE001
            fail(f"raw {item['bldg_id']}: AWS {raw3.code_of(exc)[0]}")
        if h.get("ChecksumSHA256") != raw3.b64_sha256(item["sha256"]) or h.get("ContentLength") != item["bytes"]:
            fail(f"raw {item['bldg_id']} cambió respecto a la marca")
    return doc


# ------------------------------------------------------------- descarga raw

def reserve_bytes(ctx, size):
    """Reserva `size` del presupuesto --max-bytes ANTES de descargar; nunca permite excederlo."""
    if ctx["bytes_used"] + size > ctx["args"].max_bytes:
        raise Stop(f"--max-bytes agotado: usados {ctx['bytes_used']} + siguiente objeto {size} > "
                   f"{ctx['args'].max_bytes}; el lote queda sin completar")
    ctx["bytes_used"] += size


def fetch_profile(s3, bucket, key, dest, row, release, max_bytes, reserve=None):
    """Streaming S3 -> disco con verificación de tamaño, checksum S3, SSE y metadatos."""
    head = s3.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED")
    size = head.get("ContentLength")
    if not isinstance(size, int) or size < 1 or size > max_bytes:
        raise ValueError(f"tamaño en S3 {size!r} fuera de (0, {max_bytes}]")
    if reserve is not None:
        reserve(size)  # Stop si bytes_usados + size supera --max-bytes; reserva antes de descargar
    if head.get("ServerSideEncryption") != "AES256":
        raise ValueError("el objeto raw no declara SSE-S3 (AES256)")
    expected_b64 = head.get("ChecksumSHA256")
    if not expected_b64:
        raise ValueError("el objeto raw no tiene ChecksumSHA256 en S3")
    meta = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
    if meta.get("bldg-id") != str(row["bldg_id"]) or meta.get("license") != "CC-BY-4.0":
        raise ValueError("metadatos del objeto raw (bldg-id/license) no coinciden")
    body = s3.get_object(Bucket=bucket, Key=key)["Body"]
    sha, total = hashlib.sha256(), 0
    with dest.open("xb") as writer:
        for chunk in iter(lambda: body.read(1 << 20), b""):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("el streaming excede el máximo por archivo")
            sha.update(chunk)
            writer.write(chunk)
    digest = sha.hexdigest()
    if total != size or raw3.b64_sha256(digest) != expected_b64:
        raise ValueError("bytes/SHA-256 descargados no coinciden con S3")
    if meta.get("sha256") and meta["sha256"] != digest:
        raise ValueError("SHA-256 descargado distinto del metadato del objeto")
    return size, digest


# -------------------------------------------------------- entrada para Spark

def build_ingest_shim(work, rows, files, selection_path):
    """Salida con el formato del ingestor local (marca, roster, consolidado) para el adaptador."""
    import pyarrow.parquet as pq

    ingest = work / "ingesta"
    (ingest / "consolidado").mkdir(parents=True)
    ids = sorted(r["bldg_id"] for r in rows)
    by_id = {r["bldg_id"]: r for r in rows}
    (ingest / ing.MARKER).write_text(json.dumps({
        "formato": ing.FORMAT, "origen": FORMAT,
        "seleccion_sha256": sha256_path(selection_path)}, indent=2) + "\n", encoding="utf-8")
    with (ingest / ing.JOURNAL).open("x", encoding="utf-8") as journal:
        for bid in ids:
            row, info = by_id[bid], files[bid]
            journal.write(json.dumps(dict(
                bldg_id=bid, estado_eeuu=row["estado"], tipo_vivienda=row["tipo_vivienda"],
                url=row["url"], estado_proceso="aceptado", bytes=info["bytes"], sha256=info["sha256"],
                filas=ing.STOCK_ROWS, segundos=0.0, error=None, intentos=1, capturado_utc=now(),
                ruta=f"raw/resstock/{row['estado']}/{bid}-0.parquet")) + "\n")
    parquet = ingest / "consolidado" / "resstock_perfiles_lote.parquet"
    writer = None
    try:
        for bid in ids:
            table = pq.read_table(files[bid]["path"], columns=["bldg_id", "timestamp", ing.ENERGY])
            table = table.rename_columns(["bldg_id", "timestamp_fin_local", "electricidad_kwh"])
            writer = writer or pq.ParquetWriter(parquet, table.schema, compression="snappy")
            writer.write_table(table)
    finally:
        if writer:
            writer.close()
    handle = pq.ParquetFile(parquet)
    if handle.metadata.num_rows != len(ids) * ing.STOCK_ROWS:
        raise Stop("el consolidado temporal no tiene filas = perfiles x 35,040")
    (ingest / "consolidado" / "consolidado.json").write_text(json.dumps({
        "formato": ing.FORMAT, "generado_utc": now(), "perfiles": len(ids),
        "filas": len(ids) * ing.STOCK_ROWS, "sha256_parquet": sha256_path(parquet),
        "profile_roster": {"bldg_ids": ids, "intervals_per_profile": ing.STOCK_ROWS},
        "atribucion": ing.ATTRIBUTION}, indent=2) + "\n", encoding="utf-8")
    return ingest


def run_step(name, command, log_path, timeout):
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}  # Spark no necesita AWS
    with log_path.open("ab") as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise Stop(f"{name}: tiempo excedido ({timeout}s)") from None
    if result.returncode != 0:
        tail = log_path.read_bytes()[-400:].decode("utf-8", "replace").replace("\n", " ")
        raise Stop(f"{name}: código {result.returncode}: {tail}")


def run_spark_chain(work, datos, args):
    py = args.spark_python or sys.executable
    logs = work / "pasos.log"
    prepared, entrada, salida = work / "preparada", work / "entrada-spark", work / "salida-spark"
    base = datos / "manifiesto-integracion.json"
    run_step("adaptador", [py, str(REPO / "scripts/adaptar_lote_resstock_spark.py"),
                           "--ingesta", str(work / "ingesta"), "--output", str(prepared),
                           "--base-manifest", str(base),
                           "--eia", str(datos / "eia_residencial_mensual.csv"),
                           "--clima", str(datos / "clima_open_meteo_muestra.csv"),
                           "--seleccion-candidatos", str(datos / "resstock_seleccion_propuesta.csv")],
             logs, 600)
    run_step("preparar_entrada_spark", [py, str(REPO / "scripts/preparar_entrada_spark.py"),
                                        "--prepared", str(prepared), "--base-manifest", str(base),
                                        "--output", str(entrada)], logs, 600)
    run_step("job_spark", [py, str(REPO / "scripts/job_spark_piloto.py"), "--input", str(entrada),
                           "--output", str(salida), "--master", args.spark_master], logs,
             args.timeout_spark)
    return entrada, salida


# --------------------------------------------------------------- verificación

def verify_spark_output(salida, ids):
    """Gate: reporte 0 reglas fallidas, roster exacto, filas y hashes físicos de cada archivo."""
    import pyarrow.parquet as pq

    salida = Path(salida)
    for dirpath, dirnames, filenames in os.walk(salida):  # sin enlaces simbólicos en todo el árbol
        for name in dirnames + filenames:
            if os.path.islink(os.path.join(dirpath, name)):
                raise Stop(f"enlace simbólico en la salida de Spark: {name}")
    for name in AUX_NAMES:
        if not (salida / name).is_file():
            raise Stop(f"falta {name} en la salida de Spark")
    report = json.loads((salida / "reporte_calidad.json").read_text(encoding="utf-8"))
    manifest = json.loads((salida / "manifiesto_ejecucion.json").read_text(encoding="utf-8"))
    rules = report["resumen_reglas"]
    if (rules["estado_global"] not in {"VALID", "VALID_WITH_WARNINGS"} or rules["reglas_fallidas"] != 0
            or rules["bloqueo_publicacion_capas"]
            or rules["reglas_cumplidas"] != rules["total_reglas_evaluadas"]):
        raise Stop(f"QC de Spark no aprobado: {rules}")
    if manifest.get("quality_status") != rules["estado_global"]:
        raise Stop("el manifiesto de ejecución y el reporte discrepan en el estado de calidad")
    tables, outputs = {t["table"]: t for t in manifest["output_inventory"]}, []
    for table, (layer, folder) in PUBLISH_TABLES.items():
        if table not in tables or not tables[table]["files"]:
            raise Stop(f"falta la tabla {table} en el manifiesto de ejecución")
        listed = set()
        for item in tables[table]["files"]:
            rel = safe_relpath(item.get("file"), folder=f"{layer}/{folder}", suffix=".parquet")
            if rel in listed or any(o["relpath"] == rel for o in outputs):
                raise Stop(f"ruta duplicada en el manifiesto de ejecución: {rel}")
            listed.add(rel)
            path = salida / rel
            if (not isinstance(item.get("bytes"), int) or not isinstance(item.get("sha256"), str)
                    or path.is_symlink() or not path.is_file()
                    or salida.resolve() not in path.resolve().parents
                    or path.stat().st_size != item["bytes"] or sha256_path(path) != item["sha256"]):
                raise Stop(f"{rel}: bytes/SHA-256 no coinciden con el manifiesto de ejecución")
            outputs.append(dict(tabla=table, capa=layer, carpeta=folder, path=path,
                                relpath=rel, bytes=item["bytes"], sha256=item["sha256"]))
        ondisk = {p.relative_to(salida).as_posix() for p in (salida / layer / folder).rglob("*.parquet")}
        if ondisk != listed:
            raise Stop(f"{table}: archivos Parquet en disco distintos de los del manifiesto "
                       f"({sorted(ondisk ^ listed)[:3]})")
    silver_rows = tables["silver.resstock_profile_interval"]["row_count"]
    if silver_rows != len(ids) * ing.STOCK_ROWS:
        raise Stop(f"Silver ResStock tiene {silver_rows} filas; se esperaban {len(ids) * ing.STOCK_ROWS}")
    seen = set()
    for out in outputs:
        if out["capa"] == "silver":
            seen |= set(pq.read_table(out["path"], columns=["bldg_id"])["bldg_id"].to_pylist())
    if seen != set(ids):
        raise Stop("los bldg_id de Silver no coinciden exactamente con el roster del lote")
    intervals = {}
    for out in outputs:
        if out["capa"] == "gold":
            tab = pq.read_table(out["path"], columns=["bldg_id", "n_intervals"]).to_pydict()
            for bid, n in zip(tab["bldg_id"], tab["n_intervals"]):
                intervals[bid] = intervals.get(bid, 0) + n
    if set(intervals) != set(ids) or any(v != ing.STOCK_ROWS for v in intervals.values()):
        raise Stop("Gold mensual no cubre exactamente 35,040 intervalos por perfil del roster")
    return report, manifest, outputs, dict(silver_filas=silver_rows, gold_filas=tables[
        "gold_resstock_monthly"]["row_count"])


# ---------------------------------------------------------------- publicación

def put_new(s3, bucket, key, path, size, digest, extra_meta):
    """PUT privado condicional (sin ACL). 412/409 persistente => Stop: no se sobrescribe."""
    for attempt in range(2):
        with Path(path).open("rb") as body:
            try:
                s3.put_object(Bucket=bucket, Key=key, Body=body, ContentLength=size,
                              ServerSideEncryption="AES256", ChecksumAlgorithm="SHA256",
                              ChecksumSHA256=raw3.b64_sha256(digest), IfNoneMatch="*",
                              Metadata=extra_meta)
                return
            except Exception as exc:  # noqa: BLE001
                code, status = raw3.code_of(exc)
                if status == 412 or code == "PreconditionFailed":
                    raise Stop(f"{key}: ya existe; no se sobrescribe") from None
                if (status == 409 or code == "ConditionalRequestConflict") and attempt == 0:
                    sleep(1)
                    continue
                if code in raw3.FATAL_CODES:
                    raise raw3.Fatal(f"AWS {code}: permisos/credenciales/bucket") from None
                raise Stop(f"{key}: AWS {code}") from None


def check_publish_budget(outputs, extra_files, limit, commit_bytes=0):
    """--max-bytes-publicar cubre tablas + reportes auxiliares (+ marca de commit cuando se conoce)."""
    total = sum(o["bytes"] for o in outputs) + sum(o["bytes"] for o in extra_files) + commit_bytes
    if total > limit:
        raise Stop(f"la publicación ({total} bytes con auxiliares/commit) excede --max-bytes-publicar {limit}")
    return total


def publish_batch(s3, bucket, release, lote, run_id, outputs, extra_files):
    published = []
    for out in outputs + extra_files:
        layer = out["capa"]
        rel = safe_relpath(out["relpath"], suffix=None if out["relpath"].startswith("_report/") else ".parquet")
        key = safe_key(layer_prefix(layer, release, lote, run_id) + rel, layer, release, lote, run_id)
        put_new(s3, bucket, key, out["path"], out["bytes"], out["sha256"],
                {"sha256": out["sha256"], "lote": lote, "license": "CC-BY-4.0",
                 "source": "NREL-ResStock-OEDI"})
        try:
            raw3.verify_object(s3, bucket, key, out["bytes"], out["sha256"], readback=True)
        except ValueError as exc:
            raise Stop(f"{key}: verificación posterior al PUT falló: {exc}") from None
        published.append(dict(key=key, bytes=out["bytes"], sha256=out["sha256"],
                              tabla=out.get("tabla", "reporte")))
    return published


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return dict(path=path, bytes=path.stat().st_size, sha256=sha256_path(path))


# ----------------------------------------------------------------- un lote

def process_batch(ctx, batch):
    args, s3, diary = ctx["args"], ctx["s3"], ctx["diary"]
    lote, rows = batch["lote"], batch["rows"]
    ids = sorted(r["bldg_id"] for r in rows)
    ckey = commit_key(args.processing_release, lote)
    if exists(s3, args.bucket, ckey):
        try:
            verify_commit(ctx, batch, ckey)
        except Stop as exc:
            diary.event(lote, "commit", "invalido", error=str(exc)[:300])
            raise
        diary.event(lote, "commit", "ya_completo_verificado", perfiles=len(ids))
        return "omitido"
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    work = args.tmp / f"resstock-{lote}"
    if work.exists():
        raise Stop(f"{work} ya existe (intento previo sin verificar). Revísalo y bórralo tú; "
                   "este script no borra temporales de un intento no verificado")
    work.mkdir(parents=True)
    (work / WORKDIR_MARK).write_text(run_id + "\n")
    t0 = monotonic()
    diary.event(lote, "inicio", "ok", run_id=run_id, perfiles=len(ids), primero=ids[0], ultimo=ids[-1])
    try:
        rawdir = work / "raw"
        rawdir.mkdir()
        prefix = raw3.prefix_for(args.release)
        files = {}
        for row in sorted(rows, key=lambda r: r["bldg_id"]):
            dest = rawdir / f"{row['bldg_id']}.parquet"
            try:
                size, digest = fetch_profile(s3, args.bucket, raw3.key_for(prefix, row["bldg_id"]),
                                             dest, row, args.release, args.max_bytes_archivo,
                                             reserve=lambda n: reserve_bytes(ctx, n))
                raw3.validate_profile(dest, row["bldg_id"])
            except ValueError as exc:
                raise Stop(f"perfil {row['bldg_id']} inválido: {exc}") from None
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, (Stop, raw3.Fatal)):
                    raise
                code = raw3.code_of(exc)[0]
                if code in raw3.FATAL_CODES:
                    raise raw3.Fatal(f"AWS {code}: permisos/credenciales/bucket") from None
                raise Stop(f"perfil {row['bldg_id']}: {code}") from None
            files[row["bldg_id"]] = dict(bytes=size, sha256=digest, path=dest)
        diary.event(lote, "descarga", "ok", perfiles=len(files),
                    bytes=sum(f["bytes"] for f in files.values()))
        datos = args.datos
        shim = build_ingest_shim(work, rows, files, datos / "resstock_seleccion_propuesta.csv")
        diary.event(lote, "consolidado_temporal", "ok")
        entrada, salida = run_spark_chain(work, datos, args)
        diary.event(lote, "spark", "ok")
        report, manifest, outputs, counts = verify_spark_output(salida, ids)
        diary.event(lote, "verificacion_spark", "ok", **counts)
        extras = []
        for name, src in (("reporte_calidad.json", salida / "reporte_calidad.json"),
                          ("manifiesto_ejecucion.json", salida / "manifiesto_ejecucion.json")):
            extras.append(dict(capa="gold", path=src, relpath=f"_report/{name}",
                               bytes=src.stat().st_size, sha256=sha256_path(src)))
        check_publish_budget(outputs, extras, args.max_bytes_publicar)
        published = publish_batch(s3, args.bucket, args.processing_release, lote, run_id, outputs, extras)
        diary.event(lote, "publicacion", "ok", objetos=len(published))
        context = {name: dict(bytes=(datos / name).stat().st_size, sha256=sha256_path(datos / name))
                   for name in CONTRACT_FILES}
        commit = dict(
            formato=FORMAT, estado="completo", lote=lote, run_id=run_id,
            release=args.processing_release, raw_release=args.release,
            seleccion_sha256=ctx["selection_sha"], semilla=args.seed,
            ventana=dict(inicio=batch["inicio"], tamano=len(ids)),
            roster=dict(bldg_ids=ids, intervals_per_profile=ing.STOCK_ROWS,
                        filas=len(ids) * ing.STOCK_ROWS),
            raw=[dict(bldg_id=b, bytes=files[b]["bytes"], sha256=files[b]["sha256"]) for b in ids],
            spark=dict(estado=report["resumen_reglas"]["estado_global"],
                       reglas=report["resumen_reglas"]["reglas_cumplidas"],
                       version=report["metadatos_ejecucion"]["version_spark"], **counts),
            publicado=published,
            contexto_eia_clima_no_republicado=context,
            atribucion=raw3.ATTRIBUTION, limitaciones=LIMITATIONS, capturado_utc=now())
        info = write_json(work / "commit.json", commit)
        check_publish_budget(outputs, extras, args.max_bytes_publicar, info["bytes"])
        if info["bytes"] > COMMIT_MAX_BYTES:
            raise Stop("la marca de commit excede el tamaño máximo permitido")
        put_new(s3, args.bucket, ckey, info["path"], info["bytes"], info["sha256"],
                {"sha256": info["sha256"], "lote": lote, "license": "CC-BY-4.0"})
        raw3.verify_object(s3, args.bucket, ckey, info["bytes"], info["sha256"], readback=True)
    except ValueError as exc:
        diary.event(lote, "lote", "fallido", run_id=run_id, error=str(exc)[:300],
                    temporal=str(work.name))
        raise Stop(str(exc)) from None
    except BaseException as exc:
        diary.event(lote, "lote", "fallido", run_id=run_id, error=str(exc)[:300],
                    temporal=str(work.name),
                    huerfanos_posibles=f"silver|gold/resstock/scale10k/{args.processing_release}/{lote}/{run_id}/")
        raise
    shutil.rmtree(work)  # solo tras la verificación completa y la marca de commit leída de vuelta
    diary.event(lote, "lote", "completo", run_id=run_id, perfiles=len(ids),
                segundos=round(monotonic() - t0, 1), commit_sha256=info["sha256"])
    return "completo"


# ----------------------------------------------------------------- ejecución

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--bucket", help="Bucket PRIVADO (no se guarda en Git ni en el diario)")
    p.add_argument("--release", default=raw3.RELEASE_DEFAULT,
                   help="Release raw OEDI (prefijo de lectura; por defecto, ResStock AMY 2018)")
    p.add_argument("--output-release", default=None,
                   help="Namespace de salida/commit; por defecto toma release_id del manifiesto o --release")
    p.add_argument("--datos", type=Path, default=REPO / "datos",
                   help="Carpeta con los 4 archivos de contrato y manifiesto-integracion.json")
    p.add_argument("--seed", type=int, default=22030511)
    p.add_argument("--esperados", type=int, default=raw3.EXPECTED_IDS)
    p.add_argument("--offset", type=int, default=0, help="Inicio de las ventanas en el orden estable")
    p.add_argument("--lote-tam", type=int, default=MAX_BATCH, help=f"Perfiles por lote (<= {MAX_BATCH})")
    p.add_argument("--lote-inicio", type=int, default=0, help="Índice del primer lote")
    p.add_argument("--max-lotes", type=int, default=1, help="Lotes máximos de esta ejecución")
    p.add_argument("--max-bytes", type=int, help="Tope de bytes raw descargados por ejecución")
    p.add_argument("--max-bytes-archivo", type=int, default=25_000_000)
    p.add_argument("--max-bytes-publicar", type=int, default=2_000_000_000,
                   help="Tope de bytes Silver/Gold publicados por lote")
    p.add_argument("--tmp", type=Path, default=None, help="Directorio temporal de trabajo")
    p.add_argument("--diario", type=Path, default=Path("procesamiento_resstock_diario.jsonl"))
    p.add_argument("--readback-commit", action="store_true",
                   help="Al omitir un lote ya completo, releer también cada objeto publicado (si no, HEAD + checksum)")
    p.add_argument("--spark-python", help="Intérprete con pyspark (por defecto, el actual)")
    p.add_argument("--spark-master", default="local[2]")
    p.add_argument("--timeout-spark", type=int, default=3600)
    p.add_argument("--ejecutar", action="store_true", help="OPT-IN: usa red y AWS")
    args = p.parse_args(argv)
    if not 1 <= args.lote_tam <= MAX_BATCH:
        p.error(f"--lote-tam debe estar entre 1 y {MAX_BATCH}")
    if min(args.offset, args.lote_inicio, args.seed) < 0 or args.max_lotes < 1 \
            or args.timeout_spark < 1 or args.max_bytes_archivo < 1 or args.max_bytes_publicar < 1:
        p.error("parámetros numéricos fuera de rango")
    if args.max_bytes is not None and args.max_bytes < 1:
        p.error("--max-bytes debe ser >= 1")
    if args.bucket and not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,62}", args.bucket):
        p.error("--bucket inválido")
    if args.ejecutar and not (args.bucket and args.max_bytes):
        p.error("--ejecutar exige --bucket y --max-bytes explícitos")
    return args


def load_plan(args):
    for name in CONTRACT_FILES:
        if not (args.datos / name).is_file() or (args.datos / name).is_symlink():
            raise ValueError(f"Falta {name} en --datos (archivo regular, no enlace)")
    selection_path = args.datos / "resstock_seleccion_propuesta.csv"
    selection = raw3.load_selection(selection_path, args.esperados)
    manifest = json.loads((args.datos / "manifiesto-integracion.json").read_text(encoding="utf-8"))
    manifest_release = manifest.get("release_id")
    args.processing_release = raw3.safe_release(
        args.output_release or manifest_release or args.release)
    ordered = raw3.order_selection(selection, args.seed)
    batches = plan_batches(ordered, args.offset, args.lote_tam, args.lote_inicio, args.max_lotes)
    if not batches:
        raise ValueError("La ventana pedida queda fuera de la selección")
    return raw3.selection_sha(selection_path), batches


def run(args, session=None):
    selection_sha, batches = load_plan(args)
    plan = dict(formato=FORMAT, modo="ejecutar" if args.ejecutar else "plan",
                release=args.processing_release, raw_release=args.release,
                seleccion_sha256=selection_sha, lotes=[dict(
                    lote=b["lote"], inicio=b["inicio"], perfiles=len(b["rows"]),
                    primer_id=b["rows"][0]["bldg_id"]) for b in batches],
                prefijos=dict(raw=raw3.prefix_for(args.release),
                              silver=f"silver/resstock/scale10k/{args.processing_release}/",
                              gold=f"gold/resstock/scale10k/{args.processing_release}/"),
                limitaciones=LIMITATIONS, atribucion=raw3.ATTRIBUTION)
    if not args.ejecutar:
        plan["siguiente"] = "repetir con --ejecutar --bucket B --max-bytes BYTES (CloudShell autorizado)"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return plan
    args.tmp = args.tmp or Path(tempfile.gettempdir())
    resolved_tmp = args.tmp.resolve()
    if REPO in resolved_tmp.parents or resolved_tmp == REPO:
        raise raw3.Fatal("--tmp no puede estar dentro del repositorio")
    need = args.lote_tam * args.max_bytes_archivo // 2 + args.max_bytes_publicar
    free = shutil.disk_usage(args.tmp).free
    if free < need:
        raise raw3.Fatal(f"Espacio temporal insuficiente: {free} bytes libres; se requieren ~{need}")
    session = session or raw3.make_session()
    s3, sts = session.client("s3"), session.client("sts")
    info = raw3.preflight(s3, sts, args.bucket, session.region_name, args)
    license_sha = raw3.check_license(raw3.http_open, args.release)
    diary = Diary(args.diario)
    ctx = dict(args=args, s3=s3, diary=diary, bytes_used=0, selection_sha=selection_sha)
    results, stop = {}, None
    t0 = monotonic()
    try:
        for batch in batches:
            results[batch["lote"]] = process_batch(ctx, batch)
    except (Stop, raw3.Fatal) as exc:
        stop = str(exc)[:300]
        results.setdefault(batch["lote"], "fallido")
    finally:
        diary.close()
    done = [b for b in batches if results.get(b["lote"]) in {"completo", "omitido"}]
    summary = dict(plan, region=info["region"], identidad_validada=info["identidad_validada"],
                   licencia_citation_sha256=license_sha, resultados=results,
                   lotes_completos_o_ya_existentes=len(done),
                   perfiles_en_lotes_completos=sum(len(b["rows"]) for b in done),
                   bytes_raw_descargados=ctx["bytes_used"], segundos=round(monotonic() - t0, 1),
                   motivo_parada=stop,
                   nota="No se declara la meta de 10,000: solo cuentan lotes con marca de commit y "
                        "una consolidación/QC global posterior.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main(argv=None):
    args = parse_args(argv)
    try:
        summary = run(args)
    except (raw3.Fatal, ValueError) as exc:
        print(f"ERROR (falla cerrada): {exc}", file=sys.stderr)
        return 2
    return 1 if summary.get("motivo_parada") else 0


if __name__ == "__main__":
    sys.exit(main())
