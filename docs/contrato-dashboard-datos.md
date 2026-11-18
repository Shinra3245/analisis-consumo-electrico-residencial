# Contrato de datos para el tablero web (v1)

**Estado:** Implementado y verificado en `tablero/data/v1/`.
**Script generador:** [`scripts/generar_datos_tablero.py`](../scripts/generar_datos_tablero.py) y flag `--export-tablero` en [`scripts/job_spark_piloto.py`](../scripts/job_spark_piloto.py).
**Esquema:** `1.0`
**Ubicación de entrega:** `tablero/data/v1/`

---

## 1. Convenciones y principios metodológicos

1. **Separación estricta de fuentes:**
   - **ResStock:** 10 modelos físicos de simulación energética residencial (AMY 2018; 5 en Colorado, 5 en Nueva York). Son perfiles individuales exploratorios, no lecturas de medidores de hogares reales ni una muestra representativa estatal o nacional.
   - **EIA-861M:** Ventas residenciales agregadas reportadas oficialmente por empresas de servicios públicos (utilities) para 51 jurisdicciones (50 estados + DC).
   - **Open-Meteo (ERA5-Land):** Reanálisis meteorológico horario en 2 celdas de Colorado (Denver y Grand Junction) del 1 al 7 de enero de 2018. Desacoplado del consumo, sin uniones espaciales ni temporales artificiales.
2. **Tratamiento temporal y zonas horarias:**
   - Los timestamps de origen de ResStock (`timestamp_fin_local`) representan la marca de **fin de intervalo de 15 minutos en Eastern Standard Time (EST) fijo (UTC−5)**, sin horario de verano.
   - Para el agregado mensual `gold_resstock_monthly`, el periodo mensual se asigna al inicio del intervalo restando 15 minutos (`timestamp_fin_local - 15m`).
   - Para el patrón horario `gold_resstock_pattern`, el inicio de intervalo se convierte **explícitamente a UTC (+5 horas)** y luego a la **zona IANA del estado**:
     - Colorado (`CO`): `America/Denver` (Mountain Time).
     - Nueva York (`NY`): `America/New_York` (Eastern Time).
   - Se preserva el desplazamiento UTC en minutos (`utc_offset_minutes`) para distinguir horas repetidas durante la transición de horario de verano (DST fall-back).
   - En Colorado, el año meteorológico 2018 en EST fijo abarca desde `2017-12-31 22:00` hasta `2018-12-31 21:45` en hora local `America/Denver`. Por tanto, los periodos `2017-12` (2 horas) y `2018-12` (incompleto al final del año) se marcan explícitamente como `is_partial_period = true`.
3. **Bloqueo exacto de la comparación Colorado/EIA (87.16%):**
   - El archivo crudo del agregado estatal ResStock de Colorado 2018 (`timeseries_aggregates`) **no está presente en `origin/main`** (ausente del archivo de entrega y del repositorio).
   - La cifra de 87.16% recibida en `demo_colorado_2018_verificacion.csv` compara poblaciones incompatibles (unifamiliar aislada modelada vs totalidad del sector residencial EIA).
   - Siguiendo la regla de oro del proyecto y las directrices de gobernanza, **no se inventan datos sustitutos**. La métrica queda formalmente catalogada en el manifiesto como `not_reproduced` con el bloqueo documentado.
4. **Alcance acotado a 10 perfiles piloto:**
   - El piloto consta estrictamente de 10 perfiles físicos descargados y verificados. Los 10,000 registros de `resstock_seleccion_propuesta.csv` son candidatos de estratificación, no perfiles disponibles. No se afirma cobertura nacional completa.

---

## 2. Inventario de artefactos en `tablero/data/v1/`

| Archivo | Grano | Filas | Bytes | SHA-256 | Clave primaria |
|---|---|---:|---:|---|---|
| [`gold_eia_monthly.json`](../tablero/data/v1/gold_eia_monthly.json) | Estado × Mes × Estado dato | 5,304 | 601,763 | `af48f3b56264759b5f261c088125e3545c40e012015b228ed7307b9fc01da825` | `(period, state_code)` |
| [`gold_resstock_monthly.json`](../tablero/data/v1/gold_resstock_monthly.json) | Perfil × Mes fuente | 120 | 20,187 | `9ad49b84ca04544d298316f6ab680afc6af2938ae89d26538398b735e94d5a10` | `(bldg_id, source_period)` |
| [`gold_resstock_pattern.json`](../tablero/data/v1/gold_resstock_pattern.json) | Perfil × Periodo local × Día × Hora local × Offset | 6,730 | 2,965,848 | `b020c7030e0de6b8289f134c138cb812777980387bc3a45ca29bc8e43e08def1` | `(bldg_id, period_local, day_type, hour_local, utc_offset_minutes)` |
| [`gold_resstock_profile_summary.json`](../tablero/data/v1/gold_resstock_profile_summary.json) | Perfil piloto (anual) | 10 | 3,042 | `c06c40b4f2e34e35cc0f1fc9c7d2eff8f4bd6e803e9755988ebbf485d41bca12` | `(bldg_id)` |
| [`gold_climate.json`](../tablero/data/v1/gold_climate.json) | Punto × Hora UTC | 336 | 99,993 | `ab57a0bd00ad539ec8bb036b31de78d92d5e1fc56a2a3510deef90b606f02556` | `(point_id, timestamp_utc)` |
| [`manifest.json`](../tablero/data/v1/manifest.json) | Manifiesto de metadatos v1.0 | 1 | 5,822 | `bdf50cfc00bc8777918a513511eb9f0ee4c7b848a60965e6488d0705a66699a7` | — |

---

## 3. Especificación detallada de esquemas

### 3.1 `gold_eia_monthly.json`
- **Fuente:** `datos/eia_residencial_mensual.csv` (SHA-256 `dff80ba196...`)
- **Cobertura:** 2018-01 a 2026-08 (51 jurisdicciones: 50 estados + DC).
- **Columnas:**
  - `period` (`string`): Formato `YYYY-MM`.
  - `state_code` (`string`): Código postal de 2 letras.
  - `data_status` (`string`): `"Final"` (2018-01 a 2025-12) o `"Preliminary"` (2026-01 a 2026-08).
  - `sales_mwh` (`number`): Ventas residenciales en MWh (redondeado a 2 decimales).

### 3.2 `gold_resstock_monthly.json`
- **Fuente:** `datos/resstock_perfiles_piloto.parquet` + `datos/resstock_seleccion_propuesta.csv`.
- **Cobertura:** 10 edificios × 12 meses (2018-01 a 2018-12 en calendario fuente EST).
- **Columnas:**
  - `bldg_id` (`integer`): Identificador del modelo físico ResStock.
  - `source_period` (`string`): Formato `YYYY-MM` (asignado por inicio del intervalo EST).
  - `kwh_month` (`number`): Consumo mensual modelado en kWh (redondeado a 4 decimales).
  - `state_code` (`string`): `"CO"` o `"NY"`.
  - `housing_type` (`string`): Tipo de vivienda RECS.

### 3.3 `gold_resstock_pattern.json`
- **Fuente:** `datos/resstock_perfiles_piloto.parquet` (350,400 intervalos) con conversión horaria local.
- **Cobertura:** 6,730 celdas (3,370 para CO, 3,360 para NY).
- **Columnas:**
  - `bldg_id` (`integer`): ID de modelo.
  - `period_local` (`string`): Periodo civil local `YYYY-MM` (incluye `2017-12` a `2018-12` para CO).
  - `day_type` (`string`): `"weekday"` (lunes–viernes) o `"weekend"` (sábado–domingo).
  - `hour_local` (`integer`): Hora local `0`–`23`.
  - `utc_offset_minutes` (`integer`): Desplazamiento horario respecto a UTC en minutos (`-420` para MST, `-360` para MDT, `-300` para EST, `-240` para EDT).
  - `is_partial_period` (`boolean`): `true` para `2017-12` y `2018-12` en CO; `false` en meses completos.
  - `median_kwh` (`number`): Mediana horaria de consumo en kWh.
  - `mean_kwh` (`number`): Media horaria en kWh.
  - `p10_kwh` (`number`): Percentil 10 en kWh.
  - `p90_kwh` (`number`): Percentil 90 en kWh.
  - `n_obs` (`integer`): Cantidad de observaciones horarias agrupadas en la celda.
  - `state_code` (`string`): `"CO"` o `"NY"`.
  - `housing_type` (`string`): Tipo de vivienda.
  - `time_zone` (`string`): `"America/Denver"` o `"America/New_York"`.

### 3.4 `gold_resstock_profile_summary.json`
- **Fuente:** 10 modelos físicos (8,760 horas por modelo).
- **Cobertura:** 10 filas.
- **Columnas:**
  - `bldg_id` (`integer`): ID de edificio.
  - `source_year` (`integer`): `2018`.
  - `annual_kwh` (`number`): Consumo anual total en kWh.
  - `mean_hour_kwh` (`number`): Consumo medio por hora en kWh.
  - `peak_hour_kwh` (`number`): Consumo en la hora pico anual en kWh.
  - `n_hours` (`integer`): `8760`.
  - `state_code` (`string`): `"CO"` o `"NY"`.
  - `housing_type` (`string`): Tipo de vivienda RECS.
  - `profile_weight` (`number`): Factor de ponderación original (`253.903673`).

### 3.5 `gold_climate.json`
- **Fuente:** `datos/clima_open_meteo_muestra.csv` (SHA-256 `c73e7c14b7...`).
- **Cobertura:** 336 registros horarios (168 h por punto, 2018-01-01 a 2018-01-07).
- **Columnas:**
  - `point_id` (`string`): `"denver_co"` o `"grand_junction_co"`.
  - `state_code` (`string`): `"CO"`.
  - `timestamp_utc` (`string`): Timestamp ISO 8601 UTC.
  - `temperature_c` (`number`): Temperatura a 2 metros en °C.
  - `model` (`string`): `"ERA5-Land"`.
  - `requested_latitude`, `requested_longitude` (`number`): Coordenadas solicitadas.
  - `cell_latitude`, `cell_longitude` (`number`): Coordenadas reales de la celda de reanálisis.

### 3.6 `manifest.json`
Declara:
- `manifest_version`: `"1.0"`, `schema_version`: `"1.0"`.
- `generated_at_utc`: Marca temporal de generación.
- `generator_script`: `"scripts/generar_datos_tablero.py"`.
- `data_status`: `"VALID_WITH_WARNINGS"`.
- `coverage_summary`: Coberturas declaradas de EIA, ResStock y Clima.
- `methodology_separation`: Reglas de separación metodológica y bloqueo documentado de la razón 87.16%.
- `source_inventory`: Hashes SHA-256, tamaños, licencias y URLs oficiales de las fuentes de entrada.
- `qc_rules`: 21 reglas evaluadas, 21 aprobadas, 0 fallidas, 3 advertencias metodológicas formales.
- `tables`: Registro de cada tabla con nombre de archivo, filas, bytes, SHA-256 y claves primarias.

---

## 4. Comandos de ejecución y validación

### Generación directa y liviana (recomendada):
```bash
python3 scripts/generar_datos_tablero.py --input datos --output tablero/data/v1
```

### Generación integrada con PySpark:
```bash
JAVA_HOME=/usr/lib/jvm/java-17-temurin-jdk \
PYSPARK_PYTHON=/tmp/bigdata-spark-venv/bin/python \
/tmp/bigdata-spark-venv/bin/python scripts/job_spark_piloto.py \
  --input datos \
  --output /tmp/salidas-spark-piloto \
  --export-tablero tablero/data/v1 \
  --master 'local[2]'
```

### Verificación automatizada con Node.js y validación frontend:
```bash
node -e '
const fs = require("fs");
const crypto = require("crypto");
const manifest = JSON.parse(fs.readFileSync("tablero/data/v1/manifest.json", "utf8"));
for (const [tname, t] of Object.entries(manifest.tables)) {
  const buf = fs.readFileSync("tablero/data/v1/" + t.file);
  const sha = crypto.createHash("sha256").update(buf).digest("hex");
  if (sha !== t.sha256 || buf.length !== t.bytes) throw new Error("Mismatch en " + tname);
  const rows = JSON.parse(buf.toString("utf8"));
  if (rows.length !== t.rows) throw new Error("Rows mismatch en " + tname);
  console.log(`OK: ${tname} (${rows.length} filas, sha=${sha.slice(0,12)}...)`);
}
'
```
