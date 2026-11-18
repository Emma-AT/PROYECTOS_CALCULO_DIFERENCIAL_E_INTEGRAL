"""Genera las tablas y figuras en resultados/. Uso: python -m src.reporte"""

import sys
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from src.escenarios import comparar, escalar_c, preparar, recomendar
from src.limpieza import cargar_datos
from src.modelo import densidad_weibull, potencia

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "resultados"


def figura_weibull(base: dict, ruta: Path) -> None:
    """Histograma del viento de 60 días con la densidad de Weibull ajustada."""
    malla = np.linspace(0, 25, 301)
    fig = Figure(figsize=(8, 5))
    ax = fig.subplots()
    ax.hist(base["viento"]["v_limpia_m_s"], bins=30, density=True, alpha=0.5, label="Datos")
    etiqueta = f"Weibull k={base['k60']:.2f}, c={base['c60']:.2f} m/s"
    ax.plot(malla, densidad_weibull(malla, base["k60"], base["c60"]), label=etiqueta)
    ax.set(title="Viento a 55 m (60 días)", xlabel="Velocidad (m/s)", ylabel="f(v) (s/m)")
    ax.legend()
    fig.savefig(ruta, dpi=200)


def figura_area_potencia(base: dict, ruta: Path) -> None:
    """Área sombreada P(v)·f(v): su integral es la potencia media P̄ de cada opción."""
    p = base["params"]
    malla = np.linspace(0, 25, 501)
    fig = Figure(figsize=(8, 5))
    ax = fig.subplots()
    for t in base["turbinas"]:
        c_h = escalar_c(p["c_anual_ms"], t.altura_m, p["h_ref_m"], p["alpha"])
        y = potencia(malla, t, base["rho_media"], p["rho_ref"]) * densidad_weibull(
            malla, p["k_anual"], c_h
        )
        ax.plot(malla, y, label=t.nombre)
        ax.fill_between(malla, y, alpha=0.25)
    ax.set(
        title="P(v)·f(v): el área es la potencia media",
        xlabel="Velocidad (m/s)",
        ylabel="P·f (kW·s/m)",
    )
    ax.legend()
    fig.savefig(ruta, dpi=200)


def main() -> None:
    """Corre todo el análisis y guarda resultados."""
    sys.stdout.reconfigure(encoding="utf-8")  # para imprimir ₡ en la consola de Windows
    SALIDA.mkdir(exist_ok=True)
    base = preparar(cargar_datos(RAIZ / "datos" / "P09_C-01_AGUIRRE.xlsx"))
    p = base["params"]
    tabla = comparar(base, p["alpha"], p["precio"])
    tabla.to_csv(SALIDA / "comparacion_opciones.csv", index=False)
    figura_weibull(base, SALIDA / "weibull_60_dias.png")
    figura_area_potencia(base, SALIDA / "area_potencia_media.png")
    print(f"Pérdidas calibradas L = {base['L']:.1%}")
    print(tabla.to_string(index=False))
    print(recomendar(tabla))
    print("Con precio 20 % menor:", recomendar(tabla, "vpn_precio_80_colones"))


if __name__ == "__main__":
    main()
