"""Paleta de colores del proyecto y estilo de los gráficos.

Paleta base tomada de la referencia (azul marino oscuro con acento lila-azulado).
Los colores por grupo se derivan de ella para que las cuatro líneas se distingan.
"""

import matplotlib.pyplot as plt

FUENTE = "Fuente: datos simulados del Proyecto 5 (P05_C-10), Mediación Virtual, Sede del Sur."

PALETA = {
    "fondo": "#101728",  # fondo de la página
    "fondo_profundo": "#0a0f20",  # barra lateral
    "tarjeta": "#141c30",  # tarjetas y área de los gráficos
    "borde": "#24304a",
    "texto": "#e9edf7",
    "texto_suave": "#a0abc2",
    "tenue": "#7c879f",
    "acento": "#8c99ff",
    "alerta": "#ff7a8a",  # ventana de las últimas 24 h
}

# Colores por grupo sobre fondo oscuro (G03, la recomendada, usa el acento)
COLORES_OSCURO = {"G01": "#7c879f", "G02": "#5eb5e6", "G03": "#8c99ff", "G04": "#f2b880"}
# Variante más profunda para fondo blanco (ficha técnica impresa)
COLORES_CLARO = {"G01": "#64748b", "G02": "#2a8bbd", "G03": "#5b6bf0", "G04": "#c07a2c"}


# Líneas y rellenos de los gráficos sobre fondo blanco (los de la app y la ficha impresa)
LINEAS_CLARO = {"linea": "#111827", "hist": "#94a3b8", "alerta": "#dc2626"}


def aplicar_tema(oscuro=True):
    """Ajusta matplotlib. Oscuro para la app; claro para figuras impresas."""
    if oscuro:
        p = PALETA
        plt.rcParams.update(
            {
                "figure.facecolor": p["tarjeta"],
                "axes.facecolor": p["tarjeta"],
                "savefig.facecolor": p["tarjeta"],
                "axes.edgecolor": p["borde"],
                "axes.labelcolor": p["texto_suave"],
                "text.color": p["texto"],
                "xtick.color": p["texto_suave"],
                "ytick.color": p["texto_suave"],
                "grid.color": p["borde"],
                "legend.facecolor": p["fondo"],
                "legend.edgecolor": p["borde"],
                "legend.labelcolor": p["texto"],
                "axes.titlecolor": p["texto"],
            }
        )
    else:
        plt.rcdefaults()
