"""Aplicación web: campaña de voluntariado para el conteo de rapaces en Kèköldi.

Para abrirla (desde la carpeta del proyecto):

    streamlit run app.py

Toda la matemática está en src/; aquí solo se arma la página:
controles a la izquierda, indicadores arriba y gráficos en pestañas.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from src import escenarios as es
from src import graficos as gr
from src.datos import RUTA_POR_DEFECTO, Parametros, cargar_base
from src.limpieza import limpiar_conteos, resumen_limpieza
from src.modelo import CurvaDePaso, perfil_horario, totales_diarios

st.set_page_config(page_title="Rapaces Kèköldi · campaña óptima", page_icon="🦅", layout="wide")


# ----------------------------------------------------------------------
# Cálculos guardados en caché (no se repiten si nada cambió)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Leyendo la base…")
def leer(contenido: bytes | None) -> tuple[pd.DataFrame, Parametros]:
    """Lee el Excel subido o, si no hay, el de la carpeta datos/."""
    fuente = io.BytesIO(contenido) if contenido else RUTA_POR_DEFECTO
    base = cargar_base(fuente)
    return base.conteos, base.parametros


@st.cache_data(show_spinner="Limpiando y calculando totales diarios…")
def preparar(conteos: pd.DataFrame, factor: float, hi: float, hf: float):
    """Limpia los conteos y calcula N_d (integral de cada día)."""
    limpio = limpiar_conteos(conteos, factor=factor)
    return limpio, totales_diarios(limpio, hi, hf)


def pct(x: float) -> str:
    return f"{x:.1%}".replace(".", ",")


def miles(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


# ----------------------------------------------------------------------
# Barra lateral: datos y controles
# ----------------------------------------------------------------------
st.sidebar.header("Datos")
subido = st.sidebar.file_uploader("Cargar otra base (.xlsx con la misma estructura)", type=["xlsx"])
try:
    conteos, p0 = leer(subido.getvalue() if subido else None)
except ValueError as error:
    st.error(f"No se pudo usar el archivo: {error}")
    st.stop()

st.sidebar.header("Parámetros de la campaña")
L = st.sidebar.slider("Duración de la campaña L (días)", 7, 35, p0.dias_campana)
horas = st.sidebar.slider("Horas por turno", 1, 9, p0.horas_turno)
inicio_trad = st.sidebar.slider(
    "Inicio de la campaña tradicional (días desde el 20/9)",
    0,
    49 - L,
    min(int(p0.inicio_tradicional), 49 - L),
)
st.sidebar.header("Supuestos del modelo")
# El vuelo no puede empezar después de las 7:00 ni terminar antes de las 16:00.
margen = min(7 - p0.hi, p0.hf - 16)
minimo_ajuste = -float(int(margen * 4)) / 4  # redondeado a cuartos de hora
ajuste = st.sidebar.slider(
    "Ajuste a la duración del vuelo (± h)",
    minimo_ajuste,
    1.0,
    0.0,
    0.25,
    help="Negativo: el vuelo empieza más tarde y termina más temprano.",
)
factor = st.sidebar.select_slider(
    "Criterio de 'cero de más' (veces sus vecinas)", options=[3, 4, 5, 7, 10], value=5
)

p = Parametros(
    hi=p0.hi - ajuste,
    hf=p0.hf + ajuste,
    dias_campana=L,
    horas_turno=horas,
    inicio_tradicional=float(inicio_trad),
)
st.sidebar.caption(
    f"Vuelo migratorio: {es.hora_texto(p.hi)} a {es.hora_texto(p.hf)} "
    f"(Excel: {es.hora_texto(p0.hi)} a {es.hora_texto(p0.hf)})."
)

# ----------------------------------------------------------------------
# Cálculos
# ----------------------------------------------------------------------
limpio, totales = preparar(conteos, factor, p.hi, p.hf)
t = totales["dia"]
curvas = {e: CurvaDePaso(e, t, totales[e]) for e in [*es.ESPECIES, "Total"]}
escenarios = es.comparar_escenarios(totales, limpio, p)
optimo = escenarios[escenarios["nombre"].str.startswith("Óptima")].iloc[0]
trad = escenarios[escenarios["nombre"] == "Tradicional"].iloc[0]

# ----------------------------------------------------------------------
# Encabezado, recomendación e indicadores
# ----------------------------------------------------------------------
st.title("🦅 ¿Cuándo y a qué hora contar rapaces en Kèköldi?")
st.caption(
    "Programa de conteo de rapaces migratorias · Kèköldi, Talamanca. "
    "Datos simulados con fines didácticos (MA-0321, UCR Sede del Sur)."
)
st.success(f"**Recomendación.** {es.recomendacion(escenarios)}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Aves en la temporada (estimado)", miles(curvas["Total"].total))
c2.metric(
    "Registradas: campaña recomendada",
    pct(optimo["frac_registrada"]),
    f"{(optimo['frac_registrada'] - trad['frac_registrada']) * 100:+.1f} pts vs. tradicional",
)
c3.metric("Registradas: campaña tradicional", pct(trad["frac_registrada"]))
c4.metric(
    "Mejor turno",
    f"{es.hora_texto(optimo['hora_inicio'])}–{es.hora_texto(optimo['hora_fin'])}",
    f"{pct(optimo['frac_turno'])} de las aves del día",
    delta_color="off",
)

st.subheader("Aves por especie y fechas clave del paso")
fecha0 = pd.Timestamp(totales["fecha"].min())
cols = st.columns(3)
for col, especie in zip(cols, es.ESPECIES, strict=True):
    c = curvas[especie]
    col.metric(especie, miles(c.total) + " aves")
    col.caption(
        f"5 %: {es.dia_a_fecha(c.percentil(0.05), fecha0)} · "
        f"50 %: {es.dia_a_fecha(c.percentil(0.5), fecha0)} · "
        f"95 %: {es.dia_a_fecha(c.percentil(0.95), fecha0)}  \n"
        f"Fecha media: {es.dia_a_fecha(c.fecha_media(), fecha0)} · "
        f"dispersión: {c.dispersion():.1f} días"
    )

# ----------------------------------------------------------------------
# Pestañas con gráficos
# ----------------------------------------------------------------------
tabs = st.tabs(
    [
        "Paso diario",
        "Curva acumulada",
        "Mejor fecha G(a)",
        "Mejor turno",
        "Escenarios",
        "Limpieza de datos",
        "Descargas",
    ]
)

with tabs[0]:
    st.pyplot(gr.conteos_diarios(totales, es.ESPECIES, optimo["inicio"], L, inicio_trad))
    st.markdown(
        "Cada punto es el **total de un día**, N_d = ∫ r_d(x) dx desde h_i hasta h_f: "
        "la suma de las horas contadas más dos triángulos para las horas sin conteo. "
        "El **área gris** es la integral G(a): las aves que pasan durante la campaña."
    )

with tabs[1]:
    st.pyplot(gr.curva_acumulada(totales, [*es.ESPECIES, "Total"]))
    st.markdown(
        "F(t) = (1/N)·∫ n(u) du indica qué fracción del paso ya ocurrió. Los puntos marcan "
        "las fechas del 5, 50 y 95 %. El gavilán aludo pasa primero, luego el de Swainson "
        "y al final el zopilote."
    )

with tabs[2]:
    st.pyplot(gr.funcion_G(totales, L, inicio_trad))
    st.pyplot(gr.condicion_optimo(totales, L))
    chequeo = es.comprobar_extremos(totales, optimo["inicio"], L)
    st.markdown(
        f"Por el teorema fundamental del cálculo, G'(a) = n(a + L) − n(a). En el máximo "
        f"G'(a) = 0, o sea, **el primer y el último día de la campaña tienen casi las mismas "
        f"aves**. Con la serie suavizada eso ocurre en a ≈ "
        f"{chequeo['a_donde_G_prima_es_cero']:.1f}, y el óptimo calculado es a = "
        f"{optimo['inicio']:.0f}."
    )

with tabs[3]:
    perfil = perfil_horario(limpio, dias=(optimo["inicio"], optimo["fin"]))
    st.pyplot(gr.perfil_y_turno(perfil, optimo["hora_inicio"], horas, p.hi, p.hf))
    st.markdown(
        "Promedio de aves por hora durante las fechas recomendadas. Las barras negras son el "
        "turno que registra más aves; los triángulos rayados son las horas sin conteo."
    )

with tabs[4]:
    st.pyplot(gr.barras_escenarios(escenarios))
    vista = escenarios[
        [
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "frac_fechas",
            "frac_turno",
            "frac_registrada",
            "aves_registradas",
            *[f"frac_{e}" for e in es.ESPECIES],
        ]
    ].copy()
    vista["turno"] = [
        f"{es.hora_texto(a)}–{es.hora_texto(b)}"
        for a, b in zip(escenarios["hora_inicio"], escenarios["hora_fin"], strict=True)
    ]
    st.dataframe(
        vista.style.format(
            {c: "{:.1%}" for c in vista.columns if c.startswith("frac")}
            | {"aves_registradas": "{:,.0f}"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "frac_fechas: fracción del paso en esas fechas · frac_turno: fracción del día en el "
        "turno · frac_registrada = frac_fechas × frac_turno."
    )

with tabs[5]:
    st.dataframe(resumen_limpieza(limpio), hide_index=True)
    atipicos = limpio[limpio["correccion"] == "atípico"]
    st.markdown(
        f"Criterio: un conteo de al menos 20 aves que es más de **{factor} veces** el promedio "
        "de sus horas vecinas se considera un error de digitación (un cero de más). Esos "
        "valores y las horas sin conteo se rellenan interpolando dentro del mismo día."
    )
    st.dataframe(
        atipicos[["fecha", "hora_inicio", "especie", "condicion", "aves_contadas", "aves_limpias"]],
        hide_index=True,
    )
    if not atipicos.empty:
        ej = atipicos.loc[atipicos["aves_contadas"].idxmax()]
        dia = limpio[(limpio["dia"] == ej["dia"]) & (limpio["especie"] == ej["especie"])]
        st.pyplot(
            gr.antes_y_despues(
                dia["aves_contadas"].to_numpy(),
                dia["aves_limpias"].to_numpy(),
                f"{ej['especie']}, {pd.Timestamp(ej['fecha']):%d/%m}",
            )
        )

with tabs[6]:
    st.download_button(
        "Descargar escenarios (CSV)",
        escenarios.to_csv(index=False).encode("utf-8-sig"),
        "escenarios.csv",
        "text/csv",
    )
    st.download_button(
        "Descargar totales diarios por especie (CSV)",
        totales.to_csv(index=False).encode("utf-8-sig"),
        "totales_diarios.csv",
        "text/csv",
    )
    st.download_button(
        "Descargar conteos limpios (CSV)",
        limpio.to_csv(index=False).encode("utf-8-sig"),
        "conteos_limpios.csv",
        "text/csv",
    )
    resumen = pd.DataFrame([c.resumen() for c in curvas.values()])
    st.dataframe(resumen.round(3), hide_index=True)
