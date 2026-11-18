#!/usr/bin/env python3
"""Genera la presentación con el estilo doodle de la referencia del equipo."""
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentaciones" / "Avance_Big_Data_17_noviembre_2026.pptx"
ASSETS = ROOT / "presentaciones" / "assets"
BG = "76D5E9"
GRID = "A2E3EF"
CREAM = "FFF5DD"
INK = "202020"
NAVY = "173552"
CORAL = "FF8175"
YELLOW = "FFD05C"
MINT = "8CE4D6"
WHITE = "FFFFFF"
FONT = "Comic Neue"
TITLE_FONT = "QTMagicMarker"


def rgb(value):
    return RGBColor.from_string(value)


def text(slide, value, x, y, w, h, size=18, color=INK, bold=False,
         font=FONT, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP, margin=0.04):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear(); tf.word_wrap = True
    tf.margin_left = Inches(margin); tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin); tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = value
    run.font.name = font; run.font.size = Pt(size); run.font.bold = bold
    run.font.color.rgb = rgb(color)
    return shape


def box(slide, x, y, w, h, fill=CREAM, line=INK, rounded=True, width=1.6):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = rgb(fill)
    shape.line.color.rgb = rgb(line); shape.line.width = Pt(width)
    if rounded:
        shape.adjustments[0] = 0.08
    return shape


def doodle_bg(slide):
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb = rgb(BG)
    # Dibuja la cuadrícula como líneas finas detrás del contenido.
    for x in range(0, 14):
        line = slide.shapes.add_connector(1, Inches(x), Inches(0), Inches(x), Inches(7.5))
        line.line.color.rgb = rgb(GRID); line.line.width = Pt(0.55)
    for y in range(0, 9):
        line = slide.shapes.add_connector(1, Inches(0), Inches(y), Inches(13.333), Inches(y))
        line.line.color.rgb = rgb(GRID); line.line.width = Pt(0.55)


def new_slide(prs, title, number, tag="AVANCE DEL PROYECTO"):
    s = prs.slides.add_slide(prs.slide_layouts[6]); doodle_bg(s)
    # Ventana de aplicación con barra superior color menta.
    box(s, .55, .42, 12.23, 6.62, CREAM, INK, True, 2)
    box(s, .55, .42, 12.23, .48, MINT, INK, True, 1.5)
    for i,c in enumerate((CORAL,YELLOW,WHITE)):
        dot=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(.78+i*.22), Inches(.57), Inches(.12), Inches(.12))
        dot.fill.solid(); dot.fill.fore_color.rgb=rgb(c); dot.line.color.rgb=rgb(INK); dot.line.width=Pt(.7)
    text(s, tag, 1.65, .55, 8.8, .23, 10, NAVY, True, FONT)
    text(s, f"{number:02d} / 07", 11.75, .55, .7, .22, 10, NAVY, True, FONT, PP_ALIGN.RIGHT)
    text(s, title, .95, 1.12, 11.35, .72, 27, INK, True, TITLE_FONT)
    text(s, "BIG DATA · INSTITUTO TECNOLÓGICO DE CELAYA", .98, 6.72, 10.3, .2, 9, NAVY, True)
    return s


def add_image(slide, name, x, y, w, h):
    path=ASSETS/name
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w), height=Inches(h))


def bullet_card(slide, heading, items, x, y, w, h, accent=CORAL, fs=18):
    box(slide,x,y,w,h,CREAM,INK,True,1.5)
    box(slide,x+.04,y+.04,.12,h-.08,accent,accent,False,.5)
    text(slide,heading,x+.28,y+.19,w-.55,.4,18,INK,True,TITLE_FONT)
    yy=y+.72
    for item in items:
        text(slide,"✦",x+.31,yy,.25,.35,15,accent,True)
        text(slide,item,x+.62,yy,w-.9,.62,fs,INK)
        yy += .76


def build():
    content=json.loads((ROOT/"docs/contenido-presentacion-avance.json").read_text(encoding="utf-8"))
    content=content["presentation"]
    acad=content["academic_information"]
    prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
    prs.core_properties.title="Análisis del consumo eléctrico residencial"
    prs.core_properties.subject="Avance del proyecto de Big Data · Colorado 2018"
    prs.core_properties.author="Equipo del proyecto · Instituto Tecnológico de Celaya"

    # 1 · Portada académica
    s=prs.slides.add_slide(prs.slide_layouts[6]); doodle_bg(s)
    box(s,.42,.36,12.5,6.82,CREAM,INK,True,2)
    box(s,.42,.36,12.5,.5,MINT,INK,True,1.6)
    for i,c in enumerate((CORAL,YELLOW,WHITE)):
        d=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(.68+i*.23), Inches(.53), Inches(.12), Inches(.12))
        d.fill.solid();d.fill.fore_color.rgb=rgb(c);d.line.color.rgb=rgb(INK)
    text(s,"PROYECTO FINAL · BIG DATA",1.6,.5,7,.25,11,NAVY,True)
    text(s,"Análisis del consumo\neléctrico residencial",.85,1.2,7.55,1.28,31,INK,True,TITLE_FONT)
    text(s,"Primer avance · muestra exploratoria de Colorado, 2018",.9,2.62,7.2,.48,16,NAVY,True)
    add_image(s,"01-portada.png",8.45,1.22,3.95,3.1)
    box(s,.86,3.27,7.15,2.34,WHITE,INK,True,1.3)
    text(s,"EQUIPO",1.1,3.43,1.5,.28,12,CORAL,True,TITLE_FONT)
    left=acad["team"][:2]; right=acad["team"][2:]
    for i,m in enumerate(left):
        text(s,m["name"],1.12,3.88+i*.63,3.0,.28,13,INK,True)
        text(s,m["control_number"],1.12,4.19+i*.63,2.8,.2,11,NAVY)
    for i,m in enumerate(right):
        text(s,m["name"],4.3,3.88+i*.63,3.35,.28,13,INK,True)
        text(s,m["control_number"],4.3,4.19+i*.63,2.8,.2,11,NAVY)
    box(s,8.55,4.55,3.78,1.52,YELLOW,INK,True,1.4)
    text(s,acad["institution"],8.78,4.72,3.34,.43,13,INK,True,align=PP_ALIGN.CENTER)
    text(s,acad["program"],8.78,5.17,3.34,.35,11,INK,align=PP_ALIGN.CENTER)
    text(s,"Materia: "+acad["course"],8.78,5.52,3.34,.26,12,INK,True,align=PP_ALIGN.CENTER)
    text(s,"Profesor: "+acad["professor"],.96,5.9,7.1,.3,13,NAVY,True)
    text(s,"REVISIÓN DE AVANCE · 16 NOV 2026",8.55,6.46,3.78,.24,10,NAVY,True,align=PP_ALIGN.CENTER)

    # 2 · Propósito y alcance
    s=new_slide(prs,"¿Qué estamos investigando?",2,"PROPÓSITO Y ALCANCE")
    bullet_card(s,"La pregunta",[
        "¿Cómo cambian los patrones de consumo eléctrico residencial?",
        "Buscamos comparar perfiles, clima y estadísticas oficiales.",
        "La propuesta V2 fue aprobada para continuar."
    ],.95,2.05,7.15,3.85,CORAL,17)
    add_image(s,"01-portada.png",8.4,2.05,3.55,3.6)
    box(s,8.45,5.7,3.45,.65,YELLOW,INK,True,1.3)
    text(s,"En este avance: probar fuentes",8.62,5.88,3.1,.28,13,INK,True,align=PP_ALIGN.CENTER)

    # 3 · Fuentes
    s=new_slide(prs,"Cada fuente cuenta algo distinto",3,"DATOS REVISADOS")
    cards=[("ResStock","Perfiles de viviendas simulados",CORAL),("EIA","Ventas residenciales por estado",YELLOW),("Open-Meteo","Clima histórico estimado para Denver",MINT)]
    for i,(name,desc,col) in enumerate(cards):
        x=.95+i*3.98
        box(s,x,2.02,3.62,2.15,WHITE,INK,True,1.5)
        box(s,x,2.02,3.62,.43,col,INK,True,1.2)
        text(s,name,x+.22,2.65,3.18,.38,20,INK,True,TITLE_FONT,PP_ALIGN.CENTER)
        text(s,desc,x+.28,3.17,3.06,.66,15,INK,align=PP_ALIGN.CENTER,valign=MSO_ANCHOR.MIDDLE)
    add_image(s,"02-fuentes.png",2.55,4.35,7.95,1.63)
    box(s,1.3,6.02,10.75,.48,YELLOW,INK,True,1.2)
    text(s,"Son perspectivas diferentes: las mantenemos separadas mientras revisamos su compatibilidad.",1.55,6.12,10.25,.24,13,INK,True,align=PP_ALIGN.CENTER)

    # 4 · Muestra
    s=new_slide(prs,"Primera muestra: Colorado, año 2018",4,"RESSTOCK · VIVIENDA UNIFAMILIAR SEPARADA")
    add_image(s,"03-muestra.png",1.0,2.02,5.35,2.3)
    metrics=[("35,040","intervalos de 15 min"),("5,869","modelos de vivienda"),("≈1.49 M","unidades representadas")]
    for i,(val,label) in enumerate(metrics):
        y=2.0+i*1.22
        box(s,6.65,y,5.2,.94,[CORAL,YELLOW,MINT][i],INK,True,1.4)
        text(s,val,6.9,y+.15,1.75,.4,22,INK,True,TITLE_FONT)
        text(s,label,8.75,y+.25,2.8,.33,15,INK,True)
    box(s,1.3,4.85,10.7,1.0,WHITE,INK,True,1.3)
    text(s,"Revisamos un archivo de unos 31 MB. Resume modelos ponderados; no son lecturas de medidores reales.",1.62,5.1,10.08,.5,16,INK,True,align=PP_ALIGN.CENTER,valign=MSO_ANCHOR.MIDDLE)

    # 5 · Comparación
    s=new_slide(prs,"¿Qué observamos al comparar?",5,"RESSTOCK Y VENTAS EIA")
    add_image(s,"05-comparacion.png",.95,2.0,7.15,3.65)
    box(s,8.35,2.05,3.75,.9,CORAL,INK,True,1.3)
    text(s,"16.81 M MWh",8.58,2.22,3.3,.37,21,INK,True,TITLE_FONT,PP_ALIGN.CENTER)
    text(s,"ResStock · categoría seleccionada",8.58,2.62,3.3,.22,11,INK,align=PP_ALIGN.CENTER)
    box(s,8.35,3.15,3.75,.9,MINT,INK,True,1.3)
    text(s,"19.29 M MWh",8.58,3.32,3.3,.37,21,INK,True,TITLE_FONT,PP_ALIGN.CENTER)
    text(s,"EIA · todo el sector residencial",8.58,3.72,3.3,.22,11,INK,align=PP_ALIGN.CENTER)
    box(s,8.35,4.25,3.75,.73,YELLOW,INK,True,1.3)
    text(s,"Relación simple: 87%",8.55,4.44,3.35,.3,16,INK,True,align=PP_ALIGN.CENTER)
    box(s,1.05,5.83,11.1,.62,WHITE,INK,True,1.3)
    text(s,"No mide precisión: una categoría modelada se compara con todas las viviendas del estado.",1.3,5.98,10.6,.3,14,INK,True,align=PP_ALIGN.CENTER)

    # 6 · Verificaciones
    s=new_slide(prs,"Revisamos continuidad y datos faltantes",6,"CONTROLES INICIALES")
    add_image(s,"06-calidad.png",.95,2.05,4.4,3.8)
    bullet_card(s,"Resultado de la revisión",[
        "35,040 intervalos continuos y regulares.",
        "Sin celdas vacías ni valores negativos en el total.",
        "Clima: 8,760 horas para un punto de Denver.",
        "Aún no unimos consumo y clima: cambian ubicación y horario."
    ],5.45,2.0,6.45,3.95,MINT,15)
    box(s,1.25,6.03,10.75,.48,YELLOW,INK,True,1.2)
    text(s,"El clima es una estimación para Denver, no una medición de todo Colorado.",1.5,6.13,10.25,.25,13,INK,True,align=PP_ALIGN.CENTER)

    # 7 · Próximos pasos
    s=new_slide(prs,"¿Qué sigue después de este avance?",7,"SIGUIENTES PASOS")
    add_image(s,"07-ruta.png",1.05,2.02,7.25,3.35)
    steps=["Confirmar atribución y condiciones de uso.","Ampliar la muestra por viviendas o lugares.","Preparar un procesamiento que pueda repetirse.","Después: analizar anomalías y crear un tablero."]
    bullet_card(s,"Ruta de trabajo",steps,8.25,2.0,3.85,3.9,CORAL,14)
    box(s,1.35,5.82,10.55,.67,YELLOW,INK,True,1.2)
    text(s,"Ya hay una muestra comprobable; el tablero y el análisis final siguen pendientes.",1.62,6.0,10.0,.3,14,INK,True,align=PP_ALIGN.CENTER)

    OUT.parent.mkdir(parents=True,exist_ok=True); prs.save(OUT)
    print(OUT)


if __name__=="__main__":
    build()
