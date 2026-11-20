"""Figuras del proyecto. Cada función devuelve una ``Figure`` de matplotlib.

Todas llevan título, ejes con unidades y la fuente; las áreas que
representan integrales se sombrean.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from src.config import FUENTE, GRUPOS  # noqa: E402
from src.escenarios import PlanConsumo, concentracion_plan, malla_dia  # noqa: E402
from src.limpieza import Parametros  # noqa: E402
from src.modelo import ModeloUnCompartimento, RelacionAtencion, modelo_de  # noqa: E402

# ---------------------------------------------------------------------------
# Paleta y estilo común (verdes, blanco y negro)
# ---------------------------------------------------------------------------
# Cada tipo de eliminación tiene un verde: claro = rápida, oscuro = lenta.

COLORES = {"rápida": "#81C784", "normal": "#388E3C", "lenta": "#1B5E20"}
VERDE, GRIS, NEGRO = "#2E7D32", "#9E9E9E", "#111111"
VERDE_CLARO = "#E3F1E3"

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#444444",
        "axes.labelcolor": NEGRO,
        "axes.titlecolor": NEGRO,
        "axes.titleweight": "bold",
        "axes.prop_cycle": matplotlib.cycler(color=[VERDE, NEGRO, "#81C784", GRIS]),
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "font.size": 10,
        "legend.frameon": False,
    }
)


def _fuente(fig: Figure) -> Figure:
    """Agrega la nota de fuente al pie de la figura."""
    fig.text(0.01, 0.005, FUENTE, fontsize=7, color=GRIS, ha="left", va="bottom")
    return fig


# ---------------------------------------------------------------------------
# Datos y modelo: perfiles, área bajo la curva, factores, atención, verificación
# ---------------------------------------------------------------------------


def fig_perfiles(conc: pd.DataFrame, clasificados: pd.DataFrame) -> Figure:
    """Perfiles de concentración de los 60 voluntarios y valores tratados."""
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.2))
    for vol, g in conc.groupby("voluntario"):
        color = COLORES[clasificados.loc[vol, "grupo"]]
        for ax in ejes:
            ax.plot(g["tiempo_h"], g["concentracion_mg_L"], color=color, alpha=0.45, lw=0.9)
    tratados = conc[conc["estado"] != "observado"]
    for ax in ejes:
        for estado, marca in [("faltante", "s"), ("atípico", "X")]:
            sel = tratados[tratados["estado"] == estado]
            ax.scatter(
                sel["tiempo_h"],
                sel["concentracion_mg_L"],
                marker=marca,
                s=45,
                color=NEGRO,
                zorder=5,
                label=f"{estado} (valor tratado)",
            )
        ax.set_xlabel("Tiempo desde la toma de 200 mg (h)")
    atip = conc[conc["estado"] == "atípico"]
    ejes[0].scatter(
        atip["tiempo_h"],
        atip["valor_original"],
        marker="o",
        facecolor="none",
        edgecolor=NEGRO,
        s=60,
        label="atípico (valor original)",
    )
    ejes[0].set_ylabel("Concentración C (mg/L)")
    ejes[0].set_title("Perfiles individuales (escala lineal)")
    ejes[1].set_yscale("log")
    ejes[1].axvspan(6, 24, color=GRIS, alpha=0.12, label="fase terminal (t ≥ 6 h)")
    ejes[1].set_title("Escala logarítmica: ln C es recta en la fase terminal")
    for g in GRUPOS:
        ejes[1].plot([], [], color=COLORES[g], label=f"eliminación {g}")
    ejes[0].legend(fontsize=7)
    ejes[1].legend(fontsize=7, loc="lower left")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_auc_voluntario(
    t: np.ndarray, c: np.ndarray, modelo: ModeloUnCompartimento, dosis: float, nombre: str
) -> Figure:
    """AUC de un voluntario: trapecios en [0, 24] y cola impropia sombreada."""
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    # Área verde: lo medido (0–24 h); área gris: la cola impropia que continúa hasta ∞
    t0, c0 = np.r_[0.0, t], np.r_[0.0, c]
    ax.fill_between(t0, c0, color=VERDE, alpha=0.25, label="∫₀²⁴ C dt (trapecios)")
    tc = np.linspace(t0[-1], t0[-1] + 30, 200)
    cola = c0[-1] * np.exp(-modelo.k * (tc - t0[-1]))
    ax.fill_between(tc, cola, color=NEGRO, alpha=0.3, label="cola ∫₂₄^∞ C dt ≈ C(24)/k")
    tm = np.linspace(0, t0[-1] + 30, 600)
    ax.plot(tm, modelo.concentracion(tm, dosis), color=VERDE, lw=1.6, label="modelo C(t)")
    ax.plot(t0, c0, "o", color="black", ms=4, label="datos")
    auc = np.sum(np.diff(t0) * (c0[1:] + c0[:-1]) / 2)
    texto = (
        f"k = {modelo.k:.3f} 1/h,  t½ = {modelo.vida_media:.2f} h\n"
        f"AUC₀²⁴ = {auc:.1f} mg·h/L,  cola = {c0[-1] / modelo.k:.2f} mg·h/L"
    )
    ax.text(
        0.98,
        0.95,
        texto,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": GRIS},
    )
    ax.set_xlabel("Tiempo desde la toma (h)")
    ax.set_ylabel("Concentración C (mg/L)")
    ax.set_title(f"Área bajo la curva del voluntario {nombre}: integral impropia = trapecio + cola")
    ax.legend(loc="center right", fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_vida_media(clasificados: pd.DataFrame, factores: pd.DataFrame) -> Figure:
    """Vida media por tabaquismo y anticonceptivo, y clasificación por terciles."""
    fig, ejes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, factor, titulo in [
        (ejes[0], "fuma", "Tabaquismo"),
        (ejes[1], "anticonceptivo_hormonal", "Anticonceptivo hormonal"),
    ]:
        datos = [clasificados.loc[clasificados[factor] == v, "vida_media_h"] for v in ("No", "Sí")]
        ax.boxplot(datos, tick_labels=["No", "Sí"], widths=0.5)
        for i, d in enumerate(datos, start=1):
            ax.scatter(
                np.full(len(d), i) + np.random.default_rng(i).uniform(-0.1, 0.1, len(d)),
                d,
                s=12,
                color=VERDE,
                alpha=0.6,
            )
        p = factores.loc[factores["factor"] == factor, "p_valor"].iloc[0]
        ax.set_title(f"{titulo} (p = {p:.4f})")
        ax.set_ylabel("Vida media t½ (h)")
    cortes = clasificados.groupby("grupo", observed=True)["vida_media_h"].max()
    for g in GRUPOS:
        sel = clasificados.loc[clasificados["grupo"] == g, "vida_media_h"]
        ejes[2].hist(
            sel, bins=np.arange(2, 18.5, 0.75), color=COLORES[g], label=f"{g} (n={len(sel)})"
        )
    for g in GRUPOS[:2]:
        ejes[2].axvline(cortes[g], color="black", ls="--", lw=0.8)
    ejes[2].set_xlabel("Vida media t½ (h)")
    ejes[2].set_ylabel("Voluntarios")
    ejes[2].set_title("Grupos por terciles de t½")
    ejes[2].legend(fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_atencion(atencion: pd.DataFrame, relacion: RelacionAtencion, c_efecto: float) -> Figure:
    """Mejora del tiempo de reacción contra concentración, con la recta ajustada."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.scatter(
        atencion["concentracion_mg_L"],
        atencion["mejora_ms"],
        s=12,
        alpha=0.5,
        color=VERDE,
        label="pruebas (480)",
    )
    x = np.linspace(0, atencion["concentracion_mg_L"].max(), 50)
    ax.plot(
        x,
        relacion.mejora(x),
        color=NEGRO,
        lw=2,
        label=(
            f"mejora = {relacion.intercepto:.1f} + {relacion.pendiente:.1f}·C"
            f"  (R² = {relacion.r2:.2f})"
        ),
    )
    ax.axvline(c_efecto, color="black", ls="--", lw=1, label=f"umbral de efecto {c_efecto} mg/L")
    ax.set_xlabel("Concentración de cafeína C (mg/L)")
    ax.set_ylabel("Mejora del tiempo de reacción (ms)")
    ax.set_title("A más cafeína en sangre, reacción más rápida (≈ 24 ms por mg/L)")
    ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_verificacion(validacion: pd.DataFrame, verificacion: pd.DataFrame) -> Figure:
    """Acumulado observado contra integral exacta y error de la validación D/(Vk)."""
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = ejes[0]
    ax.scatter(verificacion["auc_modelo_0_24"], verificacion["auc_obs_0_24"], color=VERDE, s=18)
    lim = [0, verificacion[["auc_obs_0_24", "auc_modelo_0_24"]].max().max() * 1.05]
    ax.plot(lim, lim, color=NEGRO, lw=1, label="y = x")
    ax.set_xlabel("Integral exacta del modelo ∫₀²⁴ C dt (mg·h/L)")
    ax.set_ylabel("Acumulado observado, trapecio (mg·h/L)")
    ax.set_title(f"Acumulado: error medio {100 * verificacion['error_rel_acumulado'].mean():.2f} %")
    ax.legend()
    ax = ejes[1]
    ax.bar(range(len(validacion)), 100 * validacion["error_rel"], color=VERDE)
    ax.axhline(0.5, color=NEGRO, ls="--", label="tolerancia 0,5 %")
    ax.set_xlabel("Voluntario (orden V01–V60)")
    ax.set_ylabel("Error relativo (%)")
    ax.set_title("Validación: ∫₀²⁰⁰ C dt numérica contra D/(V k)")
    ax.legend()
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


# ---------------------------------------------------------------------------
# Planes de consumo: curva del día con las horas con efecto sombreadas
# ---------------------------------------------------------------------------


def dibujar_plan(
    ax: Axes,
    plan: PlanConsumo,
    modelo: ModeloUnCompartimento,
    param: Parametros,
    dias_previos: int = 0,
    color: str = VERDE,
    titulo: str = "",
) -> None:
    """Curva C_plan(t) con la franja de efecto sombreada (integral de la indicadora)."""
    # 1) Curva del plan y área sombreada donde C ≥ umbral dentro de la jornada (H_ef)
    t = malla_dia(param)
    c = concentracion_plan(plan, modelo, t, dias_previos)
    jornada = (t >= param.inicio) & (t <= param.fin)
    ax.fill_between(
        t,
        0,
        c,
        where=jornada & (c >= param.c_efecto),
        color=color,
        alpha=0.35,
        label="horas con efecto (H_ef)",
    )
    ax.plot(t, c, color=color, lw=2)
    # 2) Líneas de referencia: umbral de efecto, umbral de sueño y punto al acostarse
    ax.axhline(
        param.c_efecto,
        color="black",
        ls="--",
        lw=0.9,
        label=f"umbral de efecto {param.c_efecto} mg/L",
    )
    ax.axhline(
        param.c_sueno, color=NEGRO, ls=":", lw=1.2, label=f"umbral de sueño {param.c_sueno} mg/L"
    )
    ax.axvspan(param.inicio, param.fin, color=GRIS, alpha=0.08)
    c_dormir = float(np.interp(param.hora_dormir, t, c))
    ax.plot(param.hora_dormir, c_dormir, "o", color=NEGRO, ms=7)
    ax.annotate(
        f"{c_dormir:.2f} mg/L\nal acostarse",
        (param.hora_dormir, c_dormir),
        xytext=(6, 10),
        textcoords="offset points",
        fontsize=8,
        color=NEGRO,
    )
    # 3) Marca vertical y dosis de cada bebida; ejes en horas del día
    techo = max(c.max(), param.c_efecto) * 1.3
    for h, d in zip(plan.horas, plan.dosis_mg, strict=True):
        ax.axvline(h, color=GRIS, lw=0.8, ls="-.")
        ax.text(h + 0.15, techo * 0.97, f"{d:.0f} mg", fontsize=7, va="top", color=VERDE)
    ax.set_xlim(6, param.hora_dormir + 2)
    ax.set_ylim(0, techo)
    ax.set_xticks(range(6, int(param.hora_dormir) + 3, 2))
    ax.set_xlabel("Hora del día (h)")
    ax.set_ylabel("Cafeína en sangre C_plan(t) (mg/L)")
    ax.set_title(titulo, fontsize=10)


def fig_plan(
    plan: PlanConsumo,
    modelo: ModeloUnCompartimento,
    param: Parametros,
    dias_previos: int = 0,
    titulo: str = "",
) -> Figure:
    """Figura de un solo plan (usada por la aplicación)."""
    fig, ax = plt.subplots(figsize=(9, 4.2))
    dibujar_plan(ax, plan, modelo, param, dias_previos, titulo=titulo)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_planes_recomendados(
    guia: pd.DataFrame,
    planes: dict[str, PlanConsumo],
    modelos: dict[str, ModeloUnCompartimento],
    param: Parametros,
) -> Figure:
    """Plan recomendado de cada grupo con su franja de efecto."""
    fig, ejes = plt.subplots(1, 3, figsize=(14, 4.3))
    por_grupo = guia.set_index("grupo") if len(guia) else pd.DataFrame()
    for ax, g in zip(ejes, GRUPOS, strict=True):
        if g not in por_grupo.index:
            ax.text(
                0.5,
                0.5,
                f"Eliminación {g}:\nningún plan cumple",
                ha="center",
                transform=ax.transAxes,
                color=NEGRO,
            )
            ax.set_axis_off()
            continue
        fila = por_grupo.loc[g]
        dibujar_plan(
            ax,
            planes[fila["plan"]],
            modelos[g],
            param,
            color=COLORES[g],
            titulo=f"Eliminación {g}: plan {fila['plan']}, H_ef = {fila['horas_efecto']:.1f} h",
        )
    ejes[0].legend(fontsize=7, loc="upper right")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_mapa_planes(evaluacion: pd.DataFrame) -> Figure:
    """Horas con efecto de cada plan por grupo; ✗ marca planes que no cumplen."""
    tabla = evaluacion.pivot(index="plan", columns="grupo", values="horas_efecto")[list(GRUPOS)]
    cumple = evaluacion.pivot(index="plan", columns="grupo", values="cumple")[list(GRUPOS)]
    dormir = evaluacion.pivot(index="plan", columns="grupo", values="c_dormir")[list(GRUPOS)]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    valores = tabla.to_numpy()
    im = ax.imshow(valores, cmap="Greens", aspect="auto", vmin=0, vmax=max(12.0, valores.max()))
    for i in range(tabla.shape[0]):
        for j in range(tabla.shape[1]):
            ok = cumple.iloc[i, j]
            ax.text(
                j,
                i,
                f"{tabla.iloc[i, j]:.1f} h {'✓' if ok else '✗'}\nC(23) = {dormir.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=8,
                weight="normal" if ok else "bold",
                color="white" if valores[i, j] > 7 else NEGRO,
            )
    ax.set_xticks(range(3), [f"eliminación {g}" for g in GRUPOS])
    ax.set_yticks(range(len(tabla)), [f"Plan {p}" for p in tabla.index])
    ax.grid(False)
    fig.colorbar(im, label="Horas con efecto H_ef (h)")
    ax.set_title("Horas con efecto entre 8:00 y 20:00 (✗ = no cumple sueño o máximo)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


# ---------------------------------------------------------------------------
# Decisión: escenarios, sensibilidad, criterios y horas límite
# ---------------------------------------------------------------------------


def fig_escenarios(evaluacion: pd.DataFrame, recomendaciones: pd.DataFrame) -> Figure:
    """Horas con efecto del plan recomendado en cada escenario y grupo."""
    fig, ax = plt.subplots(figsize=(9, 4.3))
    escenarios = list(dict.fromkeys(evaluacion["escenario"]))
    ancho = 0.26
    for j, g in enumerate(GRUPOS):
        filas = (
            recomendaciones[recomendaciones["grupo"] == g]
            .set_index("escenario")
            .reindex(escenarios)
            .fillna({"horas_efecto": 0.0, "plan": "—"})
        )
        x = np.arange(len(escenarios)) + (j - 1) * ancho
        barras = ax.bar(x, filas["horas_efecto"], ancho, color=COLORES[g], label=f"eliminación {g}")
        for b, p in zip(barras, filas["plan"], strict=True):
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() + 0.15,
                f"Plan {p}",
                ha="center",
                fontsize=8,
            )
    ax.set_xticks(range(len(escenarios)), escenarios)
    ax.set_ylabel("Horas con efecto del plan elegido (h)")
    ax.set_title("Escenario base y dos alternativos: plan recomendado y horas con efecto")
    ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_sensibilidad(sens: pd.DataFrame, guia: pd.DataFrame) -> Figure:
    """Tornado: cambio en H_ef del plan elegido al variar cada parámetro."""
    fig, ejes = plt.subplots(1, 3, figsize=(14, 4.8), sharey=True)
    por_grupo = guia.set_index("grupo") if len(guia) else pd.DataFrame()
    for ax, g in zip(ejes, GRUPOS, strict=True):
        if g in por_grupo.index:
            fila_guia = por_grupo.loc[g]
        else:
            fila_guia = pd.Series({"horas_efecto": 0.0, "plan": "ninguno"})
        base = fila_guia["horas_efecto"]
        sub = sens[sens["grupo"] == g]
        params = list(dict.fromkeys(sub["parametro"]))
        for i, p in enumerate(params):
            filas = sub[sub["parametro"] == p].reset_index(drop=True)
            for j, f in filas.iterrows():
                y = i + (j - 0.5) * 0.38
                delta = f["horas_efecto"] - base
                color = NEGRO if f["cambia_decision"] else COLORES[g]
                ax.barh(y, delta, height=0.34, color=color, alpha=0.85)
                etiqueta = f"{f['cambio']}" + (
                    f" → plan {f['plan']}" if f["cambia_decision"] else ""
                )
                ax.text(
                    delta + (0.05 if delta >= 0 else -0.05),
                    y,
                    etiqueta,
                    va="center",
                    ha="left" if delta >= 0 else "right",
                    fontsize=7,
                )
        ax.axvline(0, color="black", lw=0.8)
        ax.set_yticks(range(len(params)), params)
        ax.set_xlim(-6, 4.5)
        ax.set_xlabel("Cambio en H_ef del plan recomendado (h)")
        ax.set_title(f"Eliminación {g} (base: plan {fila_guia['plan']}, {base:.1f} h)")
    fig.suptitle("Sensibilidad ±20 % (hora de dormir ±1 h): en negro, el plan recomendado cambia")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_comparacion_criterios(
    guia: pd.DataFrame, prudente: pd.DataFrame, optimizados: pd.DataFrame
) -> Figure:
    """Horas con efecto según el criterio de decisión, por grupo."""
    fig, ax = plt.subplots(figsize=(9, 4.3))
    series = [
        ("Catálogo, persona típica", guia, VERDE),
        ("Catálogo, prudente (≥80 % duerme bien)", prudente, GRIS),
        ("Plan ajustado, prudente", optimizados, NEGRO),
    ]
    for j, (nombre, tabla, color) in enumerate(series):
        valores = tabla.set_index("grupo").reindex(list(GRUPOS))
        x = np.arange(3) + (j - 1) * 0.26
        barras = ax.bar(x, valores["horas_efecto"].fillna(0), 0.26, color=color, label=nombre)
        for b, cob in zip(barras, valores["pct_personas_duermen_bien"], strict=True):
            if not np.isnan(cob):
                ax.text(
                    b.get_x() + b.get_width() / 2,
                    b.get_height() + 0.15,
                    f"{cob:.0f} %",
                    ha="center",
                    fontsize=7,
                )
    ax.set_xticks(range(3), [f"eliminación {g}" for g in GRUPOS])
    ax.set_ylabel("Horas con efecto H_ef (h)")
    ax.set_title("Horas con efecto y % del grupo que duerme bien, según el criterio")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


def fig_horas_limite(tabla: pd.DataFrame, param: Parametros) -> Figure:
    """Hora límite de una toma única de cada bebida para cada grupo."""
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(tabla))
    for j, g in enumerate(GRUPOS):
        yy = y + (j - 1) * 0.26
        ax.barh(
            yy,
            tabla[g] - param.inicio,
            0.26,
            left=param.inicio,
            color=COLORES[g],
            label=f"eliminación {g}",
        )
        for yi, h in zip(yy, tabla[g], strict=True):
            texto = "no" if np.isnan(h) else f"{int(h):02d}:{int(round(60 * (h % 1))) % 60:02d}"
            ax.text(
                param.inicio + 0.08 if np.isnan(h) else h + 0.08,
                yi,
                texto,
                va="center",
                fontsize=6.5,
            )
    ax.set_yticks(
        y, [f"{b} ({m:.0f} mg)" for b, m in zip(tabla["bebida"], tabla["cafeina_mg"], strict=True)]
    )
    ax.axvline(param.hora_dormir, color=NEGRO, ls=":", label="hora de acostarse")
    ax.set_xlabel("Última hora del día para tomarla (h)")
    ax.set_xlim(param.inicio, param.hora_dormir + 0.5)
    ax.set_title("¿Hasta qué hora? Toma única con C(23:00) < umbral de sueño")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=4)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return _fuente(fig)


# ---------------------------------------------------------------------------
# Atajos
# ---------------------------------------------------------------------------


def fig_voluntario_desde_tablas(
    conc: pd.DataFrame, resultados: pd.DataFrame, vol: str, ka: float, dosis: float
) -> Figure:
    """Atajo: figura del AUC de un voluntario a partir de las tablas."""
    g = conc[conc["voluntario"] == vol].sort_values("tiempo_h")
    return fig_auc_voluntario(
        g["tiempo_h"].to_numpy(),
        g["concentracion_mg_L"].to_numpy(),
        modelo_de(resultados.loc[vol], ka),
        dosis,
        vol,
    )
