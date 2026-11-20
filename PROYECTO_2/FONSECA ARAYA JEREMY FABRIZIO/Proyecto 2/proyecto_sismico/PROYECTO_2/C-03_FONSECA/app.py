"""Aplicación Streamlit. La interfaz importa todos los cálculos desde src/."""

from io import BytesIO

import matplotlib.pyplot as plt
import streamlit as st

from src.analisis import analizar, formato_colones, tabla_visible
from src.graficas import (
    figura_arias,
    figura_descuento,
    figura_exploracion,
    figura_movimiento,
    figura_pae,
    figura_recurrencia,
    figura_sensibilidad,
    figura_vpn,
)
from src.limpieza import EXCEL, BaseDatos, leer_base
from src.modelo import estimar_b

st.set_page_config(page_title="Golfito | Evaluación de refuerzos", page_icon="🏥", layout="wide")


@st.cache_data(show_spinner=False)
def cargar(contenido: bytes) -> BaseDatos:
    """Valida los bytes del Excel y devuelve tablas; la caché depende del contenido."""
    return leer_base(BytesIO(contenido))


@st.cache_data(show_spinner=False)
def calcular(contenido: bytes, b: float, r: float) -> dict:
    """Calcula escenarios con b adimensional y r fracción/año, y guarda en caché."""
    return analizar(cargar(contenido), b, r)


def mostrar_figura(figura: plt.Figure) -> None:
    """Presenta una figura y libera memoria para las siguientes interacciones."""
    st.pyplot(figura)
    plt.close(figura)


def main() -> None:
    """Construye la interfaz y maneja errores de entradas con mensajes legibles."""
    st.title("¿Qué refuerzo conviene financiar?")
    st.caption("Hospital de Golfito · Proyecto de cálculo integral · Datos simulados del docente")
    with st.sidebar:
        st.header("Datos y supuestos")
        archivo = st.file_uploader("Usar otro Excel con la misma estructura", type=["xlsx"])
    try:
        contenido = archivo.getvalue() if archivo else EXCEL.read_bytes()
        base = cargar(contenido)
        b_estimado = estimar_b(base.hojas["Catalogo_sismos"], base.m0)
        r_base = base.parametro("Tasa de descuento anual")
        # La identidad del archivo reinicia controles al cambiar de base.
        import hashlib

        identidad = hashlib.sha256(contenido).hexdigest()[:12]
        with st.sidebar:
            b = st.number_input(
                "Parámetro b",
                min_value=0.1,
                value=b_estimado,
                step=0.01,
                format="%.4f",
                key=f"b_{identidad}",
                help="Un b mayor indica menos eventos grandes según el modelo.",
            )
            r = st.number_input(
                "Descuento anual (%)",
                min_value=0.0,
                value=r_base,
                step=0.5,
                key=f"r_{identidad}",
                help="Valoramos hoy los ahorros futuros con descuento continuo.",
            )
            opcion = st.selectbox(
                "Alternativa para inspeccionar", ["Sin refuerzo", "Opción A", "Opción B"], index=1
            )
            st.caption(f"Base del Excel: b={b_estimado:.4f}, descuento={r_base:g} %.")
            if st.button("Restablecer valores del Excel"):
                del st.session_state[f"b_{identidad}"]
                del st.session_state[f"r_{identidad}"]
                st.rerun()
        resultado = calcular(contenido, b, r / 100)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        st.error(f"Revisá los datos: {exc}")
        st.stop()
    rec = resultado["recomendacion"]
    tabs = st.tabs(
        ["Decisión", "Movimiento del suelo", "Cálculos y verificación", "Datos y supuestos"]
    )
    with tabs[0]:
        if rec["escenario"] == "Sin refuerzo":
            st.warning(
                "Con estos supuestos, ninguna opción de refuerzo tiene VPN positivo. La evaluación económica favorece no invertir."
            )
        else:
            st.success(f"El modelo recomienda {rec['escenario']}: {rec['descripcion'].lower()}.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Inversión inicial", formato_colones(rec["costo_colones"]))
        c2.metric("Pérdida evitada cada año", formato_colones(rec["ahorro_anual_colones"]))
        c3.metric("Valor presente neto (VPN)", formato_colones(rec["vpn_colones"]))
        st.write(
            f"Horizonte: **{resultado['H']:g} años**. Plazo de obra: **{rec['plazo_meses']:g} meses**. "
            f"Probabilidad modelada de al menos un sismo **M ≥ 7 en 50 años: {resultado['prob7_50']:.2%}**."
        )
        st.caption(
            "VPN = valor actual de las pérdidas evitadas menos la inversión. Un VPN positivo favorece la inversión bajo estos supuestos."
        )
        st.dataframe(tabla_visible(resultado["escenarios"]), hide_index=True, width="stretch")
        seleccion = resultado["escenarios"].set_index("escenario").loc[opcion]
        if opcion != "Sin refuerzo":
            st.info(
                f"En {opcion}, cada ₡1 invertido evita aproximadamente ₡{seleccion.ahorro_anual_por_colon:.4f} "
                "de pérdida esperada por año. Es una razón anual, no el VPN ni un ahorro garantizado."
            )
        mostrar_figura(figura_vpn(resultado))
        with st.expander("¿Qué pasa si cambian los supuestos?"):
            st.write(
                "Comparación alrededor de los valores originales: b ±0,1 y descuento ±2 puntos porcentuales."
            )
            mostrar_figura(figura_sensibilidad(resultado))
            st.dataframe(resultado["sensibilidad"], hide_index=True)
        st.download_button(
            "Descargar comparación (CSV)",
            resultado["escenarios"].to_csv(index=False).encode("utf-8-sig"),
            "comparacion_refuerzos.csv",
            "text/csv",
        )
        st.caption(
            "Modelo académico con datos simulados. La decisión real también requiere evaluación estructural y continuidad hospitalaria."
        )
    with tabs[1]:
        i = resultado["indicadores"]
        cols = st.columns(4)
        for col, etiqueta, clave, unidad in zip(
            cols,
            ["PGA", "PGV", "PGD", "Arias"],
            ["PGA_cm_s2", "PGV_cm_s", "PGD_cm", "IA_m_s"],
            ["cm/s²", "cm/s", "cm", "m/s"],
            strict=True,
        ):
            col.metric(etiqueta, f"{i[clave]:.3f} {unidad}")
        st.write(
            "PGA, PGV y PGD son los máximos absolutos de aceleración, velocidad y desplazamiento. "
            "Arias resume la intensidad acumulando la aceleración al cuadrado."
        )
        st.write(
            f"Se resta un sesgo de **{i['linea_base_cm_s2']:.6f} cm/s²**, calculado antes del sismo."
        )
        for variable in ["aceleracion", "velocidad", "desplazamiento"]:
            mostrar_figura(figura_movimiento(resultado, variable))
        if i["duracion_s"] is not None:
            st.write(
                f"Duración significativa: **{i['duracion_s']:.2f} s** (entre {i['t5_s']:.2f} y {i['t95_s']:.2f} s)."
            )
        mostrar_figura(figura_arias(resultado))
        st.download_button(
            "Descargar series procesadas",
            resultado["series"].to_csv(index=False).encode("utf-8-sig"),
            "movimiento.csv",
            "text/csv",
        )
    with tabs[2]:
        st.subheader("1. Frecuencia de los sismos")
        st.latex(
            r"b=\frac{\log_{10}(e)}{\overline m-(3-0.05)},\quad \lambda(m)=\lambda_3 10^{-b(m-3)}"
        )
        st.write(
            f"{len(base.hojas['Catalogo_sismos'])} sismos / {base.anos_catalogo} años = "
            f"**{resultado['lambda3']:.4f} sismos/año**. b estimado: **{b_estimado:.6f}**."
        )
        st.latex(r"P(M\geq m\text{ en }T)=1-e^{-\lambda(m)T}")
        st.write(
            f"En 50 años: P(M ≥ 6) = **{resultado['prob6_50']:.2%}**, P(M ≥ 7) = **{resultado['prob7_50']:.2%}**."
        )
        mostrar_figura(figura_recurrencia(base, resultado))
        st.subheader("2. Integrar para acumular movimiento")
        st.latex(
            r"v(t)=\int_0^t a(u)\,du,\quad x(t)=\int_0^t v(u)\,du,\quad I_A=\frac{\pi}{2g}\int_0^T a_m(t)^2\,dt"
        )
        st.write("Trapecio acumulado propio; v(0)=x(0)=0. Para Arias, a_m=a/100 está en m/s².")
        st.subheader("3. Convertir riesgo en pérdida anual")
        st.latex(r"PAE=V_R\int_5^8 D(m)\,b\ln(10)\lambda(m)\,dm")
        st.write(
            "El daño del Excel se divide entre 100. Se interpola linealmente entre magnitudes y se "
            "integra con Simpson propio usando 16 subdivisiones por tramo. Se contrasta con la integral exacta del mismo modelo."
        )
        mostrar_figura(figura_pae(base, resultado))
        st.subheader("4. Comparar el beneficio con la inversión")
        st.latex(
            r"VPN=-C+\Delta PAE\frac{1-e^{-rH}}{r}\quad(r>0);\qquad VPN=-C+\Delta PAE\,H\quad(r=0)"
        )
        mostrar_figura(figura_descuento(resultado, opcion))
        with st.expander("Ver las verificaciones numéricas"):
            st.dataframe(resultado["verificacion"], hide_index=True)
            st.write(
                "En las series reales, la discrepancia entre métodos no es el error respecto a una verdad conocida. "
                "En la velocidad final puede ser grande en porcentaje por la cancelación de áreas positivas y negativas."
            )
            st.write(
                "Prueba obligatoria con a(t)=sin(t): ambas integraciones deben tener error menor que 0,5 %."
            )
            st.dataframe(resultado["seno"], hide_index=True)
    with tabs[3]:
        st.write(
            "El Excel original se conserva intacto. Las tablas procesadas viven en memoria y se pueden descargar."
        )
        st.dataframe(base.incidencias, hide_index=True)
        mostrar_figura(figura_exploracion(base))
        st.write(
            "Supuestos: catálogo completo en los años calendario cubiertos, tasa constante, eventos independientes, "
            "daño dependiente solo de magnitud y ahorro anual constante. El modelo no estima lesiones ni vidas salvadas."
        )
        st.write(
            "La probabilidad es regional. La distancia y profundidad se exploran, pero no ajustan la tasa ni el daño "
            "en el modelo simplificado solicitado. Un acelerograma aislado no calibra la recurrencia regional."
        )
        hoja = st.selectbox("Tabla para consultar", list(base.hojas))
        st.dataframe(base.hojas[hoja], hide_index=True)


if __name__ == "__main__":
    main()
