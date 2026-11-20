"""Regenera todas las tablas y figuras en ``resultados/``.

Uso:  python -m src.reporte

Flujo: AnalisisCafeina (pipeline) -> tablas CSV en resultados/tablas (y todas
juntas en resultados/resultados.xlsx) y figuras PNG (fig01 a fig12) en
resultados/figuras, que luego usan la ficha técnica, las diapositivas y el cuaderno.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from src import exportar
from src import graficos as gr
from src.config import DIR_FIGURAS, DIR_RESULTADOS, DIR_TABLAS
from src.pipeline import AnalisisCafeina

# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------


def guardar_tablas(tablas: dict[str, pd.DataFrame]) -> list[str]:
    """Escribe cada tabla como CSV y todas juntas en ``resultados/resultados.xlsx``.

    Los CSV usan ';' y coma decimal para abrirse en casillas con Excel en español.
    Salidas: lista de nombres de archivo escritos.
    """
    return exportar.guardar(tablas, DIR_TABLAS, DIR_RESULTADOS / "resultados.xlsx")


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------


def figuras(a: AnalisisCafeina) -> dict[str, plt.Figure]:
    """Construye todas las figuras de la ficha técnica y las diapositivas."""
    t, p = a.tablas, a.param
    base = t["evaluacion_planes"]
    base = base[base["escenario"] == base["escenario"].iloc[0]]
    # Voluntario típico (vida media más cercana a la mediana) y el más lento (cola más grande)
    vidas = a.resultados["vida_media_h"]
    tipico = (vidas - vidas.median()).abs().idxmin()
    lento = vidas.idxmax()
    return {
        "fig01_perfiles": gr.fig_perfiles(a.conc_limpio, a.clasificados),
        "fig02_auc_voluntario": gr.fig_voluntario_desde_tablas(
            a.conc_limpio, a.resultados, tipico, p.ka, p.dosis_mg
        ),
        "fig03_auc_cola_grande": gr.fig_voluntario_desde_tablas(
            a.conc_limpio, a.resultados, lento, p.ka, p.dosis_mg
        ),
        "fig04_vida_media": gr.fig_vida_media(a.clasificados, t["factores_vida_media"]),
        "fig05_atencion": gr.fig_atencion(a.atencion, a.relacion, p.c_efecto),
        "fig06_verificacion": gr.fig_verificacion(t["validacion_auc"], t["verificacion_datos"]),
        "fig07_mapa_planes": gr.fig_mapa_planes(base),
        "fig08_planes_recomendados": gr.fig_planes_recomendados(
            t["guia_consumo"], a.planes, a.modelos, p
        ),
        "fig09_escenarios": gr.fig_escenarios(t["evaluacion_planes"], t["recomendaciones"]),
        "fig10_sensibilidad": gr.fig_sensibilidad(t["sensibilidad"], t["guia_consumo"]),
        "fig11_horas_limite": gr.fig_horas_limite(t["horas_limite"], p),
        "fig12_criterios": gr.fig_comparacion_criterios(
            t["guia_consumo"], t["guia_consumo_prudente"], t["planes_optimizados"]
        ),
    }


def guardar_figuras(figs: dict[str, plt.Figure]) -> list[str]:
    """Guarda cada figura como PNG (160 dpi) y la cierra."""
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    nombres = []
    for nombre, fig in figs.items():
        archivo = DIR_FIGURAS / f"{nombre}.png"
        fig.savefig(archivo, dpi=160, bbox_inches="tight")
        plt.close(fig)
        nombres.append(archivo.name)
    return nombres


# ---------------------------------------------------------------------------
# Punto de entrada: python -m src.reporte
# ---------------------------------------------------------------------------


def main() -> None:
    """Ejecuta el análisis completo y escribe resultados/."""
    analisis = AnalisisCafeina.desde_excel()
    analisis.calcular_tablas()
    tablas = guardar_tablas(analisis.tablas)
    figs = guardar_figuras(figuras(analisis))
    print(f"{len(tablas) - 1} tablas CSV en {DIR_TABLAS} y el libro {tablas[-1]}")
    print(f"{len(figs)} figuras en {DIR_FIGURAS}")
    print(analisis.tablas["guia_consumo"].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
