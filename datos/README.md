# Datos de fuentes públicas integrados

Este directorio contiene dos tablas derivadas del archivo oficial **EIA-861M, Sales and Revenue**, hoja `Monthly-States`, filtradas al sector residencial (`RES`), y una muestra climática derivada de Open-Meteo Historical Weather API. Las fuentes fueron consultadas el 17 de noviembre de 2026; los datos EIA de 2026 incluidos en ese corte son preliminares.

| Archivo | Contenido | Filas de datos | Unidad |
|---|---|---:|---|
| `eia_residencial_mensual.csv` | Ventas por periodo mensual, estado y sector | 5,304 | MWh |
| `cobertura_eia.csv` | Meses disponibles, finales, preliminares y faltantes por año, estado y sector; suma anual cuando hay datos | 459 | MWh en `ventas_mwh` |
| `clima_open_meteo_muestra.csv` | Temperatura horaria a 2 m para Denver y Grand Junction, Colorado, 1–7 enero de 2018 en UTC | 336 | °C |
| `resstock_perfiles_piloto.parquet` | 10 perfiles seleccionados de Colorado y Nueva York; 35,040 intervalos por ID | 350,400 | kWh por intervalo de 15 min |
| `resstock_seleccion_propuesta.csv` | IDs y URL de perfiles candidatos; no son 10,000 perfiles descargados | 10,000 | Metadatos |
| `resstock_cobertura_estratos.csv` | Candidatos y cuotas por estado/tipo de vivienda | 254 | Conteos |
| `demo_colorado_2018_verificacion.csv` | Comparación mensual de agregado ResStock y ventas EIA de Colorado | 12 | MWh y relación descriptiva (%) |

**Fuentes:** [U.S. EIA-861M, descarga oficial](https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx) y [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). Consultar la [política de reutilización de EIA](https://www.eia.gov/about/copyrights_reuse.php), la [licencia de datos Open-Meteo](https://open-meteo.com/en/license), sus [términos de uso](https://open-meteo.com/en/terms) y la [ficha ERA5-Land de Copernicus CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview). Atribución: U.S. Energy Information Administration (EIA), EIA-861M, corte consultado el 17 de noviembre de 2026; datos meteorológicos por Open-Meteo, modelo ERA5-Land, con información del Copernicus Climate Change Service (C3S). La serie mensual EIA se filtró/normalizó desde `Monthly-States`; la tabla climática convirtió la respuesta horaria a CSV, conservó dos puntos de Colorado, el periodo 1–7 de enero y las coordenadas solicitadas y devueltas. Se indicarán esos cambios junto a los datos.

### ResStock 2025 Release 1 (AMY 2018)

Fuente: [registro OEDI 4520](https://data.openei.org/submissions/4520), [cita/licencia del release](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/citation.txt) y [README del release](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md). `citation.txt` identifica la licencia **CC BY 4.0**. El README pide citar el dataset y la guía técnica e incluir: «Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).» La frase «for research purposes only» aparece dentro de una sección titulada `Disclaimer`, junto con la provisión “as is” y la limitación de garantías/responsabilidad. Este proyecto utiliza y comparte la muestra como investigación académica autorizada; se conservan la cita, licencia, enlace al release y la indicación de que los datos se proporcionan para investigación y sin garantía.

El Parquet consolidado contiene solo `bldg_id`, `timestamp_fin_local` y `electricidad_kwh`; se cambiaron nombres de columnas para su presentación consolidada. Los timestamps del release se publican en EST y representan el fin del intervalo. La selección de 10,000 filas contiene IDs y URL candidatos: no indica que los perfiles se hayan descargado. El ZIP recibido no contenía los diez archivos fuente individuales ni todos los crudos enumerados en su manifiesto. Véase el [contrato de datos v1](../docs/contrato-datos-v1.md) para tipos, llaves y calidad observada.

Bytes, filas y SHA-256 de los siete artefactos integrados están registrados en [`manifiesto-integracion.json`](manifiesto-integracion.json). Se cotejaron contra el manifiesto de Brian y coinciden para los archivos presentes en su ZIP. El XLSX EIA crudo y los JSON Open-Meteo no estaban incluidos; el XLSX se volvió a descargar para reproducir los CSV EIA. Los crudos ResStock indicados por URL tampoco venían en el ZIP.

La serie contiene 2018–2025 y enero–agosto de 2026 según el corte recibido. Antes de análisis temporales, conservar `estado_dato` para separar meses finales y preliminares; no tratar los meses de 2026 como definitivos.

La muestra climática se incluye como tabla derivada con atribución CC BY 4.0; es una consulta educativa no comercial al servicio gratuito. Contiene dos celdas de reanálisis consultadas para Denver y Grand Junction, no estaciones meteorológicas ni una cobertura representativa de todo Colorado. No se une todavía a los perfiles eléctricos. Su SHA-256 es `c73e7c14b7c1d6c5b72ef158b35b061fb2c6da213798c99993aee398503f10a6`.

## Reproducir

La EIA mantiene el archivo histórico y puede actualizarlo. Para reproducir exactamente este corte, descarga el XLSX indicado por **Historical Data → Sales and revenue → 2010-current (xlsx)** en la [página Form EIA-861M](https://www.eia.gov/electricity/data/eia861m/). La respuesta recibida en este corte fue de 2,280,162 bytes, `Last-Modified: Fri, 23 Oct 2026 17:10:42 GMT`, SHA-256 `c7963ad7c9bd2020cc7472f100a9c5330a4dff97a62be95407137a14b9c4044e`.

Con Python 3 y la dependencia fijada:

```bash
python -m pip install -r scripts/requirements-eia.txt
python scripts/preparar_eia.py --input /ruta/a/sales_revenue.xlsx --output /tmp/eia-salida
cmp datos/eia_residencial_mensual.csv /tmp/eia-salida/eia_residencial_mensual.csv
cmp datos/cobertura_eia.csv /tmp/eia-salida/cobertura_eia.csv
```

La comparación exacta dio 5,304 registros mensuales y 459 filas de cobertura; ambos CSV reproducidos fueron idénticos byte a byte a los integrados. Para regenerar dentro de `datos/`, agrega `--overwrite` al comando solo si deseas reemplazar conscientemente los archivos existentes. Si EIA actualiza la hoja, el contenido y los hashes pueden cambiar; conserva la fecha de descarga y el hash de la nueva fuente antes de actualizar las salidas.
