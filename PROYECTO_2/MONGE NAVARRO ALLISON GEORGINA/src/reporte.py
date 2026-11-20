"""Genera todas las tablas y figuras en la carpeta resultados/.

Uso (desde la carpeta del proyecto):

    python -m src.reporte

Así cualquier persona puede regenerar los resultados con un solo comando.
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src import escenarios as es
from src import graficos as gr
from src.datos import RAIZ, RUTA_POR_DEFECTO, cargar_base
from src.limpieza import limpiar_conteos, resumen_limpieza
from src.modelo import (
    CurvaDePaso,
    mejor_turno,
    perfil_horario,
    total_diario,
    totales_diarios,
    verificar_total,
)

SALIDA = RAIZ / "resultados"


def calcular_todo(ruta: Path | str = RUTA_POR_DEFECTO) -> dict[str, object]:
    """Corre todo el análisis y devuelve las tablas en un diccionario."""
    base = cargar_base(ruta)
    p = base.parametros
    limpio = limpiar_conteos(base.conteos)
    totales = totales_diarios(limpio, p.hi, p.hf)
    t = totales["dia"]

    resumen = pd.DataFrame(
        [CurvaDePaso(e, t, totales[e]).resumen() for e in [*es.ESPECIES, "Total"]]
    )
    verificacion = pd.DataFrame(
        [{"serie": e, **verificar_total(totales[e], t)} for e in [*es.ESPECIES, "Total"]]
    )
    escenarios = es.comparar_escenarios(totales, limpio, p)
    optimo = escenarios[escenarios["nombre"].str.startswith("Óptima")].iloc[0]
    perfil = perfil_horario(limpio, dias=(optimo["inicio"], optimo["fin"]))
    h0 = float(perfil["hora"].min())
    total_dia = total_diario(perfil["Total"], p.hi, p.hf, inicio_obs=h0)
    turnos = mejor_turno(perfil["Total"], p.horas_turno, h0, total_dia)
    tabla_turnos = pd.DataFrame(
        {
            "hora_inicio": turnos.inicios,
            "hora_fin": turnos.inicios + p.horas_turno,
            "aves_promedio_dia": turnos.aves_por_inicio,
            "fraccion_del_dia": turnos.aves_por_inicio / total_dia,
        }
    )
    return {
        "base": base,
        "limpio": limpio,
        "totales": totales,
        "limpieza": resumen_limpieza(limpio),
        "atipicos": limpio[limpio["correccion"] == "atípico"][
            ["fecha", "hora_inicio", "especie", "aves_contadas", "aves_limpias"]
        ],
        "resumen_especies": resumen,
        "verificacion": verificacion,
        "escenarios": escenarios,
        "turnos": tabla_turnos,
        "perfil": perfil,
        "extremos": pd.DataFrame(
            [es.comprobar_extremos(totales, optimo["inicio"], p.dias_campana)]
        ),
        "sens_duracion": es.sensibilidad_duracion(totales, p, [7, 14, 21, 28, 35]),
        "sens_turno": es.sensibilidad_turno(limpio, p, [2, 3, 4, 5, 6, 7, 8]),
        "sens_vuelo": es.sensibilidad_vuelo(limpio, p, [-0.5, 0.0, 0.5]),
        "sens_limpieza": es.sensibilidad_limpieza(base.conteos, p, [3, 5, 10]),
        "recomendacion": es.recomendacion(escenarios),
        "parametros": pd.DataFrame([asdict(p)]),
    }


def guardar_figuras(r: dict[str, object], carpeta: Path) -> None:
    """Dibuja y guarda las figuras en PNG."""
    p = r["base"].parametros  # type: ignore[attr-defined]
    totales: pd.DataFrame = r["totales"]  # type: ignore[assignment]
    limpio: pd.DataFrame = r["limpio"]  # type: ignore[assignment]
    esc: pd.DataFrame = r["escenarios"]  # type: ignore[assignment]
    optimo = esc[esc["nombre"].str.startswith("Óptima")].iloc[0]

    # Día de ejemplo: el de mayor corrección por "cero de más".
    atip = limpio[limpio["correccion"] == "atípico"]
    ejemplo = atip.loc[atip["aves_contadas"].idxmax()]
    dia = limpio[(limpio["dia"] == ejemplo["dia"]) & (limpio["especie"] == ejemplo["especie"])]
    fecha_txt = pd.Timestamp(ejemplo["fecha"]).strftime("%d/%m")

    figuras = {
        "fig1_conteos_diarios": gr.conteos_diarios(
            totales, es.ESPECIES, optimo["inicio"], p.dias_campana, p.inicio_tradicional
        ),
        "fig2_curva_acumulada": gr.curva_acumulada(totales, [*es.ESPECIES, "Total"]),
        "fig3_funcion_G": gr.funcion_G(totales, p.dias_campana, p.inicio_tradicional),
        "fig4_condicion_optimo": gr.condicion_optimo(totales, p.dias_campana),
        "fig5_perfil_turno": gr.perfil_y_turno(
            r["perfil"],
            optimo["hora_inicio"],
            p.horas_turno,
            p.hi,
            p.hf,  # type: ignore[arg-type]
        ),
        "fig6_integral_un_dia": gr.integral_de_un_dia(
            dia["aves_limpias"].to_numpy(),
            p.hi,
            p.hf,
            f"Total del {fecha_txt} ({ejemplo['especie']}) = área bajo la tasa de paso",
        ),
        "fig7_limpieza": gr.antes_y_despues(
            dia["aves_contadas"].to_numpy(),
            dia["aves_limpias"].to_numpy(),
            f"Conteo con un cero de más: {ejemplo['especie']}, {fecha_txt}",
        ),
        "fig8_escenarios": gr.barras_escenarios(esc),
    }
    for nombre, fig in figuras.items():
        fig.savefig(carpeta / f"{nombre}.png", dpi=160)
        gr.plt.close(fig)


def main(ruta: Path | str = RUTA_POR_DEFECTO) -> None:
    """Calcula todo y guarda tablas (CSV), figuras (PNG) y la recomendación."""
    SALIDA.mkdir(exist_ok=True)
    r = calcular_todo(ruta)
    for nombre, valor in r.items():
        if isinstance(valor, pd.DataFrame) and nombre not in ("limpio", "perfil"):
            valor.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    r["limpio"].to_csv(SALIDA / "conteos_limpios.csv", index=False, encoding="utf-8-sig")  # type: ignore[union-attr]
    (SALIDA / "recomendacion.txt").write_text(str(r["recomendacion"]), encoding="utf-8")
    guardar_figuras(r, SALIDA)
    print(r["recomendacion"])
    print(f"Resultados guardados en: {SALIDA}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else RUTA_POR_DEFECTO)
