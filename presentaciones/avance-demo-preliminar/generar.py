#!/usr/bin/env python3
"""Renderiza una presentación nueva como PNG y la une directamente en PDF."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ART = ROOT / "presentaciones" / "arte_generado"
OUT = HERE / "diapositivas"
W, H = 1920, 1080
FONT_BODY = "/usr/share/fonts/texlive-comicneue/ComicNeue-Regular.otf"
FONT_BOLD = "/usr/share/fonts/texlive-comicneue/ComicNeue-Bold.otf"
FONT_TITLE = "/usr/share/fonts/texlive-qualitype/QTMagicMarker.otf"
INK, NAVY = (27, 37, 49), (25, 57, 91)
TEAL, BLUE, CORAL, YELLOW = (28, 153, 135), (103, 139, 235), (223, 89, 78), (255, 208, 92)
CREAM = (255, 248, 230)
BG = {1:"01-portada.png",2:"02-proposito.png",3:"03-fuentes.png",4:"04-muestra.png",5:"05-comparacion.png",6:"08-evidencia.png",7:"07-ruta.png"}

def font(path, size): return ImageFont.truetype(path, size)

def fit_bg(path):
    im = Image.open(path).convert("RGB")
    scale = max(W/im.width, H/im.height)
    im = im.resize((round(im.width*scale),round(im.height*scale)), Image.Resampling.LANCZOS)
    x,y=(im.width-W)//2,(im.height-H)//2
    return im.crop((x,y,x+W,y+H))

def wrap(draw, text, f, width):
    lines=[]; line=""
    for word in text.split():
        trial=(line+" "+word).strip()
        if draw.textbbox((0,0),trial,font=f)[2] <= width: line=trial
        else:
            if line: lines.append(line)
            line=word
    if line: lines.append(line)
    return "\n".join(lines)

def text(d, xy, value, size=30, color=INK, bold=False, title=False, anchor=None, spacing=None):
    f=font(FONT_TITLE if title else FONT_BOLD if bold else FONT_BODY,size)
    d.multiline_text(xy,value,font=f,fill=color,spacing=spacing or max(4,size//5),anchor=anchor)

def paragraph(d, xy, value, width, size=30, color=INK, bold=False, gap=12):
    f=font(FONT_BOLD if bold else FONT_BODY,size); lines=wrap(d,value,f,width)
    d.multiline_text(xy,lines,font=f,fill=color,spacing=7)
    return d.multiline_textbbox(xy,lines,font=f,spacing=7)[3]+gap

def pill(d, xy, value, fill, size=23):
    f=font(FONT_BOLD,size); x,y=xy; box=d.textbbox((x+16,y+8),value,font=f)
    d.rounded_rectangle((x,y,box[2]+16,box[3]+8),radius=14,fill=fill,outline=INK,width=2)
    d.text((x+16,y+8),value,font=f,fill=INK)

def slide(n):
    im=fit_bg(ART/BG[n]); d=ImageDraw.Draw(im)
    if n==1:
        text(d,(165,265),"Consumo eléctrico\nresidencial",78,INK,True,True)
        text(d,(170,455),"Demo tangible · Colorado, 2018",38,NAVY,True)
        text(d,(170,520),"BIG DATA · PROYECTO FINAL",30,CORAL,True)
        text(d,(170,575),"EQUIPO",30,CORAL,True,True)
        team=[("Brian García Mares","22030511"),("Omar Gadiel Bolaños García","22030591"),("Christian Raúl Páramo Bautista","22031149"),("Diego Emilio Ortiz Vílchez","22030642")]
        for i,(name,number) in enumerate(team):
            x=170+(i//2)*520; y=630+(i%2)*95
            text(d,(x,y),name,30,INK,True); text(d,(x,y+40),number,26,NAVY)
        text(d,(170,835),"Ing. en Sistemas Computacionales · TecNM Celaya",27,NAVY,True)
        text(d,(170,880),"M.A.V.D. José Jesús Sánchez Farías",28,INK,True)
        pill(d,(170,930),"RESULTADOS Y DEMOSTRACIÓN",YELLOW,24)
    elif n==2:
        text(d,(150,285),"¿Qué busca el proyecto?",62,INK,True,True)
        y=400
        for line in [
            "Analizar cómo cambia el consumo eléctrico residencial por región y periodo.",
            "Relacionar perfiles de vivienda con estadísticas oficiales y variables del clima.",
            "Explorar cambios inusuales y estimar cómo podría evolucionar el consumo.",
        ]:
            y=paragraph(d,(165,y),line,1030,39,gap=22)
        pill(d,(175,795),"META: CONVERTIR DATOS EN INFORMACIÓN ÚTIL",YELLOW,27)
    elif n==3:
        text(d,(245,275),"Tres fuentes, distintas perspectivas",56,INK,True,True)
        text(d,(250,345),"La comparación actual usa ResStock y EIA; el clima se incorporará después.",28,NAVY,True)
        # Tarjetas limpias sobre el arte decorativo para mantener legibilidad.
        for x in (100,675,1250):
            d.rounded_rectangle((x,410,x+540,875),radius=28,fill=CREAM,outline=INK,width=3)
        cards=[("ResStock","Perfiles modelados\nde viviendas","En la demo: Colorado, 2018",TEAL),
               ("EIA-861M","Ventas oficiales\npor sector y estado","En la demo: 12 meses",BLUE),
               ("Open-Meteo","Historial de\ntemperatura","Fuente prevista para\nanálisis posterior",CORAL)]
        xs=[455,960,1455]
        for (head,desc,foot,col),x in zip(cards,xs):
            text(d,(x,485),head,40,NAVY,True,anchor="mm")
            text(d,(x,605),desc,34,INK,True,anchor="mm")
            text(d,(x,755),foot,26,col,True,anchor="mm")
    elif n==4:
        text(d,(100,195),"Una muestra anual para comenzar",55,INK,True,True)
        text(d,(105,275),"Colorado · vivienda unifamiliar aislada · 2018",34,NAVY,True)
        paragraph(d,(110,365),"ResStock organiza el consumo en intervalos de 15 minutos.",900,36,INK,gap=42)
        paragraph(d,(110,500),"Los modelos se ponderan para representar viviendas; no son medidores individuales.",900,36,INK,gap=0)
        metrics=[("35,040","intervalos en el año"),("5,869","modelos de vivienda"),("cerca de 1.49 M","viviendas representadas")]
        for y,(val,label) in zip((230,530,825),metrics):
            text(d,(1575,y),val,42,INK,True,anchor="mm")
            text(d,(1575,y+68),label,29,NAVY,anchor="mm")
    elif n==5:
        text(d,(95,180),"La comparación cambia según el mes",55,INK,True,True)
        plot=(145,350,1310,875); d.rectangle(plot,fill=CREAM)
        months=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        res=[1812597.23,1667852.33,1322864.87,1147907.04,1114155.94,1343082.37,1512931.30,1362359.35,1212696.57,1138391.12,1401276.70,1773538.48]
        eia=[1653911.40,1452241.20,1456725.50,1297995.10,1429900.70,1783312.10,2042863.00,1994351.80,1658108.00,1404371.80,1448118.50,1665052.90]
        lx,rx,ty,by=205,1265,465,805; maxv=2_200_000
        text(d,(210,365),"Consumo mensual (millones de MWh)",25,NAVY,True)
        d.line((300,415,345,415),fill=TEAL,width=8); text(d,(355,415),"ResStock · perfil modelado",25,NAVY,anchor="lm")
        d.line((710,415,755,415),fill=BLUE,width=8); text(d,(765,415),"EIA · ventas residenciales",25,NAVY,anchor="lm")
        for val in (0,500000,1000000,1500000,2000000):
            yy=by-(val/maxv)*(by-ty); d.line((lx,yy,rx,yy),fill=(216,209,191),width=2)
            text(d,(lx-12,yy-14),f"{val/1e6:.1f}",24,NAVY,anchor="rm")
        d.line((lx,ty,lx,by),fill=INK,width=3); d.line((lx,by,rx,by),fill=INK,width=3)
        for values,col in ((res,TEAL),(eia,BLUE)):
            pts=[]
            for i,v in enumerate(values): pts.append((round(lx+i*(rx-lx)/11),round(by-(v/maxv)*(by-ty))))
            d.line(pts,fill=col,width=7,joint="curve")
            for x,y in pts: d.ellipse((x-7,y-7,x+7,y+7),fill=col,outline=CREAM,width=2)
        for i,m in enumerate(months): text(d,(round(lx+i*(rx-lx)/11),842),m,24,NAVY,anchor="mm")
        text(d,(1610,405),"16.81 M MWh",40,INK,True,anchor="mm")
        text(d,(1610,458),"ResStock · categoría seleccionada",24,NAVY,anchor="mm")
        text(d,(1610,645),"19.29 M MWh",40,INK,True,anchor="mm")
        text(d,(1610,698),"EIA · sector residencial completo",24,NAVY,anchor="mm")
        text(d,(1610,870),"87.16%",46,INK,True,anchor="mm")
        text(d,(1610,922),"relación entre totales anuales",24,NAVY,anchor="mm")
        text(d,(1610,970),"Las fuentes cubren poblaciones distintas.",21,INK,True,anchor="mm")
    elif n==6:
        # Captura real del área de resultados; conserva legibles la guía, gráfica y detalle.
        shot=Image.open(HERE/"evidencia/demo-grafica.png").convert("RGB")
        shot=shot.crop((110,55,1270,920)).resize((1190,890),Image.Resampling.LANCZOS)
        im.paste(shot,(45,130)); d=ImageDraw.Draw(im)
        d.rounded_rectangle((1285,205,1865,970),radius=26,fill=CREAM,outline=INK,width=3)
        text(d,(1325,250),"La demo permite:",38,NAVY,True)
        for i,line in enumerate(["Cambiar entre líneas, barras y relación.","Filtrar por estación del año.","Seleccionar un mes y ver sus cifras.","Consultar la tabla y qué significa cada columna."]):
            paragraph(d,(1325,335+i*112),line,490,31,INK,gap=0)
        d.rounded_rectangle((1310,825,1835,950),radius=20,fill=YELLOW,outline=INK,width=3)
        text(d,(1340,855),"Demo local basada en\nla muestra de Colorado.",30,INK,True)
    elif n==7:
        text(d,(95,185),"Siguiente etapa: sumar más años",54,INK,True,True)
        d.rounded_rectangle((1045,285,1860,970),radius=25,fill=CREAM,outline=INK,width=3)
        steps=["Identificar años disponibles en ambas fuentes.","Revisar que periodos y definiciones sean comparables.","Incorporar cada año y repetir los controles.","Explorar tendencias a través del tiempo."]
        y=350
        for i,s in enumerate(steps,1):
            d.ellipse((1090,y,1140,y+50),fill=YELLOW,outline=INK,width=2)
            text(d,(1115,y+25),str(i),28,INK,True,anchor="mm")
            paragraph(d,(1170,y+4),s,625,32,INK,gap=0)
            y+=120
        d.rounded_rectangle((1080,845,1825,940),radius=18,fill=YELLOW,outline=INK,width=3)
        text(d,(1110,867),"La muestra cubre 2018. Otros años son una ampliación futura,\nsi las fuentes ofrecen periodos comparables.",25,INK,True)
    text(d,(1810,1020),f"{n:02d} / 07",23,NAVY,True,anchor="mm")
    return im

def main():
    OUT.mkdir(parents=True,exist_ok=True); pages=[]
    for n in BG:
        im=slide(n); path=OUT/f"diapositiva-{n}.png"
        im.save(path,"PNG",optimize=True,dpi=(160,160)); pages.append(im.convert("RGB")); print(path)
    pdf=HERE/"Consumo_electrico_residencial_demo.pdf"
    pages[0].save(pdf,"PDF",save_all=True,append_images=pages[1:],resolution=160.0)
    print(pdf)

if __name__=="__main__": main()
