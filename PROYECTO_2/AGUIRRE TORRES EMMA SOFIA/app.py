"""Tablero web: ¿conviene repotenciar la Planta Eólica Tejona?  (streamlit run app.py)"""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.escenarios import comparar, escalar_c, precio_equilibrio, preparar, recomendar, vpn
from src.limpieza import cargar_datos
from src.modelo import densidad_weibull, potencia, simpson, trapecio

RUTA_EXCEL = Path(__file__).parent / "datos" / "P09_C-01_AGUIRRE.xlsx"
COLORES = ["#8A94A6", "#0B5394", "#E69138"]  # Mantener, Opción A, Opción B

st.set_page_config(page_title="Repotenciación Tejona", page_icon="🌬️", layout="wide")


@st.cache_data
def analizar(contenido: bytes) -> dict:
    """Lee el Excel (en bytes) y hace la parte pesada del análisis una sola vez."""
    return preparar(cargar_datos(io.BytesIO(contenido)))


def millones(x: float) -> str:
    """Formatea colones como miles de millones: ₡1,23 mil M."""
    return f"₡{x / 1e9:,.2f} mil M"


# ============================ Barra lateral ============================
st.sidebar.title("🌬️ Planta Eólica Tejona")
st.sidebar.caption("Tilarán, Guanacaste · 30 turbinas Vestas V47 de 660 kW")
subido = st.sidebar.file_uploader("Cargar otra base (.xlsx, misma estructura)", type="xlsx")
contenido = subido.getvalue() if subido else RUTA_EXCEL.read_bytes()
try:
    base = analizar(contenido)
except ValueError as error:
    st.error(f"El archivo no tiene la estructura esperada: {error}")
    st.stop()

p = base["params"]
turbinas = base["turbinas"]
nombres = [t.nombre for t in turbinas]

st.sidebar.subheader("Parámetros")
elegida = st.sidebar.selectbox("Opción a explorar", nombres, index=1)
turbina = turbinas[nombres.index(elegida)]
altura = st.sidebar.slider(
    "Altura del buje H (m)",
    40.0,
    140.0,
    turbina.altura_m,
    1.0,
    help="Cambia la altura de la opción elegida; el viento se escala con (H/55)^α.",
)
alpha = st.sidebar.slider(
    "Exponente de cizalladura α",
    0.05,
    0.35,
    p["alpha"],
    0.01,
    help=f"Qué tanto aumenta el viento con la altura (dato de la base: {p['alpha']:.2f}).",
)
precio = st.sidebar.slider(
    "Precio de la energía p (₡/kWh)",
    20.0,
    120.0,
    p["precio"],
    0.5,
    help=f"Precio de la base: ₡{p['precio']:.0f}/kWh.",
)
st.sidebar.caption(
    f"Tasa de descuento {p['tasa_pct']:.0f} % · vida útil {p['vida_anios']:.0f} años · "
    f"pérdidas calibradas L = {base['L']:.1%}"
)

tabla = comparar(base, alpha, precio, alturas={elegida: altura})
ref = tabla.iloc[0]
tasa, anios = p["tasa_pct"] / 100, p["vida_anios"]
tabla["precio_equilibrio"] = [precio_equilibrio(f, ref, tasa, anios) for _, f in tabla.iterrows()]
tabla.loc[0, "precio_equilibrio"] = np.nan

# ============================ Encabezado ============================
st.title("¿Conviene repotenciar la Planta Eólica Tejona?")
st.markdown(
    "Se compara **mantener** las 30 turbinas actuales contra reemplazarlas por "
    "**menos turbinas, más grandes y más altas**. La energía anual se obtiene integrando "
    "la curva de potencia contra la distribución del viento: "
    r"$\bar P=\int_0^\infty P(v)\,f(v)\,dv$."
)

texto = recomendar(tabla)
texto_80 = recomendar(tabla, "vpn_precio_80_colones")
if texto.startswith("Repotenciar"):
    st.success(f"### ✅ {texto}")
else:
    st.warning(f"### ⏸️ {texto}")
st.caption(f"Revisión con precio 20 % menor (₡{0.8 * precio:.1f}/kWh): {texto_80}")

fila = tabla[tabla["opcion"] == elegida].iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    f"Energía anual · {elegida}",
    f"{fila['energia_GWh']:.1f} GWh",
    f"{fila['energia_GWh'] - ref['energia_GWh']:+.1f} GWh vs mantener",
)
c2.metric(
    "Factor de planta",
    f"{fila['factor_planta']:.1%}",
    f"{(fila['factor_planta'] - ref['factor_planta']) * 100:+.1f} pts",
)
c3.metric("VPN frente a mantener", millones(fila["vpn_colones"]))
c4.metric(
    "Precio de equilibrio",
    "—" if np.isnan(fila["precio_equilibrio"]) else f"₡{fila['precio_equilibrio']:.1f}/kWh",
    help="Precio con el que el VPN vale 0. Por debajo de él conviene mantener.",
)

pestanas = st.tabs(
    ["📊 Decisión", "🌀 Viento y energía", "💰 Sensibilidad", "✔️ Validación", "🧹 Datos"]
)

# ============================ 1. Decisión ============================
with pestanas[0]:
    st.subheader("Escenario base y dos alternativas")
    vista = pd.DataFrame(
        {
            "Opción": tabla["opcion"],
            "Turbinas": tabla["turbinas"],
            "Altura (m)": tabla["altura_m"],
            "Energía (GWh/año)": tabla["energia_GWh"],
            "Factor de planta (%)": tabla["factor_planta"] * 100,
            "Inversión (₡ mil M)": tabla["inversion_colones"] / 1e9,
            "VPN (₡ mil M)": tabla["vpn_colones"] / 1e9,
            "VPN precio −20 % (₡ mil M)": tabla["vpn_precio_80_colones"] / 1e9,
            "Precio equilibrio (₡/kWh)": tabla["precio_equilibrio"],
        }
    )
    st.dataframe(
        vista.style.format(precision=2, na_rep="—").highlight_max(
            subset=["VPN (₡ mil M)"], color="#D9EAD3"
        ),
        hide_index=True,
    )
    st.download_button(
        "⬇️ Descargar resultados (CSV)", tabla.to_csv(index=False), "resultados_tejona.csv"
    )

    g1, g2 = st.columns(2)
    fig_e = go.Figure(
        go.Bar(
            x=tabla["opcion"],
            y=tabla["energia_GWh"],
            marker_color=COLORES,
            text=tabla["energia_GWh"].round(1),
            textposition="outside",
        )
    )
    fig_e.update_layout(title="Energía anual", yaxis_title="GWh/año", height=380)
    g1.plotly_chart(fig_e)

    fig_v = go.Figure()
    fig_v.add_bar(
        x=tabla["opcion"],
        y=tabla["vpn_colones"] / 1e9,
        name=f"₡{precio:.1f}/kWh",
        marker_color="#0B5394",
    )
    fig_v.add_bar(
        x=tabla["opcion"],
        y=tabla["vpn_precio_80_colones"] / 1e9,
        name=f"₡{0.8 * precio:.1f}/kWh (−20 %)",
        marker_color="#CC4125",
    )
    fig_v.add_hline(y=0, line_color="black", line_width=1)
    fig_v.update_layout(
        title="VPN frente a mantener",
        yaxis_title="₡ miles de millones",
        barmode="group",
        height=380,
    )
    g2.plotly_chart(fig_v)

# ============================ 2. Viento y energía ============================
with pestanas[1]:
    malla = np.linspace(0, 25, 501)
    st.subheader("La potencia media es el área bajo P(v)·f(v)")
    st.caption(
        "Cada curva es la potencia de una turbina por la probabilidad de cada velocidad, "
        "con la distribución anual llevada a la altura de su buje. El área sombreada "
        "(integral con Simpson) es la potencia media P̄ en kW."
    )
    fig_a = go.Figure()
    for t, color, f in zip(turbinas, COLORES, tabla.itertuples(), strict=True):
        c_h = escalar_c(p["c_anual_ms"], f.altura_m, p["h_ref_m"], alpha)
        y = potencia(malla, t, base["rho_media"], p["rho_ref"]) * densidad_weibull(
            malla, p["k_anual"], c_h
        )
        area = simpson(y, malla[1] - malla[0])
        fig_a.add_scatter(
            x=malla,
            y=y,
            fill="tozeroy",
            line_color=color,
            name=f"{t.nombre} ({f.altura_m:.0f} m): P̄ = {area:,.0f} kW",
        )
    fig_a.update_layout(
        xaxis_title="Velocidad del viento v (m/s)", yaxis_title="P(v)·f(v) (kW·s/m)", height=420
    )
    st.plotly_chart(fig_a)

    g1, g2 = st.columns(2)
    df = base["viento"]
    fig_h = go.Figure(
        go.Histogram(
            x=df["v_limpia_m_s"],
            histnorm="probability density",
            name="Datos 60 días (55 m)",
            marker_color="#9FC5E8",
        )
    )
    fig_h.add_scatter(
        x=malla,
        y=densidad_weibull(malla, base["k60"], base["c60"]),
        name=f"Weibull 60 días (k={base['k60']:.2f}, c={base['c60']:.2f})",
        line_color="#0B5394",
    )
    c_sel = escalar_c(p["c_anual_ms"], altura, p["h_ref_m"], alpha)
    fig_h.add_scatter(
        x=malla,
        y=densidad_weibull(malla, p["k_anual"], c_sel),
        name=f"Anual a {altura:.0f} m (c={c_sel:.2f})",
        line={"color": "#E69138", "dash": "dash"},
    )
    fig_h.update_layout(
        title="Distribución del viento",
        xaxis_title="Velocidad (m/s)",
        yaxis_title="f(v) (s/m)",
        height=400,
        legend={"y": -0.3},
    )
    g1.plotly_chart(fig_h)

    fig_c = go.Figure()
    for t, color in zip(turbinas, COLORES, strict=True):
        fig_c.add_scatter(x=t.curva_v, y=t.curva_p, name=t.nombre, line_color=color)
    fig_c.update_layout(
        title="Curvas de potencia (ρ = 1,225 kg/m³)",
        xaxis_title="Velocidad (m/s)",
        yaxis_title="Potencia de una turbina (kW)",
        height=400,
        legend={"y": -0.3},
    )
    g2.plotly_chart(fig_c)

    fig_s = go.Figure()
    fig_s.add_scatter(
        x=df["fecha_hora"],
        y=df["v_limpia_m_s"],
        name="Viento (m/s)",
        line={"width": 1, "color": "#0B5394"},
    )
    fig_s.add_scatter(
        x=df["fecha_hora"],
        y=df["p_planta_kW"] / 1000,
        yaxis="y2",
        name="Potencia teórica planta (MW)",
        fill="tozeroy",
        line={"width": 0.5, "color": "#E69138"},
        opacity=0.5,
    )
    fig_s.update_layout(
        title="Serie horaria de los 60 días: el área bajo la potencia es la energía",
        xaxis_title="Fecha",
        yaxis={"title": "Viento (m/s)"},
        yaxis2={"title": "Potencia (MW)", "overlaying": "y", "side": "right"},
        height=400,
        legend={"orientation": "h", "y": -0.25},
    )
    st.plotly_chart(fig_s)

# ============================ 3. Sensibilidad ============================
with pestanas[2]:
    st.subheader("¿Qué tan sensible es la decisión al precio de la energía?")
    precios = np.linspace(30, 100, 141)
    fig_p = go.Figure()
    for f, color in zip(tabla.iloc[1:].itertuples(), COLORES[1:], strict=True):
        curva = [
            vpn(
                f.inversion_colones,
                (f.energia_GWh - ref["energia_GWh"]) * 1e6,
                pr,
                f.mantenimiento_colones - ref["mantenimiento_colones"],
                tasa,
                anios,
            )
            / 1e9
            for pr in precios
        ]
        fig_p.add_scatter(x=precios, y=curva, name=f.opcion, line_color=color)
        fig_p.add_scatter(
            x=[f.precio_equilibrio],
            y=[0],
            mode="markers+text",
            marker={"size": 10, "color": color},
            showlegend=False,
            text=[f"₡{f.precio_equilibrio:.1f}"],
            textposition="top center",
        )
    fig_p.add_hline(y=0, line_color="black", line_width=1)
    fig_p.add_vline(x=precio, line_dash="dot", annotation_text="precio elegido")
    fig_p.add_vline(
        x=0.8 * precio,
        line_dash="dot",
        line_color="#CC4125",
        annotation_text="−20 %",
        annotation_position="bottom right",
    )
    fig_p.update_layout(
        xaxis_title="Precio de la energía (₡/kWh)",
        yaxis_title="VPN frente a mantener (₡ miles de millones)",
        height=450,
    )
    st.plotly_chart(fig_p)
    st.info(
        "Los puntos marcan el **precio de equilibrio** de cada opción "
        r"($p^*=(I/a+\Delta M)/\Delta E$). Si el precio de venta queda por debajo de ese "
        "valor, la repotenciación deja de convenir y lo mejor es mantener."
    )

# ============================ 4. Validación ============================
with pestanas[3]:
    st.subheader("Verificación del modelo")
    v_fina = np.linspace(0, 60, 6001)
    integral_f = simpson(
        densidad_weibull(v_fina, p["k_anual"], p["c_anual_ms"]), v_fina[1] - v_fina[0]
    )
    e_trap = trapecio(df["p_planta_kW"], 1.0)
    e_np = float(np.trapezoid(df["p_planta_kW"], dx=1.0))
    v1, v2, v3 = st.columns(3)
    v1.metric(
        "∫ f(v) dv (debe ser 1)",
        f"{integral_f:.6f}",
        f"error {abs(integral_f - 1):.1e}",
        delta_color="off",
    )
    v2.metric(
        "Trapecio propio vs numpy",
        f"{e_trap / 1e6:,.3f} GWh",
        f"error {abs(e_trap - e_np) / e_np:.1e}",
        delta_color="off",
    )
    v3.metric(
        "Pérdidas calibradas L",
        f"{base['L']:.1%}",
        f"medida {base['e_medida_kWh'] / 1e6:,.2f} vs teórica "
        f"{base['e_teorica_kWh'] / 1e6:,.2f} GWh",
        delta_color="off",
    )

    st.markdown("**Límite de Betz:** ninguna turbina puede tener $C_p > 16/27 \\approx 0{,}593$.")
    betz = pd.DataFrame(
        {
            "Opción": nombres,
            "Diámetro (m)": [t.diametro_m for t in turbinas],
            "Cp máximo": [t.cp(p["rho_ref"]).max() for t in turbinas],
        }
    )
    betz["¿Cumple?"] = np.where(betz["Cp máximo"] <= 16 / 27, "✅ Sí", "❌ No")
    st.dataframe(betz.style.format(precision=3), hide_index=True)

# ============================ 5. Datos ============================
with pestanas[4]:
    st.subheader("Tratamiento de faltantes y atípicos")
    conteo = df["estado_viento"].value_counts()
    d1, d2, d3 = st.columns(3)
    d1.metric("Horas válidas", int(conteo.get("ok", 0)))
    d2.metric("Viento faltante (interpolado)", int(conteo.get("faltante", 0)))
    d3.metric("Picos del anemómetro (interpolados)", int(conteo.get("pico", 0)))
    st.caption(
        "Criterio: es pico si v > 35 m/s o si se aleja más de 8 m/s de la mediana de 5 horas. "
        "Picos y faltantes se reemplazan por interpolación lineal en el tiempo."
    )
    st.dataframe(
        df.loc[
            df["estado_viento"] != "ok",
            ["fecha_hora", "velocidad_m_s", "v_limpia_m_s", "estado_viento"],
        ],
        hide_index=True,
    )
