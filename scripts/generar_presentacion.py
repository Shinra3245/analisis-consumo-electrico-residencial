#!/usr/bin/env python3
"""Genera la presentación breve del avance con las muestras ya descargadas."""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analizar_muestra_inicial import (  # noqa: E402
    EIA_NAME,
    RAW,
    RESSTOCK_NAME,
    WEATHER_NAME,
    analyze_eia,
    analyze_resstock,
    analyze_weather,
)

OUT = ROOT / "presentaciones" / "Avance_Big_Data_17_noviembre_2026.pptx"
NAVY = "15334A"
TEAL = "0D806F"
BLUE = "3658A6"
INK = "1D2935"
MUTED = "526575"
BG = "F3F7F8"
WHITE = "FFFFFF"
LINE = "D7E1E6"
PALE_TEAL = "E5F3F0"
PALE_BLUE = "EAF0FA"
PALE_GOLD = "FCF4E2"
GOLD = "A76B00"


def color(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def add_box(slide, x, y, w, h, fill=WHITE, line=None, radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(fill)
    shape.line.color.rgb = color(line or fill)
    if radius:
        shape.adjustments[0] = 0.12
    return shape


def add_text(slide, text, x, y, w, h, size=18, fill=INK, bold=False,
             font="Aptos", align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP,
             margin=0.02):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(margin)
    frame.margin_right = Inches(margin)
    frame.margin_top = Inches(margin)
    frame.margin_bottom = Inches(margin)
    frame.vertical_anchor = valign
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color(fill)
    return box


def add_bullets(slide, items, x, y, w, h, size=17, gap=10, fill=INK):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.02)
    frame.margin_right = Inches(0.02)
    frame.margin_top = Inches(0.02)
    frame.margin_bottom = Inches(0.02)
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = "• " + item
        paragraph.level = 0
        paragraph.font.name = "Aptos"
        paragraph.font.size = Pt(size)
        paragraph.font.color.rgb = color(fill)
        paragraph.space_after = Pt(gap)
    return box


def add_header(slide, title, eyebrow, number):
    add_text(slide, eyebrow.upper(), 0.7, 0.38, 10.5, 0.25, 10, TEAL, True)
    add_text(slide, title, 0.7, 0.73, 11.9, 0.65, 27, NAVY, True)
    add_text(slide, f"{number:02d} / 06", 11.85, 0.40, 0.75, 0.25, 10, MUTED, True, align=PP_ALIGN.RIGHT)
    add_box(slide, 0.7, 1.48, 11.95, 0.015, LINE)


def add_footer(slide, number):
    add_box(slide, 0.7, 7.07, 11.95, 0.012, LINE)
    add_text(slide, "BIG DATA · PROYECTO FINAL · IT CELAYA", 0.72, 7.13, 8.4, 0.2, 8, MUTED, True)
    add_text(slide, "REVISIÓN DE AVANCE · 17 NOV 2026", 8.4, 7.13, 4.15, 0.2, 8, MUTED, True, align=PP_ALIGN.RIGHT)


def new_slide(prs, title, eyebrow, number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color(BG)
    add_header(slide, title, eyebrow, number)
    add_footer(slide, number)
    return slide


def add_card(slide, x, y, w, h, title, body, accent=TEAL, fill=WHITE):
    add_box(slide, x, y, w, h, fill=fill, line=fill, radius=True)
    add_box(slide, x, y, 0.07, h, fill=accent, line=accent)
    add_text(slide, title, x + 0.24, y + 0.18, w - 0.45, 0.42, 16, NAVY, True)
    add_text(slide, body, x + 0.24, y + 0.67, w - 0.45, h - 0.82, 12, MUTED)


def draw_monthly_chart(slide, resstock, eia):
    x0, y0, w, h = 1.2, 2.48, 7.65, 3.55
    r = [resstock["monthly_electricity_mwh"][m] for m in range(1, 13)]
    e = [eia["monthly_sales_mwh"][m] for m in range(1, 13)]
    maximum = max(max(r), max(e)) * 1.08
    left, right, top, bottom = x0 + 0.53, x0 + w - 0.08, y0 + 0.12, y0 + h - 0.42
    pw, ph = right - left, bottom - top
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    for i in range(5):
        val = maximum * i / 4
        yy = bottom - ph * (val / maximum)
        add_box(slide, left, yy, pw, 0.012, LINE)
        add_text(slide, f"{val/1_000_000:.1f}M", x0, yy - 0.09, 0.45, 0.18, 8, MUTED, align=PP_ALIGN.RIGHT)
    for i, label in enumerate(months):
        xx = left + i * pw / 11
        add_text(slide, label, xx - 0.22, bottom + 0.08, 0.44, 0.18, 8, MUTED, align=PP_ALIGN.CENTER)
    for values, stroke in ((r, TEAL), (e, BLUE)):
        coords = []
        for i, value in enumerate(values):
            xx = left + i * pw / 11
            yy = bottom - ph * value / maximum
            coords.append((xx, yy))
        for p1, p2 in zip(coords, coords[1:]):
            connector = slide.shapes.add_connector(1, Inches(p1[0]), Inches(p1[1]), Inches(p2[0]), Inches(p2[1]))
            connector.line.color.rgb = color(stroke)
            connector.line.width = Pt(2.5)
        for xx, yy in coords:
            dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(xx - 0.045), Inches(yy - 0.045), Inches(0.09), Inches(0.09))
            dot.fill.solid()
            dot.fill.fore_color.rgb = color(stroke)
            dot.line.color.rgb = color(stroke)


def build_deck():
    source_paths = [RAW / name for name in (RESSTOCK_NAME, EIA_NAME, WEATHER_NAME)]
    missing = [path.name for path in source_paths if not path.exists()]
    if missing:
        raise SystemExit("Faltan fuentes locales: " + ", ".join(missing) + ". Ejecute primero analizar_muestra_inicial.py --descargar.")
    resstock = analyze_resstock(source_paths[0])
    eia = analyze_eia(source_paths[1])
    weather = analyze_weather(source_paths[2])

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Avance del proyecto de análisis de consumo eléctrico residencial"
    prs.core_properties.subject = "Revisión de avance del 17 de noviembre de 2026"
    prs.core_properties.author = "Equipo del proyecto"

    # 1. Portada
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color(NAVY)
    add_box(slide, 9.4, 0, 3.933, 7.5, TEAL)
    add_box(slide, 10.1, 1.05, 2.55, 2.55, "1A8F7C", radius=True)
    add_text(slide, "BIG DATA · PROYECTO FINAL", 0.78, 0.78, 6.8, 0.35, 11, "9FE0D1", True)
    add_text(slide, "Análisis del consumo\neléctrico residencial", 0.78, 1.72, 8.15, 1.55, 32, WHITE, True)
    add_text(slide, "Propuesta V2 aprobada · primer avance empírico · Colorado, 2018", 0.82, 3.54, 8.0, 0.48, 16, "D4E0E8")
    add_box(slide, 0.82, 4.38, 4.1, 0.53, "E6F3F0", radius=True)
    add_text(slide, "REVISIÓN DE AVANCE · 17 NOV 2026", 1.03, 4.51, 3.72, 0.25, 10, NAVY, True, align=PP_ALIGN.CENTER)
    add_text(slide, "Instituto Tecnológico de Celaya", 0.82, 6.67, 5.6, 0.28, 11, "D4E0E8")
    add_text(slide, "ResStock", 10.35, 1.65, 2.05, 0.35, 18, WHITE, True, align=PP_ALIGN.CENTER)
    add_text(slide, "MODELO", 10.36, 2.12, 2.04, 0.25, 10, "D4E0E8", True, align=PP_ALIGN.CENTER)
    add_text(slide, "EIA  ·  CLIMA", 10.02, 4.18, 2.72, 0.45, 16, WHITE, True, align=PP_ALIGN.CENTER)
    add_text(slide, "Muestra acotada\ny controles reproducibles", 10.05, 4.75, 2.72, 0.7, 13, "E5F3F0", align=PP_ALIGN.CENTER)

    # 2. Fuentes y separación
    slide = new_slide(prs, "Tres fuentes, tres significados", "Alcance de la prueba", 2)
    add_card(slide, 0.8, 1.9, 3.73, 2.12, "ResStock 2025.1", "Perfil subhorario modelado y ponderado.\nPiloto: Colorado, vivienda unifamiliar separada.", TEAL)
    add_card(slide, 4.8, 1.9, 3.73, 2.12, "EIA · EIA-861M", "Ventas residenciales oficiales por estado y mes.\nReferencia estatal, no medidor doméstico.", BLUE)
    add_card(slide, 8.8, 1.9, 3.73, 2.12, "Open-Meteo", "Temperatura histórica de reanálisis en un punto de Denver.\nNo es lectura directa de estación.", GOLD)
    add_box(slide, 0.8, 4.43, 11.73, 1.42, PALE_GOLD, radius=True)
    add_text(slide, "Decisión de diseño", 1.1, 4.66, 2.2, 0.32, 15, GOLD, True)
    add_text(slide, "Mantener capas separadas; alinear geografía, unidades y husos horarios antes de unir.", 3.25, 4.63, 8.8, 0.72, 19, NAVY, True, valign=MSO_ANCHOR.MIDDLE)
    add_text(slide, "No se usa EIA-930 como sustituto de consumo residencial.", 1.1, 6.16, 10.4, 0.3, 12, MUTED)

    # 3. Muestra ResStock
    slide = new_slide(prs, "La muestra ya fue inspeccionada", "ResStock · baseline 2018", 3)
    metrics = [("35,040", "intervalos"), ("96", "columnas"), ("5,869", "modelos"), ("31.0 MB", "archivo")]
    for i, (value, label) in enumerate(metrics):
        x = 0.85 + i * 3.03
        add_box(slide, x, 1.91, 2.76, 1.05, PALE_TEAL if i % 2 == 0 else PALE_BLUE, radius=True)
        add_text(slide, value, x + 0.12, 2.04, 2.52, 0.45, 24, TEAL if i % 2 == 0 else BLUE, True, align=PP_ALIGN.CENTER)
        add_text(slide, label.upper(), x + 0.12, 2.57, 2.52, 0.21, 9, MUTED, True, align=PP_ALIGN.CENTER)
    add_card(slide, 0.85, 3.35, 5.55, 2.38, "Cobertura del extracto", "Colorado · `upgrade=0`\nSingle-Family Detached\n2018 · cada 15 minutos\n5,869 modelos representan aproximadamente 1.49 millones de unidades ponderadas.", TEAL)
    add_card(slide, 6.75, 3.35, 5.55, 2.38, "Contrato temporal y energético", "El timestamp marca el cierre del intervalo.\nPublicación ResStock en EST.\nCampo analizado: `out.electricity.total.energy_consumption..kwh`.\nLa suma del archivo no es un consumo individual.", BLUE)
    add_text(slide, "Los archivos originales permanecen locales e ignorados por Git; no se publican datos fuente.", 0.9, 6.22, 11.5, 0.3, 11, MUTED)

    # 4. Comprobaciones y comparación
    slide = new_slide(prs, "Control básico y comparación exploratoria", "Resultados observados", 4)
    draw_monthly_chart(slide, resstock, eia)
    add_text(slide, "MWh / mes", 0.84, 2.17, 1.0, 0.2, 9, MUTED, True)
    add_box(slide, 9.2, 2.18, 3.28, 1.25, WHITE, radius=True)
    add_text(slide, "16.81M MWh", 9.43, 2.39, 2.82, 0.4, 20, TEAL, True)
    add_text(slide, "ResStock · vivienda detached", 9.43, 2.83, 2.82, 0.25, 10, MUTED)
    add_box(slide, 9.2, 3.62, 3.28, 1.25, WHITE, radius=True)
    add_text(slide, "19.29M MWh", 9.43, 3.83, 2.82, 0.4, 20, BLUE, True)
    add_text(slide, "EIA · todo el sector residencial", 9.43, 4.27, 2.82, 0.25, 10, MUTED)
    ratio = 100 * resstock["annual_total_electricity_mwh"] / eia["annual_sales_mwh"]
    add_box(slide, 9.2, 5.05, 3.28, 0.83, PALE_GOLD, radius=True)
    add_text(slide, f"Razón anual: {ratio:.2f}%", 9.42, 5.26, 2.86, 0.35, 16, GOLD, True)
    add_text(slide, "No es una métrica de error: las coberturas difieren.", 1.2, 6.25, 10.8, 0.3, 12, MUTED, True)

    # 5. Calidad, clima y límites
    slide = new_slide(prs, "Qué verificamos y qué sigue sin resolverse", "Calidad y límites", 5)
    add_box(slide, 0.85, 1.92, 5.55, 3.6, WHITE, radius=True)
    add_text(slide, "ResStock · comprobaciones", 1.15, 2.18, 4.9, 0.35, 17, TEAL, True)
    add_bullets(slide, [
        "35,040 timestamps únicos y continuos",
        "Intervalo constante: 15 minutos",
        "Cero celdas vacías en el archivo",
        "Cero valores negativos en energía total",
    ], 1.18, 2.76, 4.85, 2.2, 14, 12)
    add_box(slide, 6.75, 1.92, 5.55, 3.6, WHITE, radius=True)
    add_text(slide, "Clima · aún no integrado", 7.05, 2.18, 4.9, 0.35, 17, BLUE, True)
    add_bullets(slide, [
        "8,760 horas y cero faltantes para 2018",
        "Denver; un punto no representa todo Colorado",
        "UTC en clima frente a EST en ResStock",
        "Best Match mezcla modelos; modelo por fijar",
    ], 7.08, 2.76, 4.85, 2.25, 14, 11)
    add_box(slide, 0.85, 5.84, 11.45, 0.75, PALE_GOLD, radius=True)
    add_text(slide, "Interpretación", 1.1, 6.03, 1.45, 0.28, 12, GOLD, True)
    add_text(slide, "La serie EIA cubre todo el sector residencial; ResStock aquí es una categoría modelada.", 2.65, 5.99, 9.25, 0.34, 13, NAVY, True)

    # 6. Próximas decisiones
    slide = new_slide(prs, "Siguiente incremento: cerrar el contrato de datos", "Ruta de trabajo", 6)
    steps = [
        ("01", "Revisar", "Atribución, términos y avisos de columnas."),
        ("02", "Alinear", "Cobertura espacial y tratamiento del tiempo."),
        ("03", "Ampliar", "Comparación por tipo de vivienda y meses."),
        ("04", "Implementar", "Controles, análisis y anomalía evaluable."),
        ("05", "Medir", "Volumen, tiempo y costo antes de nube."),
    ]
    for i, (num, title, body) in enumerate(steps):
        y = 1.86 + i * 0.83
        add_box(slide, 0.94, y, 0.55, 0.55, TEAL if i < 2 else BLUE, radius=True)
        add_text(slide, num, 0.97, y + 0.14, 0.49, 0.22, 11, WHITE, True, align=PP_ALIGN.CENTER)
        add_text(slide, title, 1.8, y + 0.02, 1.75, 0.3, 15, NAVY, True)
        add_text(slide, body, 3.75, y + 0.03, 7.85, 0.34, 14, MUTED)
    add_box(slide, 0.94, 6.27, 11.3, 0.48, PALE_TEAL, radius=True)
    add_text(slide, "Avance presentado = evidencia inicial y decisiones; falta construir el sistema final.", 1.16, 6.38, 10.85, 0.23, 12, TEAL, True, align=PP_ALIGN.CENTER)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build_deck()
