# Tablero MVP — integración Gold

Tablero estático en HTML/CSS/JavaScript. Consume CSV o JSON exportado de Gold; el navegador no lee Parquet.

## Ejecutar
Desde la raíz del repositorio:

```bash
python -m http.server 8000
```
Abrir `http://localhost:8000/tablero/`.

## Carga de datos
El loader busca primero un manifiesto en `analitica/salidas/manifest.json`, `analitica/salidas/gold/manifest.json`, `analitica/salidas/tablero/manifest.json`, `data/manifest.json` o `datos/manifest.json`. Después prueba rutas candidatas centralizadas en `js/config.js`. Acepta CSV y JSON; JSON puede ser array o contener `rows`, `data`, `records`, `monthly`, `items` o `results`.

Si la estructura real de salidas es distinta, actualiza `CONFIG.candidates` o el manifiesto; no edites las vistas para cambiar rutas.

## Filtros
Los filtros se comparten en `app.js` y sus opciones se derivan de los datos cargados. Estado, año y calidad del dato se aplican donde existan. Tipo de vivienda solo aplica a ResStock; punto solo a clima; día tipo a patrones. Los filtros sin ámbito se deshabilitan y explican.

## Vistas
Resumen, ResStock, Patrones, Clima, Estimaciones y Anomalías. Los datos ausentes se presentan como estado de disponibilidad; no se inventan resultados. Las anomalías se etiquetan como sintéticas y el backtest se distingue del escenario futuro.

## Limitación de integración
Las rutas candidatas deben cotejarse con los archivos reales del repo y el manifiesto Gold de la rama integrada. Parquet no se carga directamente en navegador: se requiere exportación JSON/CSV.
