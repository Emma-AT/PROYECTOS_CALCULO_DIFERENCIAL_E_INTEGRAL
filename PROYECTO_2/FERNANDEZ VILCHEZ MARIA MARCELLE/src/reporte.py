"""Genera las tablas y figuras del proyecto en la carpeta ``resultados/``.

Uso (desde la carpeta del proyecto):  python -m src.reporte
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import escenarios as esc
from src import modelo

RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "datos" / "P01_C-02_FERNANDEZ.xlsx"
SALIDA = RAIZ / "resultados"
COLOR = {"alerta": "#2a7f62", "somnoliento": "#c0392b", "neutro": "#34495e"}


def _bandas(params: dict[str, float]) -> dict[str, tuple[float, float]]:
    """Límites de las bandas (Hz) a partir de los parámetros."""
    return {
        "theta": (params["theta_inf"], params["theta_sup"]),
        "alfa": (params["theta_sup"], params["alfa_sup"]),
        "beta": (params["alfa_sup"], params["beta_sup"]),
    }


def tabla_bandas(d: esc.Datos) -> pd.DataFrame:
    """Compara Simpson y trapecio en cada banda (media de las épocas)."""
    simp = d.potencias
    trap = modelo.potencias_por_epoca(d.ancha, d.params, "trapecio")
    filas = []
    for banda in ("theta", "alfa", "beta", "total"):
        err = (simp[banda] - trap[banda]).abs() / simp[banda]
        filas.append(
            {
                "banda": banda,
                "simpson_uV2_media": simp[banda].mean(),
                "trapecio_uV2_media": trap[banda].mean(),
                "error_relativo_medio_%": 100 * err.mean(),
                "error_relativo_max_%": 100 * err.max(),
            }
        )
    return pd.DataFrame(filas)


def tabla_ajuste(d: esc.Datos) -> pd.DataFrame:
    """Integral analítica del ajuste A f^b contra Simpson, por banda y clase."""
    f = d.ancha.columns.to_numpy(dtype=float)
    ok = ~d.artefacto
    filas = []
    for nombre, clase in (("alerta", 0), ("somnoliento", 1)):
        S = d.ancha.to_numpy()[ok & (d.somnolencia == clase)].mean(axis=0)
        A, b = modelo.ajustar_ley_potencia(f, S)
        for banda, (f1, f2) in _bandas(d.params).items():
            ana = modelo.integral_ley_potencia(A, b, f1, f2)
            num = modelo.potencia_banda(S, f, f1, f2, "simpson")
            filas.append(
                {
                    "clase": nombre,
                    "A": A,
                    "b": b,
                    "banda": banda,
                    "analitica_uV2": ana,
                    "simpson_uV2": num,
                    "error_relativo_%": 100 * modelo.error_relativo(ana, num),
                }
            )
    return pd.DataFrame(filas)


def _guardar(fig: plt.Figure, nombre: str) -> None:
    fig.tight_layout()
    fig.savefig(SALIDA / nombre, dpi=150)
    plt.close(fig)


def fig_espectro(d: esc.Datos) -> None:
    """Espectro medio alerta/somnoliento con las áreas de las bandas sombreadas."""
    f = d.ancha.columns.to_numpy(dtype=float)
    ok = ~d.artefacto
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for nombre, clase in (("alerta", 0), ("somnoliento", 1)):
        S = d.ancha.to_numpy()[ok & (d.somnolencia == clase)].mean(axis=0)
        ax.plot(f, S, color=COLOR[nombre], lw=2, label=f"Época {nombre}")
        if clase == 1:
            for banda, (a, b) in _bandas(d.params).items():
                m = (f >= a) & (f <= b)
                ax.fill_between(f[m], S[m], alpha=0.18, label=f"Área banda {banda}")
    ax.set_yscale("log")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Densidad espectral S(f) (µV²/Hz)")
    ax.set_title("Espectro medio del EEG: la potencia de banda es el área bajo S(f)")
    ax.legend(fontsize=8)
    _guardar(fig, "fig1_espectro_bandas.png")


def fig_indice(d: esc.Datos, umbral: float) -> None:
    """Índice de somnolencia por época, con umbral, alarmas y artefactos."""
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    viajes = d.potencias.index.get_level_values("viaje").to_numpy()
    epoca = d.potencias.index.get_level_values("epoca").to_numpy()
    I = d.indice.to_numpy()
    for ax, v in zip(ejes, (1, 2), strict=True):
        m = viajes == v
        t = (epoca[m] - 1) * d.params["duracion_epoca_min"]
        ax.plot(t, I[m], color=COLOR["neutro"], lw=1, alpha=0.6)
        for clase, nombre in ((0, "alerta"), (1, "somnoliento")):
            k = m & (d.somnolencia == clase)
            tk = (epoca[k] - 1) * d.params["duracion_epoca_min"]
            ax.scatter(tk, I[k], color=COLOR[nombre], s=28, label=f"Video: {nombre}")
        ka = m & d.artefacto
        ax.scatter(
            (epoca[ka] - 1) * d.params["duracion_epoca_min"],
            I[ka],
            marker="x",
            color="k",
            s=60,
            label="Artefacto",
        )
        ax.axhline(umbral, color="orange", ls="--", label=f"Umbral c = {umbral:.2f}")
        ax.set_title(f"Viaje {v}")
        ax.set_xlabel("Minuto del viaje (min)")
    ejes[0].set_ylabel("Índice I = (Pθ+Pα)/Pβ (adimensional)")
    ejes[1].legend(fontsize=8)
    fig.suptitle("Índice de somnolencia en el tiempo: la alarma suena sobre el umbral")
    _guardar(fig, "fig2_indice_tiempo.png")


def fig_roc(d: esc.Datos, base: pd.Series) -> None:
    """Curva ROC con y sin artefactos, con el área sombreada y el punto elegido."""
    y, I = d.somnolencia, d.indice.to_numpy()
    roc_sin = modelo.curva_roc(I[~d.artefacto], y[~d.artefacto])
    roc_con = modelo.curva_roc(I, y)
    fig, ax = plt.subplots(figsize=(5.8, 5.4))
    ax.fill_between(
        roc_sin.fpr, roc_sin.tpr, step="post", alpha=0.2, color=COLOR["alerta"]
    )
    ax.step(
        roc_sin.fpr,
        roc_sin.tpr,
        where="post",
        color=COLOR["alerta"],
        lw=2,
        label=f"Sin artefactos, AUC = {roc_sin.auc:.3f}",
    )
    ax.step(
        roc_con.fpr,
        roc_con.tpr,
        where="post",
        color=COLOR["somnoliento"],
        lw=1.5,
        label=f"Con artefactos, AUC = {roc_con.auc:.3f}",
    )
    ax.plot([0, 1], [0, 1], ":", color="gray", label="Azar (AUC = 0,5)")
    ax.scatter(
        1 - base["especificidad"],
        base["sensibilidad"],
        s=90,
        zorder=5,
        color="orange",
        edgecolor="k",
        label=f"Umbral c = {base['umbral']:.2f}",
    )
    ax.set_xlabel("Tasa de falsos positivos, FPR (fracción)")
    ax.set_ylabel("Tasa de verdaderos positivos, TPR (fracción)")
    ax.set_title("Curva ROC: AUC = ∫ TPR d(FPR)")
    ax.legend(fontsize=8, loc="lower right")
    _guardar(fig, "fig3_roc.png")


def fig_escenarios(tabla: pd.DataFrame, sens_min: float) -> None:
    """Barras comparando falsas alarmas por hora y sensibilidad por escenario."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
    nombres = [n.split(" (")[0] for n in tabla["escenario"]]
    a1.bar(nombres, tabla["sensibilidad"] * 100, color="#2a7f62")
    a1.axhline(sens_min * 100, color="k", ls="--", label="Mínimo exigido")
    a1.set_ylabel("Sensibilidad (%)")
    a1.set_ylim(0, 110)
    a1.legend()
    a2.bar(nombres, tabla["falsas_alarmas_por_hora"], color="#c0392b")
    a2.set_ylabel("Falsas alarmas por hora de conducción alerta (1/h)")
    for ax in (a1, a2):
        ax.tick_params(axis="x", labelrotation=15, labelsize=8)
    fig.suptitle("Comparación de escenarios")
    _guardar(fig, "fig4_escenarios.png")


def fig_sensibilidad(barrido: pd.DataFrame) -> None:
    """Umbral óptimo en función de la razón de costos, por sensibilidad mínima."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for s, g in barrido.groupby("sens_min"):
        ax.plot(
            g["razon_omision_falsa_alarma"],
            g["umbral"],
            "o-",
            label=f"Sens. mín. {s:.2f}",
        )
    ax.set_xscale("log")
    ax.set_xlabel("Razón costo omisión / costo falsa alarma (adimensional)")
    ax.set_ylabel("Umbral óptimo c (adimensional)")
    ax.set_title("Sensibilidad del umbral a los costos")
    ax.legend(fontsize=8)
    _guardar(fig, "fig5_sensibilidad.png")


def fig_ajuste(d: esc.Datos) -> None:
    """Ajuste de ley de potencias contra el espectro medio (verificación)."""
    f = d.ancha.columns.to_numpy(dtype=float)
    ok = ~d.artefacto
    S = d.ancha.to_numpy()[ok & (d.somnolencia == 0)].mean(axis=0)
    A, b = modelo.ajustar_ley_potencia(f, S)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(f, S, "o", color=COLOR["alerta"], label="Espectro medio (alerta)")
    ax.plot(f, A * f**b, color="k", label=f"Ajuste S = {A:.1f}·f^{b:.2f}")
    ax.set_yscale("log")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Densidad espectral S(f) (µV²/Hz)")
    ax.set_title("Verificación: ley de potencias integrada analíticamente")
    ax.legend()
    _guardar(fig, "fig6_ajuste_analitico.png")


def fig_reaccion(d: esc.Datos) -> None:
    """Dispersión índice contra tiempo de reacción."""
    ok = ~d.artefacto
    I = d.indice.to_numpy()
    r = modelo.correlacion(I[ok], d.tiempo_reaccion[ok])
    fig, ax = plt.subplots(figsize=(6, 4.2))
    for clase, nombre in ((0, "alerta"), (1, "somnoliento")):
        k = ok & (d.somnolencia == clase)
        ax.scatter(I[k], d.tiempo_reaccion[k], color=COLOR[nombre], label=nombre)
    ax.set_xlabel("Índice I (adimensional)")
    ax.set_ylabel("Tiempo de reacción (ms)")
    ax.set_title(f"Índice y tiempo de reacción (r = {r:.2f}, sin artefactos)")
    ax.legend()
    _guardar(fig, "fig7_indice_vs_reaccion.png")


def fig_ficha_resultados(d: esc.Datos, base: pd.Series) -> None:
    """Figura de dos paneles para la ficha: espectro con bandas y curva ROC."""
    f = d.ancha.columns.to_numpy(dtype=float)
    ok = ~d.artefacto
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.9))
    for nombre, clase in (("alerta", 0), ("somnoliento", 1)):
        S = d.ancha.to_numpy()[ok & (d.somnolencia == clase)].mean(axis=0)
        a1.plot(f, S, color=COLOR[nombre], lw=2, label=f"Época {nombre}")
        if clase == 1:
            for banda, (a, b) in _bandas(d.params).items():
                m = (f >= a) & (f <= b)
                a1.fill_between(f[m], S[m], alpha=0.2, label=f"Área {banda}")
    a1.set_yscale("log")
    a1.set_xlabel("Frecuencia (Hz)")
    a1.set_ylabel("S(f) (µV²/Hz)")
    a1.set_title("(a) Espectro medio y áreas de las bandas")
    a1.legend(fontsize=8)
    y, ind = d.somnolencia, d.indice.to_numpy()
    sin = modelo.curva_roc(ind[ok], y[ok])
    con = modelo.curva_roc(ind, y)
    a2.fill_between(sin.fpr, sin.tpr, step="post", alpha=0.2, color=COLOR["alerta"])
    a2.step(
        sin.fpr,
        sin.tpr,
        where="post",
        color=COLOR["alerta"],
        lw=2,
        label=f"Sin artefactos (AUC = {sin.auc:.3f})",
    )
    a2.step(
        con.fpr,
        con.tpr,
        where="post",
        color=COLOR["somnoliento"],
        lw=1.5,
        label=f"Con artefactos (AUC = {con.auc:.3f})",
    )
    a2.plot([0, 1], [0, 1], ":", color="gray")
    a2.scatter(
        1 - base["especificidad"],
        base["sensibilidad"],
        s=80,
        zorder=5,
        color="orange",
        edgecolor="k",
        label=f"Umbral c = {base['umbral']:.2f}",
    )
    a2.set_xlabel("FPR (fracción)")
    a2.set_ylabel("TPR (fracción)")
    a2.set_title("(b) Curva ROC")
    a2.legend(fontsize=8, loc="lower right")
    _guardar(fig, "fig8_ficha_espectro_roc.png")


def fig_ficha_verificacion(d: esc.Datos, barrido: pd.DataFrame) -> None:
    """Figura de dos paneles: sensibilidad del umbral y ajuste analítico."""
    f = d.ancha.columns.to_numpy(dtype=float)
    ok = ~d.artefacto
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.7))
    for s, g in barrido.groupby("sens_min"):
        a1.plot(
            g["razon_omision_falsa_alarma"],
            g["umbral"],
            "o-",
            label=f"Sens. mín. {s:.2f}",
        )
    a1.set_xscale("log")
    a1.set_xlabel("Costo omisión / costo falsa alarma")
    a1.set_ylabel("Umbral óptimo c")
    a1.set_title("(a) Sensibilidad del umbral a los costos")
    a1.legend(fontsize=8)
    S = d.ancha.to_numpy()[ok & (d.somnolencia == 0)].mean(axis=0)
    A, b = modelo.ajustar_ley_potencia(f, S)
    a2.plot(f, S, "o", color=COLOR["alerta"], label="Espectro medio (alerta)")
    a2.plot(f, A * f**b, color="k", label=f"Ajuste S = {A:.1f}·f^{b:.2f}")
    a2.set_yscale("log")
    a2.set_xlabel("Frecuencia (Hz)")
    a2.set_ylabel("S(f) (µV²/Hz)")
    a2.set_title("(b) Verificación analítica (ley de potencias)")
    a2.legend(fontsize=8)
    _guardar(fig, "fig9_ficha_verificacion.png")


def generar(ruta: Path = RUTA_DATOS) -> None:
    """Regenera todas las tablas (CSV) y figuras (PNG) en ``resultados/``."""
    SALIDA.mkdir(exist_ok=True)
    d = esc.preparar_datos(ruta)
    comp = esc.comparar_escenarios(d)
    barrido = esc.barrido_sensibilidad(
        d, np.array([0.5, 1, 2, 4, 8, 16, 32]), np.array([0.8, 0.9, 0.95, 1.0])
    )
    d.potencias.assign(
        indice=d.indice,
        somnolencia=d.somnolencia,
        artefacto=d.artefacto,
        tiempo_reaccion_ms=d.tiempo_reaccion,
    ).to_csv(SALIDA / "tabla_potencias_epocas.csv")
    tabla_bandas(d).to_csv(SALIDA / "tabla_simpson_vs_trapecio.csv", index=False)
    tabla_ajuste(d).to_csv(SALIDA / "tabla_ajuste_analitico.csv", index=False)
    comp.to_csv(SALIDA / "tabla_escenarios.csv", index=False)
    barrido.to_csv(SALIDA / "tabla_sensibilidad.csv", index=False)
    base = comp.iloc[0]
    fig_espectro(d)
    fig_indice(d, float(base["umbral"]))
    fig_roc(d, base)
    fig_escenarios(comp, d.params["sens_min"])
    fig_sensibilidad(barrido)
    fig_ajuste(d)
    fig_reaccion(d)
    fig_ficha_resultados(d, base)
    fig_ficha_verificacion(d, barrido)
    print(f"Listo: resultados en {SALIDA}")
    print(comp.round(3).T.to_string())


if __name__ == "__main__":
    generar()
