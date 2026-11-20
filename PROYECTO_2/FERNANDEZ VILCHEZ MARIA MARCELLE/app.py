"""Aplicación web: umbral de alarma contra la somnolencia al volante.

Ejecutar:  streamlit run app.py
Lee el mismo Excel del proyecto (o uno cargado con la misma estructura).
"""

from __future__ import annotations

import tempfile
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap

from src import escenarios as esc
from src import modelo

RUTA_DATOS = Path(__file__).resolve().parent / "datos" / "P01_C-02_FERNANDEZ.xlsx"

# Paleta lila y rosa
COLOR = {
    "alerta": "#7C5CBF",
    "somnoliento": "#EC4899",
    "neutro": "#6B5B95",
    "umbral": "#F5A524",
    "texto": "#3B2A5A",
    "rejilla": "#EDE4FB",
}
BANDA_COLOR = {"theta": "#C4B5FD", "alfa": "#F9A8D4", "beta": "#A5B4FC"}
MAPA = LinearSegmentedColormap.from_list(
    "lila", ["#F5EEFF", "#D8C2FA", "#A78BFA", "#7C3AED", "#4C1D95"]
)
plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#D9C8FF",
        "axes.labelcolor": COLOR["texto"],
        "axes.titlecolor": COLOR["texto"],
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.color": COLOR["rejilla"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": COLOR["texto"],
        "xtick.color": COLOR["texto"],
        "ytick.color": COLOR["texto"],
        "legend.frameon": False,
    }
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
html, body, .stApp { font-family: 'Quicksand', sans-serif !important; }
.stApp { background: linear-gradient(180deg, #FBF8FF 0%, #F3EBFF 100%); }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #3B2A5A; }
.block-container { padding-top: 1.2rem; max-width: 1150px; }
[data-testid="stSidebar"] { background: #F1E8FF; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff; border: 1px solid #E6DAFB !important; border-radius: 22px !important;
  box-shadow: 0 4px 16px rgba(139, 92, 246, .08);
}
.hero { background: linear-gradient(120deg, #8B5CF6 0%, #C084FC 45%, #F9A8D4 100%);
  border-radius: 28px; padding: 28px 34px; box-shadow: 0 12px 32px rgba(139, 92, 246, .30); }
.hero, .hero * { color: #ffffff !important; }
.hero h1 { font-size: 2.2rem; margin: 0; font-weight: 700; }
.hero p { margin: 6px 0 12px; font-size: 1.05rem; }
.chip { display: inline-block; background: rgba(255,255,255,.22); border: 1px solid rgba(255,255,255,.55);
  border-radius: 999px; padding: 3px 13px; margin: 2px 6px 2px 0; font-size: .85rem; }
.sec { display: flex; align-items: center; gap: 12px; margin: 28px 0 6px; }
.sec .n { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #8B5CF6, #EC4899);
  color: #ffffff !important; display: flex; align-items: center; justify-content: center; font-weight: 700; flex: none; }
.sec h2 { margin: 0; font-size: 1.5rem; }
.sub { margin: 0 0 8px 52px; color: #7a6a99 !important; }
.tip { background: #F5EEFF; border-left: 5px solid #C084FC; border-radius: 12px;
  padding: 8px 14px; margin: 8px 0 4px; font-size: .95rem; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 16px 0 6px; }
.kpi { background: #ffffff; border: 1px solid #E6DAFB; border-radius: 22px; padding: 14px 18px;
  box-shadow: 0 4px 14px rgba(139, 92, 246, .10); }
.kpi-v { font-size: 2.1rem; font-weight: 700; color: #7C3AED !important; line-height: 1.1; }
.kpi-t { font-weight: 700; }
.kpi-a { font-size: .82rem; color: #7a6a99 !important; }
.rec { background: linear-gradient(90deg, #F3E8FF, #FCE7F3); border: 1px solid #E9D5FF;
  border-radius: 20px; padding: 12px 20px; margin: 12px 0; }
.cmg { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 6px; }
.cm { border-radius: 20px; padding: 14px 10px; text-align: center; }
.cm b { display: block; font-size: 2.2rem; line-height: 1.1; }
.cm span { font-size: .85rem; }
.cm-tn { background: #EDE7FF; } .cm-fp { background: #FFE4F1; }
.cm-fn { background: #FFC2DD; } .cm-tp { background: #D9C8FF; }
.esc { background: #ffffff; border: 1px solid #E6DAFB; border-radius: 24px; padding: 16px 18px;
  min-height: 270px; box-shadow: 0 4px 14px rgba(139, 92, 246, .10); }
.esc.top { border: 2px solid #A78BFA; background: linear-gradient(180deg, #ffffff, #F7F0FF); }
.esc h4 { margin: 4px 0 2px; font-size: 1.1rem; }
.esc .big { font-size: 1.9rem; font-weight: 700; color: #7C3AED !important; }
.esc .row { display: flex; justify-content: space-between; border-bottom: 1px dashed #E6DAFB; padding: 3px 0; font-size: .92rem; }
.esc .cuando { font-size: .85rem; color: #7a6a99 !important; margin-top: 8px; }
.badge { background: #8B5CF6; color: #ffffff !important; border-radius: 999px; padding: 2px 10px;
  font-size: .72rem; font-weight: 700; }
.stDownloadButton button, .stButton button { background: linear-gradient(90deg, #8B5CF6, #C084FC);
  color: #ffffff; border: none; border-radius: 999px; padding: .4rem 1.3rem; }
.stDownloadButton button p { color: #ffffff; }
.pie { text-align: center; color: #9a8bb8 !important; font-size: .85rem; margin: 30px 0 10px; }
</style>
"""


# --------------------------------------------------------------------------
# Datos y cálculos (con caché)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Procesando espectros...")
def cargar_datos(contenido: bytes, umbral_z: float) -> esc.Datos:
    """Lee el Excel (en bytes) y calcula potencias, índice y artefactos.

    Args:
        contenido: bytes del archivo .xlsx.
        umbral_z: puntaje z modificado para marcar artefactos.

    Returns:
        Datos preparados (se guardan en caché).
    """
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "base.xlsx"
        ruta.write_bytes(contenido)
        return esc.preparar_datos(ruta, umbral_z)


@st.cache_data(show_spinner=False)
def tabla_escenarios(
    datos: esc.Datos, sens: float, c_om: float, c_fa: float
) -> pd.DataFrame:
    """Compara base y dos alternativas con los parámetros elegidos en pantalla."""
    params = {
        **datos.params,
        "sens_min": sens,
        "costo_omision": c_om,
        "costo_falsa_alarma": c_fa,
    }
    return esc.comparar_escenarios(replace(datos, params=params))


@st.cache_data(show_spinner=False)
def tabla_barrido(datos: esc.Datos) -> pd.DataFrame:
    """Umbral óptimo al variar razón de costos y sensibilidad mínima."""
    return esc.barrido_sensibilidad(
        datos, np.array([0.5, 1, 2, 4, 8, 16, 32]), np.array([0.8, 0.9, 0.95, 1.0])
    )


def _bandas(p: dict[str, float]) -> dict[str, tuple[float, float]]:
    return {
        "theta": (p["theta_inf"], p["theta_sup"]),
        "alfa": (p["theta_sup"], p["alfa_sup"]),
        "beta": (p["alfa_sup"], p["beta_sup"]),
    }


def _viaje_y_epoca(datos: esc.Datos) -> tuple[np.ndarray, np.ndarray]:
    ind = datos.potencias.index
    return (
        ind.get_level_values("viaje").to_numpy(),
        ind.get_level_values("epoca").to_numpy(),
    )


def tabla_integrales(datos: esc.Datos, viaje: int, epoca: int) -> pd.DataFrame:
    """Potencia de banda con Simpson y trapecio para una época (µV²)."""
    f = datos.ancha.columns.to_numpy(dtype=float)
    S = datos.ancha.loc[(viaje, epoca)].to_numpy()
    filas = []
    for banda, (a, b) in _bandas(datos.params).items():
        simp = modelo.potencia_banda(S, f, a, b, "simpson")
        trap = modelo.potencia_banda(S, f, a, b, "trapecio")
        filas.append(
            {
                "banda": banda,
                "Simpson (µV²)": simp,
                "Trapecio (µV²)": trap,
                "error relativo (%)": 100 * modelo.error_relativo(trap, simp),
            }
        )
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# Gráficos
# --------------------------------------------------------------------------
def fig_espectrograma(datos: esc.Datos, viaje: int) -> plt.Figure:
    """Espectrograma: tiempo (min) contra frecuencia (Hz), color = log10 S."""
    v, ep = _viaje_y_epoca(datos)
    m = v == viaje
    dur = datos.params["duracion_epoca_min"]
    f = datos.ancha.columns.to_numpy(dtype=float)
    t = (ep[m] - 1) * dur
    S = datos.ancha.to_numpy()[m]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    malla = ax.pcolormesh(
        np.append(t, t[-1] + dur),
        np.append(f - 0.5, f[-1] + 0.5),
        np.log10(S).T,
        shading="flat",
        cmap=MAPA,
    )
    p = datos.params
    for lim, nombre in (
        (p["theta_inf"], "θ"),
        (p["theta_sup"], "α"),
        (p["alfa_sup"], "β"),
    ):
        ax.axhline(lim, color="white", lw=0.9, ls="--")
        ax.text(t[-1] + dur + 0.6, lim + 0.4, nombre, color=COLOR["texto"], fontsize=9)
    ax.grid(False)
    fig.colorbar(malla, ax=ax, label="log10 S(f)  (log10 µV²/Hz)")
    ax.set_xlabel("Minuto del viaje (min)")
    ax.set_ylabel("Frecuencia (Hz)")
    ax.set_title(f"Espectrograma del viaje {viaje}")
    fig.tight_layout()
    return fig


def fig_espectro_epoca(datos: esc.Datos, viaje: int, epoca: int) -> plt.Figure:
    """Espectro de una época con las áreas de las bandas sombreadas."""
    f = datos.ancha.columns.to_numpy(dtype=float)
    S = datos.ancha.loc[(viaje, epoca)].to_numpy()
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(f, S, color=COLOR["neutro"], lw=2)
    for banda, (a, b) in _bandas(datos.params).items():
        m = (f >= a) & (f <= b)
        ax.fill_between(f[m], S[m], alpha=0.55, color=BANDA_COLOR[banda], label=banda)
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("S(f) (µV²/Hz)")
    ax.set_title(f"Viaje {viaje}, época {epoca}")
    ax.legend(fontsize=8, title="Área de banda")
    fig.tight_layout()
    return fig


def fig_indice(datos: esc.Datos, viaje: int, umbral: float) -> plt.Figure:
    """Índice en el tiempo con umbral, alarmas, somnolencia y artefactos."""
    v, ep = _viaje_y_epoca(datos)
    m = v == viaje
    dur = datos.params["duracion_epoca_min"]
    t = (ep[m] - 1) * dur
    I = datos.indice.to_numpy()[m]
    somn = datos.somnolencia[m] == 1
    art = datos.artefacto[m]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for ti, s in zip(t, somn, strict=True):
        if s:
            ax.axvspan(ti, ti + dur, color=COLOR["somnoliento"], alpha=0.13)
    x = t + dur / 2
    ax.plot(x, I, color=COLOR["neutro"], lw=1, alpha=0.5)
    alarma = I >= umbral
    ax.scatter(x[~alarma], I[~alarma], color=COLOR["alerta"], s=34, label="Sin alarma")
    ax.scatter(
        x[alarma],
        I[alarma],
        color=COLOR["umbral"],
        s=60,
        edgecolor=COLOR["texto"],
        zorder=4,
        label="Alarma",
    )
    ax.scatter(
        x[art],
        I[art],
        marker="x",
        color="k",
        s=70,
        zorder=6,
        label="Movimiento (artefacto)",
    )
    ax.axhline(umbral, color=COLOR["umbral"], ls="--", label=f"Umbral c = {umbral:.2f}")
    ax.set_xlabel("Minuto del viaje (min)")
    ax.set_ylabel("Índice I (adimensional)")
    ax.set_title(f"Viaje {viaje}: fondo rosado = somnoliento según el video")
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    fig.tight_layout()
    return fig


def fig_roc(roc: modelo.CurvaROC, r: modelo.ResultadoUmbral) -> plt.Figure:
    """Curva ROC con el área sombreada y el punto del umbral elegido."""
    fig, ax = plt.subplots(figsize=(5.2, 4.7))
    ax.fill_between(roc.fpr, roc.tpr, step="post", alpha=0.25, color=COLOR["alerta"])
    ax.step(
        roc.fpr,
        roc.tpr,
        where="post",
        color=COLOR["alerta"],
        lw=2.2,
        label=f"AUC = {roc.auc:.3f}",
    )
    ax.plot([0, 1], [0, 1], ":", color="#B9A8D9")
    ax.scatter(
        1 - r.especificidad,
        r.sensibilidad,
        s=110,
        color=COLOR["umbral"],
        edgecolor=COLOR["texto"],
        zorder=5,
        label=f"c = {r.umbral:.2f}",
    )
    ax.set_xlabel("FPR: falsas alarmas (fracción)")
    ax.set_ylabel("TPR: episodios detectados (fracción)")
    ax.set_title("Curva ROC")
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


def fig_escenarios(tabla: pd.DataFrame, sens_min: float) -> plt.Figure:
    """Sensibilidad y falsas alarmas por hora de cada escenario."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.5))
    nombres = ["Base", "Chofer\nprioritario", "Sin filtro\nde movimiento"]
    a1.bar(nombres, tabla["sensibilidad"] * 100, color="#A78BFA", width=0.6)
    a1.axhline(sens_min * 100, color=COLOR["umbral"], ls="--", label="Mínimo exigido")
    a1.set_ylabel("Sensibilidad (%)")
    a1.set_ylim(0, 112)
    a1.legend(fontsize=8)
    a2.bar(nombres, tabla["falsas_alarmas_por_hora"], color="#F472B6", width=0.6)
    a2.set_ylabel("Falsas alarmas por hora (1/h)")
    for ax in (a1, a2):
        ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    return fig


def fig_barrido(barrido: pd.DataFrame) -> plt.Figure:
    """Umbral óptimo según la razón de costos y la sensibilidad mínima."""
    fig, ax = plt.subplots(figsize=(5.6, 3.5))
    colores = ["#C4B5FD", "#A78BFA", "#7C3AED", "#EC4899"]
    for (s, g), col in zip(barrido.groupby("sens_min"), colores, strict=False):
        ax.plot(
            g["razon_omision_falsa_alarma"],
            g["umbral"],
            "o-",
            color=col,
            label=f"Sens. mín. {s:.2f}",
        )
    ax.set_xscale("log")
    ax.set_xlabel("Costo omisión / costo falsa alarma")
    ax.set_ylabel("Umbral óptimo c")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# Piezas de interfaz
# --------------------------------------------------------------------------
def tarjeta():
    """Contenedor con borde (tarjeta); si la versión no lo admite, sin borde."""
    try:
        return st.container(border=True)
    except TypeError:
        return nullcontext()


def mostrar(fig: plt.Figure, destino=st) -> None:
    """Dibuja una figura y libera su memoria."""
    destino.pyplot(fig)
    plt.close(fig)


def seccion(n: int, titulo: str, subtitulo: str) -> None:
    """Encabezado numerado de sección."""
    st.markdown(
        f'<div class="sec"><div class="n">{n}</div><h2>{titulo}</h2></div>'
        f'<p class="sub">{subtitulo}</p>',
        unsafe_allow_html=True,
    )


def consejo(texto: str) -> None:
    """Recuadro lila con una explicación en lenguaje sencillo."""
    st.markdown(f'<div class="tip">💡 {texto}</div>', unsafe_allow_html=True)


def kpi(valor: str, titulo: str, ayuda: str) -> str:
    """HTML de una tarjeta de indicador."""
    return (
        f'<div class="kpi"><div class="kpi-v">{valor}</div>'
        f'<div class="kpi-t">{titulo}</div><div class="kpi-a">{ayuda}</div></div>'
    )


def matriz_html(r: modelo.ResultadoUmbral) -> str:
    """Matriz de confusión como cuatro tarjetas de color."""
    return (
        '<div class="cmg">'
        f'<div class="cm cm-tn"><b>{r.tn}</b><span>Alerta, sin alarma ✓</span></div>'
        f'<div class="cm cm-fp"><b>{r.fp}</b><span>Alerta, con alarma<br>(falsa alarma)</span></div>'
        f'<div class="cm cm-fn"><b>{r.fn}</b><span>Somnoliento, sin alarma<br>(omisión)</span></div>'
        f'<div class="cm cm-tp"><b>{r.tp}</b><span>Somnoliento, con alarma ✓</span></div>'
        "</div>"
    )


def tarjeta_escenario(fila: pd.Series, nombre: str, cuando: str, top: bool) -> str:
    """HTML de la tarjeta de un escenario."""
    badge = '<span class="badge">Recomendado</span>' if top else ""
    return (
        f'<div class="esc{" top" if top else ""}">{badge}<h4>{nombre}</h4>'
        f'<div class="big">c = {fila["umbral"]:.2f}</div>'
        f'<div class="row"><span>Detecta</span><b>{fila["sensibilidad"]:.0%}</b></div>'
        f'<div class="row"><span>Sin falsa alarma</span><b>{fila["especificidad"]:.0%}</b></div>'
        f'<div class="row"><span>Falsas alarmas por hora</span><b>{fila["falsas_alarmas_por_hora"]:.1f}</b></div>'
        f'<div class="row"><span>AUC</span><b>{fila["AUC"]:.3f}</b></div>'
        f'<div class="cuando">{cuando}</div></div>'
    )


CUANDO = [
    "Cuando lo más importante es no omitir ningún episodio de somnolencia.",
    "Cuando molestar al chofer pesa casi como una omisión.",
    "Si el equipo no puede filtrar el movimiento del chofer.",
]
NOMBRES = ["Base", "Chofer prioritario", "Sin filtro de movimiento"]


# --------------------------------------------------------------------------
# Aplicación
# --------------------------------------------------------------------------
def main() -> None:
    """Construye la interfaz de la aplicación."""
    st.set_page_config(
        page_title="Sueño al volante",
        page_icon="🌙",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### ⚙️ Opciones avanzadas")
        subido = st.file_uploader(
            "Cargar otra base (.xlsx, misma estructura)", type="xlsx"
        )
        z = st.slider("Detector de movimiento (z modificado)", 3.5, 30.0, 10.0, 0.5)
    contenido = subido.getvalue() if subido else RUTA_DATOS.read_bytes()
    try:
        datos = cargar_datos(contenido, z)
    except (ValueError, KeyError, FileNotFoundError) as error:
        st.error(f"No se pudo leer la base: {error}")
        st.stop()
        return
    p = datos.params

    # ---- Portada
    n_ep = len(datos.somnolencia)
    st.markdown(
        '<div class="hero"><h1>🌙 Sueño al volante</h1>'
        "<p>Ruta Golfito–San José · ¿A partir de qué valor debe sonar la alarma de la diadema EEG?</p>"
        f'<span class="chip">{n_ep} intervalos de 5 min</span>'
        f'<span class="chip">{len(set(_viaje_y_epoca(datos)[0].tolist()))} viajes</span>'
        '<span class="chip">datos simulados</span>'
        '<span class="chip">MA-0321 · Proyecto 2</span></div>',
        unsafe_allow_html=True,
    )

    # ---- Ajustes
    st.markdown(
        '<div class="sec"><div class="n">✦</div><h2>Tus ajustes</h2></div>'
        '<p class="sub">Mueve los controles y mira cómo cambia todo lo demás.</p>',
        unsafe_allow_html=True,
    )
    with tarjeta():
        c1, c2, c3 = st.columns(3)
        sens = c1.slider(
            "Sensibilidad mínima",
            0.50,
            1.00,
            float(p["sens_min"]),
            0.01,
            help="Qué fracción de los episodios de somnolencia debe detectar la alarma.",
        )
        c_om = c2.slider(
            "Costo de una omisión",
            1.0,
            30.0,
            float(p["costo_omision"]),
            0.5,
            help="Qué tan grave es no avisar cuando el chofer sí se duerme.",
        )
        c_fa = c3.slider(
            "Costo de una falsa alarma",
            1.0,
            30.0,
            float(p["costo_falsa_alarma"]),
            0.5,
            help="Qué tan molesto es avisar cuando el chofer iba alerta.",
        )
        d1, d2 = st.columns([1, 2])
        excluir = d1.checkbox(
            "Descartar movimiento",
            value=True,
            help="Quita los intervalos con artefactos de movimiento.",
        )
        usar = ~datos.artefacto if excluir else np.ones_like(datos.artefacto)
        y = datos.somnolencia[usar]
        I = datos.indice.to_numpy()[usar]
        roc = modelo.curva_roc(I, y)
        try:
            rec = modelo.elegir_umbral(roc, sens, c_om, c_fa)
        except ValueError:
            rec = None
        usar_rec = d1.checkbox(
            "Usar umbral recomendado", value=rec is not None, disabled=rec is None
        )
        c_manual = d2.slider(
            "Umbral c manual",
            float(np.floor(I.min() * 100) / 100),
            float(np.ceil(I.max() * 100) / 100),
            float(rec.umbral if rec else np.median(I)),
            0.01,
            disabled=usar_rec,
        )
    consejo(
        "Con solo 16 episodios de somnolencia, el umbral recomendado cambia a saltos: "
        "casi no se mueve mientras la omisión cueste más que la falsa alarma. "
        "Prueba omisión = 1 y falsa alarma = 8, o desmarca «Usar umbral recomendado» "
        "y mueve el umbral manual."
    )
    c = rec.umbral if (usar_rec and rec) else c_manual
    r = modelo.evaluar_umbral(I, y, c, c_om, c_fa)
    n_alerta = int((y == 0).sum())
    fa_h = r.falsas_alarmas_por_hora(n_alerta, p["duracion_epoca_min"])

    # ---- Indicadores y recomendación
    st.markdown(
        '<div class="kpis">'
        + kpi(f"{r.sensibilidad:.0%}", "Detecta", "de los episodios de somnolencia")
        + kpi(
            f"{r.especificidad:.0%}",
            "Sin falsa alarma",
            "de los intervalos en que iba alerta",
        )
        + kpi(f"{fa_h:.1f} / h", "Falsas alarmas", "por hora de conducción alerta")
        + kpi(f"{roc.auc:.3f}", "AUC", "0,5 = azar · 1 = perfecto")
        + "</div>",
        unsafe_allow_html=True,
    )
    if rec:
        fa_rec = rec.falsas_alarmas_por_hora(n_alerta, p["duracion_epoca_min"])
        st.markdown(
            f'<div class="rec">💜 <b>Recomendación:</b> umbral <b>c = {rec.umbral:.2f}</b>. '
            f"Detecta {rec.sensibilidad:.0%} de la somnolencia con {rec.fp} falsas alarmas "
            f"({fa_rec:.1f} por hora).</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Ningún umbral alcanza la sensibilidad mínima con estos parámetros.")

    # ---- 1. Espectro
    seccion(
        1,
        "Lo que “escucha” la diadema",
        "Cada 5 minutos mide cuánta energía hay en cada frecuencia de las ondas cerebrales.",
    )
    viajes = sorted(set(_viaje_y_epoca(datos)[0].tolist()))
    with tarjeta():
        viaje = st.radio(
            "Viaje", viajes, horizontal=True, format_func=lambda v: f"Viaje {v}"
        )
        mostrar(fig_espectrograma(datos, viaje))
        consejo(
            "Cada columna es un intervalo de 5 min; los colores oscuros son frecuencias con más "
            "energía. Las líneas punteadas separan las bandas θ (theta), α (alfa) y β (beta)."
        )
    with tarjeta():
        epocas = sorted(
            _viaje_y_epoca(datos)[1][_viaje_y_epoca(datos)[0] == viaje].tolist()
        )
        epoca = st.select_slider(
            "Elige un intervalo del viaje", options=epocas, value=epocas[0]
        )
        izq, der = st.columns([3, 2])
        mostrar(fig_espectro_epoca(datos, viaje, epoca), izq)
        der.markdown("**Área de cada banda**")
        der.dataframe(tabla_integrales(datos, viaje, epoca).round(3), hide_index=True)
        consejo(
            "La potencia de una banda es el <b>área bajo la curva</b> entre dos frecuencias: "
            "una integral. Se calcula con Simpson y se compara con el trapecio."
        )

    # ---- 2. Índice
    seccion(
        2,
        "El índice y la alarma",
        "Las ondas lentas (θ + α) suben al dormirse y las rápidas (β) bajan.",
    )
    with tarjeta():
        mostrar(fig_indice(datos, viaje, c))
        consejo(
            "El índice es I = (θ + α) / β. Si el punto pasa la línea dorada (el umbral), "
            "suena la alarma. La zona rosada es donde el video vio al chofer somnoliento."
        )

    # ---- 3. Qué tan bien funciona
    seccion(
        3,
        "¿Qué tan bien funciona?",
        "Cada umbral posible es un punto de la curva ROC; el elegido va en dorado.",
    )
    izq, der = st.columns([1, 1])
    with izq:
        with tarjeta():
            mostrar(fig_roc(roc, r))
            consejo(
                "Cuanto más pegada a la esquina de arriba a la izquierda, mejor. "
                "El AUC es el área bajo esta curva."
            )
    with der:
        with tarjeta():
            st.markdown(f"**Aciertos y errores con c = {c:.2f}**")
            st.markdown(matriz_html(r), unsafe_allow_html=True)
            st.markdown(f"Costo total: **{r.costo:.1f}** unidades.")
            consejo(
                "Una omisión (rosa fuerte) es lo más grave: la alarma no sonó y el chofer "
                "sí se estaba durmiendo."
            )

    # ---- 4. Escenarios
    seccion(
        4,
        "¿Y si cambian las reglas?",
        "Tres escenarios comparados con los ajustes de arriba.",
    )
    tabla = tabla_escenarios(datos, sens, c_om, c_fa)
    cols = st.columns(3)
    for i, col in enumerate(cols):
        col.markdown(
            tarjeta_escenario(tabla.iloc[i], NOMBRES[i], CUANDO[i], i == 0),
            unsafe_allow_html=True,
        )
    with tarjeta():
        g1, g2 = st.columns([3, 2])
        mostrar(fig_escenarios(tabla, sens), g1)
        mostrar(fig_barrido(tabla_barrido(datos)), g2)
        consejo(
            "A la derecha: el umbral óptimo casi no cambia aunque cambien los costos, "
            "salvo cuando una falsa alarma se considera casi tan grave como una omisión."
        )

    # ---- Datos y método
    seccion(5, "Datos y método", "Para quien quiera revisar los números.")
    epocas_df = datos.potencias.assign(
        indice=datos.indice,
        somnolencia=datos.somnolencia,
        artefacto=datos.artefacto,
        tiempo_reaccion_ms=datos.tiempo_reaccion,
    )
    with st.expander("📋 Tabla por intervalo (potencias en µV², índice adimensional)"):
        st.write(
            f"{len(epocas_df)} intervalos; {int(datos.artefacto.sum())} con movimiento brusco."
        )
        st.dataframe(epocas_df.round(3))
        st.download_button(
            "Descargar tabla por época (CSV)",
            epocas_df.to_csv().encode("utf-8"),
            file_name="potencias_por_epoca.csv",
            mime="text/csv",
        )
    with st.expander("📊 Escenarios en tabla"):
        st.dataframe(tabla.round(3))
        st.download_button(
            "Descargar escenarios (CSV)",
            tabla.to_csv(index=False).encode("utf-8"),
            file_name="escenarios.csv",
            mime="text/csv",
        )
    st.markdown(
        '<div class="pie">Datos simulados con fines didácticos · '
        "MA-0321 Cálculo Diferencial e Integral · UCR Sede del Sur</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
