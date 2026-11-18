# Tablero de consumo eléctrico residencial

Aplicación web estática, sin dependencias de frontend ni compilación. Sus seis vistas leen las tablas Gold descritas por `manifest.json` y validan esquema, filas, bytes y SHA-256 antes de usar los datos.

## Ejecutar el paquete disponible en el repositorio

```bash
python3 -m http.server 8000 -d tablero
# abrir http://localhost:8000/
```

## Datos integrados

El tablero consume EIA mensual, el piloto ResStock, clima horario independiente y cuatro tablas de analítica EIA para anomalías y backtest. Las salidas de anomalías son candidatos estadísticos; su evaluación usa cambios sintéticos. El pronóstico mostrado es un backtest de 2024–2025, no una predicción futura. Ver [`docs/analitica-anomalias-pronostico.md`](../docs/analitica-anomalias-pronostico.md).

El lote local más reciente usa 50 perfiles ResStock (1,752,000 intervalos). La aplicación muestra la cantidad realmente incluida en el manifiesto; 10,000 perfiles sigue siendo una meta, no un lote procesado. Los datos de ResStock y EIA tienen coberturas diferentes y no se suman ni se interpretan como la misma población. Clima permanece separado del consumo.

## Reproducir las tablas de analítica

Ejecutar desde la raíz del repositorio:

```bash
python3 scripts/analitica_anomalias_pronostico.py --salida /tmp/analitica-anomalias
python3 scripts/exportar_analitica_tablero.py \
  --base tablero/data/v1 \
  --analitica /tmp/analitica-anomalias \
  --salida /tmp/tablero-data-integrado
```

El exportador valida el manifiesto base y crea una carpeta nueva; no sobrescribe la salida existente. Para integrar otra salida Gold, apunta `--base` al directorio que contiene su `manifest.json`. El paquete integrado se sirve así:

```bash
python3 -m http.server 8000 -d tablero
# abrir http://localhost:8000/?data=/data/v1-integrada/
```

Coloca el paquete de datos en `tablero/data/v1-integrada/` antes de servirlo, o sirve una copia de trabajo que contenga esa ruta. No se versionan aquí las salidas ampliadas de 50 perfiles; revisa gobernanza y tamaño antes de publicarlas.

## Empaquetar un archivo HTML autónomo

Para mostrar el tablero desde un objeto privado de S3 con una URL prefirmada (sin depender de que CSS, módulos y JSON sean públicos), se puede generar un solo HTML autocontenido:

```bash
python3 scripts/empaquetar_tablero_autonomo.py \
  --web tablero \
  --datos tablero/data/v1 \
  --salida /tmp/consumo-residencial-autonomo.html
```

El empaquetador verifica hashes, bytes y filas de todas las tablas incluidas. El resultado conserva las seis vistas y filtros; todo queda dentro del HTML, por lo que es más pesado que la web modular. Una URL prefirmada es temporal y quien la posea puede leer ese objeto hasta que expire; no equivale a publicar el bucket ni a una dirección permanente. El acceso estable requiere un servicio de distribución autorizado, por ejemplo CloudFront con acceso privado a S3.

## Interpretación

- **Resumen y Patrones:** separan ventas oficiales EIA de perfiles residenciales modelados ResStock. La vista horaria presenta tiempo local IANA y deja identificar periodos parciales.
- **Clima:** muestra la serie consultada en UTC; no existe unión con consumo en esta versión.
- **Anomalías:** lista candidatos de variación interanual y mide sensibilidad con inyecciones sintéticas. No confirma eventos reales.
- **Estimaciones:** compara observado, baseline estacional y modelo log-lineal durante un holdout conocido.
- **Flujo/Calidad:** consulta cobertura, manifiesto y controles reportados por las fuentes.

Si falta una tabla o no coincide su hash, el tablero muestra el estado y no presenta cifras de esa tabla.
