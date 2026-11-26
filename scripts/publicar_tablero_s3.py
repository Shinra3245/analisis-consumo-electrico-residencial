#!/usr/bin/env python3
"""Prepara un release local reproducible del dashboard web con Gold v2 y soporte de carga privada a S3.

Por defecto, opera en modo local/plan: valida estrictamente las 11 tablas del paquete Gold v2
frente a su manifiesto y reglas QC, rechaza symlinks y escapes en cada componente de archivo,
compila un HTML autocontenido e inmutable en un directorio de staging hermano, verifica
íntegramente el HTML y release_manifest.json en disco y realiza un renombrado atómico, sin invocar
servicios cloud.

Si el operador especifica explícitamente --upload, realiza una verificación previa para rechazar
claves existentes, aplica escritura condicional (IfNoneMatch='*') mediante SSE-S3 sin ACL pública,
y verifica ContentLength, ServerSideEncryption, ContentType y Metadata.sha256 mediante HeadObject,
fallando cerrado ante cualquier discrepancia.
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Contrato estricto: las 11 tablas Gold esperadas en v2
EXPECTED_V2_TABLES = {
    "gold_eia_monthly",
    "gold_resstock_monthly",
    "gold_resstock_pattern",
    "gold_resstock_pattern_aggregate",
    "gold_resstock_profile_summary",
    "gold_climate",
    "gold_demography_state_year",
    "gold_anomaly_candidates",
    "gold_anomaly_synthetic_eval",
    "gold_forecast_metrics",
    "gold_forecast_series",
}


def sha256_bytes(data: bytes) -> str:
    """Calcula el hash SHA-256 de una secuencia de bytes."""
    return hashlib.sha256(data).hexdigest()


def safe_inline_json(value: dict) -> str:
    """Serializa JSON de forma segura para incrustar dentro de etiquetas script HTML."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def validate_release_id(release_id: str) -> None:
    """Valida que el identificador de release tenga una estructura segura y acotada."""
    if not release_id:
        raise ValueError("El identificador de release no puede estar vacío.")

    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$", release_id):
        raise ValueError(
            f"Identificador de release inválido: '{release_id}'. "
            "Debe comenzar con caracter alfanumérico y contener solo letras, números, '.', '-' o '_' (máx 64 caracteres)."
        )
    if ".." in release_id or "/" in release_id or "\\" in release_id:
        raise ValueError(f"El release-id contiene caracteres de navegación no permitidos: '{release_id}'")


def validate_s3_prefix(s3_prefix: str) -> str:
    """Normaliza y valida que el prefijo S3 resida estrictamente bajo el namespace site/releases."""
    if not s3_prefix:
        return "site/releases"

    clean = s3_prefix.strip("/")
    parts = [p for p in clean.split("/") if p]

    if any(p in (".", "..") for p in parts) or "\\" in clean:
        raise ValueError(f"Prefijo S3 contiene segmentos de navegación inválidos: '{s3_prefix}'")

    if len(parts) < 2 or parts[:2] != ["site", "releases"]:
        raise ValueError(
            f"Restricción de namespace S3: el prefijo debe ubicarse bajo 'site/releases' (recibido: '{s3_prefix}')."
        )

    return "/".join(parts)


def verify_safe_file_within_root(file_path: Path, root_dir: Path) -> Path:
    """Verifica que file_path y cada componente de su ruta no sean symlinks y residan dentro de root_dir."""
    if file_path.is_symlink():
        raise ValueError(f"Seguridad de rutas: el archivo '{file_path}' es un enlace simbólico no permitido.")

    resolved_root = root_dir.resolve()

    # Comprobar cada componente intermedio entre file_path y root_dir
    curr = file_path
    while curr != root_dir and curr != curr.parent:
        if curr.is_symlink():
            raise ValueError(f"Seguridad de rutas: componente symlink detectado en '{curr}'.")
        curr = curr.parent

    resolved_file = file_path.resolve()
    if resolved_root not in resolved_file.parents and resolved_file != resolved_root:
        raise ValueError(
            f"Seguridad de rutas: el archivo '{file_path}' escapa de su directorio raíz '{root_dir}'."
        )

    return resolved_file


def validate_paths(web_dir: Path, data_dir: Path, out_dir: Path) -> None:
    """Valida seguridad de rutas, rechaza symlinks, solapamientos y directorios preexistentes."""
    if web_dir.is_symlink() or data_dir.is_symlink() or out_dir.is_symlink():
        raise ValueError("Seguridad de rutas: no se permiten enlaces simbólicos en web, data ni salida.")

    resolved_web = web_dir.resolve()
    resolved_data = data_dir.resolve()
    resolved_out = out_dir.resolve()

    if resolved_out == resolved_web or resolved_out == resolved_data:
        raise ValueError("Ruta de salida no puede ser idéntica a directorio web o data.")

    if resolved_web in resolved_out.parents or resolved_data in resolved_out.parents:
        raise ValueError("La ruta de salida no puede estar anidada dentro del código web ni de datos.")

    if resolved_out in resolved_web.parents or resolved_out in resolved_data.parents:
        raise ValueError("El directorio web o de datos no puede estar dentro del directorio de salida.")

    if resolved_out.exists():
        raise ValueError(
            f"El directorio de release ya existe: '{resolved_out}'. "
            "Para preservar la inmutabilidad y trazabilidad histórica, especifique un nuevo directorio "
            "(ej. dist/release-<id>)."
        )


def validate_bucket_name(bucket: str) -> None:
    """Valida reglas estrictas de nombres de bucket DNS de Amazon S3."""
    if not bucket:
        return

    bucket_pattern = r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"
    if not re.match(bucket_pattern, bucket):
        raise ValueError(
            f"Nombre de bucket S3 inválido: '{bucket}'. "
            "Debe tener entre 3 y 63 caracteres, letras minúsculas, números, puntos o guiones."
        )
    if ".." in bucket or ".-" in bucket or "-." in bucket:
        raise ValueError(f"Nombre de bucket S3 contiene secuencias prohibidas: '{bucket}'")
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", bucket):
        raise ValueError(f"El nombre de bucket S3 no puede tener formato de dirección IP: '{bucket}'")


def build_bundle(web_dir: Path, data_dir: Path) -> tuple[str, bytes, dict]:
    """Valida exhaustivamente el manifiesto v2, las 11 tablas contractuales y compila el HTML."""
    manifest_target = data_dir / "manifest.json"
    index_target = web_dir / "index.html"
    css_target = web_dir / "css/styles.css"

    if not index_target.is_file() or not manifest_target.is_file():
        raise FileNotFoundError("Se requieren index.html en web_dir y manifest.json en data_dir.")

    manifest_file = verify_safe_file_within_root(manifest_target, data_dir)
    index_file = verify_safe_file_within_root(index_target, web_dir)
    css_file = verify_safe_file_within_root(css_target, web_dir)

    manifest_raw = manifest_file.read_bytes()
    manifest_hash = sha256_bytes(manifest_raw)
    manifest = json.loads(manifest_raw.decode("utf-8"))

    schema_version = str(manifest.get("schema_version", manifest.get("manifest_version", "")))
    if schema_version != "1.0":
        raise ValueError(f"El manifiesto Gold debe declarar esquema 1.0 (encontrado: '{schema_version}').")

    # Validación estricta de reglas QC del manifiesto
    qc_meta = manifest.get("qc_rules", {})
    failed_rules = qc_meta.get("failed_rules", 0)
    if failed_rules > 0:
        raise ValueError(
            f"El manifiesto declara {failed_rules} reglas de calidad fallidas. Generación de release bloqueada."
        )
    qc_status = qc_meta.get("status", "")
    if qc_status not in ("VALID", "VALID_WITH_WARNINGS"):
        raise ValueError(f"Estado de calidad no válido en el manifiesto de datos: '{qc_status}'.")

    # Validación de inventario contractual de las 11 tablas
    tables_dict = manifest.get("tables", {})
    actual_table_keys = set(tables_dict.keys())

    missing_tables = EXPECTED_V2_TABLES - actual_table_keys
    if missing_tables:
        raise ValueError(f"Faltan tablas contractuales v2 en el manifiesto: {sorted(missing_tables)}")

    extra_tables = actual_table_keys - EXPECTED_V2_TABLES
    if extra_tables:
        raise ValueError(f"Se detectaron tablas no contempladas en el contrato v2: {sorted(extra_tables)}")

    files = {"manifest.json": manifest_raw.decode("utf-8")}
    tables_meta = {}
    total_rows = 0

    for table_name in sorted(EXPECTED_V2_TABLES):
        entry = tables_dict[table_name]

        rel_file = entry.get("file")
        expected_bytes = entry.get("bytes")
        expected_sha = entry.get("sha256")
        expected_rows = entry.get("rows")

        if not rel_file or expected_bytes is None or not expected_sha or expected_rows is None:
            raise ValueError(
                f"Metadatos incompletos para tabla '{table_name}': 'file', 'bytes', 'sha256' y 'rows' son obligatorios."
            )

        rel_path = Path(rel_file)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"Ruta de archivo insegura en manifiesto para tabla '{table_name}': {rel_path}")

        raw_table_target = data_dir / rel_path
        if not raw_table_target.is_file():
            raise FileNotFoundError(f"Archivo de tabla no encontrado en disco: {raw_table_target}")

        # Verificación estricta anti-symlink y no-escape para cada tabla y sus subdirectorios
        full_table_path = verify_safe_file_within_root(raw_table_target, data_dir)

        raw_bytes = full_table_path.read_bytes()
        actual_bytes = len(raw_bytes)
        actual_sha = sha256_bytes(raw_bytes)

        if actual_bytes != expected_bytes:
            raise ValueError(
                f"Discrepancia de tamaño en '{table_name}': esperado {expected_bytes} B, obtenido {actual_bytes} B"
            )
        if actual_sha != expected_sha:
            raise ValueError(
                f"Discrepancia de SHA-256 en '{table_name}': esperado {expected_sha}, obtenido {actual_sha}"
            )

        try:
            rows = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Error al parsear JSON de la tabla '{table_name}': {e}")

        if not isinstance(rows, list):
            raise ValueError(f"Formato inválido en '{table_name}': se esperaba arreglo JSON de registros.")
        if len(rows) != expected_rows:
            raise ValueError(
                f"Discrepancia de filas en '{table_name}': esperado {expected_rows} filas, obtenido {len(rows)}"
            )

        total_rows += len(rows)
        files[rel_path.as_posix()] = raw_bytes.decode("utf-8")
        tables_meta[table_name] = {
            "file": rel_path.as_posix(),
            "rows": len(rows),
            "bytes": actual_bytes,
            "sha256": actual_sha,
        }

    # Empaquetado estático de HTML, CSS y JavaScript
    html_src = index_file.read_text(encoding="utf-8")
    css_src = css_file.read_text(encoding="utf-8")

    js_files = ["js/config.js", "js/data.js", "js/charts.js", "js/iso.js", "js/main.js"]
    js_parts = []
    for name in js_files:
        js_target = web_dir / name
        if not js_target.is_file():
            raise FileNotFoundError(f"Archivo JavaScript no encontrado: {js_target}")
        safe_js_file = verify_safe_file_within_root(js_target, web_dir)
        js_parts.append(safe_js_file.read_text(encoding="utf-8"))

    combined_js = "\n".join(js_parts)
    combined_js = re.sub(r"^\s*import\s+.*?;\s*$", "", combined_js, flags=re.M)
    combined_js = re.sub(r"\bexport\s+(?=(?:(?:async\s+)?function|const|let|var|class)\b)", "", combined_js)

    if re.search(r"^\s*(?:import|export)\s", combined_js, flags=re.M):
        raise ValueError("Quedó una declaración de módulo ES sin resolver al incrustar JavaScript.")

    css_link_regex = re.compile(r'<link\s+rel="stylesheet"\s+href="css/styles\.css"\s*>', re.I)
    script_tag_regex = re.compile(r'<script\s+type="module"\s+src="js/main\.js"\s*>\s*</script>', re.I)

    html_out, n_css = css_link_regex.subn(lambda _: "<style>\n" + css_src + "\n</style>", html_src, count=1)
    if n_css != 1:
        raise ValueError("No se pudo reemplazar la etiqueta <link> de CSS en index.html.")

    bundle_script = (
        "<script>window.__GOLD_DATA_BUNDLE__=" + safe_inline_json(files) + ";"
        "const __goldFetch=window.fetch.bind(window);window.fetch=async(input,init)=>{"
        "const u=new URL(typeof input==='string'?input:input.url,location.href);"
        "const key=decodeURIComponent(u.pathname.split('/').pop());"
        "const raw=window.__GOLD_DATA_BUNDLE__[key];"
        "return raw===undefined?__goldFetch(input,init):new Response(raw,{status:200,"
        "headers:{'Content-Type':key.endsWith('.json')?'application/json':'text/plain'}});};"
        "</script>\n"
    )

    inlined_script = bundle_script + '<script type="module">\n' + combined_js + "\n</script>"
    html_out, n_js = script_tag_regex.subn(lambda _: inlined_script, html_out, count=1)
    if n_js != 1:
        raise ValueError("No se pudo reemplazar la etiqueta <script> de main.js en index.html.")

    bundle_bytes = html_out.encode("utf-8")
    data_summary = {
        "manifest_sha256": manifest_hash,
        "tables_count": len(tables_meta),
        "total_rows": total_rows,
        "tables": tables_meta,
    }

    return html_out, bundle_bytes, data_summary


def execute_s3_upload(
    html_bytes: bytes,
    bucket: str,
    key: str,
    region: str,
    expected_sha: str,
) -> dict:
    """Ejecuta una carga privada a S3 garantizando inmutabilidad y validación estricta con HeadObject."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        raise RuntimeError("La librería 'boto3' es requerida para ejecutar la acción opcional --upload.")

    s3_client = boto3.client("s3", region_name=region)

    # 1. Comprobación previa de existencia para rechazar sobreescrituras (inmutabilidad estricta)
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        raise RuntimeError(
            f"Violación de inmutabilidad: el objeto 's3://{bucket}/{key}' ya existe en S3. "
            "No se permite sobrescribir ni reemplazar un release previo."
        )
    except ClientError as e:
        error_code = str(e.response.get("Error", {}).get("Code", ""))
        if error_code not in ("404", "NoSuchKey", "NotFound"):
            raise RuntimeError(f"Error al verificar existencia previa en S3: {e}")

    # 2. Carga privada usando SSE-S3 y condición IfNoneMatch='*' (condicional a nivel API de S3)
    try:
        put_params = {
            "Bucket": bucket,
            "Key": key,
            "Body": html_bytes,
            "ContentType": "text/html; charset=utf-8",
            "ServerSideEncryption": "AES256",
            "Metadata": {"sha256": expected_sha},
            "IfNoneMatch": "*",  # Escritura condicional atómica: solo crea si no existe
        }
        s3_client.put_object(**put_params)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Fallo cerrado en put_object hacia 's3://{bucket}/{key}': {e}")

    # 3. Verificación post-carga con HeadObject: tamaño, cifrado, tipo y metadatos
    try:
        head_resp = s3_client.head_object(Bucket=bucket, Key=key)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Fallo al verificar el objeto remoto tras la carga: {e}")

    remote_size = head_resp.get("ContentLength")
    if remote_size != len(html_bytes):
        raise RuntimeError(
            f"Verificación fallida: tamaño remoto ({remote_size} B) difiere del local ({len(html_bytes)} B)."
        )

    server_side_enc = head_resp.get("ServerSideEncryption")
    if server_side_enc != "AES256":
        raise RuntimeError(f"Verificación fallida: cifrado no esperado ({server_side_enc}).")

    remote_content_type = head_resp.get("ContentType", "")
    if "text/html" not in remote_content_type:
        raise RuntimeError(f"Verificación fallida: ContentType no esperado ({remote_content_type}).")

    remote_meta_sha = head_resp.get("Metadata", {}).get("sha256", "")
    if remote_meta_sha != expected_sha:
        raise RuntimeError(
            f"Verificación fallida: Metadata.sha256 remoto ('{remote_meta_sha}') no coincide con local ('{expected_sha}')."
        )

    return {
        "status": "UPLOAD_VERIFIED",
        "etag_md5": head_resp.get("ETag", "").strip('"'),
        "server_side_encryption": server_side_enc,
        "content_length": remote_size,
        "content_type": remote_content_type,
        "verified_sha256": remote_meta_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--web", type=Path, default=ROOT / "tablero", help="Ruta del directorio web del tablero.")
    parser.add_argument("--datos", type=Path, default=ROOT / "tablero/data/v2", help="Ruta de tablas Gold v2.")
    parser.add_argument(
        "--salida-dir",
        type=Path,
        default=ROOT / "dist/release-v2",
        help="Directorio local donde se generará la carpeta de release inmutable (debe ser una ruta nueva).",
    )
    parser.add_argument(
        "--release-id",
        type=str,
        default="",
        help="Identificador único del release (alfanumérico, '.', '-' o '_'). Si se omite, se deriva de fecha y hash.",
    )
    parser.add_argument(
        "--s3-prefix",
        type=str,
        default="site/releases",
        help="Prefijo S3 obligatorio bajo el namespace 'site/releases' (por defecto: 'site/releases').",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=False,
        help="Ejecuta la acción de carga privada a S3 hacia el bucket especificado.",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default="",
        help="Nombre del bucket S3 de destino (requerido únicamente si se activa --upload).",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="Región AWS del bucket (por defecto: us-east-1).",
    )

    args = parser.parse_args()

    # Validaciones iniciales de rutas, identificadores y bucket
    try:
        validate_paths(args.web, args.datos, args.salida_dir)
        validate_bucket_name(args.bucket)
        clean_prefix = validate_s3_prefix(args.s3_prefix)
    except ValueError as e:
        print(f"ERROR de validación: {e}", file=sys.stderr)
        return 1

    if args.upload and not args.bucket:
        print("ERROR: La opción --upload requiere indicar un --bucket válido.", file=sys.stderr)
        return 1

    print("=" * 72)
    print("Preparación de Release Autónomo del Dashboard (Gold v2)")
    print(f"Directorio Web:        {args.web}")
    print(f"Directorio Datos Gold: {args.datos}")
    print(f"Directorio de Salida:  {args.salida_dir}")
    print("=" * 72)

    # 1. Compilación y validación exhaustiva de datos
    print("Validando tablas Gold v2 y empaquetando HTML autónomo...")
    try:
        html_str, html_bytes, data_summary = build_bundle(args.web, args.datos)
    except Exception as e:
        print(f"ERROR durante el empaquetado: {e}", file=sys.stderr)
        return 1

    bundle_sha = sha256_bytes(html_bytes)
    bundle_size = len(html_bytes)

    # 2. Validación o generación segura de Release ID
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_utc.strftime("%Y%m%dT%H%M%SZ")
    if args.release_id:
        try:
            validate_release_id(args.release_id)
            release_id = args.release_id
        except ValueError as e:
            print(f"ERROR en --release-id: {e}", file=sys.stderr)
            return 1
    else:
        release_id = f"v2-{now_utc.strftime('%Y%m%d')}-{bundle_sha[:8]}"

    proposed_key = f"{clean_prefix}/{release_id}/index.html"

    # 3. Creación atómica mediante staging hermano
    parent_dir = args.salida_dir.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = parent_dir / f".staging_{args.salida_dir.name}_{uuid.uuid4().hex[:8]}"

    try:
        staging_dir.mkdir(parents=True, exist_ok=False)
        index_dest = staging_dir / "index.html"
        index_dest.write_text(html_str, encoding="utf-8")

        release_manifest = {
            "release_id": release_id,
            "built_at_utc": now_str,
            "schema_version": "1.0",
            "package_version": "2.0",
            "artifact": {
                "file": "index.html",
                "bytes": bundle_size,
                "sha256": bundle_sha,
                "content_type": "text/html; charset=utf-8",
            },
            "s3_target": {
                "proposed_object_key": proposed_key,
                "server_side_encryption": "AES256",
                "access_control": "private (no ACL sent; bucket policy and Block Public Access remain unchanged)",
            },
            "source_data": data_summary,
        }

        manifest_dest = staging_dir / "release_manifest.json"
        with open(manifest_dest, "w", encoding="utf-8") as f:
            json.dump(release_manifest, f, indent=2, ensure_ascii=False)

        # Verificación estricta previa al rename atómico: releer y verificar HTML y manifiesto
        if not index_dest.is_file() or index_dest.is_symlink():
            raise IOError("El archivo index.html en staging es inválido o no existe.")
        if not manifest_dest.is_file() or manifest_dest.is_symlink():
            raise IOError("El archivo release_manifest.json en staging es inválido o no existe.")

        read_html_bytes = index_dest.read_bytes()
        read_manifest_bytes = manifest_dest.read_bytes()

        actual_html_size = len(read_html_bytes)
        actual_html_sha = sha256_bytes(read_html_bytes)

        if actual_html_size != bundle_size or actual_html_sha != bundle_sha:
            raise ValueError("Discrepancia en staging: bytes o hash de index.html no coinciden con el empaquetado.")

        try:
            read_manifest_obj = json.loads(read_manifest_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Discrepancia en staging: release_manifest.json no es JSON válido: {e}")

        if read_manifest_obj.get("release_id") != release_id:
            raise ValueError("Discrepancia en staging: release_id no coincide en release_manifest.json.")

        if read_manifest_obj.get("s3_target", {}).get("proposed_object_key") != proposed_key:
            raise ValueError("Discrepancia en staging: proposed_object_key no coincide en release_manifest.json.")

        declared_bytes = read_manifest_obj.get("artifact", {}).get("bytes")
        declared_sha = read_manifest_obj.get("artifact", {}).get("sha256")

        if actual_html_size != declared_bytes:
            raise ValueError(
                f"Discrepancia en staging: tamaño de HTML ({actual_html_size} B) difiere del declarado ({declared_bytes} B)."
            )
        if actual_html_sha != declared_sha:
            raise ValueError(
                f"Discrepancia en staging: SHA-256 de HTML ({actual_html_sha}) difiere del declarado ({declared_sha})."
            )

        # Renombrado atómico a la ruta final
        staging_dir.rename(args.salida_dir)
    except Exception as e:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        print(f"ERROR durante la escritura atómica del release local: {e}", file=sys.stderr)
        return 1

    final_manifest = args.salida_dir / "release_manifest.json"
    print(f"✔ Release local generado atómicamente en: {args.salida_dir}")
    print(f"  - Release ID:    {release_id}")
    print(f"  - Archivo HTML:  index.html ({bundle_size:,} bytes)")
    print(f"  - SHA-256:       {bundle_sha}")
    print(f"  - S3 Clave Prop: {proposed_key}")
    print(f"  - Manifiesto:    release_manifest.json ({final_manifest.stat().st_size:,} bytes)")

    # 4. Modo Upload (opcional y desactivado por defecto)
    if args.upload:
        print("\nIniciando carga privada hacia Amazon S3...")
        try:
            upload_result = execute_s3_upload(
                html_bytes=html_bytes,
                bucket=args.bucket,
                key=proposed_key,
                region=args.region,
                expected_sha=bundle_sha,
            )
            print("✔ Carga verificada exitosamente:")
            print(f"  - ETag (MD5):             {upload_result.get('etag_md5')}")
            print(f"  - Cifrado en reposo:      {upload_result.get('server_side_encryption')}")
            print(f"  - ContentType verificado: {upload_result.get('content_type')}")
            print(f"  - SHA-256 verificado:     {upload_result.get('verified_sha256')}")
            print(f"  - Tamaño confirmado:      {upload_result.get('content_length'):,} bytes")
            print("\nNota importante: El objeto se almacenó con acceso privado.")
            print("Para compartir temporalmente, genere una URL prefirmada con vigencia acotada desde la consola S3.")
        except Exception as e:
            print(f"ERROR en la carga o verificación en S3: {e}", file=sys.stderr)
            return 1
    else:
        print("\nModo local/plan completado. No se ejecutaron llamadas de red ni acciones AWS.")
        print("Para cargar conscientemente este artefacto en el bucket del equipo, ejecute:")
        print(f"  python3 scripts/publicar_tablero_s3.py --upload --bucket <nombre-bucket> --region {args.region}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
