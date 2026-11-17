# Guion para la revisión de avance — 17 de noviembre

**Duración sugerida:** 4–5 minutos más preguntas.
**Estado:** material listo para exponer como avance parcial. No es la presentación final ni afirma que el sistema esté terminado.

Diapositivas: [PowerPoint](../presentaciones/Avance_Big_Data_17_noviembre_2026.pptx) y [PDF](../presentaciones/Avance_Big_Data_17_noviembre_2026.pdf). Para regenerar el PowerPoint con la muestra local: `python scripts/generar_presentacion.py`.

## Diapositiva 1 — Proyecto y pregunta (30 s)

**Mostrar:** título, objetivo y aprobación de la propuesta V2.

**Decir:** “El proyecto analiza patrones de consumo eléctrico residencial de Estados Unidos con perfiles modelados, estadísticas oficiales y clima. La propuesta V2 fue aprobada sin observaciones. Este avance se concentra en comprobar una muestra pequeña antes de escalar.”

## Diapositiva 2 — Qué representa cada fuente (40 s)

| Fuente | En esta prueba | Qué no representa |
|---|---|---|
| ResStock 2025.1 | Perfil modelado, agregado y ponderado para Colorado | Lectura de medidores individuales |
| EIA | Ventas mensuales del sector residencial de Colorado | Serie horaria ni subgrupo de vivienda |
| Open-Meteo | Temperatura de reanálisis horaria en un punto de Denver | Lectura directa de estación o clima representativo de todo Colorado |

**Decir:** “Las fuentes tienen alcances distintos; las conservamos separadas. La lluvia de datos de red EIA-930 se deja como contexto opcional, no como consumo doméstico.”

## Diapositiva 3 — Primera muestra inspeccionada (50 s)

- ResStock: baseline `upgrade=0`, Colorado, vivienda unifamiliar separada.
- Archivo de 31.0 MB, 96 columnas y 35,040 filas.
- `models_used`: 5,869; unidades ponderadas representadas: 1,490,160.655.
- Periodo 2018, marcas cada 15 minutos; la marca indica fin del intervalo y está publicada en EST.
- EIA: 12 meses de 2018, estado `Final`, unidad MWh.
- Clima: 8,760 temperaturas horarias de reanálisis en °C, ubicación Denver, zona UTC; consulta con el `Best Match` predeterminado, no un modelo fijado.

**Decir:** “La primera extracción fue deliberadamente pequeña frente a la salida completa de ResStock. No incluimos los archivos originales en Git; guardamos un procedimiento para volver a obtenerlos.”

## Diapositiva 4 — Comprobaciones y comparación exploratoria (60 s)

**Mostrar:** [gráfica mensual](evidencia/comparacion-resstock-eia-co-2018.svg) y [tabla reproducible](resultados-muestra-inicial.md).

- En la muestra ResStock: 35,040 timestamps únicos, secuencia continua de 15 minutos, cero celdas vacías y cero negativos en el total de electricidad.
- Total anual en el perfil agregado de vivienda separada: 16.81 millones de MWh.
- Ventas residenciales EIA para todo Colorado: 19.29 millones de MWh.
- Razón anual simple entre ambas series: 87.16%; las razones mensuales van de 68.31% a 114.85%.

**Decir:** “La razón sirve para inspeccionar forma y escala, no es una métrica de precisión. ResStock describe un tipo de vivienda modelado y EIA todas las ventas residenciales estatales. No afirmamos que deban coincidir.”

## Diapositiva 5 — Decisión técnica y límites (45 s)

- Comenzar con agregados ResStock y muestras estatales pequeñas; ampliar después de medir archivos y procesamiento.
- Usar EIA residencial para referencia macro mensual; no mezclarla con demanda horaria de red.
- Mantener clima aparte hasta resolver representatividad y conversión entre UTC, EST y hora local.
- No activar AWS hasta medir volumen local y estimar costo.
- La detección de anomalías, estimación, tablero integrado y reproducción progresiva todavía no están implementados.

## Diapositiva 6 — Próximos pasos (35 s)

1. Confirmar atribución/avisos de columnas de ResStock y condiciones de reutilización EIA/Open-Meteo.
2. Revisar con el profesor/equipo la muestra y registrar comentarios.
3. Ampliar el análisis mensual por tipo de vivienda y comparar coberturas con cautela.
4. Implementar controles, análisis reproducible y después una primera detección de anomalías evaluable.
5. Definir si la escala observada justifica una prueba cloud con costo estimado.

## Demostración opcional

Si el equipo quiere repetir el resumen desde los archivos locales:

```bash
python -m pip install -r requirements.txt
python scripts/analizar_muestra_inicial.py
```

Si no están los tres archivos en `data/raw/`, el script puede obtener únicamente la muestra acotada:

```bash
python scripts/analizar_muestra_inicial.py --descargar
```

La descarga del agregado ResStock es de aproximadamente 31 MB; todos los originales quedan excluidos del repositorio.

## Preguntas previsibles

- **¿Por qué Colorado?** Para validar un primer extracto estatal y el proceso de lectura; aún no representa análisis nacional.
- **¿Por qué un resultado modelado?** ResStock permite explorar resolución subhoraria y características de vivienda; las ventas EIA aportan una referencia macro independiente.
- **¿87.16% significa que ResStock tiene 12.84% de error?** No. Las poblaciones y definiciones no son equivalentes; la razón es exploratoria y requiere reconciliación metodológica.
- **¿Ya hay anomalías o predicciones?** Todavía no. El avance actual valida acceso, esquema y controles básicos de una muestra.
- **¿Está desplegado en AWS o es streaming en vivo?** No. La nube está condicionada a costo y volumen; el flujo planeado será replay de históricos, no medidores en vivo.

## Fuentes para citar en la exposición

- [ResStock FAQ: unidades, timestamps, ponderación y agregados](https://natlabrockies.github.io/ResStock.github.io/docs/FAQ.html)
- [ResStock Data: estructura del release y tipos de archivo](https://natlabrockies.github.io/ResStock.github.io/docs/data.html)
- [Registro OEDI: licencia general CC BY 3.0 US](https://registry.opendata.aws/oedi-data-lake/)
- [EIA EIA-861M: ventas mensuales por estado y sector](https://www.eia.gov/electricity/data/eia861m/)
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api): reanálisis meteorológico; `Best Match` combina modelos.
