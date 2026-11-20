"""Genera la ficha técnica, el resumen ejecutivo y las diapositivas en PDF.

Uso:  python -m src.documentos   (ejecuta antes src.reporte para tener las figuras)

Todas las cifras se toman de las tablas calculadas, no se escriben a mano.
"""

# ---------------------------------------------------------------------------
# Imports, rutas y constantes generales
# ---------------------------------------------------------------------------
# Librerías (reportlab para la ficha y el resumen, matplotlib para las diapositivas),
# carpetas de salida, autor, curso y la lista de referencias en formato APA.

from __future__ import annotations

import io
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import matplotlib

# "Agg" dibuja sin abrir ventanas; por eso los imports siguientes llevan noqa: E402.
matplotlib.use("Agg")

import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src import reporte  # noqa: E402
from src.config import COBERTURA_PRUDENTE, DIR_FIGURAS, FUENTE, GRUPOS, RAIZ  # noqa: E402
from src.escenarios import hora_texto  # noqa: E402
from src.graficos import COLORES  # noqa: E402
from src.pipeline import AnalisisCafeina  # noqa: E402

# Carpetas de salida y datos que se repiten en portadas y pies de página.
DIR_INFORME = RAIZ / "informe"
DIR_PRESENTACION = RAIZ / "presentacion"
AUTOR = "Kendall Fabricio Villalobos Villalta"
CARNE = "C38486"
URL_APP = "https://guia-cafeina-production.up.railway.app"
CURSO = "MA-0321 Cálculo Diferencial e Integral · UCR Sede del Sur (Golfito) · II Ciclo 2026"

# Referencias citadas; las etiquetas <i> son cursiva de reportlab (en las diapositivas se quitan).
REFERENCIAS = [
    "Abernethy, D. R., & Todd, E. L. (1985). Impairment of caffeine clearance by chronic use of "
    "low-dose oestrogen-containing oral contraceptives. <i>European Journal of Clinical "
    "Pharmacology, 28</i>(4), 425–428.",
    "Burden, R. L., Faires, J. D., & Burden, A. M. (2017). <i>Análisis numérico</i> (10.ª ed.). "
    "Cengage Learning.",
    "Drake, C., Roehrs, T., Shambroom, J., & Roth, T. (2013). Caffeine effects on sleep taken 0, "
    "3, or 6 hours before going to bed. <i>Journal of Clinical Sleep Medicine, 9</i>(11), "
    "1195–1200. https://doi.org/10.5664/jcsm.3170",
    "EFSA Panel on Dietetic Products, Nutrition and Allergies. (2015). Scientific opinion on the "
    "safety of caffeine. <i>EFSA Journal, 13</i>(5), 4102. https://doi.org/10.2903/j.efsa.2015.4102",
    "Fredholm, B. B., Bättig, K., Holmén, J., Nehlig, A., & Zvartau, E. E. (1999). Actions of "
    "caffeine in the brain with special reference to factors that contribute to its widespread "
    "use. <i>Pharmacological Reviews, 51</i>(1), 83–133.",
    "Institute of Medicine. (2001). <i>Caffeine for the sustainment of mental task performance: "
    "Formulations for military operations</i>. National Academies Press. "
    "https://doi.org/10.17226/10219",
    "Nehlig, A. (2018). Interindividual differences in caffeine metabolism and factors driving "
    "caffeine consumption. <i>Pharmacological Reviews, 70</i>(2), 384–411. "
    "https://doi.org/10.1124/pr.117.014407",
    "Rowland, M., & Tozer, T. N. (2011). <i>Clinical pharmacokinetics and pharmacodynamics: "
    "Concepts and applications</i> (4th ed.). Lippincott Williams &amp; Wilkins.",
    "Stewart, J. (2018). <i>Cálculo de una variable: Trascendentes tempranas</i> (8.ª ed.). "
    "Cengage Learning.",
]


# ---------------------------------------------------------------------------
# Datos compartidos: cifras clave y formato de números
# ---------------------------------------------------------------------------
# La clase Cifras reúne las tablas calculadas que citan los tres documentos;
# num y sci escriben los números con coma decimal y en notación científica.


@dataclass
class Cifras:
    """Cifras del análisis que se citan en los documentos (con unidades en el nombre)."""

    a: AnalisisCafeina

    def __post_init__(self) -> None:
        """Toma las tablas del análisis y las guarda con nombres cortos (indexadas por grupo)."""
        t = self.a.tablas
        self.p = self.a.param
        self.res = self.a.clasificados
        self.guia = t["guia_consumo"].set_index("grupo")
        self.prudente = t["guia_consumo_prudente"].set_index("grupo")
        self.ajustado = t["planes_optimizados"].set_index("grupo")
        self.fact = t["factores_vida_media"].set_index(["factor", "categoria"])
        self.verif = t["verificacion_datos"]
        self.valid = t["validacion_auc"]
        self.sens = t["sensibilidad"]
        ev = t["evaluacion_planes"]
        self.ev_base = ev[ev["escenario"] == ev["escenario"].iloc[0]]
        self.rec_esc = t["recomendaciones"]
        self.bitacora = t["bitacora_limpieza"]
        self.metodos = t["comparacion_horas_efecto"]
        self.limites = t["horas_limite"].set_index("bebida")
        # Vida media mínima y máxima de cada grupo (los límites de los terciles).
        self.cortes = self.res.groupby("grupo", observed=True)["vida_media_h"].agg(["min", "max"])

    def plan_txt(self, g: str) -> str:
        """'Plan E (08:00 Café chorreado + 14:00 Energética grande)'."""
        f = self.guia.loc[g]
        return f"plan {f['plan']} ({f['descripcion']})"

    def cambios_por_parametro(self) -> pd.Series:
        """Número de decisiones (de 6 casos) que cambian por parámetro."""
        return self.sens.groupby("parametro")["cambia_decision"].sum().sort_values(ascending=False)


def num(x: float, d: int = 1) -> str:
    """Número con coma decimal (formato es-CR)."""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", " ")


def sci(x: float) -> str:
    """Notación científica legible: 5,2 × 10⁻⁵."""
    mantisa, exponente = f"{x:.1e}".split("e")
    sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return f"{mantisa.replace('.', ',')} × 10{str(int(exponente)).translate(sup)}"


# ---------------------------------------------------------------------------
# Estilos y utilidades de reportlab
# ---------------------------------------------------------------------------
# Fuentes, estilos de párrafo y piezas reutilizables (fórmulas, figuras, tablas
# y pie de página) para la ficha técnica y el resumen ejecutivo.


def _registrar_fuentes() -> None:
    """Registra DejaVu Sans (incluida en matplotlib) para tener ≥, ≈, ∫, ½, etc."""
    base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", str(base / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(base / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(base / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique"
    )


def _estilos(tam: float = 9.2) -> dict[str, ParagraphStyle]:
    """Estilos de párrafo de los documentos.

    ``tam`` es el tamaño de letra del cuerpo; títulos, pies y referencias se calculan a partir
    de él (cuerpo, viñeta, h1, título, centro, pie y ref).
    """
    base = getSampleStyleSheet()
    cuerpo = ParagraphStyle(
        "cuerpo",
        parent=base["Normal"],
        fontName="DejaVu",
        fontSize=tam,
        leading=tam * 1.32,
        alignment=TA_JUSTIFY,
        spaceAfter=3,
    )
    return {
        "cuerpo": cuerpo,
        "vineta": ParagraphStyle("vineta", parent=cuerpo, leftIndent=10, bulletIndent=2),
        "h1": ParagraphStyle(
            "h1",
            parent=cuerpo,
            fontName="DejaVu-Bold",
            fontSize=tam + 2.6,
            leading=(tam + 2.6) * 1.2,
            spaceBefore=6,
            spaceAfter=3,
            textColor=colors.HexColor("#1B5E20"),
            alignment=0,
        ),
        "titulo": ParagraphStyle(
            "titulo",
            parent=cuerpo,
            fontName="DejaVu-Bold",
            fontSize=tam + 6,
            leading=(tam + 6) * 1.2,
            alignment=1,
            textColor=colors.HexColor("#1B5E20"),
        ),
        "centro": ParagraphStyle("centro", parent=cuerpo, alignment=1, fontSize=tam - 0.6),
        "pie": ParagraphStyle(
            "pie",
            parent=cuerpo,
            fontSize=tam - 1.8,
            leading=(tam - 1.8) * 1.25,
            textColor=colors.HexColor("#555555"),
            alignment=0,
        ),
        "ref": ParagraphStyle(
            "ref",
            parent=cuerpo,
            fontSize=tam - 0.8,
            leftIndent=14,
            firstLineIndent=-14,
            alignment=0,
        ),
    }


def formula(latex: str, ancho_cm: float | None = None, tam: int = 13) -> Image:
    """Renderiza una fórmula LaTeX (mathtext) como imagen para reportlab."""
    # Dibuja la fórmula con matplotlib y la guarda como PNG en memoria.
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex}$", fontsize=tam)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=250, bbox_inches="tight", pad_inches=0.03, transparent=True)
    plt.close(fig)
    buf.seek(0)
    alto_px, ancho_px = mpimg.imread(io.BytesIO(buf.getvalue())).shape[:2]
    buf.seek(0)
    # Pasa de píxeles a puntos (72 por pulgada) y la reduce si supera ``ancho_cm``.
    ancho = ancho_px / 250 * 72 * 0.85
    alto = alto_px / 250 * 72 * 0.85
    if ancho_cm and ancho > ancho_cm * cm:
        alto, ancho = alto * ancho_cm * cm / ancho, ancho_cm * cm
    return Image(buf, width=ancho, height=alto)


def figura(nombre: str, ancho_cm: float) -> Image:
    """Inserta una figura de resultados/figuras con su proporción original."""
    ruta = DIR_FIGURAS / f"{nombre}.png"
    alto_px, ancho_px = mpimg.imread(ruta).shape[:2]
    return Image(str(ruta), width=ancho_cm * cm, height=ancho_cm * cm * alto_px / ancho_px)


def tabla(filas: list[list[str]], anchos: list[float], tam: float = 7.8) -> Table:
    """Tabla con encabezado sombreado; ``anchos`` en cm."""
    est = ParagraphStyle("t", fontName="DejaVu", fontSize=tam, leading=tam * 1.2)
    est_b = ParagraphStyle("tb", parent=est, fontName="DejaVu-Bold", textColor=colors.white)
    # Cada celda es un Paragraph para que el texto se parta en varias líneas.
    datos = [
        [Paragraph(str(c), est_b if i == 0 else est) for c in fila] for i, fila in enumerate(filas)
    ]
    t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1)
    # Encabezado verde, filas alternadas blanco/verde claro y bordes finos.
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF6EE")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CFE3D0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t


def _pie_pagina(canvas, doc) -> None:  # noqa: ANN001
    """Número de página y nota de datos simulados."""
    canvas.saveState()
    canvas.setFont("DejaVu", 7)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(2 * cm, 1.1 * cm, f"{AUTOR} · C-09 · Proyecto 2 · datos simulados")
    canvas.drawRightString(letter[0] - 2 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Ficha técnica
# ---------------------------------------------------------------------------
# Dos tablas de apoyo y construir_ficha, que arma el documento de 5 páginas
# apartado por apartado (problema, marco teórico, datos, modelo, resultados...).


def _tabla_guia(c: Cifras) -> Table:
    """Tabla con el plan recomendado (criterio oficial) de cada grupo de eliminación.

    También se usa en el resumen ejecutivo.
    """
    filas = [
        [
            "Grupo (t½)",
            "Plan recomendado (criterio oficial)",
            "H_ef",
            "C a las 23 h",
            "Cafeína",
            "Última toma",
            "Máx./día*",
            "% duerme bien",
        ]
    ]
    # Una fila por grupo: rápida, normal y lenta.
    for g in GRUPOS:
        f = c.guia.loc[g]
        filas.append(
            [
                f"{g} ({num(c.cortes.loc[g, 'min'])}–{num(c.cortes.loc[g, 'max'])} h)",
                f"<b>{f['plan']}</b>: {f['descripcion']}",
                f"{num(f['horas_efecto'])} h",
                f"{num(f['c_dormir'], 2)} mg/L",
                f"{f['cafeina_mg']:.0f} mg",
                hora_texto(f["hora_limite_ultima_toma"]),
                f"{f['maximo_diario_mg']:.0f} mg",
                f"{f['pct_personas_duermen_bien']:.0f} %",
            ]
        )
    return tabla(filas, [2.4, 4.4, 1.2, 1.9, 1.6, 1.6, 1.9, 1.7])


def _tabla_alternativas(c: Cifras) -> Table:
    """Tabla con las alternativas prudentes: plan del catálogo y plan ajustado por grupo.

    Sirven para que duerma bien al menos el porcentaje COBERTURA_PRUDENTE del grupo.
    """
    filas = [
        [
            "Grupo",
            f"Catálogo prudente (≥{COBERTURA_PRUDENTE:.0f} % duerme bien)",
            "H_ef",
            "Plan ajustado prudente (exploratorio)",
            "H_ef",
            "Cafeína",
            "% duerme bien",
        ]
    ]
    for g in GRUPOS:
        pr, aj = c.prudente.loc[g], c.ajustado.loc[g]
        filas.append(
            [
                g,
                f"{pr['plan']}: {pr['descripcion']}",
                f"{num(pr['horas_efecto'])} h",
                aj["descripcion"],
                f"{num(aj['horas_efecto'])} h",
                f"{aj['cafeina_mg']:.0f} mg",
                f"{aj['pct_personas_duermen_bien']:.0f} %",
            ]
        )
    return tabla(filas, [1.5, 4.4, 1.2, 5.6, 1.2, 1.4, 1.6])


def construir_ficha(c: Cifras, destino: Path) -> None:
    """Ficha técnica de modelación (4–6 páginas).

    Va llenando la lista ``h`` con párrafos, fórmulas, figuras y tablas en orden de lectura;
    al final reportlab la reparte en páginas y la guarda en ``destino``.
    """
    # Atajos: estilos, cifras usadas a menudo y dos funciones cortas para agregar
    # un párrafo (par) o una viñeta (vin) a la lista h.
    e = _estilos()
    p, res = c.p, c.res
    fs = c.fact
    cambios = c.cambios_por_parametro()
    m = c.metodos
    rel = c.a.relacion
    h: list = []
    par = lambda txt, est="cuerpo": h.append(Paragraph(txt, e[est]))  # noqa: E731
    vin = lambda txt: h.append(Paragraph(txt, e["vineta"], bulletText="•"))  # noqa: E731

    # Encabezado: título, tema, autor y curso.
    par("Ficha técnica de modelación", "titulo")
    par("Cafeína, atención y sueño en semana de exámenes", "centro")
    par(f"{AUTOR} · Carné {CARNE} · Código C-09 · {CURSO}", "centro")
    h.append(Spacer(1, 4))

    # 1. Problema: cliente, persona usuaria, pregunta de decisión y criterio de éxito.
    par("1. Problema y pregunta de decisión", "h1")
    par(
        "<b>Cliente:</b> Coordinación de Vida Estudiantil de la Sede del Sur (UCR, Golfito), que prepara "
        "una campaña sobre café y bebidas energéticas para la semana de exámenes. <b>Persona usuaria:</b> "
        "estudiantes que estudian de 8:00 a 20:00 y se acuestan a las 23:00. La cafeína bloquea los "
        "receptores de adenosina y mejora la atención (Fredholm et al., 1999), pero su eliminación varía "
        "mucho entre personas: fumar la acelera y los anticonceptivos hormonales la retrasan (Nehlig, 2018; "
        "Abernethy y Todd, 1985); tomarla tarde reduce el sueño (Drake et al., 2013)."
    )
    par(
        "<b>Pregunta de decisión:</b> ¿cuántas tomas, de qué bebida y hasta qué hora conviene consumir "
        "cafeína para tener más horas de atención en la jornada sin afectar el sueño? <b>Criterio de "
        f"éxito:</b> por grupo de eliminación, el plan con más horas con C ≥ {num(p.c_efecto)} mg/L entre "
        f"las {p.inicio:.0f}:00 y las {p.fin:.0f}:00, con C(23:00) &lt; {num(p.c_sueno)} mg/L y cafeína "
        f"≤ {p.max_diario_mg:.0f} mg/día (EFSA, 2015)."
    )

    # 2. Marco teórico: exponencial, modelo con absorción, integral impropia (AUC),
    # superposición, horas con efecto y métodos numéricos. Las fórmulas van como imagen.
    par("2. Marco teórico", "h1")
    par(
        "<b>Decrecimiento exponencial y vida media.</b> Si la velocidad de eliminación es proporcional a la "
        "cantidad presente, dC/dt = −kC, cuya solución es C = C₀e<super>−kt</super>; así ln C = ln C₀ − kt es una recta "
        "de pendiente −k, y la vida media cumple C(t½) = C₀/2 ⇒ t½ = ln 2 / k (Stewart, 2018)."
    )
    par(
        "<b>Modelo de un compartimento con absorción.</b> La cantidad en el intestino A cumple dA/dt = −kₐA "
        "y la concentración dC/dt = kₐA/V − kC. Resolviendo con factor integrante y C(0) = 0 (Rowland y "
        "Tozer, 2011):"
    )
    h.append(Spacer(1, 3))
    h.append(
        formula(
            r"C(t)=\frac{D\,k_a}{V\,(k_a-k)}\left(e^{-kt}-e^{-k_a t}\right),\qquad "
            r"t_{max}=\frac{\ln(k_a/k)}{k_a-k}",
            15,
        )
    )
    par(
        "<b>Integral impropia y área bajo la curva.</b> Integrando término a término (antiderivada de "
        "e<super>−at</super> es −e<super>−at</super>/a) y tomando el límite, la integral converge porque k, kₐ &gt; 0:"
    )
    h.append(Spacer(1, 3))
    h.append(
        formula(
            r"\int_0^{t} C\,ds=\frac{Dk_a}{V(k_a-k)}\left[\frac{1-e^{-kt}}{k}-"
            r"\frac{1-e^{-k_a t}}{k_a}\right],\quad AUC=\lim_{t\to\infty}\int_0^t C\,ds=\frac{D}{Vk}",
            15,
        )
    )
    par(
        "En la fase terminal C(t) ≈ C(24)e<super>−k(t−24)</super>, de modo que la cola es ∫<sub>24</sub><super>∞</super> C dt = C(24)/k. La "
        "<b>depuración</b> CL = D/AUC (L/h) es el volumen de sangre «limpiado» por hora, y V = CL/k."
    )
    par(
        "<b>Superposición.</b> El sistema es lineal en la dosis: si C₁ y C₂ son soluciones, C₁ + C₂ también "
        "lo es. Un plan con tomas (tⱼ, Dⱼ) produce C_plan(t) = Σⱼ C(t − tⱼ; Dⱼ). Las <b>horas con efecto</b> "
        "son la integral de una función indicadora (medida del conjunto donde C supera el umbral):"
    )
    h.append(Spacer(1, 3))
    h.append(
        formula(
            r"H_{ef}=\int_{8}^{20}\mathbf{1}\left[C_{plan}(t)\geq c_{ef}\right]dt,\qquad "
            r"\bar{C}=\frac{1}{20-8}\int_8^{20}C_{plan}(t)\,dt",
            14,
        )
    )
    par(
        "<b>Métodos numéricos</b> (Burden et al., 2017): trapecio compuesto (error −(b−a)h²f″/12, exacto "
        "en rectas), Simpson para espaciado irregular (exacto en parábolas) y bisección, cuya convergencia "
        "garantiza el teorema del valor intermedio cuando f cambia de signo."
    )

    # 3. Datos: qué trae la base, patrones observados y cómo se trataron faltantes y atípicos
    # (la lista sale de la bitácora de limpieza).
    par("3. Datos, exploración y tratamiento", "h1")
    par(
        f"La base trae 780 concentraciones (60 voluntarios × 13 tiempos de 0,25 a 24 h tras 200 mg), las "
        f"características de los 60 voluntarios ({(res['fuma'] == 'Sí').sum()} fuman y "
        f"{(res['anticonceptivo_hormonal'] == 'Sí').sum()} usan anticonceptivo hormonal), 480 pruebas de "
        "tiempo de reacción y las tablas de bebidas, planes y parámetros. <b>Patrones:</b> la concentración "
        "media sube a su pico cerca de 1 h y decae exponencialmente (ln C es recta desde 6 h); el tiempo "
        "de reacción medio baja de 336 ms (sin cafeína) a 231 ms en el pico y vuelve a 306 ms a las 12 h."
    )
    atip = c.bitacora[c.bitacora["estado"] == "atípico"]
    falt = c.bitacora[c.bitacora["estado"] == "faltante"]
    par(
        f"<b>Faltantes ({len(falt)}):</b> {', '.join(f'{r.voluntario} a {num(r.tiempo_h, 2)} h' for r in falt.itertuples())}. "
        f"<b>Atípicos ({len(atip)}):</b> {', '.join(f'{r.voluntario} a {num(r.tiempo_h, 0)} h ({num(r.valor_original, 2)} mg/L)' for r in atip.itertuples())}, "
        "detectados porque difieren más de ×1,8 de la interpolación log-lineal de sus vecinos. Los "
        "interiores se interpolan linealmente (lo mismo que supone el trapecio), los de 24 h se "
        "extrapolan con la recta terminal, y ningún valor imputado se usa para estimar k. Detalle en "
        "<i>docs/bitacora_supuestos.md</i>."
    )
    h.append(figura("fig01_perfiles", 15.5))

    # 4. Modelo: variables, unidades, dominio, supuestos y pasos del cálculo por voluntario.
    par("4. Construcción del modelo", "h1")
    par(
        "<b>Variables y unidades:</b> t (h), C (mg/L), D (mg), k y kₐ (1/h), V (L), CL (L/h), AUC (mg·h/L), "
        f"H_ef (h). <b>Dominio:</b> t ≥ 0 tras cada toma; jornada [{p.inicio:.0f}, {p.fin:.0f}] h. "
        f"<b>Supuestos:</b> cinética lineal; kₐ = {num(p.ka, 0)} h⁻¹ común (dato); C(0) = 0; persona "
        "representativa de cada grupo = mediana de k y V. <b>Procedimiento por voluntario:</b> (1) k por "
        "mínimos cuadrados de ln C para t ≥ 6 h; (2) AUC = trapecio en [0, 24] + C(24)/k; (3) CL = D/AUC "
        "y V = CL/k; (4) grupos por terciles de t½; (5) evaluación de los seis planes por superposición "
        "en una malla de 1 min."
    )

    # 5. Resultados: vida media, V, CL y peso de la cola impropia; efecto de fumar y del
    # anticonceptivo; relación cafeína-atención; mapa de planes y tabla de la guía.
    par("5. Resultados", "h1")
    par(
        f"La vida media mediana es {num(res['vida_media_h'].median(), 2)} h (rango "
        f"{num(res['vida_media_h'].min(), 1)}–{num(res['vida_media_h'].max(), 1)} h); V mediano "
        f"{num(res['v_l'].median())} L (≈ {num((res['v_l'] / res['peso_kg']).median(), 2)} L/kg) y CL "
        f"mediana {num(res['cl_l_h'].median(), 2)} L/h, valores del orden reportado para la cafeína "
        f"(Institute of Medicine, 2001). La cola impropia aporta en mediana {num(res['pct_cola'].median())} % "
        f"del AUC y hasta {num(res['pct_cola'].max())} % en la persona más lenta: sin la integral impropia "
        "se subestimaría gravemente su exposición."
    )
    h.append(figura("fig03_auc_cola_grande", 12.5))
    par(
        f"<b>Factores.</b> Fumar acorta t½ (mediana {num(fs.loc[('fuma', 'Sí'), 'mediana_t12_h'])} h contra "
        f"{num(fs.loc[('fuma', 'No'), 'mediana_t12_h'])} h) y el anticonceptivo la alarga "
        f"({num(fs.loc[('anticonceptivo_hormonal', 'Sí'), 'mediana_t12_h'])} h contra "
        f"{num(fs.loc[('anticonceptivo_hormonal', 'No'), 'mediana_t12_h'])} h); prueba de permutaciones "
        f"p = {num(fs.loc[('fuma', 'Sí'), 'p_valor'], 4)} y {num(fs.loc[('anticonceptivo_hormonal', 'Sí'), 'p_valor'], 4)}. "
        f"Terciles: rápida t½ ≤ {num(c.cortes.loc['rápida', 'max'], 2)} h, normal hasta "
        f"{num(c.cortes.loc['normal', 'max'], 2)} h, lenta por encima. <b>Atención:</b> mejora del tiempo "
        f"de reacción = {num(rel.intercepto)} + {num(rel.pendiente)}·C ms (R² = {num(rel.r2, 2)})."
    )
    h.append(KeepTogether([figura("fig07_mapa_planes", 9.0)]))
    par("Con el criterio oficial (persona representativa) la decisión es:")
    h.append(_tabla_guia(c))
    par(
        "* Máximo diario con los horarios del plan: por linealidad, escalar todas las dosis por s escala "
        "C(23) por s, así que s* = c_sueño / C(23). Última toma: bisección de C(23; t) = c_sueño.",
        "pie",
    )
    h.append(figura("fig08_planes_recomendados", 17.0))

    # 6. Verificación: validación del AUC, comparación con los acumulados de la base y
    # entre métodos numéricos; luego escenarios, sensibilidad y riesgo dentro del grupo.
    par("6. Verificación, escenarios y sensibilidad", "h1")
    vin(
        f"<b>Validación obligatoria:</b> integrando con Simpson el modelo de cada voluntario hasta 200 h se "
        f"recupera D/(Vk) con error máximo {num(100 * c.valid['error_rel'].max(), 3)} % (&lt; 0,5 %); "
        "∫<sub>0</sub><super>T</super> e<super>−kt</super>dt con T = 200–400 h coincide con 1/k (error &lt; 10⁻⁶)."
    )
    vin(
        f"<b>Contra los acumulados de la base:</b> el acumulado observado ∫₀²⁴C dt difiere de la integral "
        f"exacta del modelo {num(100 * c.verif['error_rel_acumulado'].mean(), 2)} % en promedio; el modelo "
        f"explica en mediana {num(100 * c.verif['r2'].median(), 0)} % de cada perfil (RMSE medio "
        f"{num(c.verif['rmse_mg_L'].mean(), 2)} mg/L)."
    )
    vin(
        f"<b>Dos reglas:</b> Simpson difiere {num(100 * c.verif['error_rel_simpson_modelo'].mean())} % de la "
        "integral exacta porque la parábola por 10, 12 y 24 h no sigue a la exponencial; con datos "
        "sintéticos el trapecio sobrestima ≈ 3 % (lo que subestima V en ≈ 3 %). H_ef por interpolación y "
        f"por bisección coinciden (error máximo {sci(m['error_rel'].max())})."
    )
    h.append(figura("fig06_verificacion", 14.0))
    # Texto de escenarios: el plan elegido y sus horas con efecto por grupo en cada escenario.
    esc_txt = []
    for nombre in dict.fromkeys(c.a.tablas["evaluacion_planes"]["escenario"]):
        sub = c.rec_esc[c.rec_esc["escenario"] == nombre].set_index("grupo")
        esc_txt.append(
            f"{nombre}: "
            + ", ".join(
                f"{g} {sub.loc[g, 'plan']} ({num(sub.loc[g, 'horas_efecto'])} h)"
                for g in GRUPOS
                if g in sub.index
            )
        )
    vin(
        "<b>Escenarios:</b> "
        + "; ".join(esc_txt)
        + ". La acumulación de cinco días sube H_ef y C(23) "
        "pero no cambia la decisión; acostarse una hora antes obliga a planes más suaves."
    )
    vin(
        "<b>Sensibilidad (±20 %, hora de dormir ±1 h):</b> decisiones que cambian (de 6 casos): "
        + ", ".join(f"{k} {int(v)}" for k, v in cambios.items())
        + ". Lo que más mueve la decisión es la velocidad de eliminación personal (k, V) y la exigencia "
        "sobre el sueño; kₐ y el umbral de efecto solo cambian las horas, no el plan elegido."
    )
    vin(
        "<b>Riesgo dentro del grupo:</b> el plan de la persona típica deja bajo el umbral de sueño solo al "
        + ", ".join(
            f"{c.guia.loc[g, 'pct_personas_duermen_bien']:.0f} % del grupo {g}" for g in GRUPOS
        )
        + f". Por eso se calcula una alternativa prudente (≥ {COBERTURA_PRUDENTE:.0f} % del grupo):"
    )
    h.append(_tabla_alternativas(c))
    h.append(Spacer(1, 4))
    h.append(figura("fig12_criterios", 12.5))

    # 7. Recomendación: qué, quién, cuándo, recursos, resultado esperado, indicadores y límites.
    par("7. Recomendación", "h1")
    par(
        "<b>Qué:</b> una guía de consumo por tipo de eliminación con la regla «dosis mayor temprano, dosis "
        "pequeñas después y nunca después de la hora límite». Con el criterio oficial: rápida → "
        f"{c.plan_txt('rápida')}; normal → {c.plan_txt('normal')}; lenta → {c.plan_txt('lenta')}. Quien "
        "fuma pertenece casi siempre al grupo rápido y quien usa anticonceptivo hormonal, al lento."
    )
    par(
        "<b>Quién y cuándo:</b> Vida Estudiantil, dos semanas antes de exámenes, con afiches y la aplicación "
        f"web ({URL_APP}, con código QR) para que cada estudiante simule su día. <b>Recursos:</b> "
        "alojamiento de la aplicación en Railway (plan Hobby, unos 5 USD al mes) y difusión por canales "
        "institucionales; el otro costo es la impresión. <b>Resultado esperado:</b> hasta "
        f"{num(c.guia['horas_efecto'].max())} h de atención eficaz por día manteniendo C(23) &lt; "
        f"{num(p.c_sueno)} mg/L. <b>Indicadores:</b> encuesta antes/después (hora de la última toma, horas de "
        "sueño) y una prueba de tiempo de reacción en un stand durante la semana de exámenes."
    )
    par(
        "<b>Condiciones y límites:</b> datos simulados; una sola dosis de prueba; cinética lineal; kₐ común; "
        "sin tolerancia ni otros componentes de las energéticas. La recomendación deja de valer si la hora "
        "de acostarse cambia, si el umbral de sueño es más estricto o si la persona no conoce su tipo de "
        "eliminación (en ese caso conviene la guía del grupo lento). No es una recomendación médica."
    )

    # Referencias y declaración de autoría con la tabla para la firma.
    par("Referencias", "h1")
    for r in REFERENCIAS:
        par(r, "ref")

    par("Declaración de autoría", "h1")
    par(
        "Declaro que este proyecto fue elaborado de forma individual con la base de datos que me fue "
        "asignada, que todo tratamiento de los datos está documentado y que el código y las "
        "visualizaciones son de mi autoría o están debidamente citados."
    )
    h.append(Spacer(1, 6))
    h.append(
        tabla([["Nombre completo", "Carné", "Firma"], [AUTOR, CARNE, " "]], [7.5, 3.5, 6.5], 8.5)
    )

    # Tamaño carta con márgenes de 2 cm; reportlab pagina el contenido y agrega el pie.
    doc = SimpleDocTemplate(
        str(destino),
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.7 * cm,
        title="Ficha técnica · Cafeína, atención y sueño",
        author=AUTOR,
    )
    doc.build(h, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


# ---------------------------------------------------------------------------
# Resumen ejecutivo
# ---------------------------------------------------------------------------
# Una página para quien toma la decisión: recomendación, por qué, tabla de la guía,
# versión prudente, implementación, cómo medir y riesgos.


def construir_resumen(c: Cifras, destino: Path) -> None:
    """Resumen ejecutivo de una página para la Coordinación de Vida Estudiantil."""
    # Misma mecánica que la ficha (lista h con par y vin), con letra un poco más pequeña.
    e = _estilos(8.9)
    p = c.p
    h: list = []
    par = lambda txt, est="cuerpo": h.append(Paragraph(txt, e[est]))  # noqa: E731
    vin = lambda txt: h.append(Paragraph(txt, e["vineta"], bulletText="•"))  # noqa: E731
    par("Resumen ejecutivo", "titulo")
    par(
        "Para: Coordinación de Vida Estudiantil, UCR Sede del Sur · De: "
        f"{AUTOR} (analista) · Proyecto C-09",
        "centro",
    )
    h.append(Spacer(1, 4))
    # Recomendación y justificación con las cifras principales.
    par(
        "<b>Recomendación.</b> Lanzar una guía de cafeína diferenciada por velocidad de eliminación: una "
        "dosis mayor en la mañana, dosis pequeñas después y una hora límite por grupo. Así se obtienen "
        f"entre {num(c.guia['horas_efecto'].min())} y {num(c.guia['horas_efecto'].max())} horas de atención "
        f"eficaz entre las {p.inicio:.0f}:00 y las {p.fin:.0f}:00 con menos de {num(p.c_sueno)} mg/L de "
        f"cafeína en sangre al acostarse ({p.hora_dormir:.0f}:00) y sin superar {p.max_diario_mg:.0f} mg/día."
    )
    par(
        "<b>Por qué.</b> En 60 voluntarios la vida media de la cafeína va de "
        f"{num(c.res['vida_media_h'].min())} a {num(c.res['vida_media_h'].max())} h. Fumar la acorta "
        f"(mediana {num(c.fact.loc[('fuma', 'Sí'), 'mediana_t12_h'])} h) y el anticonceptivo hormonal la "
        f"alarga ({num(c.fact.loc[('anticonceptivo_hormonal', 'Sí'), 'mediana_t12_h'])} h). Cada mg/L de "
        f"cafeína mejora el tiempo de reacción ≈ {num(c.a.relacion.pendiente, 0)} ms. Un mismo plan puede "
        "dar casi 10 h de atención a una persona y quitarle el sueño a otra."
    )
    # Tabla de la guía y nota con la integral que se usó.
    h.append(_tabla_guia(c))
    par(
        "Integral usada: horas con efecto = ∫₈²⁰ 1[C(t) ≥ 1,5 mg/L] dt; C(t) por superposición de cada "
        "toma con el modelo de un compartimento (AUC = D/(Vk), validado con error &lt; 0,5 %).",
        "pie",
    )
    h.append(Spacer(1, 3))
    # Versión prudente por grupo y horas límite de una sola toma.
    par(
        "<b>Condición importante.</b> Los planes anteriores protegen el sueño de la persona típica de cada "
        f"grupo, pero no de todos: si la campaña quiere que al menos el {COBERTURA_PRUDENTE:.0f} % duerma "
        "bien, conviene comunicar la versión prudente:"
    )
    for g in GRUPOS:
        aj = c.ajustado.loc[g]
        vin(
            f"<b>{g.capitalize()}:</b> {aj['descripcion']} ({aj['cafeina_mg']:.0f} mg, "
            f"{num(aj['horas_efecto'])} h con efecto, {aj['pct_personas_duermen_bien']:.0f} % duerme bien)."
        )
    par(
        "<b>Hora límite de una sola toma</b> (C(23:00) &lt; 1 mg/L): café chorreado "
        + ", ".join(f"{g} {hora_texto(c.limites.loc['Café chorreado', g])}" for g in GRUPOS)
        + "; energética grande "
        + ", ".join(f"{g} {hora_texto(c.limites.loc['Energética grande', g])}" for g in GRUPOS)
        + "."
    )
    # Implementación, medición del efecto y riesgos.
    par(
        "<b>Implementación.</b> Quién: Vida Estudiantil con apoyo de la Oficina de Salud. Cuándo: dos semanas "
        f"antes de exámenes. Con qué: afiches con código QR a la aplicación web ({URL_APP}), donde cada "
        "estudiante elige su tipo, sus bebidas y horas y ve su curva y su concentración al acostarse. "
        "Costo: impresión, horas de difusión y el alojamiento en Railway (unos 5 USD al mes)."
    )
    par(
        "<b>Cómo medir el efecto.</b> Encuesta antes/después (hora de la última toma, horas de sueño, "
        "cafeína diaria) y un stand con prueba de tiempo de reacción en la semana de exámenes. Meta: "
        "que la mayoría de quienes toman cafeína lo hagan antes de su hora límite."
    )
    par(
        "<b>Riesgos y límites.</b> Datos simulados con fines didácticos; la decisión es más sensible a la "
        "velocidad de eliminación personal, a la hora de acostarse y al umbral de sueño. Si una persona no "
        "conoce su tipo, debe seguir la guía del grupo lento. No sustituye el consejo médico.",
        "cuerpo",
    )
    # Márgenes más pequeños para que todo quepa en una página.
    doc = SimpleDocTemplate(
        str(destino),
        pagesize=letter,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.3 * cm,
        title="Resumen ejecutivo · Cafeína",
        author=AUTOR,
    )
    doc.build(h, onFirstPage=_pie_pagina)


# ---------------------------------------------------------------------------
# Diapositivas: utilidades de dibujo
# ---------------------------------------------------------------------------
# Cada lámina es una figura de matplotlib de 16:9. Estas funciones dibujan las piezas
# que se repiten: marco de la lámina, texto, recuadros, cifras, imágenes y tarjetas.

# Tamaño de la lámina en pulgadas (16:9) y paleta de colores.
ANCHO, ALTO = 13.333, 7.5
VERDE_OSCURO, VERDE, VERDE_CLARO, VERDE_SUAVE = "#1B5E20", "#2E7D32", "#E3F1E3", "#F3F9F3"
NEGRO, GRIS_TEXTO = "#111111", "#555555"


def _contar_pruebas() -> int:
    """Número de pruebas que recoge pytest (incluye las parametrizadas).

    Ejecuta ``pytest --collect-only`` y lee la cifra del texto de salida (0 si no la encuentra).
    """
    salida = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    hallado = re.search(r"(\d+) tests? collected", salida)
    return int(hallado.group(1)) if hallado else 0


def _lamina(seccion: str, titulo: str, numero: int, total: int) -> tuple[plt.Figure, float]:
    """Lámina blanca con sección, título que enuncia la conclusión y pie.

    Devuelve la figura y la altura (fracción de la figura) donde empieza el
    contenido.

    Todas las coordenadas son fracciones de la figura: van de 0 a 1 y el origen
    (0, 0) está abajo a la izquierda; (1, 1) es la esquina de arriba a la derecha.
    """
    # Sección en mayúsculas y título partido en líneas de hasta 64 caracteres.
    fig = plt.figure(figsize=(ANCHO, ALTO), facecolor="white")
    fig.text(0.05, 0.925, seccion.upper(), fontsize=11, color=VERDE, weight="bold")
    lineas = textwrap.wrap(titulo, 64)
    fig.text(
        0.05,
        0.895,
        "\n".join(lineas),
        fontsize=25 if len(lineas) == 1 else 21,
        color=NEGRO,
        weight="bold",
        va="top",
        linespacing=1.15,
    )
    # Línea separadora bajo el título (más abajo si el título ocupa dos líneas) y pie.
    y_linea = 0.805 if len(lineas) == 1 else 0.74
    fig.add_artist(
        Line2D(
            [0.05, 0.95], [y_linea, y_linea], color=VERDE_CLARO, lw=2.5, transform=fig.transFigure
        )
    )
    fig.text(0.05, 0.03, f"{AUTOR} · C-09 · Proyecto 2 MA-0321", fontsize=9, color=GRIS_TEXTO)
    fig.text(0.95, 0.03, f"{numero}/{total}", fontsize=9, color=GRIS_TEXTO, ha="right")
    return fig, y_linea - 0.045


def _texto(
    fig: plt.Figure,
    x: float,
    y: float,
    lineas: list[str],
    tam: float = 15,
    sep: float | None = None,
    ancho: float | None = None,
    color: str = NEGRO,
    peso: str = "normal",
) -> float:
    """Escribe líneas (mathtext permitido); '**' al inicio pone la línea en negrita.

    ``ancho`` (fracción de la figura) parte el texto sin fórmulas en varias
    líneas. Devuelve la y final.
    """
    # Cuántos caracteres caben por línea según el ancho disponible y el tamaño de letra.
    sep = sep or tam * 0.0029
    caracteres = int((ancho or (0.95 - x)) * ANCHO * 72 / (tam * 0.53))
    dibujo = fig.canvas.get_renderer()
    # Escribe cada línea de arriba hacia abajo; una línea vacía deja medio espacio y
    # las fórmulas ($...$) no se parten. y baja según la altura real del texto dibujado.
    for linea in lineas:
        negrita = linea.startswith("**")
        linea = linea.replace("**", "")
        if not linea:
            y -= sep * 0.55
            continue
        formula = "$" in linea
        for parte in [linea] if formula else textwrap.wrap(linea, caracteres):
            texto = fig.text(
                x,
                y,
                parte,
                fontsize=tam * 1.2 if formula else tam,
                va="top",
                color=VERDE_OSCURO if negrita else color,
                weight="bold" if negrita else peso,
            )
            alto = texto.get_window_extent(renderer=dibujo).height / fig.bbox.height
            y -= max(sep, alto + sep * (0.5 if formula else 0.3))
    return y


def _caja(
    fig: plt.Figure,
    caja: tuple[float, float, float, float],
    lineas: list[str],
    titulo: str | None = None,
    tam: float = 14,
    fondo: str = VERDE_CLARO,
) -> None:
    """Recuadro redondeado con título opcional y texto; crece hacia arriba si no cabe.

    ``caja`` = (x, y, ancho, alto) en fracciones de la figura (0 a 1, origen abajo a la
    izquierda); (x, y) es la esquina inferior izquierda del recuadro.
    """
    x, y, w, h = caja

    def escribir(arriba: float) -> float:
        """Escribe título y líneas desde la altura ``arriba``; devuelve la y final."""
        yy = arriba - 0.03
        if titulo:
            fig.text(
                x + 0.02, yy, titulo, fontsize=tam, weight="bold", color=VERDE_OSCURO, va="top"
            )
            yy -= tam * 0.0042
        return _texto(fig, x + 0.02, yy, lineas, tam=tam, ancho=w - 0.04)

    # Escribe una vez para medir; si el texto no cabe, lo borra, agranda la caja y reescribe.
    previos = len(fig.texts)
    necesario = y + h - escribir(y + h) + 0.015
    if necesario > h:
        for t in fig.texts[previos:]:
            t.remove()
        h = necesario
        escribir(y + h)
    # Fondo redondeado detrás del texto (zorder=0).
    fig.add_artist(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=0.012",
            transform=fig.transFigure,
            facecolor=fondo,
            edgecolor="none",
            zorder=0,
        )
    )


def _simple(fig: plt.Figure, caja: tuple[float, float, float, float], lineas: list[str]) -> None:
    """Recuadro «En palabras simples» para el público no especializado."""
    _caja(fig, caja, lineas, "En palabras simples", tam=14)


def _cifra(
    fig: plt.Figure, caja: tuple[float, float, float, float], valor: str, etiqueta: str
) -> None:
    """Número grande con su explicación debajo.

    ``caja`` = (x, y, ancho, alto) en fracciones de la figura (0 a 1, origen abajo a la
    izquierda). Dibuja el recuadro, luego ``valor`` arriba y ``etiqueta`` debajo.
    """
    x, y, w, h = caja
    fig.add_artist(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=0.012",
            transform=fig.transFigure,
            facecolor=VERDE_SUAVE,
            edgecolor=VERDE_CLARO,
            lw=1.5,
            zorder=0,
        )
    )
    fig.text(
        x + 0.02, y + h - 0.025, valor, fontsize=26, weight="bold", color=VERDE_OSCURO, va="top"
    )
    _texto(fig, x + 0.02, y + h - 0.095, [etiqueta], tam=12, ancho=w - 0.04, color=NEGRO)


def _imagen(
    fig: plt.Figure,
    ruta: Path,
    caja: tuple[float, float, float, float],
    fuente: str | None = FUENTE,
) -> None:
    """Coloca una imagen en la caja (x, y, ancho, alto) en fracciones de la figura."""
    ax = fig.add_axes(caja)
    ax.imshow(mpimg.imread(ruta))
    ax.axis("off")
    # Nota de fuente debajo de la imagen (las capturas de pantalla no la llevan).
    if fuente:
        fig.text(
            caja[0],
            caja[1] - 0.012,
            fuente + " · unidades en los ejes",
            fontsize=8,
            color=GRIS_TEXTO,
            va="top",
        )


def _tomas(descripcion: str) -> list[str]:
    """'08:00 Café chorreado + 14:00 Té negro' -> ['08:00  Café chorreado', ...]."""
    return [t.replace(" ", "  ", 1) for t in descripcion.split(" + ")]


def _tarjeta_grupo(
    fig: plt.Figure, caja: tuple[float, float, float, float], c: Cifras, g: str
) -> None:
    """Tarjeta con el plan recomendado de un tipo de eliminación."""
    f = c.guia.loc[g]
    _caja(
        fig,
        caja,
        [
            f"**Plan {f['plan']}**",
            *_tomas(f["descripcion"]),
            "",
            f"{num(f['horas_efecto'])} h con concentración",
            f"Última bebida: {hora_texto(f['hora_limite_ultima_toma'])}",
        ],
        f"Eliminación {g}",
        tam=14,
    )


def _curvas_grupos(fig: plt.Figure, c: Cifras, caja: tuple[float, float, float, float]) -> None:
    """Curva de una toma de la dosis de prueba para la persona típica de cada grupo."""
    # Ejes dentro de la lámina y una curva C(t) de 0 a 24 h por grupo.
    ax = fig.add_axes(caja)
    t = np.linspace(0, 24, 400)
    for g in GRUPOS:
        m = c.a.modelos[g]
        ax.plot(
            t,
            m.concentracion(t, c.p.dosis_mg),
            color=COLORES[g],
            lw=2.5,
            label=f"{g}: t½ = {num(m.vida_media)} h",
        )
    # Línea del umbral de efecto, etiquetas y estilo limpio (sin bordes arriba y a la derecha).
    ax.axhline(c.p.c_efecto, color=NEGRO, ls="--", lw=1)
    ax.text(24, c.p.c_efecto + 0.1, "umbral de efecto", ha="right", fontsize=9)
    ax.set_xlabel("Horas después de tomar 200 mg")
    ax.set_ylabel("C(t) (mg/L)")
    ax.set_title("Persona típica de cada grupo", fontsize=11)
    ax.legend(fontsize=9, frameon=False)
    ax.grid(alpha=0.25)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


# ---------------------------------------------------------------------------
# Diapositivas: construcción de las 14 láminas
# ---------------------------------------------------------------------------
# construir_presentacion arma lámina por lámina con las utilidades anteriores y
# guarda todas en un solo PDF.


def construir_presentacion(c: Cifras, destino: Path, captura: Path | None) -> int:
    """Diapositivas en PDF (una idea por lámina). Devuelve el número de láminas.

    ``captura`` es la imagen de la aplicación web para la lámina 10 (se omite si no existe).
    """
    # Datos comunes: atajos, ruta de cada figura, la frase de recomendación y la posición
    # de las tres tarjetas de grupo (se reutilizan en las láminas 1 y 14).
    p, g_ = c.p, c.guia
    fig_ = lambda n: DIR_FIGURAS / f"{n}.png"  # noqa: E731
    total = 14
    laminas: list[plt.Figure] = []
    frase = (
        "Cada tipo de persona tiene su plan y su hora límite: así gana horas de "
        "concentración sin perder el sueño."
    )
    tarjetas = [(0.05 + 0.31 * i, 0.12, 0.28, 0.36) for i in range(3)]

    # Lámina 1: portada con la recomendación en una frase y el plan de cada grupo.
    f, y0 = _lamina(
        "Vida Estudiantil · UCR Sede del Sur (Golfito)",
        "Cafeína, atención y sueño en semana de exámenes",
        1,
        total,
    )
    _texto(f, 0.05, y0, [f"{AUTOR} · Carné {CARNE} · {CURSO}"], tam=12, color=GRIS_TEXTO)
    f.text(0.05, y0 - 0.07, "RECOMENDACIÓN EN UNA FRASE", fontsize=11, color=VERDE, weight="bold")
    _texto(f, 0.05, y0 - 0.11, [frase], tam=20, ancho=0.9)
    for caja, g in zip(tarjetas, GRUPOS, strict=True):
        _tarjeta_grupo(f, caja, c, g)
    laminas.append(f)

    # Lámina 2: problema, pregunta de decisión y las tres condiciones del criterio de éxito.
    f, y0 = _lamina(
        "Problema y criterio de éxito",
        "La pregunta: cuántas tomas, de qué bebida y hasta qué hora",
        2,
        total,
    )
    _texto(
        f,
        0.05,
        y0,
        [
            "**El problema**",
            "La cafeína bloquea la adenosina y mejora la atención. Pero si a la hora de "
            "acostarse queda mucha en la sangre, el sueño empeora, y dormir es clave para la memoria.",
            "Cada cuerpo la elimina a distinta velocidad: fumar la acelera y el anticonceptivo "
            "hormonal la retrasa.",
            "",
            "**Pregunta de decisión**",
            "¿Cuántas tomas, de qué bebida y hasta qué hora conviene consumir cafeína para tener "
            "más horas de atención en la jornada sin afectar el sueño?",
            "",
            "**Para cada tipo (rápida, normal, lenta)**",
            r"$\max\ H_{ef}=\int_{8}^{20}\mathbf{1}\left[C_{plan}(t)\geq c_{ef}\right]dt$",
        ],
        tam=15,
        ancho=0.5,
    )
    # Tres cifras apiladas a la derecha: más horas con efecto, sueño y máximo diario.
    for i, (valor, texto) in enumerate(
        [
            (
                "Más horas",
                f"con al menos {num(p.c_efecto)} mg/L entre las {p.inicio:.0f}:00 y las "
                f"{p.fin:.0f}:00",
            ),
            (
                f"< {num(p.c_sueno)} mg/L",
                f"de cafeína en la sangre a las {p.hora_dormir:.0f}:00, hora de acostarse",
            ),
            (f"≤ {p.max_diario_mg:.0f} mg", "de cafeína en todo el día (EFSA, 2015)"),
        ]
    ):
        _cifra(f, (0.62, 0.55 - 0.205 * i, 0.33, 0.18), valor, texto)
    laminas.append(f)

    # Lámina 3: marco teórico I, decrecimiento exponencial y modelo con absorción.
    f, y0 = _lamina(
        "Marco teórico I",
        "La cafeína entra rápido a la sangre y sale de forma exponencial",
        3,
        total,
    )
    _texto(
        f,
        0.05,
        y0,
        [
            "**Decrecimiento exponencial y vida media**",
            r"$\dfrac{dC}{dt}=-kC\ \Rightarrow\ C=C_0\,e^{-kt},\qquad t_{1/2}=\dfrac{\ln 2}{k}$",
            "",
            "**Un compartimento con absorción** (EDO lineal)",
            r"$\dfrac{dA}{dt}=-k_aA,\qquad \dfrac{dC}{dt}=\dfrac{k_a A}{V}-kC,\qquad C(0)=0$",
            r"$C(t)=\dfrac{D\,k_a}{V\,(k_a-k)}\left(e^{-kt}-e^{-k_a t}\right)$",
            "Se resuelve con factor integrante. k se estima con la pendiente de ln C desde las 6 h.",
            "",
            f"Unidades: C en mg/L, D en mg, k y kₐ en 1/h (kₐ = {num(p.ka, 0)}, dato), V en L.",
        ],
        tam=15,
        ancho=0.5,
    )
    # Gráfico de las tres curvas y explicación sencilla de la vida media.
    _curvas_grupos(f, c, (0.62, 0.4, 0.33, 0.33))
    rap, len_ = c.a.modelos["rápida"].vida_media, c.a.modelos["lenta"].vida_media
    _simple(
        f,
        (0.58, 0.08, 0.37, 0.21),
        [
            "La vida media es lo que tarda la cafeína en bajar a la mitad: "
            f"{num(rap)} h en alguien rápido y {num(len_)} h en alguien lento.",
        ],
    )
    laminas.append(f)

    # Lámina 4: marco teórico II, integral impropia (AUC), superposición y horas con efecto.
    f, y0 = _lamina(
        "Marco teórico II",
        "El área bajo la curva es una integral impropia que converge",
        4,
        total,
    )
    _texto(
        f,
        0.05,
        y0,
        [
            "**Integral impropia y convergencia** (k > 0)",
            r"$\int_0^{\infty}e^{-kt}\,dt=\lim_{T\to\infty}\dfrac{1-e^{-kT}}{k}=\dfrac{1}{k}$",
            r"$AUC=\int_0^{\infty}C\,dt=\dfrac{D}{V\,k},\qquad CL=\dfrac{D}{AUC},\qquad V=\dfrac{CL}{k}$",
            "**Con los datos:** trapecio hasta las 24 h más la cola",
            r"$AUC\approx\int_0^{24}C\,dt+\dfrac{C(24)}{k}$",
            "**Superposición** (la EDO es lineal en la dosis)",
            r"$C_{plan}(t)=\sum_j C(t-t_j;\,D_j)$",
            "**Integral de la función indicadora**",
            r"$H_{ef}=\int_{8}^{20}\mathbf{1}\left[C_{plan}(t)\geq c_{ef}\right]dt$",
        ],
        tam=15,
        ancho=0.52,
    )
    _simple(
        f,
        (0.6, 0.2, 0.35, 0.52),
        [
            "El área bajo la curva mide cuánta cafeína «vio» el cuerpo en total (mg·h/L).",
            "",
            "La curva nunca llega a cero, así que se integra hasta el infinito. Como baja "
            "exponencialmente, el área es finita.",
            "",
            "Con varias bebidas, las curvas se suman.",
            "",
            f"Las horas con efecto son el tiempo en que la curva está sobre {num(p.c_efecto)} mg/L.",
        ],
    )
    _texto(
        f,
        0.6,
        0.16,
        [
            "Métodos propios: trapecio, Simpson, integral acumulada y bisección (Burden et al., 2017)."
        ],
        tam=11,
        ancho=0.35,
        color=GRIS_TEXTO,
    )
    laminas.append(f)

    # Lámina 5: datos, perfiles de concentración y tratamiento de faltantes y atípicos.
    atip = c.bitacora[c.bitacora["estado"] == "atípico"]
    n_falt = len(c.bitacora) - len(atip)
    f, y0 = _lamina(
        "Datos",
        f"Datos: 780 mediciones de 60 voluntarios; {len(c.bitacora)} valores se trataron "
        "con criterio explícito",
        5,
        total,
    )
    _imagen(f, fig_("fig01_perfiles"), (0.03, 0.12, 0.6, 0.58))
    _cifra(f, (0.66, 0.5, 0.14, 0.19), str(n_falt), "datos faltantes")
    _cifra(f, (0.81, 0.5, 0.14, 0.19), str(len(atip)), "datos atípicos")
    _texto(
        f,
        0.66,
        0.45,
        [
            "**Cómo se trataron**",
            "Faltantes en medio: interpolación lineal. A las 24 h: recta de ln C.",
            "Atípico: se aleja más de 1,8 veces de lo esperado por sus vecinos; se trata como "
            "faltante.",
            "Ningún valor corregido se usa para estimar k.",
        ],
        tam=13,
        ancho=0.29,
    )
    laminas.append(f)

    # Lámina 6: integración, AUC con trapecio más cola y por qué importa la cola impropia.
    f, y0 = _lamina(
        "Integración",
        f"La cola impropia aporta hasta {num(c.res['pct_cola'].max(), 0)} % del área en quien "
        "elimina lento",
        6,
        total,
    )
    _imagen(f, fig_("fig03_auc_cola_grande"), (0.02, 0.12, 0.58, 0.6))
    _texto(
        f,
        0.64,
        y0,
        [
            "**Para cada voluntario**",
            "1. k con la pendiente de ln C",
            "2. AUC = trapecio + C(24)/k",
            "3. CL = D/AUC y V = CL/k",
        ],
        tam=14,
        ancho=0.31,
    )
    _cifra(
        f,
        (0.64, 0.32, 0.15, 0.16),
        f"{num(c.res['vida_media_h'].median())} h",
        "vida media típica",
    )
    _cifra(
        f,
        (0.8, 0.32, 0.15, 0.16),
        f"{num(c.res['v_l'].median(), 0)} L",
        "volumen típico",
    )
    _simple(
        f,
        (0.64, 0.08, 0.31, 0.2),
        [
            "Si solo midiéramos hasta las 24 h, subestimaríamos la exposición de quien elimina lento."
        ],
    )
    laminas.append(f)

    # Lámina 7: verificación, errores del modelo y número de pruebas automáticas.
    n_pruebas = _contar_pruebas()
    f, y0 = _lamina(
        "Verificación",
        "Verificación: el modelo reproduce los acumulados de la base con "
        f"{num(100 * c.verif['error_rel_acumulado'].mean(), 1)} % de error",
        7,
        total,
    )
    _imagen(f, fig_("fig06_verificacion"), (0.02, 0.27, 0.62, 0.45))
    for i, (valor, texto) in enumerate(
        [
            (
                f"{num(100 * c.valid['error_rel'].max(), 3)} %",
                "error máximo al recuperar D/(Vk) (tolerancia 0,5 %)",
            ),
            (
                f"{num(100 * c.verif['error_rel_acumulado'].mean(), 1)} %",
                "entre el área medida y la integral del modelo",
            ),
            (f"{n_pruebas} pruebas", "automáticas con pytest en GitHub Actions"),
        ]
    ):
        _cifra(f, (0.67, 0.53 - 0.2 * i, 0.28, 0.17), valor, texto)
    _texto(
        f,
        0.04,
        0.2,
        [
            "Cada integral se calcula de dos formas: trapecio y fórmula exacta; Simpson y exacta "
            f"({num(100 * c.verif['error_rel_simpson_modelo'].mean())} %, por el salto de 12 a "
            f"24 h); malla y bisección ({sci(c.metodos['error_rel'].max())}).",
            r"$\int_0^{T}e^{-kt}\,dt\ \to\ 1/k$ se verifica con la integral truncada.",
        ],
        tam=12,
        ancho=0.6,
    )
    laminas.append(f)

    # Lámina 8: patrones, efecto de fumar y del anticonceptivo, y relación cafeína-reacción.
    fs = c.fact
    rel = c.a.relacion
    f, y0 = _lamina(
        "Patrones",
        "Fumar acelera y el anticonceptivo hormonal retrasa la eliminación",
        8,
        total,
    )
    _imagen(f, fig_("fig04_vida_media"), (0.03, 0.32, 0.94, 0.42))
    for i, (valor, texto) in enumerate(
        [
            (
                f"{num(fs.loc[('fuma', 'Sí'), 'mediana_t12_h'])} h vs "
                f"{num(fs.loc[('fuma', 'No'), 'mediana_t12_h'])} h",
                "vida media típica: fuma contra no fuma (p < 0,001)",
            ),
            (
                f"{num(fs.loc[('anticonceptivo_hormonal', 'Sí'), 'mediana_t12_h'])} h vs "
                f"{num(fs.loc[('anticonceptivo_hormonal', 'No'), 'mediana_t12_h'])} h",
                "con anticonceptivo hormonal contra sin él (p < 0,001)",
            ),
            (
                f"{num(rel.pendiente, 0)} ms",
                f"más rápida la reacción por cada mg/L de cafeína (R² = {num(rel.r2, 2)})",
            ),
        ]
    ):
        _cifra(f, (0.05 + 0.31 * i, 0.08, 0.28, 0.19), valor, texto)
    laminas.append(f)

    # Lámina 9: solución, mapa de los seis planes por tipo y regla para elegir.
    lenta_b = c.ev_base.set_index(["grupo", "plan"]).loc[("lenta", "B"), "c_dormir"]
    f, y0 = _lamina(
        "Solución",
        "Ningún plan sirve a todos: el mejor depende del tipo de eliminación",
        9,
        total,
    )
    _imagen(f, fig_("fig07_mapa_planes"), (0.03, 0.1, 0.5, 0.63))
    _texto(
        f,
        0.57,
        y0,
        [
            "**Seis planes × tres tipos (superposición)**",
            "Más tomas dan más horas con efecto, pero dejan más cafeína al acostarse.",
            "",
            f"El tipo lento acumula: con dos cafés llega a {num(lenta_b, 2)} mg/L a las 23:00.",
            "",
            "El tipo rápido tolera una energética grande a las 14:00.",
        ],
        tam=14,
        ancho=0.38,
    )
    _simple(
        f,
        (0.57, 0.08, 0.38, 0.19),
        [
            "Se elige el plan con más horas de efecto que cumple sueño y máximo; si empatan, "
            "el de menos cafeína. ✗ = no cumple.",
        ],
    )
    laminas.append(f)

    # Lámina 10: aplicación web (captura si existe), pasos de la demostración y código.
    f, y0 = _lamina(
        "Aplicación web y código",
        "Aplicación web: cada estudiante simula su día y ve si va a dormir bien",
        10,
        total,
    )
    if captura and captura.exists():
        _imagen(f, captura, (0.03, 0.1, 0.58, 0.64), fuente=None)
    _texto(
        f,
        0.65,
        y0,
        [
            "**Demostración**",
            "1. Elegir su tipo y su hora de acostarse",
            "2. Armar el día: bebidas y horas",
            "3. Ver las horas con efecto (área sombreada) y la cafeína al acostarse",
            "4. Comparar planes y escenarios; descargar Excel o CSV",
            f"**{URL_APP.removeprefix('https://')}**",
            "",
            "**Código en Python**",
            "src/: limpieza, modelo, escenarios, reporte",
            "pytest + ruff en GitHub Actions",
            "python -m src.reporte regenera todo",
        ],
        tam=14,
        ancho=0.3,
    )
    laminas.append(f)

    # Lámina 11: escenarios y sensibilidad, qué parámetros cambian la decisión.
    cambios = c.cambios_por_parametro()
    escenarios = list(dict.fromkeys(c.a.tablas["evaluacion_planes"]["escenario"]))
    f, y0 = _lamina(
        "Escenarios y sensibilidad",
        "La velocidad de eliminación y la hora de dormir son lo que más mueve la decisión",
        11,
        total,
    )
    _imagen(f, fig_("fig09_escenarios"), (0.02, 0.1, 0.55, 0.6))
    # Texto de la derecha: plan por grupo en cada escenario y luego los parámetros
    # agrupados según cuántas de las 6 decisiones cambian.
    lineas = ["**Escenario base y dos alternativos**"]
    for nombre in escenarios:
        sub = c.rec_esc[c.rec_esc["escenario"] == nombre].set_index("grupo")
        lineas.append(
            f"{nombre}: " + ", ".join(f"{g} {sub.loc[g, 'plan']}" for g in GRUPOS if g in sub.index)
        )
    lineas += ["", "**Sensibilidad** (±20 %; hora de dormir ±1 h)"]
    for v, grupo in cambios.groupby(cambios, sort=False):
        nombres = " y ".join(", ".join(grupo.index).rsplit(", ", 1))
        lineas.append(
            f"{nombres}: cambian {int(v)} de 6 decisiones." if v else f"{nombres}: no la cambian."
        )
    _texto(f, 0.6, y0, lineas, tam=12.5, ancho=0.35)
    _simple(
        f,
        (0.6, 0.08, 0.35, 0.17),
        [
            "Quien se acuesta antes o necesita dormir con menos cafeína debe elegir un plan más suave."
        ],
    )
    laminas.append(f)

    # Lámina 12: recomendación, guía por tipo e implementación (quién, cómo, costo, indicador).
    f, y0 = _lamina(
        "Recomendación",
        "Una guía por tipo: plan, hora límite y tope diario",
        12,
        total,
    )
    for i, g in enumerate(GRUPOS):
        r = g_.loc[g]
        _caja(
            f,
            (0.05 + 0.31 * i, 0.42, 0.28, 0.36),
            [
                f"**Plan {r['plan']}** · {num(r['horas_efecto'])} h con efecto",
                *_tomas(r["descripcion"]),
                f"Última bebida: {hora_texto(r['hora_limite_ultima_toma'])}",
                f"Tope con esos horarios: {r['maximo_diario_mg']:.0f} mg",
                f"Duerme bien el {r['pct_personas_duermen_bien']:.0f} % del grupo",
            ],
            f"Eliminación {g}",
            tam=13,
        )
    # Fila de cuatro recuadros pequeños con la implementación.
    for i, (titulo, texto) in enumerate(
        [
            ("Quién y cuándo", "Vida Estudiantil, dos semanas antes de exámenes."),
            ("Cómo", "Afiches con código QR a la aplicación web."),
            ("Costo", "Impresión y alojamiento en Railway (≈ 5 USD/mes)."),
            ("Indicador", "Encuesta antes y después: hora de la última toma y horas de sueño."),
        ]
    ):
        _caja(f, (0.05 + 0.2267 * i, 0.19, 0.21, 0.2), [texto], titulo, tam=12, fondo=VERDE_SUAVE)
    _texto(
        f,
        0.05,
        0.15,
        [
            "Riesgo: el plan protege a la persona típica, no a todo el grupo. La aplicación ofrece "
            f"una opción segura (≥ {COBERTURA_PRUDENTE:.0f} % del grupo) y, si alguien no conoce "
            "su tipo, debe seguir la guía lenta.",
        ],
        tam=12,
        ancho=0.9,
    )
    laminas.append(f)

    # Lámina 13: referencias (sin las etiquetas HTML de reportlab).
    f, y0 = _lamina("Referencias", "Referencias", 13, total)
    y = y0
    for r in REFERENCIAS:
        texto = r.replace("<i>", "").replace("</i>", "").replace("&amp;", "&")
        y = _texto(f, 0.05, y, [texto], tam=11, ancho=0.9) - 0.018
    laminas.append(f)

    # Lámina 14: cierre con la frase, las tarjetas de grupo, preguntas y límites.
    f, y0 = _lamina("Recomendación", "En una frase", 14, total)
    _texto(f, 0.05, y0, [frase], tam=20, ancho=0.9, color=VERDE_OSCURO, peso="bold")
    for caja, g in zip(tarjetas, GRUPOS, strict=True):
        _tarjeta_grupo(f, (caja[0], 0.17, caja[2], 0.36), c, g)
    f.text(0.95, 0.58, "Gracias · ¿Preguntas?", fontsize=14, color=VERDE, weight="bold", ha="right")
    _texto(
        f,
        0.05,
        0.13,
        [
            "Deja de valer si cambia la hora de acostarse o si el umbral de sueño es más estricto. "
            "Datos simulados con fines didácticos: no es una recomendación médica.",
        ],
        tam=11,
        ancho=0.9,
        color=GRIS_TEXTO,
    )
    laminas.append(f)

    # Guarda cada lámina como una página del PDF y libera la memoria de la figura.
    with PdfPages(destino) as pdf:
        for lam in laminas:
            pdf.savefig(lam)
            plt.close(lam)
    return len(laminas)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------


def main() -> None:
    """Regenera resultados y los tres PDF."""
    # Recalcula el análisis y guarda tablas y figuras actualizadas.
    analisis = AnalisisCafeina.desde_excel()
    analisis.calcular_tablas()
    reporte.guardar_tablas(analisis.tablas)
    reporte.guardar_figuras(reporte.figuras(analisis))
    # Prepara fuentes y cifras, y genera la ficha, el resumen y la presentación.
    _registrar_fuentes()
    cifras = Cifras(analisis)
    DIR_INFORME.mkdir(exist_ok=True)
    DIR_PRESENTACION.mkdir(exist_ok=True)
    construir_ficha(cifras, DIR_INFORME / "ficha_tecnica.pdf")
    construir_resumen(cifras, DIR_INFORME / "resumen_ejecutivo.pdf")
    n = construir_presentacion(
        cifras, DIR_PRESENTACION / "presentacion.pdf", DIR_PRESENTACION / "captura_app.png"
    )
    print(f"PDF generados en {DIR_INFORME} y {DIR_PRESENTACION} ({n} diapositivas)")


if __name__ == "__main__":
    main()
