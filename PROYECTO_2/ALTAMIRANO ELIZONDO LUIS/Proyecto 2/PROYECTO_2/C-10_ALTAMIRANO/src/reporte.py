"""Genera las tablas (CSV) y figuras (PNG) del análisis en resultados/.

Uso:  python -m src.reporte
Escribe las figuras en versión clara (ficha técnica impresa) en resultados/ y en versión
oscura (diapositivas con la paleta del proyecto) en resultados/oscuro/.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy import integrate  # solo para comparar con los métodos propios

from src.escenarios import (
    bootstrap_diferencia,
    elegir_estrategia,
    resumen_grupo,
    sensibilidad_tratamientos,
    sensibilidad_umbral,
    umbral_de_cambio,
)
from src.estilo import COLORES_CLARO, COLORES_OSCURO, FUENTE, PALETA, aplicar_tema
from src.limpieza import cargar_datos, depurar_entregas, informe_depuracion, leer_parametros
from src.modelo import (
    densidad_modelo,
    error_relativo,
    f_empirica,
    f_modelo,
    fraccion_ultimas,
    ip_modelo,
    ip_modelo_cerrado,
    simpson,
    trapecio,
)

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DATOS = RAIZ / "datos" / "P05_C-10_ALTAMIRANO.xlsx"
SALIDA = RAIZ / "resultados"


def _tema(nombre: str) -> dict:
    """Aplica el tema de matplotlib y devuelve los colores que usan las figuras."""
    oscuro = nombre == "oscuro"
    aplicar_tema(oscuro)
    if oscuro:
        return {
            "grupos": COLORES_OSCURO,
            "linea": PALETA["texto"],
            "hist": PALETA["tenue"],
            "alerta": PALETA["alerta"],
            "obs": PALETA["texto_suave"],
            "mod": PALETA["acento"],
            "fuente": PALETA["tenue"],
        }
    return {
        "grupos": COLORES_CLARO,
        "linea": "#111827",
        "hist": "#94a3b8",
        "alerta": "#dc2626",
        "obs": "#334155",
        "mod": COLORES_CLARO["G03"],
        "fuente": "#6b7280",
    }


def _fuente(fig: Figure, c: dict) -> None:
    fig.text(0.99, 0.005, FUENTE, ha="right", va="bottom", fontsize=7, color=c["fuente"])


def figura_acumulada(dep: pd.DataFrame, resumen: pd.DataFrame, c: dict) -> Figure:
    """F empírica y del modelo por grupo; el área entre F y 1 (en horas/T) es el IP."""
    fig, ejes = plt.subplots(2, 2, figsize=(10, 7.2), sharex=True, sharey=True)
    for ax, (_, r) in zip(ejes.ravel(), resumen.iterrows(), strict=False):
        g, T = r["grupo"], r["T_h"]
        s = dep[(dep["grupo"] == g) & ~dep["tardia"]]
        malla, F = f_empirica(s["tau"])
        col = c["grupos"][g]
        ax.fill_between(malla, F, 1, color=col, alpha=0.2, label=f"IP = {r['ip_obs']:.2f} (área)")
        ax.step(malla, F, where="post", color=col, lw=1.8, label="F observada")
        ax.plot(
            malla,
            f_modelo(malla * T, r["k"], T),
            color=c["linea"],
            ls="--",
            lw=1.2,
            label=f"modelo (k = {r['k']:.3f} 1/h)",
        )
        ax.set_title(f"{g}: {r['estrategia']}", fontsize=9)
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(alpha=0.3)
    for ax in ejes[1]:
        ax.set_xlabel("Fracción del plazo transcurrida, t/T (sin unidad)")
    for ax in ejes[:, 0]:
        ax.set_ylabel("Fracción acumulada de entregas")
    fig.suptitle("Entregas acumuladas por grupo y área que representa el índice de procrastinación")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    _fuente(fig, c)
    return fig


def figura_densidad(dep: pd.DataFrame, resumen: pd.DataFrame, ventana_h: float, c: dict) -> Figure:
    """Densidad f_k(t) en 1/h, histograma observado y últimas 24 h sombreadas."""
    fig, ejes = plt.subplots(2, 2, figsize=(10, 7.2), sharey=True)
    for ax, (_, r) in zip(ejes.ravel(), resumen.iterrows(), strict=False):
        g, T = r["grupo"], r["T_h"]
        s = dep[(dep["grupo"] == g) & ~dep["tardia"]]
        ax.hist(
            s["horas"],
            bins=np.linspace(0, T, 25),
            density=True,
            color=c["grupos"][g],
            alpha=0.45,
            label="observado",
        )
        t = np.linspace(0, T, 400)
        ax.plot(t, densidad_modelo(t, r["k"], T), color=c["linea"], lw=1.5, label="modelo f_k")
        m = t >= T - ventana_h
        ax.fill_between(
            t[m],
            0,
            densidad_modelo(t[m], r["k"], T),
            color=c["alerta"],
            alpha=0.4,
            label=f"últimas {ventana_h:.0f} h: obs {100 * r['ultimas_obs']:.0f} %, "
            f"modelo {100 * r['ultimas_modelo']:.0f} %",
        )
        ax.set_title(f"{g}: {r['estrategia']}", fontsize=9)
        ax.set_xlabel("Horas desde la apertura (h)")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)
    for ax in ejes[:, 0]:
        ax.set_ylabel("Densidad de entregas (1/h)")
    fig.suptitle("Densidad de entregas: observada y del modelo, con las últimas 24 h sombreadas")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    _fuente(fig, c)
    return fig


def figura_ultimas(resumen: pd.DataFrame, c: dict) -> Figure:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    x = np.arange(len(resumen))
    ax.bar(x - 0.2, 100 * resumen["ultimas_obs"], 0.4, label="Observada", color=c["obs"])
    ax.bar(x + 0.2, 100 * resumen["ultimas_modelo"], 0.4, label="Modelo", color=c["mod"])
    ax.set_xticks(x, resumen["grupo"])
    ax.set_ylabel("Entregas en las últimas 24 h (% de las entregas a tiempo)")
    ax.set_xlabel("Grupo")
    ax.set_title("Entregas de las últimas 24 h: observada y del modelo")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    _fuente(fig, c)
    return fig


def figura_notas(resumen: pd.DataFrame, elegida: str, c: dict) -> Figure:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    colores = [c["grupos"][g] for g in resumen["grupo"]]
    barras = ax.bar(resumen["grupo"], resumen["nota_media"], color=colores)
    for b, h in zip(barras, resumen["horas_docente"], strict=False):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.5,
            f"{b.get_height():.1f}\n({h:.1f} h docentes)",
            ha="center",
            fontsize=8,
        )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Nota media (puntos, de 0 a 100)")
    ax.set_xlabel("Grupo")
    ax.set_title(f"Nota media por grupo (estrategia elegida: {elegida})")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    _fuente(fig, c)
    return fig


def _cola(t: float, k: float, T: float) -> float:
    """1 - F_k(t): lo que integra scipy.quad para comparar con Simpson."""
    return 1.0 - float(f_modelo(t, k, T))


def tabla_verificacion(res: pd.DataFrame, dep: pd.DataFrame, ventana_h: float) -> pd.DataFrame:
    """Cada integral importante se obtiene de dos formas y se reporta el error relativo.

    scipy.integrate se usa solo para comparar con los métodos propios.
    """
    filas = []

    def fila(g: str, integral: str, nombre_a: str, a: float, nombre_b: str, b: float) -> None:
        filas.append(
            {
                "grupo": g,
                "integral": integral,
                "método A": nombre_a,
                "valor A": a,
                "método B": nombre_b,
                "valor B": b,
                "error relativo": error_relativo(a, b),
            }
        )

    for _, r in res.iterrows():
        g, k, T = r["grupo"], float(r["k"]), float(r["T_h"])
        s = dep[(dep["grupo"] == g) & ~dep["tardia"] & ~dep["antes_apertura"]]
        malla, F = f_empirica(s["tau"])
        ip_trap = trapecio(1.0 - F, malla)
        ip_simp = ip_modelo(k, T, n=4000)
        dens = partial(densidad_modelo, k=k, T=T)
        fila(
            g,
            "∫ f_k dt en [0, T] (sin unidad)",
            "Simpson propio",
            simpson(dens, 0.0, T, 20000),
            "valor exacto",
            1.0,
        )
        fila(
            g,
            "IP del modelo (sin unidad)",
            "Simpson propio",
            ip_simp,
            "fórmula cerrada",
            ip_modelo_cerrado(k, T),
        )
        fila(
            g,
            "IP del modelo (sin unidad)",
            "Simpson propio",
            ip_simp,
            "scipy.integrate.quad",
            integrate.quad(_cola, 0.0, T, args=(k, T))[0] / T,
        )
        fila(
            g,
            f"fracción de las últimas {ventana_h:.0f} h",
            "Simpson propio",
            simpson(dens, T - ventana_h, T, 4000),
            "fórmula ln(1+hk)/ln(1+kT)",
            fraccion_ultimas(k, T, ventana_h),
        )
        fila(
            g,
            "IP observado (sin unidad)",
            "trapecio propio",
            ip_trap,
            "promedio de t/T",
            float(s["tau"].mean()),
        )
        fila(
            g,
            "IP observado (sin unidad)",
            "trapecio propio",
            ip_trap,
            "scipy.integrate.trapezoid",
            float(integrate.trapezoid(1.0 - F, malla)),
        )
    return pd.DataFrame(filas)


FORMULAS = {
    "01_ip": r"$IP=\dfrac{1}{T}\int_0^T\left[1-F(t)\right]dt$",
    "02_ip_es_promedio": r"$\int_0^1\tau f(\tau)\,d\tau=\left[\tau\,(F-1)\right]_0^1+\int_0^1\left(1-F\right)d\tau$",
    "03_densidad": r"$f_k(t)=\dfrac{k}{\ln(1+kT)\,\left[1+k(T-t)\right]}$",
    "04_acumulada": r"$F_k(t)=1-\dfrac{\ln\left(1+k(T-t)\right)}{\ln(1+kT)}$",
    "05_integra_uno": r"$\int_0^T f_k(t)\,dt=\dfrac{1}{\ln(1+kT)}\int_1^{1+kT}\dfrac{du}{u}=1$",
    "06_ultimas_24h": r"$\int_{T-24}^{T} f_k(t)\,dt=\dfrac{\ln(1+24k)}{\ln(1+kT)}$",
    "07_ip_modelo": r"$IP(k)=1+\dfrac{1}{kT}-\dfrac{1}{\ln(1+kT)}$",
}


def generar_formulas(carpeta: Path) -> None:
    """Escribe las fórmulas de las diapositivas como PNG con fondo transparente y letra clara."""
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, texto in FORMULAS.items():
        fig = plt.figure(figsize=(8, 1.4))
        fig.text(0.5, 0.5, texto, ha="center", va="center", fontsize=30, color=PALETA["texto"])
        fig.savefig(
            carpeta / f"{nombre}.png",
            dpi=300,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.12,
        )
        plt.close(fig)


def generar(ruta_datos: Path = RUTA_DATOS, salida: Path = SALIDA) -> dict:
    """Calcula todo y escribe tablas y figuras. Devuelve un diccionario con los resultados."""
    salida = Path(salida)
    (salida / "oscuro").mkdir(parents=True, exist_ok=True)
    hojas = cargar_datos(ruta_datos)
    p = leer_parametros(hojas["Parametros"])
    dep = depurar_entregas(hojas["Entregas"], hojas["Tareas"], p["nota_max"])
    res = resumen_grupo(dep, hojas["Grupos"], p["ventana_h"], p["nota_max"])
    elegida, expl = elegir_estrategia(res, p["umbral_nota"])

    tablas = {
        "resumen_grupos": res,
        "sensibilidad_umbral": sensibilidad_umbral(res, [0.5, 1, 2, 3, 5, 6, 7, 8]),
        "umbral_de_cambio": umbral_de_cambio(res),
        "sensibilidad_tratamientos": sensibilidad_tratamientos(
            hojas["Entregas"],
            hojas["Tareas"],
            hojas["Grupos"],
            p["ventana_h"],
            p["nota_max"],
            p["umbral_nota"],
        ),
        "verificacion_integrales": tabla_verificacion(res, dep, p["ventana_h"]),
    }
    pd.Series(informe_depuracion(hojas["Entregas"], dep)).to_csv(
        salida / "depuracion.csv", header=["valor"]
    )
    for nombre, tabla in tablas.items():
        tabla.to_csv(salida / f"{nombre}.csv", index=False)

    for tema, carpeta, dpi in (("claro", salida, 150), ("oscuro", salida / "oscuro", 200)):
        c = _tema(tema)
        figuras = {
            "fig_acumulada": figura_acumulada(dep, res, c),
            "fig_densidad": figura_densidad(dep, res, p["ventana_h"], c),
            "fig_ultimas24": figura_ultimas(res, c),
            "fig_notas": figura_notas(res, elegida, c),
        }
        for nombre, fig in figuras.items():
            fig.savefig(carpeta / f"{nombre}.png", dpi=dpi)
            plt.close(fig)
    aplicar_tema(False)
    generar_formulas(salida / "formulas")

    otro = "G04" if elegida != "G04" else "G01"
    dif, lo, hi = bootstrap_diferencia(dep, elegida, otro)
    return {
        "resumen": res,
        "elegida": elegida,
        "explicacion": expl,
        "tablas": tablas,
        "bootstrap": (dif, lo, hi),
        "parametros": p,
    }


if __name__ == "__main__":
    r = generar()
    print(r["resumen"].round(3).to_string())
    print("Estrategia elegida:", r["elegida"])
    v = r["tablas"]["verificacion_integrales"]
    print(
        f"Error relativo máximo en las verificaciones de integrales: {v['error relativo'].max():.2e}"
    )
    print(f"Tablas y figuras escritas en {SALIDA}")
