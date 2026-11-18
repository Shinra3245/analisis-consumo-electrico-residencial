#!/usr/bin/env python3
"""Empaqueta una salida de preparar_datos.py como entrada autocontenida para Spark.

Solo copia artefactos derivados; no copia archivos fuente bajo raw/. Rechaza una
carpeta de salida preexistente para evitar reemplazos accidentales.
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

INTERVALS_PER_PROFILE = 35040
REQUIRED = (
    "resstock_perfiles_piloto.parquet",
    "resstock_seleccion_propuesta.csv",
    "eia_residencial_mensual.csv",
    "clima_open_meteo_muestra.csv",
    "resstock_seleccion_piloto.csv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_prepared_record(manifest: list[dict], filename: str) -> dict:
    expected = f"datos/{filename}"
    matches = [row for row in manifest if row.get("archivo") == expected]
    if len(matches) != 1:
        raise ValueError(f"manifiesto.json debe declarar exactamente una vez {expected}.")
    return matches[0]


def csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as stream:
        return max(0, sum(1 for _ in csv.reader(stream)) - 1)


def build_input(prepared: Path, base_manifest_path: Path, output: Path) -> None:
    prepared = prepared.resolve(strict=True)
    base_manifest_path = base_manifest_path.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"La salida ya existe; elige una carpeta nueva: {output}")
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("La carpeta de entrada y la salida no pueden solaparse.")

    source_data = prepared / "datos"
    preparation_manifest_path = prepared / "manifiesto.json"
    preparation_manifest = json.loads(preparation_manifest_path.read_text(encoding="utf-8"))
    base_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    base_records = {row["file"]: row for row in base_manifest.get("artifacts", [])}
    prepared_records = {name: load_prepared_record(preparation_manifest, name) for name in REQUIRED}

    roster_record = prepared_records["resstock_perfiles_piloto.parquet"]
    roster = roster_record.get("profile_roster")
    if not isinstance(roster, dict):
        raise ValueError("El registro del Parquet no contiene profile_roster.")
    ids = roster.get("bldg_ids")
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in ids)
        or len(ids) != len(set(ids))
        or roster.get("intervals_per_profile") != INTERVALS_PER_PROFILE
    ):
        raise ValueError("profile_roster debe declarar IDs únicos y 35,040 intervalos por perfil.")

    parquet = source_data / "resstock_perfiles_piloto.parquet"
    table = pq.read_table(parquet, columns=["bldg_id"])
    counts: dict[int, int] = {}
    for value in table["bldg_id"].to_pylist():
        key = int(value)
        counts[key] = counts.get(key, 0) + 1
    expected_ids = set(ids)
    if (
        set(counts) != expected_ids
        or len(counts) != len(ids)
        or table.num_rows != len(ids) * INTERVALS_PER_PROFILE
        or any(count != INTERVALS_PER_PROFILE for count in counts.values())
    ):
        raise ValueError("El Parquet no coincide con el roster y cobertura esperada por perfil.")

    with (source_data / "resstock_seleccion_piloto.csv").open(
        encoding="utf-8", newline=""
    ) as pilot_file:
        pilot_rows = list(csv.DictReader(pilot_file))
    try:
        pilot_ids = {int(row["bldg_id"]) for row in pilot_rows}
    except (KeyError, ValueError) as exc:
        raise ValueError("resstock_seleccion_piloto.csv tiene IDs inválidos.") from exc
    if pilot_ids != expected_ids or len(pilot_rows) != len(expected_ids):
        raise ValueError("La selección piloto no coincide con los IDs del Parquet y profile_roster.")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    try:
        artifacts = []
        for filename in REQUIRED:
            source = source_data / filename
            target = staging / filename
            shutil.copy2(source, target)
            prepared_record = prepared_records[filename]
            if target.stat().st_size != prepared_record.get("bytes") or sha256(target) != prepared_record.get("sha256"):
                raise ValueError(f"El artefacto {filename} no coincide con manifiesto.json.")

            if filename == "resstock_perfiles_piloto.parquet":
                rows = table.num_rows
                roster_value = {
                    "bldg_ids": sorted(expected_ids),
                    "intervals_per_profile": INTERVALS_PER_PROFILE,
                }
            elif filename.endswith(".csv"):
                rows = csv_row_count(target)
                roster_value = None
                if rows != prepared_record.get("filas"):
                    raise ValueError(f"Conteo CSV no coincide con manifiesto.json: {filename}.")
            else:
                rows = prepared_record.get("filas")
                roster_value = None

            previous = base_records.get(filename)
            if previous is None and filename != "resstock_seleccion_piloto.csv":
                raise ValueError(f"El manifiesto base no contiene metadatos para {filename}.")
            artifact = dict(previous or {})
            artifact.update(
                {
                    "file": filename,
                    "format": "parquet" if filename.endswith(".parquet") else "csv",
                    "bytes": target.stat().st_size,
                    "rows": rows,
                    "sha256": sha256(target),
                }
            )
            if filename == "resstock_perfiles_piloto.parquet":
                artifact["profile_roster"] = roster_value
                artifact["transform"] = (
                    f"{len(expected_ids)} perfiles individuales concatenados; roster de IDs efectivamente "
                    "descargados; intervalos verificados a 35,040 por perfil."
                )
            elif filename == "resstock_seleccion_piloto.csv":
                artifact.update(
                    {
                        "source": "ResStock 2025 Release 1 national metadata, upgrade=0",
                        "source_url": "https://data.openei.org/submissions/4520",
                        "license": "CC BY 4.0; preserve attribution and disclaimer",
                        "transform": "Roster de selección piloto; IDs descargados, separado del índice de candidatos.",
                    }
                )
            artifacts.append(artifact)

        manifest = {
            "manifest_version": base_manifest.get("manifest_version", "1.0"),
            "integrated_date": datetime.now(timezone.utc).date().isoformat(),
            "note": "Entrada temporal local para Spark. No incluye archivos fuente bajo raw/.",
            "artifacts": artifacts,
        }
        (staging / "manifiesto-integracion.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True,
                        help="Raíz de salida de scripts/preparar_datos.py.")
    parser.add_argument("--base-manifest", type=Path, default=Path("datos/manifiesto-integracion.json"))
    parser.add_argument("--output", type=Path, required=True,
                        help="Carpeta de entrada nueva para scripts/job_spark_piloto.py.")
    args = parser.parse_args()
    build_input(args.prepared, args.base_manifest, args.output)
    print(f"Entrada Spark preparada sin fuentes raw: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
