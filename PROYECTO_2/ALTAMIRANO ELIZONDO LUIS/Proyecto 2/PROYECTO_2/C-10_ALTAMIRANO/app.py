"""Aplicación web (Streamlit): procrastinación y entregas en Mediación Virtual.

Ejecutar con:  streamlit run app.py
Importa todas las funciones de src/; aquí solo hay interfaz y gráficos.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.escenarios import (
    bootstrap_diferencia,
    elegir_estrategia,
    resumen_grupo,
    sensibilidad_tratamientos,
    sensibilidad_umbral,
    texto_recomendacion,
    umbral_de_cambio,
)
from src.estilo import COLORES_CLARO, FUENTE, LINEAS_CLARO, aplicar_tema
from src.explicador import explicar
from src.limpieza import cargar_datos, depurar_entregas, informe_depuracion, leer_parametros
from src.modelo import (
    densidad_modelo,
    estimar_k,
    f_empirica,
    f_modelo,
    fraccion_ultimas,
    indice_procrastinacion,
)

RUTA_DEFECTO = Path(__file__).resolve().parent / "datos" / "P05_C-10_ALTAMIRANO.xlsx"
COLORES = COLORES_CLARO
aplicar_tema(oscuro=False)  # la página es oscura, pero los gráficos van sobre fondo blanco

st.set_page_config(page_title="Procrastinación y entregas", layout="wide")


@st.cache_data(show_spinner="Leyendo y depurando los datos…")
def preparar(origen, atipicos):
    """Lee el Excel y lo depura. Se guarda en caché para no repetir el cálculo."""
    hojas = cargar_datos(origen)
    p = leer_parametros(hojas["Parametros"])
    dep = depurar_entregas(hojas["Entregas"], hojas["Tareas"], p["nota_max"], atipicos)
    return hojas, p, dep


@st.cache_data(show_spinner="Calculando indicadores…")
def indicadores(origen, atipicos):
    hojas, p, dep = preparar(origen, atipicos)
    res = resumen_grupo(dep, hojas["Grupos"], p["ventana_h"], p["nota_max"])
    sens = sensibilidad_tratamientos(
        hojas["Entregas"],
        hojas["Tareas"],
        hojas["Grupos"],
        p["ventana_h"],
        p["nota_max"],
        p["umbral_nota"],
    )
    return res, sens


def csv(df):
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------- barra lateral
st.title("Procrastinación y entregas de tareas en Mediación Virtual")
st.caption("MA-0321 · Proyecto Aplicado 2 · Sede del Sur, UCR")

with st.sidebar:
    st.header("Controles")
    subido = st.file_uploader("Otra base (Excel con la misma estructura)", type=["xlsx"])
    origen = subido if subido is not None else str(RUTA_DEFECTO)
    atipicos = st.radio(
        "Notas mayores que 100",
        ["dividir10", "descartar", "tope"],
        format_func={
            "dividir10": "Corregir (÷10)",
            "descartar": "Descartar",
            "tope": "Tope en 100",
        }.get,
    )

try:
    hojas, p, dep = preparar(origen, atipicos)
    res, sens = indicadores(origen, atipicos)
except (ValueError, KeyError) as error:
    st.error(f"No se pudo leer la base: {error}")
    st.stop()

with st.sidebar:
    grupo = st.selectbox("Grupo", res["grupo"].tolist(), index=2 if len(res) > 2 else 0)
    tareas = ["Todas"] + sorted(dep["tarea"].unique().tolist())
    tarea = st.selectbox("Tarea", tareas)
    umbral = st.number_input(
        "Diferencia mínima de nota (puntos)",
        min_value=0.0,
        max_value=20.0,
        value=float(p["umbral_nota"]),
        step=0.5,
    )

# ------------------------------------------------------- datos de la selección
sel = dep[dep["grupo"] == grupo]
if tarea != "Todas":
    sel = sel[sel["tarea"] == tarea]
T = float(sel["plazo_h"].iloc[0])
a_tiempo = sel[~sel["tardia"] & ~sel["antes_apertura"]]
ip_obs = indice_procrastinacion(a_tiempo["tau"]) if len(a_tiempo) else float("nan")
try:
    k_est = estimar_k(ip_obs, T)
    k_msg = None
except ValueError as error:
    k_est, k_msg = 0.1, str(error)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Curva acumulada", "Densidad y últimas 24 h", "Decisión", "Explicación en palabras", "Datos"]
)

with st.sidebar:
    modo_k = st.radio("Valor de k", ["Estimado por bisección", "Manual"])
    k_manual = st.slider(
        "k manual (1/h)",
        0.001,
        3.0,
        0.1,
        0.001,
        format="%.3f",
        disabled=(modo_k != "Manual"),
        help="Solo se usa si eliges 'Manual': muévelo para ver cómo cambia el modelo.",
    )
k = k_est if modo_k == "Estimado por bisección" else k_manual

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Índice de procrastinación (IP)", f"{ip_obs:.3f}")
    c2.metric("k estimado (1/h)", f"{k_est:.3f}")
    c3.metric("Entregas tardías", f"{100 * sel['tardia'].mean():.1f} %")
    c4.metric("Nota media", f"{sel['nota'].mean():.1f}")
    if k_msg:
        st.warning(f"Con esta selección no se pudo estimar k: {k_msg}")
    malla, F = f_empirica(a_tiempo["tau"])
    fig, ax = plt.subplots(figsize=(7, 4.3))
    ax.fill_between(
        malla,
        F,
        1,
        color=COLORES.get(grupo, COLORES_CLARO["G03"]),
        alpha=0.18,
        label=f"IP = {ip_obs:.2f} (área)",
    )
    ax.step(
        malla,
        F,
        where="post",
        color=COLORES.get(grupo, COLORES_CLARO["G03"]),
        lw=1.8,
        label="F observada",
    )
    ax.plot(
        malla,
        f_modelo(malla * T, k, T),
        color=LINEAS_CLARO["linea"],
        ls="--",
        label=f"modelo (k = {k:.3f} 1/h)",
    )
    ax.set_xlabel("Fracción del plazo transcurrida, t/T (sin unidad)")
    ax.set_ylabel("Fracción acumulada de entregas")
    ax.set_title(f"{grupo} · {tarea}: entregas acumuladas")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(
        "El área sombreada es la integral de 1 − F: coincide con el promedio de t/T. " + FUENTE
    )

with tab2:
    ventana = p["ventana_h"]
    obs24 = float((a_tiempo["horas"] >= T - ventana).mean()) if len(a_tiempo) else float("nan")
    mod24 = fraccion_ultimas(k, T, ventana)
    c1, c2 = st.columns(2)
    c1.metric(f"Últimas {ventana:.0f} h: observado", f"{100 * obs24:.1f} %")
    c2.metric(
        f"Últimas {ventana:.0f} h: modelo",
        f"{100 * mod24:.1f} %",
        f"{100 * (mod24 - obs24):+.1f} pts",
    )
    t = np.linspace(0, T, 400)
    fig, ax = plt.subplots(figsize=(7, 4.3))
    ax.hist(
        a_tiempo["horas"],
        bins=np.linspace(0, T, 25),
        density=True,
        color=LINEAS_CLARO["hist"],
        alpha=0.6,
        label="observado",
    )
    ax.plot(t, densidad_modelo(t, k, T), color=LINEAS_CLARO["linea"], label="modelo f_k")
    m = t >= T - ventana
    ax.fill_between(
        t[m],
        0,
        densidad_modelo(t[m], k, T),
        color=LINEAS_CLARO["alerta"],
        alpha=0.4,
        label=f"últimas {ventana:.0f} h",
    )
    ax.set_xlabel("Horas desde la apertura (h)")
    ax.set_ylabel("Densidad de entregas (1/h)")
    ax.set_title(f"{grupo} · {tarea}: densidad de entregas")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Fracción de las últimas horas: ln(1 + 24k) / ln(1 + kT). " + FUENTE)

with tab3:
    elegida, expl = elegir_estrategia(res, umbral)
    st.subheader(
        f"Estrategia recomendada: {res.set_index('grupo').loc[elegida, 'estrategia']} ({elegida})"
    )
    st.write(texto_recomendacion(res, elegida, expl))
    st.markdown("**Escenario base y dos alternativas**")
    base = res.loc[res["horas_docente"].idxmin()]
    otros = res[res["grupo"] != base["grupo"]].sort_values("nota_media", ascending=False).head(2)
    escenarios = [("Escenario base", base)] + [
        (f"Alternativa {i}", fila) for i, (_, fila) in enumerate(otros.iterrows(), 1)
    ]
    for col, (etiqueta, fila) in zip(st.columns(3), escenarios, strict=False):
        with col:
            st.markdown(f"**{etiqueta}: {fila['estrategia']} ({fila['grupo']})**")
            es_base = etiqueta == "Escenario base"
            dif = None if es_base else f"{fila['nota_media'] - base['nota_media']:+.1f} vs base"
            st.metric("Nota media", f"{fila['nota_media']:.1f}", dif)
            st.metric("Entregas tardías", f"{fila['tardias_pct']:.1f} %")
            st.metric("Horas docentes por tarea", f"{fila['horas_docente']:.1f}")
    tabla = res[
        [
            "grupo",
            "estrategia",
            "horas_docente",
            "nota_media",
            "tardias_pct",
            "ip_obs",
            "k",
            "ultimas_obs",
            "ultimas_modelo",
            "no_entregas_pct",
        ]
    ].rename(
        columns={
            "horas_docente": "h docentes/tarea",
            "nota_media": "nota media",
            "tardias_pct": "tardías %",
            "ip_obs": "IP",
            "k": "k (1/h)",
            "ultimas_obs": "últ. 24 h obs.",
            "ultimas_modelo": "últ. 24 h modelo",
            "no_entregas_pct": "sin entrega %",
        }
    )
    st.dataframe(tabla.round(3), hide_index=True, width="stretch")
    st.download_button(
        "Descargar indicadores (CSV)", csv(tabla.round(4)), "indicadores_grupos.csv", "text/csv"
    )

    otra = "G04" if elegida != "G04" else "G01"
    dif, lo, hi = bootstrap_diferencia(dep, elegida, otra, repeticiones=2000)
    st.info(
        f"Diferencia de nota media entre {elegida} y {otra}: {dif:.1f} puntos "
        f"(intervalo del 95 %: de {lo:.1f} a {hi:.1f}, remuestreando estudiantes)."
    )
    st.markdown("**Sensibilidad al tratamiento de los datos**")
    st.dataframe(sens, hide_index=True, width="stretch")
    st.markdown("**Sensibilidad a la diferencia mínima de nota**")
    st.dataframe(sensibilidad_umbral(res, [0.5, 1, 2, 3, 5, 6, 7, 8]), hide_index=True)
    st.caption("Cambia de estrategia a partir de estos umbrales:")
    st.dataframe(umbral_de_cambio(res), hide_index=True)
    st.download_button("Descargar sensibilidad (CSV)", csv(sens), "sensibilidad.csv", "text/csv")
    st.warning(
        "Limitación: los grupos no se asignaron al azar, así que la diferencia de notas puede deberse "
        "en parte a diferencias entre los estudiantes y no solo a la estrategia."
    )
    with st.expander("Qué se hizo con los datos"):
        st.json(informe_depuracion(hojas["Entregas"], dep))

with tab4:
    st.write("Resumen en lenguaje sencillo de la recomendación para quien toma la decisión.")
    r = res.set_index("grupo")
    datos_ia = {
        "recomendada": elegida,
        "umbral_puntos": umbral,
        "grupos": {
            g: {
                "estrategia": row["estrategia"],
                "nota_media": round(float(row["nota_media"]), 1),
                "ip": round(float(row["ip_obs"]), 2),
                "horas_docentes": round(float(row["horas_docente"]), 1),
                "tardias_pct": round(float(row["tardias_pct"]), 1),
                "ultimas24h_pct": round(100 * float(row["ultimas_obs"]), 1),
            }
            for g, row in r.iterrows()
        },
    }
    if st.button("Explicar este resultado"):
        try:
            clave = st.secrets.get("GROQ_API_KEY")
        except (FileNotFoundError, KeyError):
            clave = None  # no hay secrets.toml: se usa el texto local
        texto, origen_texto = explicar(datos_ia, clave=clave)
        st.write(texto)
        st.caption(
            "Redactado con IA a partir de las cifras calculadas por el proyecto."
            if origen_texto == "ia"
            else "Texto generado por el código del proyecto (sin IA)."
        )

with tab5:
    st.write(
        "Aquí están los datos del Excel. Cada fila de *Entregas depuradas* es la entrega de un estudiante "
        "en una tarea, ya limpia. Cambia el grupo y la tarea a la izquierda para filtrarla."
    )
    st.markdown(f"**Entregas depuradas: {grupo} · {tarea}** ({len(sel)} filas)")
    vista = sel[
        [
            "grupo",
            "tarea",
            "estudiante",
            "intento",
            "fecha",
            "nota",
            "nota_original",
            "horas",
            "tau",
            "tardia",
        ]
    ].copy()
    vista["fecha"] = vista["fecha"].dt.strftime("%Y-%m-%d %H:%M")
    vista = vista.rename(
        columns={
            "nota_original": "nota original",
            "horas": "horas desde apertura (h)",
            "tau": "t/T (fracción del plazo)",
            "tardia": "tardía",
        }
    )
    st.dataframe(vista.round(3), hide_index=True, width="stretch")
    st.download_button(
        "Descargar esta tabla (CSV)", csv(vista), "entregas_depuradas.csv", "text/csv"
    )
    for nombre in ["Entregas", "Tareas", "Grupos", "Parametros"]:
        with st.expander(f"Hoja «{nombre}» del Excel, tal como viene"):
            st.dataframe(hojas[nombre], hide_index=True, width="stretch")
