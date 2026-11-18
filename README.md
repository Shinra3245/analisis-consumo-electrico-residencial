# Análisis, predicción y detección de anomalías del consumo eléctrico residencial

Proyecto final de la asignatura **Big Data** del Instituto Tecnológico de Celaya. La propuesta versión 2 fue revisada y aprobada por el profesor para continuar con su desarrollo.

## Propósito

Desarrollar una plataforma de análisis para explorar el consumo eléctrico residencial en Estados Unidos, comparar patrones entre estados y grupos de viviendas, detectar comportamientos inusuales y estimar la evolución del consumo con sus supuestos claramente documentados.

## Alcance inicial

- Integrar perfiles residenciales modelados con estadísticas eléctricas oficiales y variables meteorológicas.
- Analizar patrones por hora, día, mes, año, temporada, región y características de vivienda.
- Detectar anomalías en los perfiles o grupos y distinguir cambios de consumo de periodos sin datos.
- Explorar estimaciones diarias, mensuales y anuales; reportar límites cuando los datos históricos no permitan validar una predicción.
- Demostrar procesamiento continuo mediante reproducción progresiva de datos históricos, conservando su fecha original e identificándolo como simulación.
- Presentar resultados en un tablero con secciones para resumen, patrones, clima, estimaciones, anomalías y seguimiento de registros.

## Fuentes previstas

| Fuente | Uso previsto | Consideración |
|---|---|---|
| ResStock 2025.1 | Perfiles residenciales, características de viviendas y resúmenes estatales | Son perfiles modelados, no mediciones directas de hogares. |
| U.S. Energy Information Administration (EIA) | Estadísticas residenciales por estado; demanda horaria del sistema como contexto opcional | Las estadísticas residenciales y la demanda multisectorial de red son productos distintos. EIA-930 se pospone hasta justificar su uso y normalizar el tiempo. |
| Open-Meteo | Variables meteorológicas históricas y previsiones disponibles | Se validará la compatibilidad espacial y temporal con las demás fuentes. |

La propuesta contempla iniciar el análisis detallado con al menos 10,000 perfiles. Un año de registros cada 15 minutos para esa selección equivaldría aproximadamente a 350.4 millones de filas. Son metas de escala de la propuesta, no el primer hito técnico: el MVP empieza con agregados geográficos y un subconjunto medido para reducir riesgo de tamaño, acceso y costo. Consulta la [decisión inicial de alcance](docs/decision-alcance-mvp.md).

## Arquitectura propuesta

La propuesta plantea Amazon S3 para archivos y resultados, Amazon Kinesis Data Streams para recibir registros y Apache Spark en Amazon EMR para procesarlos. El tablero consumirá resultados agregados. La elección final y configuración se documentarán antes de activar servicios; las pruebas en nube serán acotadas y tendrán presupuesto definido.

## Estado actual

- [x] Propuesta versión 2 aprobada por el profesor.
- [x] Pipeline local Spark Silver/Gold ejecutado con 21 controles de calidad aprobados.
- [x] Dashboard local v1 conectado a cinco tablas Gold JSON, con manifiesto y comprobación de SHA-256.
- [x] Patrones horarios convertidos a hora local para los 10 perfiles piloto de Colorado y Nueva York, con cambios DST y meses parciales identificados.
- [ ] Estimaciones y anomalías: faltan salidas evaluadas; el dashboard no presenta cifras inventadas.
- [ ] Escala de 10,000 perfiles: solo se procesaron 10 perfiles; los IDs restantes son candidatos.
- [ ] AWS/EMR/Kinesis/S3: sin despliegue; primero deben registrarse región y presupuesto aprobados.
- [ ] Comparación Colorado/EIA: la razón de 87.16% no se pudo reproducir desde el agregado fuente, que no está versionado.

Los datos integrados son un piloto acotado, no una cobertura completa de Estados Unidos. El clima permanece como serie independiente y no se une al consumo.

## Abrir el dashboard local

Desde la raíz del repositorio, ejecuta:

```bash
python3 -m http.server 8000 -d tablero
```

Después abre <http://localhost:8000/>. La interfaz no requiere instalación de paquetes ni conexión a internet; las tablas y el manifiesto ya están en `tablero/data/v1/`.

## Equipo

| Integrante | Matrícula |
|---|---|
| Brian Garcia Mares | 22030511 |
| Omar Gadiel Bolaños García | 22030591 |
| Christian Raul Páramo Bautista | 22031149 |
| Diego Emilio Ortiz Vilchez | 22030642 |

## Documentación

- [Descripción y alcance](docs/descripcion-del-proyecto.md)
- [Fuentes de datos y consideraciones](docs/fuentes-de-datos.md)
- [Arquitectura propuesta](docs/arquitectura-propuesta.md)
- [Criterios de trabajo y registro de avances](docs/seguimiento.md)
- [Plan de desarrollo y reparto por integrante](docs/plan-de-desarrollo.md)
- [Tareas para la revisión de avance del 17 de noviembre](docs/plan-avance-17-noviembre.md)
- [Validación inicial de fuentes](docs/validacion-inicial-fuentes.md)
- [Resultados de la primera muestra](docs/resultados-muestra-inicial.md)
- [Contenido resumido por diapositiva en JSON](docs/contenido-presentacion-avance.json)
- [Versión legible del contenido de presentación](docs/presentacion-avance-17-noviembre.md)
- [PowerPoint borrador anterior, pendiente de aplicar el estilo final](presentaciones/Avance_Big_Data_17_noviembre_2026.pptx)
- [PDF borrador anterior](presentaciones/Avance_Big_Data_17_noviembre_2026.pdf)
- [Esquema conceptual y calidad inicial de datos](docs/esquema-inicial-calidad-datos.md)
- [Decisión inicial de alcance y MVP](docs/decision-alcance-mvp.md)
- [Especificación del tablero y dirección visual isométrica](docs/especificacion-tablero.md)
- [Plan urgente de la siguiente etapa: dashboard, AWS, escala y analítica](docs/plan-urgente-siguiente-etapa.md)
- [Contrato Gold consumido por el dashboard](docs/contrato-dashboard-datos.md)
- [Ejecución del pipeline y exportación al dashboard](docs/ejecucion-job-spark-local.md)
- [Guía del dashboard local](tablero/README.md)

El plan de desarrollo es una propuesta de organización basada en la guía disponible; se actualizará si el profesor comparte una rúbrica detallada o confirma fechas y requisitos adicionales.

La muestra y sus resultados son exploratorios; las vistas de estimaciones y anomalías aún no contienen resultados analíticos.

## Repositorio

Este repositorio es la referencia compartida para código, documentación, decisiones y avances del proyecto. No se publicarán aquí credenciales, tokens, datos personales de terceros ni conjuntos de datos que no tengan autorización de redistribución.
