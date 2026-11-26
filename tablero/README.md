# Tablero de consumo eléctrico residencial

Aplicación web estática, sin dependencias de frontend ni compilación. Sus seis vistas leen las tablas Gold descritas por `manifest.json` y validan esquema, filas, bytes y SHA-256 antes de usar los datos.

## Ejecutar el paquete disponible en el repositorio

```bash
python3 -m http.server 8000 -d tablero
# abrir http://localhost:8000/
```

Por defecto, el tablero carga la versión de datos **v2** (`tablero/data/v2/`). Para inspeccionar la versión anterior **v1** o probar la compatibilidad hacia atrás:

```bash
# abrir http://localhost:8000/?data=data/v1/
```

Cuando se carga `data/v1/`, el tablero reconoce el esquema `1.0` de forma honesta, preserva intactas las seis vistas y muestra las tarjetas demográficas como pendientes de entrega en lugar de vaciar las vistas o fallar.

---

## Datos integrados (Publicación v2)

La publicación `tablero/data/v2/` consolida 11 tablas Gold verificadas criptográficamente según la especificación técnica en [`docs/contrato-dashboard-datos-v2.md`](../docs/contrato-dashboard-datos-v2.md) (preservando el contrato base v1 documentado en [`docs/contrato-dashboard-datos.md`](../docs/contrato-dashboard-datos.md)):
1. **EIA mensual (`gold_eia_monthly.json`):** Ventas residenciales oficiales para 51 jurisdicciones (2018-01 a 2026-08).
2. **Piloto ResStock (`gold_resstock_monthly.json`, `gold_resstock_pattern.json`, `gold_resstock_pattern_aggregate.json`, `gold_resstock_profile_summary.json`):** 10 perfiles modelados con agregación horaria en tiempo local IANA y distinción de meses parciales.
3. **Clima ERA5-Land (`gold_climate.json`):** 336 registros horarios desacoplados del consumo.
4. **Analítica EIA (`gold_anomaly_candidates.json`, `gold_anomaly_synthetic_eval.json`, `gold_forecast_metrics.json`, `gold_forecast_series.json`):** Detección de candidatos de variación interanual con evaluación sintética y backtest temporal 2024–2025.
5. **Demografía y ventas per cápita (`gold_demography_state_year.json`):** 306 filas cubriendo 51 jurisdicciones (50 estados + DC) durante 6 años completos (2020–2025) a grano `(state_fips, year)`.

### Principios metodológicos de la integración demográfica
- **Distinción de las cuatro dimensiones:**
  - **Dimensión 1 (Población):** Volumen absoluto de residentes (al 1 de julio, Census PEP Vintage 2025). *California lidera con ~39.4 millones de habitantes en 2025.*
  - **Dimensión 2 (Densidad poblacional):** Habitantes por milla cuadrada terrestre. *New Jersey lidera entre los 50 estados (~1,298 hab./mi² en 2025).*
  - **Dimensión 3 (Ventas totales):** Volumen anual agregado de electricidad residencial (EIA-861M Final). *Texas lidera con ~170.5 millones de MWh en 2025.*
  - **Dimensión 4 (Ventas por habitante):** Intensidad per cápita calculada (`residential_kwh_per_capita = (sales_mwh * 1000) / population`). *Louisiana lidera con ~6,864 kWh/hab en 2025, mientras que estados como Hawaii (~1,935 kWh/hab) y California (~2,163 kWh/hab) presentan intensidades notablemente menores.*
- **Tratamiento explícito del Distrito de Columbia (DC):** DC es un distrito federal exclusivamente urbano (68.35 mi² de tierra, ~11,348 hab./mi²). No se mezcla silenciosamente con los 50 estados; el gráfico de dispersión ofrece un control para incluirlo o aislar la escala interestatal, y la tabla comparativa lo destaca con una insignia visible.
- **Sin afirmaciones de causalidad:** El análisis es estrictamente descriptivo. La correlación entre densidad o población y ventas por habitante no implica causa-efecto; factores como el clima (grados-día), uso de gas natural vs. bombas de calor/electricidad para calefacción y tarifas explican gran parte de la varianza.
- **Separación de ResStock:** Las cifras agregadas macroestadísticas (Census + EIA) no se cruzan ni se confunden con los modelos físicos de 10 viviendas de ResStock. Se prohíbe presentar la cifra de 87.16% como precisión del modelo.

---

## Reproducción de datos `tablero/data/v2/`

Para reconstruir el paquete `tablero/data/v2/` desde los insumos canónicos:

```bash
python3 scripts/generar_datos_tablero.py \
  --input datos \
  --demografia-input datos/demografia_estatal \
  --v1-base tablero/data/v1 \
  --output tablero/data/v2
```

El script valida los hashes de entrada (`energy_demography_state_year_v1.csv` y su `manifest.json`), genera los 306 registros Gold de demografía, evalúa 27 reglas de control de calidad (6 específicas de demografía), transfiere las tablas analíticas desde `v1-base` y emite el `manifest.json` v2 con SHA-256 de todas las tablas.

---

## Empaquetar un archivo HTML autónomo

Para distribuir el tablero como un único archivo autocontenido para S3 o visualización local (por defecto empaqueta la publicación actual `tablero/data/v2`):

```bash
python3 scripts/empaquetar_tablero_autonomo.py \
  --web tablero \
  --salida /tmp/consumo-residencial-autonomo.html
```

Para empaquetar explícitamente la versión anterior v1 como compatibilidad:

```bash
python3 scripts/empaquetar_tablero_autonomo.py \
  --web tablero \
  --datos tablero/data/v1 \
  --salida /tmp/consumo-residencial-autonomo-v1.html
```

---

## Verificación de integridad

Validar la integridad de los artefactos generados frente a su manifiesto:

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
console.log("Todas las tablas v2 coinciden exactamente con manifest.json.");
'
```
