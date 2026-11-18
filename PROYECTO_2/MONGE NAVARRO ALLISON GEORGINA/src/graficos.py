"""Gráficos del proyecto (los usan el reporte, el cuaderno y la app web).

Reglas: cada gráfico tiene título, ejes con unidades y las áreas que
representan integrales van sombreadas. Cada especie tiene siempre el
mismo color en todos los gráficos.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, PercentFormatter

from src.modelo import (
    acumulada,
    colas_triangulares,
    fecha_percentil,
    media_movil,
    mejor_ventana,
)

# Un color fijo por especie (paleta apta para daltonismo).
COLORES = {
    "Gavilán aludo": "#2a78d6",
    "Gavilán de Swainson": "#eb6834",
    "Zopilote cabecirrojo": "#1baf7a",
    "Total": "#0b0b0b",
}
GRIS_AREA = "#b9b8b2"
TINTA = "#52514e"

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#e6e5e0",
        "grid.linewidth": 0.8,
        "axes.edgecolor": TINTA,
        "axes.labelcolor": "#0b0b0b",
        "xtick.color": TINTA,
        "ytick.color": TINTA,
        "lines.linewidth": 2,
        "font.size": 10,
        "axes.titleweight": "bold",
    }
)

MILES = FuncFormatter(lambda v, _: f"{v / 1000:,.0f}")


def _nueva(ancho: float = 9, alto: float = 4.5) -> tuple[Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(ancho, alto), layout="constrained")
    return fig, ax


def conteos_diarios(
    totales: pd.DataFrame, especies: list[str], inicio: float, L: int, inicio_trad: float
) -> Figure:
    """Aves por día de cada especie, con la campaña óptima sombreada.

    El área gris es G(a): la integral de n(t) dentro de la campaña.
    La campaña tradicional se marca con líneas punteadas.
    """
    fig, ax = _nueva()
    t = totales["dia"].to_numpy(dtype=float)
    for especie in especies:
        ax.plot(t, totales[especie], color=COLORES[especie], label=especie)
    dentro = (t >= inicio) & (t <= inicio + L)
    ax.fill_between(
        t,
        0,
        totales["Total"],
        where=dentro,
        color=GRIS_AREA,
        alpha=0.6,
        label="Campaña óptima (área = aves registradas)",
    )
    ax.plot(t, totales["Total"], color=COLORES["Total"], lw=1.2, ls="-", label="Total")
    for borde in (inicio_trad, inicio_trad + L):
        ax.axvline(borde, color=TINTA, ls=":", lw=1.5)
    ax.text(inicio_trad + 0.3, ax.get_ylim()[1] * 0.55, "campaña\ntradicional", color=TINTA)
    ax.set(
        title="Paso diario de rapaces y campaña óptima",
        xlabel="Días desde el 20 de septiembre (días)",
        ylabel="Aves por día (miles de aves/día)",
    )
    ax.yaxis.set_major_formatter(MILES)
    ax.legend(frameon=False, loc="upper left")
    return fig


def curva_acumulada(totales: pd.DataFrame, especies: list[str]) -> Figure:
    """F(t) de cada especie con las fechas del 5, 50 y 95 % marcadas."""
    fig, ax = _nueva()
    t = totales["dia"].to_numpy(dtype=float)
    for especie in especies:
        F = acumulada(totales[especie].to_numpy(), t)
        ax.plot(t, F, color=COLORES[especie], label=especie)
        for p in (0.05, 0.5, 0.95):
            fecha = fecha_percentil(F, t, p)
            ax.plot(fecha, p, "o", ms=6, color=COLORES[especie], mec="white", mew=1.5)
    for p in (0.05, 0.5, 0.95):
        ax.axhline(p, color=TINTA, lw=0.8, ls="--")
        ax.text(t[-1], p, f" {p:.0%}", va="center", color=TINTA)
    ax.set(
        title="Fracción acumulada del paso F(t)",
        xlabel="Días desde el 20 de septiembre (días)",
        ylabel="Fracción del paso ya ocurrida",
        ylim=(0, 1.02),
    )
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(frameon=False, loc="lower right")
    return fig


def funcion_G(totales: pd.DataFrame, L: int, inicio_trad: float) -> Figure:
    """G(a)/N: fracción del paso que registra una campaña que empieza el día a."""
    fig, ax = _nueva(9, 4)
    t = totales["dia"].to_numpy(dtype=float)
    r = mejor_ventana(totales["Total"].to_numpy(), L, t)
    frac = r.G / r.G.max() * r.fraccion
    ax.plot(r.inicios, frac, color=COLORES["Total"])
    ax.plot(r.inicio, r.fraccion, "o", ms=9, color=COLORES["Total"], mec="white", mew=2)
    ax.annotate(
        f"óptimo: día {r.inicio:.0f} ({r.fraccion:.0%})",
        (r.inicio, r.fraccion),
        xytext=(0, 12),
        textcoords="offset points",
        ha="center",
        color="#0b0b0b",
    )
    i_trad = int(np.argmin(np.abs(r.inicios - inicio_trad)))
    ax.plot(inicio_trad, frac[i_trad], "s", ms=8, color=TINTA)
    ax.annotate(
        f"tradicional: día {inicio_trad:.0f} ({frac[i_trad]:.0%})",
        (inicio_trad, frac[i_trad]),
        xytext=(10, -5),
        textcoords="offset points",
        color=TINTA,
    )
    ax.set(
        title=f"G(a): fracción del paso registrada por una campaña de {L} días",
        xlabel="Día de inicio de la campaña a (días desde el 20 de septiembre)",
        ylabel="G(a) / N",
        ylim=(None, r.fraccion * 1.12),
    )
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    return fig


def condicion_optimo(totales: pd.DataFrame, L: int, ancho: int = 5) -> Figure:
    """Muestra G'(a) = n(a+L) - n(a): se anula cerca del inicio óptimo."""
    fig, ax = _nueva(9, 4)
    t = totales["dia"].to_numpy(dtype=float)
    suave = media_movil(totales["Total"].to_numpy(), ancho)
    k = int(L)
    ax.plot(t[:-k], suave[:-k], color=COLORES["Gavilán aludo"], label="n(a): primer día")
    ax.plot(t[:-k], suave[k:], color=COLORES["Gavilán de Swainson"], label="n(a + L): último día")
    r = mejor_ventana(totales["Total"].to_numpy(), L, t)
    ax.axvline(r.inicio, color=TINTA, ls=":", lw=1.5)
    ax.text(r.inicio + 0.3, ax.get_ylim()[1] * 0.95, "inicio óptimo", color=TINTA, va="top")
    ax.set(
        title=f"Condición del óptimo: n(a) = n(a + L)  (media móvil de {ancho} días)",
        xlabel="Día de inicio de la campaña a (días)",
        ylabel="Aves por día (miles de aves/día)",
    )
    ax.yaxis.set_major_formatter(MILES)
    ax.legend(frameon=False)
    return fig


def perfil_y_turno(
    perfil: pd.DataFrame, hora_ini: float, horas: int, hi: float, hf: float
) -> Figure:
    """Perfil horario promedio, colas triangulares y el mejor turno sombreado."""
    fig, ax = _nueva(9, 4)
    h = perfil["hora"].to_numpy(dtype=float)
    y = perfil["Total"].to_numpy(dtype=float)
    en_turno = (h >= hora_ini) & (h < hora_ini + horas)
    ax.bar(
        h,
        y,
        width=0.96,
        align="edge",
        color=np.where(en_turno, COLORES["Total"], GRIS_AREA),
        edgecolor="white",
        linewidth=2,
    )
    # Colas triangulares (horas no observadas).
    h0, h1 = h[0], h[-1] + 1
    ax.fill([hi, h0, h0], [0, y[0], 0], color=GRIS_AREA, alpha=0.5, hatch="//", ec=TINTA)
    ax.fill([h1, h1, hf], [0, y[-1], 0], color=GRIS_AREA, alpha=0.5, hatch="//", ec=TINTA)
    ax.text(hora_ini + horas / 2, y.max() * 1.04, "mejor turno", ha="center", color="#0b0b0b")
    ax.set_ylim(0, y.max() * 1.15)
    ax.set(
        title="Aves promedio por hora y mejor turno de observación",
        xlabel="Hora del día (h)",
        ylabel="Aves por hora (miles de aves/h)",
        xlim=(hi - 0.3, hf + 0.3),
    )
    ax.set_xticks(np.arange(int(np.floor(hi)), int(np.ceil(hf)) + 1))
    ax.yaxis.set_major_formatter(MILES)
    return fig


def integral_de_un_dia(conteos: np.ndarray, hi: float, hf: float, titulo: str) -> Figure:
    """Explica N_d: bloques horarios + dos triángulos = área bajo la tasa."""
    fig, ax = _nueva(9, 4)
    h = 7 + np.arange(conteos.size)
    ax.bar(
        h,
        conteos,
        width=1,
        align="edge",
        color=GRIS_AREA,
        edgecolor="white",
        lw=2,
        label="horas contadas (bloques)",
    )
    antes, despues = colas_triangulares(conteos, hi, hf)
    ax.fill(
        [hi, 7, 7],
        [0, conteos[0], 0],
        color=COLORES["Gavilán aludo"],
        alpha=0.5,
        label=f"cola antes de las 7:00 ≈ {antes:,.0f} aves",
    )
    ax.fill(
        [16, 16, hf],
        [0, conteos[-1], 0],
        color=COLORES["Gavilán de Swainson"],
        alpha=0.5,
        label=f"cola después de las 16:00 ≈ {despues:,.0f} aves",
    )
    ax.set(title=titulo, xlabel="Hora del día (h)", ylabel="Tasa de paso (aves/h)")
    ax.legend(frameon=False, loc="upper right")
    return fig


def antes_y_despues(original: np.ndarray, limpio: np.ndarray, titulo: str) -> Figure:
    """Un día con un 'cero de más': conteo original vs. corregido."""
    fig, ax = _nueva(9, 4)
    h = 7 + np.arange(original.size)
    ax.plot(h, original, "o-", color=COLORES["Gavilán de Swainson"], label="original", ms=8)
    ax.plot(h, limpio, "o-", color=COLORES["Gavilán aludo"], label="corregido", ms=8)
    ax.set_yscale("log")
    ax.set(
        title=titulo, xlabel="Hora de inicio del bloque (h)", ylabel="Aves contadas (escala log)"
    )
    ax.legend(frameon=False)
    return fig


def barras_escenarios(escenarios: pd.DataFrame) -> Figure:
    """Fracción de aves registrada por cada escenario."""
    fig, ax = _nueva(9, 3.6)
    nombres = escenarios["nombre"]
    valores = escenarios["frac_registrada"]
    mejor = valores.idxmax()
    colores = [COLORES["Total"] if i == mejor else GRIS_AREA for i in escenarios.index]
    ax.barh(nombres, valores, color=colores, height=0.6)
    for i, v in enumerate(valores):
        ax.text(v + 0.01, i, f"{v:.1%}", va="center", color="#0b0b0b")
    ax.invert_yaxis()
    ax.set(
        title="Fracción del paso que registra cada campaña (fechas × turno)",
        xlabel="Aves registradas / aves de la temporada",
        xlim=(0, max(valores) * 1.2),
    )
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", visible=False)
    return fig
