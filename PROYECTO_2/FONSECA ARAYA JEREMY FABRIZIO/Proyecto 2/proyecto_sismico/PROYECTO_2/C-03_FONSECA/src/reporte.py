"""Regenera tablas, figuras, ficha, propuesta, resumen y diapositivas con Python."""

import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.analisis import analizar, formato_colones
from src.graficas import (
    figura_arias,
    figura_descuento,
    figura_exploracion,
    figura_movimiento,
    figura_pae,
    figura_recurrencia,
    figura_sensibilidad,
    figura_vpn,
)
from src.limpieza import EXCEL, RUTA_BASE, BaseDatos, leer_base

AZUL = colors.HexColor("#17364a")
VERDE = colors.HexColor("#087e8b")
FUENTE = "Excel P03_C-03_FONSECA.xlsx del docente. Datos simulados."


def estilos() -> dict:
    """Registra fuentes incluidas con Matplotlib y devuelve estilos de documentos."""
    carpeta = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", str(carpeta / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuB", str(carpeta / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVuB", italic="DejaVu", boldItalic="DejaVuB"
    )
    s = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo",
            parent=s["Title"],
            fontName="DejaVuB",
            fontSize=20,
            leading=25,
            textColor=AZUL,
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "sub": ParagraphStyle(
            "sub",
            fontName="DejaVuB",
            fontSize=12,
            leading=16,
            textColor=VERDE,
            spaceBefore=11,
            spaceAfter=7,
        ),
        "texto": ParagraphStyle(
            "texto", fontName="DejaVu", fontSize=11, leading=15.5, spaceAfter=8
        ),
        "pequeno": ParagraphStyle(
            "pequeno", fontName="DejaVu", fontSize=9, leading=12, spaceAfter=6
        ),
    }


def pie(c: canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Añade identificación y número de página a los documentos del estudiante."""
    c.setFont("DejaVu", 8)
    c.setFillColor(AZUL)
    c.drawString(
        42, 27, "UCR · MA-0321 · Jeremy Fabrizio Fonseca Araya · C23005 · Borrador para revisión"
    )
    c.drawRightString(570, 27, str(doc.page))


def documento(ruta: Path, bloques: list, s: dict) -> None:
    """Construye un PDF tamaño carta a partir de bloques con salto de página explícito."""
    contenido = []
    for tipo, texto in bloques:
        if tipo == "salto":
            contenido.append(PageBreak())
        elif tipo == "imagen":
            contenido.append(Image(str(texto), width=520, height=243, kind="proportional"))
        elif tipo == "tabla":
            tabla = Table(
                [[Paragraph(escape(str(v)), s["pequeno"]) for v in fila] for fila in texto],
                hAlign="LEFT",
                repeatRows=1,
            )
            tabla.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f1f2")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.7, VERDE),
                    ]
                )
            )
            contenido.extend([tabla, Spacer(1, 8)])
        else:
            contenido.append(Paragraph(texto, s[tipo]))
    doc = SimpleDocTemplate(
        str(ruta), pagesize=letter, rightMargin=42, leftMargin=42, topMargin=38, bottomMargin=44
    )
    doc.build(contenido, onFirstPage=pie, onLaterPages=pie)


def exportar_datos(base: BaseDatos, r: dict, salida: Path) -> dict:
    """Exporta tablas numéricas sin redondear y un resumen JSON con hash de la fuente."""
    for nombre, tabla in [
        ("escenarios", r["escenarios"]),
        ("movimiento", r["series"]),
        ("verificacion", r["verificacion"]),
        ("sensibilidad", r["sensibilidad"]),
        ("prueba_seno", r["seno"]),
        ("incidencias", base.incidencias),
    ]:
        tabla.to_csv(salida / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    catalogo = base.hojas["Catalogo_sismos"]
    catalogo.groupby(catalogo.fecha_hora.dt.year).size().rename("sismos").to_csv(
        salida / "conteos_anuales.csv"
    )
    catalogo.select_dtypes(include="number").describe().to_csv(salida / "estadisticas_catalogo.csv")
    catalogo[["magnitud_Mw", "profundidad_km", "distancia_sitio_km"]].corr().to_csv(
        salida / "correlaciones.csv"
    )
    resumen = {
        k: r[k]
        for k in ["b", "r", "H", "lambda3", "prob6_50", "prob7_50", "indicadores", "recomendacion"]
    }
    resumen["sha256_excel"] = hashlib.sha256(EXCEL.read_bytes()).hexdigest()
    resumen["anos_catalogo"] = base.anos_catalogo
    (salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    dic = base.hojas["Diccionario"]
    texto = "# Diccionario de datos\n\nTranscripción automática de la hoja Diccionario.\n\n"
    texto += "| Hoja | Columna | Significado | Unidad |\n|---|---|---|---|\n"
    texto += "\n".join(
        "| " + " | ".join(str(x) for x in fila) + " |"
        for fila in dic.itertuples(index=False, name=None)
    )
    (RUTA_BASE / "docs" / "DICCIONARIO.md").write_text(texto + "\n", encoding="utf-8")
    # Variante explícita: beneficios desde la terminación de la obra, sin cambiar el caso principal.
    demora = r["escenarios"].copy()
    H, tasa = r["H"], r["r"]
    L = np.minimum(demora.plazo_meses / 12, H)
    factor = H - L if tasa == 0 else (np.exp(-tasa * L) - np.exp(-tasa * H)) / tasa
    demora["vpn_beneficio_tras_obra_colones"] = (
        -demora.costo_colones + demora.ahorro_anual_colones * factor
    )
    demora.to_csv(salida / "efecto_plazo_obra.csv", index=False, encoding="utf-8-sig")
    return resumen


def exportar_figuras(base: BaseDatos, r: dict, salida: Path) -> None:
    """Guarda las mismas figuras usadas por la app como PNG reproducibles."""
    figuras = {
        "exploracion": figura_exploracion(base),
        "recurrencia": figura_recurrencia(base, r),
        "arias": figura_arias(r),
        "pae": figura_pae(base, r),
        "vpn": figura_vpn(r),
        "descuento": figura_descuento(r),
        "sensibilidad": figura_sensibilidad(r),
    }
    for variable in ["aceleracion", "velocidad", "desplazamiento"]:
        figuras[variable] = figura_movimiento(r, variable)
    for nombre, fig in figuras.items():
        fig.savefig(salida / f"{nombre}.png", dpi=160)
        plt.close(fig)


def textos(base: BaseDatos, r: dict) -> dict:
    """Compone textos dinámicos desde resultados para evitar cifras escritas a mano."""
    rec, i = r["recomendacion"], r["indicadores"]
    tabla = r["escenarios"].set_index("escenario")
    formato = formato_colones
    return {
        "decision": f"El modelo favorece {rec['escenario']}",
        "recomendacion": f"Para el caso base, se recomienda {rec['escenario']}, con inversión de {formato(rec['costo_colones'])}, "
        f"pérdida anual evitada de {formato(rec['ahorro_anual_colones'])} y VPN de {formato(rec['vpn_colones'])} "
        f"a {r['H']:g} años. El plazo de obra indicado es {rec['plazo_meses']:g} meses.",
        "datos": f"Se analizan {len(base.hojas['Catalogo_sismos'])} sismos en {base.anos_catalogo} años y "
        f"{len(base.hojas['Acelerograma'])} muestras de aceleración. Hay tres aceleraciones faltantes y seis profundidades faltantes.",
        "riesgo": f"λ₃={r['lambda3']:.6f} eventos/año; b={r['b']:.6f}. La probabilidad regional modelada en 50 años es "
        f"{100 * r['prob6_50']:.2f} % para M≥6 y {100 * r['prob7_50']:.2f} % para M≥7.",
        "movimiento": f"PGA={i['PGA_cm_s2']:.3f} cm/s²; PGV={i['PGV_cm_s']:.3f} cm/s; PGD={i['PGD_cm']:.3f} cm. "
        f"Arias={i['IA_m_s']:.6f} m/s. Duración 5–95 %={i['duracion_s']:.3f} s.",
        "sesgo": f"La media previa es {i['linea_base_cm_s2']:.6f} cm/s². El desplazamiento final pasa de "
        f"{i['desplazamiento_final_sin_corregir_cm']:.3f} cm sin corregir a {i['desplazamiento_final_cm']:.3f} cm corregido.",
        "economia": f"La pérdida anual actual es {formato(tabla.loc['Sin refuerzo', 'pae_colones_ano'])}. "
        f"Con A queda en {formato(tabla.loc['Opción A', 'pae_colones_ano'])}; con B, "
        f"en {formato(tabla.loc['Opción B', 'pae_colones_ano'])}. La reducción adicional de B no compensa "
        f"su costo en el caso base: su VPN es {formato(tabla.loc['Opción B', 'vpn_colones'])}.",
    }


def generar_ficha(base: BaseDatos, r: dict, salida: Path, s: dict) -> None:
    """Genera cinco páginas de ficha técnica y una declaración de autoría sin firmar."""
    t = textos(base, r)
    b = [
        ("titulo", "Amenaza sísmica y refuerzo del Hospital de Golfito"),
        (
            "texto",
            "Ficha técnica de modelación · Proyecto Aplicado 2, tema 3<br/>Jeremy Fabrizio Fonseca Araya · C23005 · C-03<br/>"
            "Universidad de Costa Rica, Sede del Sur · MA-0321 · II ciclo 2026<br/>Docente: Francisco Campos Sandi",
        ),
        ("sub", "1. Problema y decisión"),
        (
            "texto",
            "El caso supone un pabellón antiguo vulnerable y fondos para una de dos propuestas. "
            "La persona usuaria es el área de ingeniería del Hospital Manuel Mora Valverde. "
            "Se busca decidir si conviene reforzar y cuál alternativa tiene el mayor valor presente neto de pérdidas evitadas.",
        ),
        ("texto", t["recomendacion"]),
        ("sub", "Datos, unidades y tratamiento"),
        (
            "texto",
            t["datos"]
            + " El Excel original permanece intacto. Se lee completo con pandas.read_excel. "
            "Los lugares son reales y los datos simulados por el docente (Campos Sandi, 2026).",
        ),
        (
            "texto",
            "Se interpolan linealmente los tres huecos internos del acelerograma. Las seis profundidades permanecen "
            "vacías: no intervienen en la estimación de b ni de la frecuencia. IQR señala 23 magnitudes y 18 profundidades, "
            "que se conservan porque no existe evidencia de error. Los picos de aceleración se conservan.",
        ),
        (
            "texto",
            "Los conteos varían entre 10 y 30 sismos por año, sin convertir esa variación por sí sola en una tendencia. "
            "La media de magnitudes es 3,33616 Mw y el máximo observado 6,0. Los gráficos y correlaciones quedan en el cuaderno. "
            "Se supone cobertura completa de 1996–2025. Distancias y profundidades se exploran, pero no corrigen el modelo asignado.",
        ),
        (
            "pequeno",
            "Unidades: aceleración cm/s²; velocidad cm/s; desplazamiento cm; Arias m/s; recurrencia eventos/año; daño fraccionario; PAE colones/año; VPN colones.",
        ),
        ("salto", ""),
        ("titulo", "Fundamento y construcción del modelo"),
        ("sub", "2. La media de una densidad determina b"),
        (
            "texto",
            "Sea β=b ln(10), m_c=2,95 y f(m)=βe<super>−β(m−m_c)</super> para m≥m_c. "
            "Esta densidad exponencial integra uno. Con u=m−m_c, su media se separa en m_c más la integral de uβe<super>−βu</super>.",
        ),
        (
            "texto",
            "Por partes: ∫₀∞uβe<super>−βu</super>du = [−ue<super>−βu</super>]₀∞ + ∫₀∞e<super>−βu</super>du = 1/β. "
            "Entonces E[M]=m_c+1/β. Al igualarla con la media muestral se obtiene b=log₁₀(e)/(media−2,95). "
            "El 0,05 corrige medio intervalo de redondeo de las magnitudes de 0,1 Mw, conforme al enunciado.",
        ),
        (
            "texto",
            "La recurrencia se ancla en λ₃=N/años: λ(m)=λ₃10<super>−b(m−3)</super>. "
            "Con eventos independientes y tasa estacionaria, Poisson da P(N≥1)=1−e<super>−λ(m)T</super>. "
            + t["riesgo"],
        ),
        ("sub", "3. El teorema fundamental conecta aceleración y movimiento"),
        (
            "texto",
            "Como a=v′ y v=x′, con v(0)=x(0)=0 se tiene v(t)=∫₀ᵗa(u)du y x(t)=∫₀ᵗv(u)du "
            "(OpenStax, s. f.-a). El trapecio acumulado suma Δt(y_i+y_(i−1))/2. Conserva el signo del movimiento.",
        ),
        (
            "texto",
            "Se resta la aceleración media en los primeros segundos indicados por Evento, usando t&lt;t₀. "
            "Un sesgo constante c genera error ct en velocidad y ct²/2 en desplazamiento. Una corrección simple no garantiza "
            "eliminar toda deriva instrumental (Boore, 1999). " + t["sesgo"],
        ),
        (
            "texto",
            "PGA, PGV y PGD son máximos absolutos. IA=π/(2g)∫a_m²dt, con a_m=a/100 y g=9,80665 m/s². "
            "La unidad resultante es m/s. La duración significativa es t95−t5 de la integral acumulada de a². "
            + t["movimiento"],
        ),
        ("salto", ""),
        ("titulo", "Pérdidas y decisión económica"),
        ("sub", "4. La integral pondera el daño por su frecuencia"),
        (
            "texto",
            "La densidad de eventos es ν(m)=−λ′(m)=b ln(10)λ(m). Tiene unidades de eventos/(año·Mw), "
            "y no es una densidad normalizada a uno. Se usa PAE=V∫₅⁸D(m)ν(m)dm. "
            "D es el porcentaje de daño dividido entre 100; V es el valor de reposición del Excel.",
        ),
        (
            "texto",
            "Se construye D como rectas entre los puntos entregados. Se utiliza Simpson propio con 16 subdivisiones "
            "por tramo: h/3[y₀+y_n+4Σy_impares+2Σy_pares]. El paso es uniforme y el número de intervalos par "
            "(OpenStax, s. f.-b). La refinación no añade observaciones ni resuelve la incertidumbre del daño.",
        ),
        (
            "texto",
            "Verificación analítica: en un tramo, u=m−m_i, D=d_i+s_i u, β=b ln(10), h=m_(i+1)−m_i. "
            "Por sustitución y partes, PAE_i/V=λ_i{d_i(1−e<super>−βh</super>)+s_i[(1−e<super>−βh</super>)/β−he<super>−βh</super>]}. "
            "Se suman los tramos y se comparan con los métodos numéricos.",
        ),
        ("sub", "5. Valor presente neto"),
        (
            "texto",
            "ΔPAE=PAE_actual−PAE_refuerzo. Con ahorro anual constante, VPN=−C+∫₀ᴴΔPAE·e<super>−rt</super>dt. "
            "La sustitución u=−rt da VPN=−C+ΔPAE(1−e<super>−rH</super>)/r. Si r=0, el límite es −C+ΔPAE·H. "
            "El porcentaje del Excel se divide entre 100 y se interpreta como tasa continua.",
        ),
        (
            "texto",
            "El costo, horizonte, descuento y plazo provienen del Excel. Se incluye no invertir, con VPN=0. "
            "La fórmula principal considera ahorro desde t=0, como el enunciado. Se calcula además una variante con ahorro "
            "desde el fin de obra en efecto_plazo_obra.csv. " + t["economia"],
        ),
        (
            "tabla",
            [["Alternativa", "Inversión (₡)", "PAE (₡/año)", "VPN (₡)"]]
            + [
                [
                    fila.escenario,
                    formato_colones(fila.costo_colones),
                    formato_colones(fila.pae_colones_ano),
                    formato_colones(fila.vpn_colones),
                ]
                for _, fila in r["escenarios"].iterrows()
            ],
        ),
        ("salto", ""),
        ("titulo", "Resultados, verificación y sensibilidad"),
        ("imagen", salida / "pae.png"),
        (
            "texto",
            "El área de cada curva es su PAE. Los eventos moderados pueden aportar bastante porque su frecuencia "
            "compensa un daño individual menor. El registro de un único sismo no se usa para estimar la recurrencia regional.",
        ),
        ("sub", "6. Qué se verificó"),
        (
            "texto",
            "La doble integración propia de sen(t) reproduce 1−cos(t) y t−sen(t), con errores de norma máxima "
            f"de {r['seno'].error_relativo_max_pct.iloc[0]:.6f} % y {r['seno'].error_relativo_max_pct.iloc[1]:.6f} %, menores a 0,5 %. "
            "Las pruebas también comprueban unidades, entradas inválidas, balances, daño constante y descuento cero.",
        ),
        (
            "texto",
            "Error relativo=100|resultado−referencia|/|referencia|. Simpson refinado coincide con la integral "
            "exacta del daño lineal con error menor a 0,00001 %. El Simpson de la tabla original difiere aproximadamente 3 %. "
            "En el acelerograma, trapecio y Simpson discrepan 0,0185 % para Arias y 11,90 % para velocidad final, "
            "equivalente a solo 0,05545 cm/s. Esa referencia pequeña amplifica el porcentaje por cancelación.",
        ),
        ("sub", "7. Condiciones de la recomendación"),
        (
            "texto",
            "Se varía b±0,1 y descuento ±2 puntos porcentuales. Con b base, A sigue siendo preferida en las "
            "tres tasas. Con b+0,1, ninguna inversión tiene VPN positivo. Este resultado obliga a revisar la recurrencia "
            "antes de decidir. La variación de b afecta más el VPN de A que el rango de descuento explorado.",
        ),
        ("salto", ""),
        ("titulo", "Implementación, límites y referencias"),
        ("sub", "8. Implementación y recomendación aplicable"),
        (
            "texto",
            "La clase BaseDatos conserva tablas y criterios de limpieza. limpieza.py valida e interpola; "
            "numericos.py implementa las reglas; modelo.py calcula las integrales; escenarios.py compara opciones. "
            "La app Streamlit carga otra base, utiliza caché, permite tres controles y descarga CSV. "
            "python -m src.reporte regenera tablas, figuras y documentos. analisis.ipynb conserva la ejecución.",
        ),
        (
            "texto",
            t["recomendacion"]
            + " El área de ingeniería debería verificar curvas de daño y cotizaciones, "
            "confirmar recursos y planificar continuidad del servicio antes de contratar. El seguimiento debe registrar "
            "costo real, plazo y cumplimiento técnico. La pérdida esperada se reestima con nueva evidencia, "
            "no se valida esperando que un año sin terremotos demuestre el ahorro.",
        ),
        (
            "texto",
            "Límites: datos didácticos; catálogo supuesto completo y estacionario; extrapolación hasta M≥7; "
            "daño simplificado sin distancia ni respuesta del edificio; ausencia de lesiones, interrupción hospitalaria y costos "
            "indirectos. Se necesitarían registros instrumentales, estudio estructural y costos reales para una decisión efectiva.",
        ),
        (
            "pequeno",
            "Estado de entrega: código y materiales locales preparados. Fork, historial semanal, CI en GitHub, "
            "enlace público y pull request deben completarse y verificarse con la cuenta del estudiante.",
        ),
        ("sub", "Referencias"),
        (
            "pequeno",
            "Campos Sandi, F. (2026). <i>Proyecto aplicado 2: Modelación con integración para resolver problemas de decisión. Proyecto 3, C-03</i> [Enunciado y datos simulados]. Universidad de Costa Rica.",
        ),
        (
            "pequeno",
            "Boore, D. M. (1999). <i>Effect of baseline corrections on response spectra for two recordings of the 1999 Chi-Chi, Taiwan, earthquake</i> (Open-File Report 99-545). U.S. Geological Survey. https://pubs.usgs.gov/of/1999/0545/",
        ),
        (
            "pequeno",
            "OpenStax. (s. f.-a). 5.3 The fundamental theorem of calculus. En <i>Calculus volume 1</i>. https://openstax.org/books/calculus-volume-1/pages/5-3-the-fundamental-theorem-of-calculus",
        ),
        (
            "pequeno",
            "OpenStax. (s. f.-b). 3.6 Numerical integration. En <i>Calculus volume 2</i>. https://openstax.org/books/calculus-volume-2/pages/3-6-numerical-integration",
        ),
        ("salto", ""),
        ("titulo", "Declaración de autoría para revisión"),
        (
            "texto",
            "El enunciado exige adjuntar una declaración. El siguiente texto se presenta sin firma para que "
            "el estudiante lo revise y complete únicamente cuando refleje su trabajo y las reglas del curso.",
        ),
        (
            "texto",
            "Declaro que este proyecto fue elaborado de forma individual con la base de datos que me fue asignada, "
            "que todo tratamiento de los datos está documentado y que el código y las visualizaciones son de mi autoría "
            "o están debidamente citados.",
        ),
        ("sub", "Asistencia utilizada"),
        (
            "texto",
            "La implementación inicial, las pruebas y los borradores de documentos se prepararon con asistencia "
            "de ChatGPT/Codex (OpenAI, 2026). El estudiante debe revisar los procedimientos, efectuar sus propios ajustes, "
            "registrarlos en su bitácora y explicar el modelo en la defensa. No se ha firmado esta declaración ni simulado "
            "un historial de desarrollo.",
        ),
        (
            "texto",
            "Nombre: Jeremy Fabrizio Fonseca Araya<br/>Carné: C23005<br/><br/>Firma: __________________________<br/><br/>Fecha: __________________________",
        ),
        (
            "pequeno",
            "OpenAI. (2026). <i>ChatGPT/Codex</i> [Asistente de inteligencia artificial]. https://chatgpt.com/",
        ),
    ]
    documento(RUTA_BASE / "informe" / "ficha_tecnica.pdf", b, s)


def generar_breves(base: BaseDatos, r: dict, s: dict) -> None:
    """Genera propuesta inicial y resumen ejecutivo, una página cada uno."""
    t = textos(base, r)
    resumen = [
        ("titulo", "Resumen ejecutivo"),
        (
            "texto",
            "Para: área de ingeniería del Hospital Manuel Mora Valverde, Golfito<br/>Caso académico con datos simulados · Jeremy Fabrizio Fonseca Araya, C23005",
        ),
        ("sub", t["decision"]),
        ("texto", t["recomendacion"]),
        ("texto", t["economia"]),
        ("sub", "Qué respalda esta decisión"),
        (
            "texto",
            "Se compara la situación actual con encamisado de columnas y vigas (A), y muros de corte "
            "con refuerzo de fundaciones (B). La pérdida anual integra el daño de cada magnitud multiplicado "
            "por su frecuencia. El ahorro futuro se descuenta y se compara con la inversión. "
            + t["riesgo"],
        ),
        ("sub", "Cuándo puede cambiar"),
        (
            "texto",
            "La opción A conserva el mayor VPN al variar el descuento ±2 puntos porcentuales con b base. "
            "Al aumentar b en 0,1, ambas inversiones tienen VPN negativo. Antes de financiar, se debe comprobar "
            "la recurrencia y las curvas de daño. El modelo no representa pérdidas humanas ni interrupción del servicio.",
        ),
        ("sub", "Implementación y seguimiento"),
        (
            "texto",
            "El área de ingeniería debe validar el diagnóstico del pabellón y las cotizaciones, reservar el presupuesto "
            "y planificar continuidad hospitalaria durante el plazo de obra. Se propone registrar costo real, avance, "
            "cumplimiento técnico y nuevas estimaciones de pérdida. El ahorro es esperado, no una garantía anual.",
        ),
        (
            "pequeno",
            "Fuente: Campos Sandi, F. (2026). Proyecto aplicado 2, C-03, y Excel individual. UCR. "
            "Cálculos propios del programa, con asistencia de ChatGPT/Codex declarada en la ficha. "
            "Datos simulados: no constituyen un dictamen estructural del hospital.",
        ),
    ]
    propuesta = [
        ("titulo", "Propuesta de modelación"),
        (
            "texto",
            "Semana 10 · Proyecto Aplicado 2, tema 3 · C-03<br/>Jeremy Fabrizio Fonseca Araya · C23005<br/>MA-0321 · Francisco Campos Sandi · UCR, Sede del Sur",
        ),
        ("sub", "Problema y persona usuaria"),
        (
            "texto",
            "El área de ingeniería del Hospital Manuel Mora Valverde necesita comparar dos propuestas de "
            "reforzamiento de un pabellón vulnerable. El caso dispone de fondos para una opción y requiere justificar "
            "la inversión considerando las pérdidas evitadas y el costo.",
        ),
        ("sub", "Pregunta y criterio de éxito"),
        (
            "texto",
            "¿Conviene reforzar, con cuál opción y cuánto daño económico anual se evita por colón invertido? "
            "Se elegirá el mayor VPN entre no invertir, A y B, usando el horizonte y descuento del Excel. "
            "Se informará la probabilidad de al menos un sismo M≥7 en 50 años.",
        ),
        ("sub", "Datos y procedimientos"),
        (
            "texto",
            t["datos"] + " Se documentará el tratamiento de faltantes y atípicos, se estimará b, "
            "se integrará la aceleración corregida para obtener velocidad y desplazamiento, y se calcularán "
            "Arias y duración significativa. Simpson propio permitirá integrar pérdidas y comparar el VPN.",
        ),
        ("sub", "Verificación y producto"),
        (
            "texto",
            "Se contrastarán reglas numéricas y fórmulas exactas. La doble integración de sen(t) deberá "
            "reproducir las soluciones conocidas con error menor a 0,5 %. Se analizarán b±0,1 y el descuento. "
            "El producto será una aplicación Streamlit con tres alternativas, tablas descargables y explicación "
            "del modelo, junto con cuaderno, pruebas, ficha técnica y exposición.",
        ),
        (
            "pequeno",
            "Alcance: estudio académico con datos simulados. Se documentarán las hipótesis de completitud, "
            "estacionariedad, independencia, daño por magnitud y ahorro constante. La propuesta debe revisarse con el docente.",
        ),
    ]
    documento(RUTA_BASE / "informe" / "resumen_ejecutivo.pdf", resumen, s)
    documento(RUTA_BASE / "informe" / "propuesta.pdf", propuesta, s)


def generar_diapositivas(base: BaseDatos, r: dict, salida: Path) -> None:
    """Produce 13 diapositivas PDF con una idea central y un guion de 13 minutos."""
    t = textos(base, r)
    slides = [
        (
            t["decision"],
            "Hospital Manuel Mora Valverde, Golfito. Área de ingeniería.\n"
            "Jeremy Fabrizio Fonseca Araya · C23005\n" + t["recomendacion"],
            "vpn",
            "Presentar el caso, la institución y la recomendación. Aclarar que son datos simulados.",
            60,
        ),
        (
            "El VPN compara beneficios y costo de inversión",
            "Pregunta: ¿conviene reforzar y cuál opción maximiza el VPN?\n"
            "Alternativas: situación actual, encamisado (A), muros de corte y fundaciones (B).\n"
            "El escenario sin inversión tiene VPN=0 y también participa en la decisión.",
            None,
            "Explicar al cliente qué se decide y por qué no basta con elegir el menor daño.",
            50,
        ),
        (
            "La base se conserva y los faltantes se documentan",
            t["datos"] + "\nSe interpolan tres aceleraciones. "
            "Las profundidades faltantes se conservan. Los valores IQR y los picos no se eliminan automáticamente.",
            "exploracion",
            "Explicar la limpieza y la variación anual. La cola de eventos grandes es parte del fenómeno.",
            60,
        ),
        (
            "La media de magnitudes permite estimar b",
            "β=b ln(10), m_c=2,95\nf(m)=β exp[−β(m−m_c)]\n"
            "E[M]=m_c+∫₀∞uβe^(−βu)du=m_c+1/β\n"
            "Por partes: ∫₀∞uβe^(−βu)du=1/β\n"
            f"b=log₁₀(e)/(media−2,95)={r['b']:.6f}",
            None,
            "Describir sustitución y partes, y explicar la corrección de medio intervalo de redondeo.",
            75,
        ),
        (
            "La recurrencia disminuye con la magnitud",
            t["riesgo"] + "\nλ(m)=λ₃ 10^[−b(m−3)]\n"
            "P(N≥1)=1−exp[−λ(m)T]\nLa probabilidad M≥7 extrapola más allá del máximo del catálogo.",
            "recurrencia",
            "Explicar independencia y tasa estacionaria. No se predice una fecha exacta.",
            60,
        ),
        (
            "Corregir el sesgo evita una deriva acumulada",
            "Teorema fundamental: a=v′ y v=x′.\n"
            "v(t)=∫₀ᵗa(u)du; x(t)=∫₀ᵗv(u)du\n"
            "Se supone v(0)=x(0)=0.\nUn sesgo c añade ct a v y ct²/2 a x.\n" + t["sesgo"],
            "desplazamiento",
            "Mostrar el cambio y explicar que no se cambia el dato original: se crea una serie corregida.",
            65,
        ),
        (
            "Arias acumula la aceleración al cuadrado",
            "IA=π/(2g)∫a_m²dt; a_m=a/100\nCon a_m en m/s², IA queda en m/s.\n" + t["movimiento"],
            "arias",
            "Definir PGA, PGV, PGD y el intervalo 5–95 %. Arias no se mide en joules.",
            50,
        ),
        (
            "El área ponderada por frecuencia es la PAE",
            "ν(m)=−λ′(m)=b ln(10)λ(m)\n"
            "PAE=V∫₅⁸D(m)ν(m)dm\nD es fracción, no porcentaje.\n"
            "Simpson propio sobre daño lineal por tramos.\nLa integral resulta en colones/año.",
            "pae",
            "Señalar el área. Explicar por qué los sismos moderados también contribuyen.",
            65,
        ),
        (
            "El descuento convierte el ahorro futuro a valor actual",
            "VPN=−C+∫₀ᴴΔPAE exp(−rt)dt\n"
            "Por sustitución: VPN=−C+ΔPAE(1−e^(−rH))/r.\n"
            "Si r=0: VPN=−C+ΔPAE·H.\nSe supone ahorro constante y se compara con Simpson.",
            "descuento",
            "Mostrar la antiderivada. El área es beneficio presente y todavía debe restarse el costo.",
            60,
        ),
        (
            "Las soluciones conocidas comprueban el programa",
            "Para a=sen(t): v=1−cos(t), x=t−sen(t).\n"
            f"Errores máximos: {r['seno'].error_relativo_max_pct.iloc[0]:.6f} % y {r['seno'].error_relativo_max_pct.iloc[1]:.6f} %.\n"
            "En la señal real, trapecio y Simpson difieren: no conocemos el error físico.\n"
            "Demo: cambiar b y descuento, descargar CSV y mostrar pytest.",
            None,
            "Dedicar parte de esta lámina a la app y al código numericos.py. Mostrar las pruebas sin afirmar CI remoto todavía.",
            120,
        ),
        (
            "La decisión cambia al aumentar b en 0,1",
            "Con b base, A conserva el mayor VPN para descuento ±2 puntos.\n"
            "Con b+0,1, las dos inversiones tienen VPN negativo.\n"
            "La recomendación depende de la recurrencia asumida.\nLa sensibilidad no es un intervalo de confianza.",
            "sensibilidad",
            "Explicar por qué un b mayor reduce eventos grandes y el beneficio del refuerzo.",
            65,
        ),
        (
            "Referencias del modelo y los métodos",
            "Campos Sandi, F. (2026). Proyecto aplicado 2, C-03. UCR.\n"
            "Boore, D. M. (1999). Effect of baseline corrections… USGS OFR 99-545.\n"
            "OpenStax. (s. f.-a). The fundamental theorem of calculus. Calculus 1, §5.3.\n"
            "OpenStax. (s. f.-b). Numerical integration. Calculus 2, §3.6.\n"
            "Referencias completas y enlaces en la ficha y docs/REFERENCIAS.md.",
            None,
            "Identificar las fuentes del enunciado, cálculo y corrección de línea base. Asistencia declarada en la ficha.",
            20,
        ),
        (
            t["decision"] + ", sujeta a validar los supuestos",
            t["recomendacion"] + "\n"
            "Ingeniería debe revisar diagnóstico, cotizaciones y continuidad del servicio.\n"
            "Seguimiento: costo, plazo, cumplimiento técnico y nueva estimación de pérdidas.\n"
            "Datos simulados, daño simplificado y pérdidas indirectas fuera del modelo.",
            None,
            "Cerrar repitiendo qué se propone, quién debe verificarlo y cuándo deja de convenir.",
            65,
        ),
    ]
    c = canvas.Canvas(str(RUTA_BASE / "presentacion" / "diapositivas.pdf"), pagesize=(960, 540))
    guion = [
        "# Guion de exposición\n",
        f"Duración orientativa: {sum(x[4] for x in slides) / 60:.1f} minutos.\n",
    ]
    for numero, (titulo, cuerpo, figura, nota, segundos) in enumerate(slides, 1):
        c.setFillColor(colors.white)
        c.rect(0, 0, 960, 540, fill=True, stroke=False)
        titulo_estilo = ParagraphStyle(
            "slide_title", fontName="DejaVuB", fontSize=26, leading=32, textColor=AZUL
        )
        p = Paragraph(escape(titulo), titulo_estilo)
        _, alto = p.wrap(864, 90)
        p.drawOn(c, 48, 500 - alto)
        cuerpo_estilo = ParagraphStyle(
            "slide_body",
            fontName="DejaVu",
            fontSize=17 if figura else 20,
            leading=25 if figura else 31,
            textColor=AZUL,
        )
        p = Paragraph(escape(cuerpo).replace("\n", "<br/><br/>"), cuerpo_estilo)
        ancho = 360 if figura else 830
        _, altura = p.wrap(ancho, 365)
        if altura > 370:
            raise ValueError(f"Texto demasiado largo en diapositiva {numero}: {altura}")
        p.drawOn(c, 48, 398 - altura)
        if figura:
            c.drawImage(
                str(salida / f"{figura}.png"),
                420,
                112,
                width=500,
                height=260,
                preserveAspectRatio=True,
                anchor="c",
            )
        c.setFont("DejaVu", 8)
        c.setFillColor(colors.HexColor("#566775"))
        c.drawString(48, 30, FUENTE + " Fórmulas: enunciado y fuentes de lámina 12.")
        c.drawRightString(915, 30, f"{numero}/13")
        c.showPage()
        guion.extend([f"\n## {numero}. {titulo} ({segundos} s)\n", nota + "\n"])
    c.save()
    guion.append(
        "\n## Preparación para las preguntas\nLeé MATEMATICA.md y explicá: por qué el sesgo produce t², "
        "cómo se obtiene b desde la media, qué unidades tiene cada integral, por qué se compara con no invertir "
        "y qué supuesto cambia la decisión. Repasá el código de cada fórmula antes de exponer.\n"
    )
    (RUTA_BASE / "docs" / "GUION_DEFENSA.md").write_text("\n".join(guion), encoding="utf-8")


def main() -> None:
    """Lee el Excel y regenera resultados y documentos con un solo comando."""
    salida = RUTA_BASE / "resultados"
    for carpeta in [salida, RUTA_BASE / "informe", RUTA_BASE / "presentacion", RUTA_BASE / "docs"]:
        carpeta.mkdir(parents=True, exist_ok=True)
    base = leer_base()
    r = analizar(base)
    exportar_datos(base, r, salida)
    exportar_figuras(base, r, salida)
    s = estilos()
    generar_ficha(base, r, salida, s)
    generar_breves(base, r, s)
    generar_diapositivas(base, r, salida)
    print("Regeneradas tablas, figuras, ficha, resumen, propuesta y 13 diapositivas.")


if __name__ == "__main__":
    main()
