# Decisión de publicación de datos

Fecha de consulta de las fuentes oficiales: 17 de noviembre de 2026. Es una revisión técnica de lo que declaran las páginas citadas, no un dictamen legal. Lo que no está en esas páginas queda **pendiente** y, mientras tanto, **no se publica**.

Estados: **Confirmado** (lo dice la fuente oficial citada), **Pendiente** (no comprobado), **No verificado** (afirmación del catálogo sin respaldo hallado).

## Fuentes oficiales revisadas

| Clave | URL |
|---|---|
| R1 | https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/citation.txt |
| R2 | https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md (secciones «Citation and Data Attribution» y «Disclaimer») |
| R3 | https://data.openei.org/submissions/4520 («Content is available under Creative Commons Attribution 4.0 unless otherwise noted»; licencia https://creativecommons.org/licenses/by/4.0/) |
| E1 | https://www.eia.gov/about/copyrights_reuse.php |
| E2 | https://www.eia.gov/electricity/data/eia861m/ y https://www.eia.gov/electricity/gridmonitor/about (sin términos propios hallados; aplica E1 solo en lo que E1 declara) |
| O1 | https://open-meteo.com/en/terms (condiciones del servicio) |
| O2 | https://open-meteo.com/en/license (licencia de datos) |
| O3 | https://open-meteo.com/en/docs/historical-weather-api (cita ERA5-Land/C3S) |
| O4 | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview (ficha oficial ERA5-Land; licencia CC-BY) |

## Matriz

| Fuente | Artefacto | Decisión | Atribución requerida | Fundamento oficial | Pendientes |
|---|---|---|---|---|---|
| ResStock 2025 R1 | Archivos fuente OEDI | Uso académico de investigación y redistribución bajo CC BY 4.0 con atribución. En el repo se enlaza al release en vez de duplicar el paquete completo. | Cita del release, texto de atribución NREL/DOE, enlace a CC BY 4.0 y aviso de cambios. | `citation.txt` del release declara CC-BY-4.0; el README llama “Disclaimer” a la sección que indica uso de investigación y ausencia de garantía/responsabilidad. | Conservar el disclaimer en el material compartido; mantener el uso dentro del proyecto académico autorizado. |
| ResStock | Derivado/tabla (selección de 10,000 y cobertura) | Integrado en `datos/` bajo CC BY 4.0; los IDs son selección candidata, no perfiles descargados. | Cita del release, texto de atribución, licencia y cambios. | R1–R3; CC BY 4.0 permite reproducir, compartir y adaptar con atribución. | No afirmar que se obtuvieron 10,000 perfiles o que la selección representa una estimación nacional. |
| ResStock | Muestra (10 perfiles consolidados) | Integrada en `datos/` bajo CC BY 4.0 con nota de uso académico y disclaimer. | Cita del release, texto de atribución, licencia y cambios. | R1–R3; piloto leído y validado por perfil. | El ZIP no incluye los 10 archivos Parquet originales ni todo el crudo referenciado por el manifiesto. |
| EIA-861M / EIA-930 | Crudo (XLSX) | Sí, puede guardarse y redistribuirse según E1; se recomienda enlazar la descarga oficial. | «Source: U.S. Energy Information Administration» con fecha de publicación (E1) | E1: publicaciones del gobierno de EE. UU. en dominio público; se puede usar y distribuir datos y archivos del sitio. | E1 menciona materiales de terceros con copyright; confirmar que el XLSX no incluye ninguno. No se halló página específica del archivo. |
| EIA | Derivado/muestra (`eia_residencial_mensual.csv`, cobertura) | Sí, con atribución e indicación de transformación. | Igual | E1 | EIA-930 no fue extraído; no hay artefacto. |
| Open-Meteo (ERA5-Land) | Crudo JSON | Publicable bajo CC BY 4.0 con atribución; los JSON originales no venían en el ZIP y no se integran. | Open-Meteo, ERA5-Land, Copernicus C3S; enlace a licencia e indicar cambios (O1–O4). | O1 declara que los datos API son CC BY 4.0; los términos permiten uso gratuito no comercial y nombran contenido educativo como ejemplo. O3 identifica ERA5-Land; O4 declara CC-BY para el dataset oficial. | Obtener los crudos solo desde la fuente oficial y registrar la nueva fecha/hash. |
| Open-Meteo | Derivado/muestra (336 horas-punto, 2 puntos) | **Publicable con atribución**; CSV de muestra integrado en `datos/`. | Open-Meteo, ERA5-Land, Copernicus C3S; enlazar Open-Meteo/licencia e indicar cambios. | O1 acepta uso gratuito no comercial, incluye contenido educativo como ejemplo y licencia CC BY 4.0 para datos API; O3 y O4 documentan fuente y licencia ERA5-Land. | Mantener el uso académico sin fines comerciales y dentro de límites de llamadas. La muestra espacial no representa todo Colorado ni se unió a energía. |

## Atribución obligatoria o sugerida

- **ResStock:** R2 pide, al usar datos en productos o informes, la cita sugerida y el texto «Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).». R1 da la cita APA con DOI https://doi.org/10.25984/1876417; el DOI identifica el repositorio, no el release, por lo que se cita también la ruta del release. R2 pide citar además la guía técnica; usar la URL de R2 (https://natlabrockies.github.io/ResStock.github.io/assets/trd/ResStockTechnicalReferenceGuide_2025_1.pdf). El laboratorio fue renombrado National Laboratory of the Rockies (NLR) en diciembre 2025 (R1); R2 y R1 difieren en el nombre del publicador.
- **EIA:** acuse con fecha de publicación (E1).
- **Open-Meteo:** ver matriz.

## Interpretación para este proyecto académico

El archivo específico `citation.txt` del release indica CC BY 4.0. Esa licencia concede permiso mundial y sin regalías para reproducir y compartir el material y para crear/compartir adaptaciones, sujeto a atribución, enlace a la licencia e indicación de cambios. La frase «for research purposes only» está dentro del apartado `Disclaimer` del README y se acompaña de términos «as is», sin garantía y limitación de responsabilidad; el texto no declara expresamente que se prohíba compartir el dataset bajo su licencia. Para el proyecto académico autorizado por el profesor, el equipo interpreta que puede usar y compartir las muestras/derivados integrados manteniendo esas condiciones y el disclaimer. [CC BY 4.0, texto legal](https://creativecommons.org/licenses/by/4.0/legalcode.en) · [cita/licencia del release](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/citation.txt) · [README del release](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md).

Esta es la interpretación operativa del equipo para el trabajo escolar, no un dictamen legal ni una afirmación de respaldo de NREL/NLR. Si el uso cambia a un producto o actividad comercial, habrá que revaluar el alcance antes de ese cambio.

## Pendientes consolidados

1. Confirmar que el XLSX de EIA no contiene material de terceros; solo se utilizó la hoja/columnas declaradas.
2. Recuperar los archivos crudos ResStock referenciados en el manifiesto cuando la siguiente fase los necesite; no se requieren para abrir la demo actual.

## Integración al repositorio

Se integraron los CSV EIA y Open-Meteo y cuatro artefactos derivados ResStock con hash, atribución, licencia, cambios y alcance de investigación documentados en `datos/README.md` y `datos/manifiesto-integracion.json`. EIA se reprodujo byte a byte desde el XLSX oficial. Los archivos fuente originales que faltaban en el ZIP no se duplicaron.

## Revisión de gobernanza: release agregada privada por URL prefirmada (26 de noviembre de 2026)

Alcance: un único `index.html` autocontenido con 11 tablas Gold agregadas/derivadas (sin crudos), alojado en un bucket privado y compartido solo de forma temporal con una URL prefirmada para evaluación académica. Consulta de páginas oficiales el 26 de noviembre de 2026. No es dictamen legal; el bucket, la cuenta, las credenciales y las URLs prefirmadas no se registran aquí.

| Fuente | Página oficial consultada | Licencia/condición declarada | Atribución exigida | ¿Admisible en la release privada compartida por URL prefirmada? |
|---|---|---|---|---|
| ResStock 2025 R1 | `citation.txt` del release y https://data.openei.org/submissions/4520 | `citation.txt`: «License CC-BY-4.0». El README añade «Disclaimer» de uso de investigación y sin garantía. | Cita APA del release, texto NREL/DOE de la sección Atribución, enlace a CC BY 4.0 e indicación de cambios (agregados/derivados). | **Sí** (derivado agregado, no perfiles crudos). Condición: mantener el disclaimer y la atribución dentro del HTML; no sugerir respaldo de NREL/NLR. La lectura de «research purposes only» sigue siendo interpretación del equipo. |
| EIA-861M | https://www.eia.gov/about/copyrights_reuse.php | «U.S. government publications are in the public domain»; se pueden usar y distribuir datos y archivos. Excepción: material licenciado por terceros (p. ej. fotografías). | «Source: U.S. Energy Information Administration» con fecha de publicación. | **Sí** (series numéricas agregadas). Pendiente menor: confirmar que el XLSX no trae material de terceros. |
| Census PEP Vintage 2025 | https://www.census.gov/about/policies/citation.html y https://www.census.gov/data/developers/about/terms-of-service.html | La política de citación pide citar al Census Bureau como fuente de los datos originales y que las conclusiones son responsabilidad de quien analiza. No se encontró en las páginas consultadas una declaración de licencia/dominio público específica para el CSV `NST-EST2025-ALLDATA`. El aviso «uses the Census Bureau Data API but is not endorsed…» aplica a servicios que usan la API, no se usó la API. | Citar al Census Bureau (PEP Vintage 2025) como fuente original; no implicar respaldo. | **Pendiente (admisible provisional)**: es información estadística oficial de bajo riesgo en uso privado, pero la licencia de redistribución no quedó confirmada en texto oficial. Razón: sin cláusula explícita hallada. Mantener atribución y no ampliar la difusión pública hasta confirmarla. |
| Census TIGERweb (superficie 2020) | https://tigerweb.geo.census.gov/tigerwebmain/Files/tab20/tigerweb_tab20_state_2020_us.html y política de citación del Census | Igual que PEP: no se halló cláusula de licencia propia en las páginas consultadas. | Citar al Census Bureau (Geografía 2020, BVP20). | **Pendiente (admisible provisional)** por la misma razón. Solo se usó un valor de superficie por estado para calcular densidad. |
| NOAA/NWS `c_16ap26` (condados→zonas horarias) | https://www.weather.gov/disclaimer y https://www.weather.gov/gis/Counties | La información de NWS está en el dominio público y puede usarse sin costo para cualquier fin lícito siempre que no se: (1) reclame como propia, (2) implique respaldo/afiliación con NOAA/NWS, (3) modifique y se presente como material oficial. «As is», sin garantías. El nombre/logo de NWS está protegido. | Identificar NWS/NOAA como fuente; indicar que el mapeo a zonas horarias IANA es una transformación del equipo. No usar el logo. | **Sí**, si se declara que es derivado transformado y no producto oficial NWS. |
| Open-Meteo / ERA5-Land | https://open-meteo.com/en/terms y https://open-meteo.com/en/licence; ficha ERA5-Land del Copernicus CDS | Los términos: API gratuita solo **no comercial** (ejemplos admitidos: sitios sin publicidad/suscripción, investigación pública en instituciones públicas, contenido educativo) y aceptación de CC BY 4.0; límites 10 000 llamadas/día. La licencia exige crédito apropiado, enlace a la licencia e indicación de cambios. | Open-Meteo, ERA5-Land (Copernicus C3S/ECMWF), enlace a CC BY 4.0, indicar cambios (CSV normalizado, 2 puntos, 7 días). | **Sí, con límite**: 336 horas-punto agregadas en un tablero académico privado sin publicidad ni cobro. Si el uso se vuelve comercial o público con fines de lucro, requiere plan de pago. |

### Conclusión sobre la release privada

- **Admisible** subir/compartir el `index.html` agregado en bucket privado mediante URL prefirmada temporal: ninguna fuente prohíbe compartir derivados agregados con atribución y el acceso es restringido y revocable.
- **Condiciones**: HTML con la atribución de cada fuente, disclaimer de ResStock, aviso de transformación y de no respaldo oficial; uso académico no comercial; no incluir crudos ni la selección de 10 000 IDs; no registrar la URL prefirmada.
- **Pendiente (no bloquea el uso privado, sí la difusión pública)**: licencia/redistribución explícita de Census PEP y TIGERweb; verificación del XLSX de EIA; hora UTC exacta de descarga de las fuentes.
