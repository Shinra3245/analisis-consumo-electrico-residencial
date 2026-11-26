#!/usr/bin/env python3
"""Adapta un lote ACEPTADO de ingesta_resstock_lotes.py a la entrada de preparar_entrada_spark.py.

Es opt-in y de solo lectura sobre la salida del ingestor: no renombra ni altera nada allí y
no copia los Parquet individuales de raw/. Emite, en una carpeta nueva y mediante staging y
renombre atómico, un directorio con `datos/` (los cinco nombres que exige el contrato) y
`manifiesto.json` (la lista de registros que consume scripts/preparar_entrada_spark.py).

Los nombres `resstock_perfiles_piloto.parquet` y `resstock_seleccion_piloto.csv` son nombres
fijos del contrato actual; en un lote ampliado contienen los perfiles ACEPTADOS reales
(`perfiles_aceptados` en el manifiesto), no necesariamente 10. No afirma que Spark lo haya
procesado.
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingesta_resstock_lotes import (  # noqa: E402
    FORMAT, MARKER, STOCK_ROWS, load_selection, read_journal, safe_path, sha256_file,
)

REPO = Path(__file__).resolve().parent.parent
PARQUET = "resstock_perfiles_piloto.parquet"
PILOT_CSV = "resstock_seleccion_piloto.csv"
SELECTION = "resstock_seleccion_propuesta.csv"
EIA = "eia_residencial_mensual.csv"
WEATHER = "clima_open_meteo_muestra.csv"
COLUMNS = ["bldg_id", "timestamp_fin_local", "electricidad_kwh"]
CONSOLIDATED = "consolidado/resstock_perfiles_lote.parquet"


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return max(0, sum(1 for _ in csv.reader(stream)) - 1)


def external_file(path, name, ingest):
    """Entrada explícita: archivo regular, no simbólico, con el nombre del contrato y fuera del ingestor."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{name}: debe ser un archivo regular, no un enlace: {path}")
    resolved = path.resolve()
    if resolved.name != name:
        raise ValueError(f"{path} debe llamarse {name} (nombre del contrato y del manifiesto base)")
    if ingest == resolved or ingest in resolved.parents:
        raise ValueError(f"{name} no puede salir de la carpeta del ingestor: {path}")
    return resolved


def check_base(path, base, rows=None):
    """Compara bytes, SHA-256 y filas con el manifiesto base; no inventa metadatos."""
    record = base.get(path.name)
    if record is None:
        raise ValueError(f"El manifiesto base no declara {path.name}")
    if path.stat().st_size != record.get("bytes") or sha256_file(path) != record.get("sha256"):
        raise ValueError(f"{path.name} no coincide con bytes/SHA-256 del manifiesto base")
    count = csv_rows(path)
    if count != record.get("rows"):
        raise ValueError(f"{path.name}: {count} filas; el manifiesto base declara {record.get('rows')}")
    return count


def check_output(output, ingest, inputs):
    if os.path.lexists(output):
        raise FileExistsError(f"La salida ya existe; elige una carpeta nueva: {output}")
    if output.parent.is_symlink():
        raise ValueError("El directorio padre de la salida no puede ser un enlace simbólico")
    parent = output.parent.resolve()
    final = parent / output.name
    forbidden = [ingest, REPO / "datos", REPO / "docs", REPO / "scripts", REPO / "tablero"]
    forbidden += [p.parent for p in inputs]
    for base in forbidden:
        if final == base or base in final.parents or final in base.parents:
            raise ValueError(f"La salida se solapa con una entrada o con código del repositorio: {base}")
    return final


def accepted_ids(journal):
    return sorted(bid for bid, record in journal.items() if record["estado_proceso"] == "aceptado")


def check_consolidated(ingest, ids):
    """El Parquet consolidado debe contener exactamente los perfiles aceptados del roster."""
    import pyarrow.parquet as pq

    meta_path = safe_path(ingest, "consolidado/consolidado.json")
    parquet = safe_path(ingest, CONSOLIDATED)
    if not meta_path.is_file() or not parquet.is_file():
        raise ValueError("Falta consolidado/: ejecuta ingesta_resstock_lotes.py --consolidar primero")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    roster = meta.get("profile_roster") if isinstance(meta, dict) else None
    if (not isinstance(roster, dict) or roster.get("bldg_ids") != ids
            or roster.get("intervals_per_profile") != STOCK_ROWS
            or meta.get("perfiles") != len(ids) or meta.get("filas") != len(ids) * STOCK_ROWS):
        raise ValueError("consolidado.json no coincide con los perfiles aceptados actuales; el lote "
                         "cambió tras consolidar. Mueve consolidado/ y vuelve a consolidar")
    if sha256_file(parquet) != meta.get("sha256_parquet"):
        raise ValueError("El SHA-256 del Parquet consolidado no coincide con consolidado.json")
    handle = pq.ParquetFile(parquet)
    if handle.schema_arrow.names != COLUMNS or handle.metadata.num_rows != len(ids) * STOCK_ROWS:
        raise ValueError("Columnas o número de filas del Parquet consolidado inesperados")
    counts = Counter(int(v) for v in handle.read(columns=["bldg_id"])["bldg_id"].to_pylist())
    if set(counts) != set(ids) or any(c != STOCK_ROWS for c in counts.values()):
        raise ValueError("Los bldg_id del Parquet no coinciden con los perfiles aceptados")
    return parquet


def write_pilot_csv(path, candidates, ids):
    """Subconjunto de la selección de candidatos (mismas columnas) con los perfiles aceptados."""
    wanted = set(ids)
    with candidates.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = [row for row in reader if int(row["bldg_id"]) in wanted]
    if sorted(int(row["bldg_id"]) for row in rows) != ids:
        raise ValueError("Algún perfil aceptado no está (o está repetido) en la selección de candidatos")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build(args):
    if args.ingesta.is_symlink() or not args.ingesta.is_dir():
        raise ValueError("--ingesta debe ser un directorio, no un enlace")
    ingest = args.ingesta.resolve()
    eia = external_file(args.eia, EIA, ingest)
    weather = external_file(args.clima, WEATHER, ingest)
    candidates = external_file(args.seleccion_candidatos, SELECTION, ingest)
    base_path = args.base_manifest.resolve(strict=True)
    base = {a["file"]: a for a in json.loads(base_path.read_text(encoding="utf-8"))["artifacts"]}
    output = check_output(args.output, ingest, [eia, weather, candidates, base_path])

    marker = safe_path(ingest, MARKER)
    meta = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else None
    if not isinstance(meta, dict) or meta.get("formato") != FORMAT:
        raise ValueError("--ingesta no es una salida reconocida de ingesta_resstock_lotes.py")
    if meta.get("seleccion_sha256") != sha256_file(candidates):
        raise ValueError("La selección de candidatos no es la usada por el ingestor (SHA-256 distinto)")
    selection = load_selection(candidates)
    journal, tail = read_journal(ingest, {row["bldg_id"]: row for row in selection})
    if tail is not None:
        raise ValueError("roster.jsonl termina sin salto de línea; reanuda el ingestor para repararlo")
    ids = accepted_ids(journal)
    if not ids:
        raise ValueError("El roster no tiene perfiles aceptados")
    parquet = check_consolidated(ingest, ids)
    counts = {name: check_base(path, base) for name, path in
              ((EIA, eia), (WEATHER, weather), (SELECTION, candidates))}

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    try:
        data = staging / "datos"
        data.mkdir()
        shutil.copyfile(eia, data / EIA)
        shutil.copyfile(weather, data / WEATHER)
        shutil.copyfile(candidates, data / SELECTION)
        shutil.copyfile(parquet, data / PARQUET)
        write_pilot_csv(data / PILOT_CSV, candidates, ids)
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        records = []
        for name in (PARQUET, SELECTION, EIA, WEATHER, PILOT_CSV):
            path = data / name
            rows = len(ids) * STOCK_ROWS if name == PARQUET else (
                len(ids) if name == PILOT_CSV else counts[name])
            record = {"archivo": f"datos/{name}", "fecha_utc": stamp, "bytes": path.stat().st_size,
                      "filas": rows, "sha256": sha256_file(path),
                      "estado": "derivado" if name in (PARQUET, PILOT_CSV) else "copiado",
                      "origen": "lote aceptado de ingesta_resstock_lotes.py"
                      if name in (PARQUET, PILOT_CSV) else "copia verificada contra el manifiesto base"}
            if name == PARQUET:
                record.update(perfiles_aceptados=len(ids),
                              candidatos_en_seleccion=len(selection),
                              profile_roster={"bldg_ids": ids, "intervals_per_profile": STOCK_ROWS})
            records.append(record)
        manifest = staging / "manifiesto.json"
        manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.replace(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"Entrada preparada en {output}: {len(ids)} perfiles aceptados de "
          f"{len(selection)} candidatos. Spark no se ha ejecutado con ella.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ingesta", type=Path, required=True, help="Salida reconocida del ingestor, ya consolidada")
    p.add_argument("--output", type=Path, required=True, help="Carpeta NUEVA para preparar_entrada_spark.py --prepared")
    p.add_argument("--base-manifest", type=Path, default=Path("datos/manifiesto-integracion.json"))
    p.add_argument("--eia", type=Path, required=True, help=f"Ruta explícita a {EIA}")
    p.add_argument("--clima", type=Path, required=True, help=f"Ruta explícita a {WEATHER}")
    p.add_argument("--seleccion-candidatos", type=Path, required=True,
                   help=f"Ruta explícita a {SELECTION} (la usada por el ingestor)")
    try:
        build(p.parse_args())
    except (ValueError, FileExistsError, OSError, KeyError) as exc:
        sys.exit(f"Error: {exc}")


if __name__ == "__main__":
    main()
