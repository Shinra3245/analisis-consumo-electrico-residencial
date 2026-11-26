# Contrato de datos para el tablero web (v2)

**Estado:** Implementado y verificado en `tablero/data/v2/` (con compatibilidad garantizada hacia atrás con `tablero/data/v1/`).
**Script generador:** [`scripts/generar_datos_tablero.py`](../scripts/generar_datos_tablero.py) y flag `--export-tablero` en [`scripts/job_spark_piloto.py`](../scripts/job_spark_piloto.py).
**Esquema:** `1.0` (estándar contractual común consumido por el tablero web; la versión `v2` corresponde a la publicación del paquete de datos).
**Ubicación de entrega:** `tablero/data/v2/` (paquete completo de 11 tablas Gold + `manifest.json`).

---

## 1. Convenciones y principios metodológicos

1. **Separación estricta de fuentes:**
   - **ResStock:** 10 modelos físicos de simulación energética residencial (AMY 2018; 5 en Colorado, 5 en Nueva York). Son perfiles individuales exploratorios, no lecturas de medidores de hogares reales ni una muestra representativa estatal o nacional.
   - **EIA-861M:** Ventas residenciales agregadas reportadas oficialmente por empresas de servicios públicos (utilities) para 51 jurisdicciones (50 estados + DC).
   - **Open-Meteo (ERA5-Land):** Reanálisis meteorológico horario en 2 celdas de Colorado (Denver y Grand Junction) del 1 al 7 de enero de 2018. Desacoplado del consumo, sin uniones espaciales ni temporales artificiales.
   - **Demografía Estatal (US Census Bureau PEP Vintage 2025 + EIA-861M):** Tabla macroestadística anual a nivel jurisdicción para 51 entidades (50 estados + Distrito de Columbia) durante los años 2020 a 2025 (306 registros exactos).
2. **Distinción de las cuatro dimensiones de análisis macro:**
   - **Dimensión 1 (Población):** Volumen absoluto de residentes al 1 de julio (`population_estimate`, personas). *Líder 2025: California (CA, ~39.4 millones).*
   - **Dimensión 2 (Densidad territorial):** Residentes por milla cuadrada de superficie terrestre (`population_density_per_sq_mi`, hab./mi²). *Líder estatal 2025: New Jersey (NJ, ~1,298 hab./mi²).*
   - **Dimensión 3 (Ventas totales de electricidad):** Volumen anual agregado de electricidad residencial (`residential_sales_mwh`, MWh). *Líder 2025: Texas (TX, ~170.5 millones de MWh).*
   - **Dimensión 4 (Ventas residenciales por habitante):** Intensidad de consumo per cápita (`residential_kwh_per_capita`, kWh/hab/año). *Líder 2025: Louisiana (LA, ~6,864 kWh/hab).*
3. **Tratamiento no sesgado del Distrito de Columbia (DC):**
   - El Distrito de Columbia es una jurisdicción federal 100% urbana (superficie terrestre de 68.35 mi²), cuya densidad (~11,348 hab./mi²) es un orden de magnitud superior a la del estado más denso (NJ, ~1,298 hab./mi²).
   - **Regla estricta:** No mezclar silenciosamente a DC con los 50 estados en rankings o escalas sin advertencia explícita. El tablero provee una insignia visual clara (`Distrito federal urbano`), calcula el ranking de densidad entre estados excluyendo a DC de dicha posición estatal, y provee un control interactivo en los gráficos de dispersión para aislar o incluir a DC.
4. **Declaración formal de no causalidad:**
   - Esta comparación macroestadística es estrictamente descriptiva. Una correlación entre densidad poblacional y ventas por habitante **no implica causalidad**. El consumo residencial está mediado por el clima regional (grados-día de calefacción y refrigeración), la cuota de penetración del gas natural frente a calefacción eléctrica/resistiva, tarifas y regulaciones de eficiencia.
5. **Bloqueo exacto de la comparación Colorado/EIA (87.16%):**
   - Se prohíbe presentar la cifra de 87.16% como una métrica de precisión o exactitud. Corresponde a una comparación no representativa entre poblaciones dispares.
6. **Compatibilidad hacia atrás sin pérdida de vistas:**
   - La publicación v2 incluye las 11 tablas requeridas por las seis vistas del tablero (`resumen`, `patrones`, `clima`, `anomalias`, `estimaciones`, `calidad`). Al cambiar el origen de datos mediante `?data=data/v1/`, el tablero reconoce el manifiesto 1.0 y muestra estados pendientes para la sección demográfica sin vaciar las vistas preexistentes.

---

## 2. Inventario de artefactos en `tablero/data/v2/`

| Archivo | Grano / Clave primaria | Filas | Bytes | SHA-256 | Fuente |
|---|---|---:|---:|---|---|
| [`gold_eia_monthly.json`](../tablero/data/v2/gold_eia_monthly.json) | `(period, state_code)` | 5,304 | 601,763 | `af48f3b56264759b5f261c088125e3545c40e012015b228ed7307b9fc01da825` | EIA-861M |
| [`gold_resstock_monthly.json`](../tablero/data/v2/gold_resstock_monthly.json) | `(bldg_id, source_period)` | 120 | 20,187 | `9ad49b84ca04544d298316f6ab680afc6af2938ae89d26538398b735e94d5a10` | NREL ResStock |
| [`gold_resstock_pattern.json`](../tablero/data/v2/gold_resstock_pattern.json) | `(bldg_id, period_local, day_type, hour_local, utc_offset_minutes)` | 6,730 | 3,255,238 | `81de45ee3a4f6b56b8365b9619e9baaa2fce76941c20468facbd75aae98af52c` | NREL ResStock |
| [`gold_resstock_pattern_aggregate.json`](../tablero/data/v2/gold_resstock_pattern_aggregate.json) | `(state_code, housing_type, time_zone, period_local, day_type, hour_local, utc_offset_minutes)` | 6,730 | 3,714,866 | `14e4cfcfb591bf69f851a10b1af53e756a728da21c3bf259c9a51bf5a0b32f0e` | NREL ResStock |
| [`gold_resstock_profile_summary.json`](../tablero/data/v2/gold_resstock_profile_summary.json) | `(bldg_id)` | 10 | 3,042 | `c06c40b4f2e34e35cc0f1fc9c7d2eff8f4bd6e803e9755988ebbf485d41bca12` | NREL ResStock |
| [`gold_climate.json`](../tablero/data/v2/gold_climate.json) | `(point_id, timestamp_utc)` | 336 | 99,993 | `ab57a0bd00ad539ec8bb036b31de78d92d5e1fc56a2a3510deef90b606f02556` | Open-Meteo ERA5-Land |
| [`gold_demography_state_year.json`](../tablero/data/v2/gold_demography_state_year.json) | `(state_fips, year)` | 306 | 120,094 | `b6be401bd6fe875c3c8033addf5abdf590a028f437a8373e4985fb18c45e4fbe` | Census PEP + EIA-861M |
| [`gold_anomaly_candidates.json`](../tablero/data/v2/gold_anomaly_candidates.json) | `(period, state_code)` | 43 | 8,035 | `a04a7e0abafefecc454350a0c1ac0ef9ae73458e312740fa838ee1e2cf4a5f5c` | Analítica EIA |
| [`gold_anomaly_synthetic_eval.json`](../tablero/data/v2/gold_anomaly_synthetic_eval.json) | `(injection_pct)` | 4 | 833 | `b32621ac8929d32effe0f6e3bc1f8e04c557a93bf7c440a8c786c11fea202b47` | Analítica EIA |
| [`gold_forecast_metrics.json`](../tablero/data/v2/gold_forecast_metrics.json) | `(state_code)` | 51 | 14,222 | `cdfa236e53797a3946b6827ef00b9cff01f739cb73bcac36d1436711441f05f1` | Analítica EIA |
| [`gold_forecast_series.json`](../tablero/data/v2/gold_forecast_series.json) | `(period, state_code)` | 1,224 | 159,811 | `b3d87379f42ddfe34a14f6511de58f8943907684327ff861c2b3f9526acd5319` | Analítica EIA |
| [`manifest.json`](../tablero/data/v2/manifest.json) | Manifiesto de metadatos (publicación v2) | 1 | 18,498 | `c76f7a1821f7bb0f9765b6d99f1e2f3f7742edddc89669d403ebb76eadc9fd64` | Pipeline Gold |

---

## 3. Especificación técnica de `gold_demography_state_year.json`

### 3.1 Procedencia e insumo canónico
- **Archivo de origen:** `datos/demografia_estatal/energy_demography_state_year_v1.csv`
- **Hash de origen SHA-256:** `5333c61ecd66e07100262d003dc1e5826e22ee3ead7698978fc4189ee15c0106` (29,789 bytes, 306 filas de datos).
- **Manifiesto de origen:** `datos/demografia_estatal/manifest.json`.

### 3.2 Esquema de columnas (11 campos reales)
| Campo | Tipo | Ejemplo | Descripción y Unidad |
|---|---|---|---|
| `state_fips` | `string` | `"06"` | Código FIPS estatal a 2 dígitos con cero a la izquierda. |
| `state_code` | `string` | `"CA"` | Código postal de 2 letras de la jurisdicción. |
| `year` | `integer` | `2025` | Año calendario de observación (`2020` a `2025`). |
| `population_estimate` | `integer` | `39355309` | Población residente estimada al 1 de julio (personas). |
| `land_area_sq_mi_2020` | `number` | `155779.22` | Superficie de tierra firme en millas cuadradas (Censo 2020). |
| `population_density_per_sq_mi` | `number` | `252.63` | Densidad poblacional terrestre (`population_estimate / land_area_sq_mi_2020`). |
| `residential_sales_mwh` | `number` | `85117947.53` | Ventas anuales de electricidad residencial en MWh (EIA-861M). |
| `residential_kwh_per_capita` | `number` | `2162.70` | Ventas por habitante en kWh/hab/año (`(residential_sales_mwh * 1000) / population_estimate`). |
| `eia_data_status` | `string` | `"Final"` | Estatus de publicación de datos EIA (`Final` para 2020–2025). |
| `census_vintage` | `integer` | `2025` | Vintage metodológico de estimaciones del Censo (`2025`). |
| `source_version` | `string` | `"v1-bbc916d22b5c4260"` | Identificador o etiqueta de release del dataset canónico de Brian (#13/#14). |

### 3.3 Reglas de Control de Calidad (QC) demográficas expuestas en `manifest.json`
El manifiesto v2 expone el arreglo `rules` con los 27 resultados detallados (21 base + 6 de demografía). Las 6 reglas demográficas registradas corresponden exactamente a:
- `conteos_totales_esperados`: Condición `filas == 306 (51 jurisdicciones x 6 años 2020-2025)` (`cumplida: true`, `fallos: 0`).
- `unicidad_clave_primaria`: Condición `tupla (state_fips, year) sin duplicados` (`cumplida: true`, `fallos: 0`).
- `cobertura_geografica_anual_completa`: Condición `51 jurisdicciones (50 estados + DC) presentes en cada año 2020-2025` (`cumplida: true`, `fallos: 0`).
- `positividad_de_indicadores`: Condición `population, land_area, sales_mwh, density y kwh_per_capita estrictamente positivos` (`cumplida: true`, `fallos: 0`).
- `consistencia_fuentes_y_vintage`: Condición `eia_data_status == 'Final' y census_vintage == 2025 en todas las filas` (`cumplida: true`, `fallos: 0`).
- `distincion_territorial_dc`: Condición `DC identificado con FIPS 11, años 2020-2025 y densidad urbana atípica (>10,000 hab/mi²)` (`cumplida: true`, `fallos: 0`).

---

## 4. Comandos de ejecución y validación

### 4.1 Generación del paquete v2 completo
```bash
python3 scripts/generar_datos_tablero.py \
  --input datos \
  --demografia-input datos/demografia_estatal \
  --v1-base tablero/data/v1 \
  --output tablero/data/v2
```

### 4.2 Verificación estricta de hash y filas v2 con Node.js
```bash
node -e '
const fs = require("fs");
const crypto = require("crypto");
const manifest = JSON.parse(fs.readFileSync("tablero/data/v2/manifest.json", "utf8"));
for (const [tname, t] of Object.entries(manifest.tables)) {
  const buf = fs.readFileSync("tablero/data/v2/" + t.file);
  const sha = crypto.createHash("sha256").update(buf).digest("hex");
  if (sha !== t.sha256 || buf.length !== t.bytes) throw new Error("Mismatch en " + tname);
  const rows = JSON.parse(buf.toString("utf8"));
  if (rows.length !== t.rows) throw new Error("Rows mismatch en " + tname);
  console.log(`OK: ${tname} (${rows.length} filas, sha=${sha.slice(0,12)}...)`);
}
console.log("Validación v2 completada con éxito.");
'
```

### 4.3 Verificación de compatibilidad v1 (sin regresiones)
```bash
node -e '
const fs = require("fs");
const crypto = require("crypto");
const manifest = JSON.parse(fs.readFileSync("tablero/data/v1/manifest.json", "utf8"));
for (const [tname, t] of Object.entries(manifest.tables)) {
  const buf = fs.readFileSync("tablero/data/v1/" + t.file);
  const sha = crypto.createHash("sha256").update(buf).digest("hex");
  if (sha !== t.sha256 || buf.length !== t.bytes) throw new Error("Mismatch en v1/" + tname);
  const rows = JSON.parse(buf.toString("utf8"));
  if (rows.length !== t.rows) throw new Error("Rows mismatch en v1/" + tname);
}
console.log("Validación v1 confirmada: intacta y sin modificaciones.");
'
```
