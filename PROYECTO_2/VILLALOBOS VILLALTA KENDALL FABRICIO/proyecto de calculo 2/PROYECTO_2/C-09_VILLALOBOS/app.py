"""Guía de cafeína para la semana de exámenes (aplicación web en Streamlit).

Ejecutar:  streamlit run app.py

Toda la matemática vive en ``src/``; este archivo solo arma la interfaz.

De dónde salen los datos:
    ``src/pipeline.py`` define ``AnalisisCafeina``, que lee el Excel, limpia los datos,
    ajusta el modelo de cada voluntario y lo agrupa por tipo de eliminación. Aquí solo
    se le piden resultados y se muestran.

Páginas de la aplicación:
    - Inicio: la recomendación de plan para cada tipo de persona.
    - Simulá tu día: el usuario arma su propio plan y ve la curva de cafeína.
    - Comparar planes: los seis planes de la campaña y la hora límite de cada bebida.
    - Escenarios: qué pasa si se repite el plan varios días o se duerme antes,
      y qué dato del modelo cambia más la decisión (sensibilidad).
    - Datos y método: limpieza de datos, fórmulas (AUC, integral impropia,
      superposición), verificación y relación cafeína-atención.
    - Glosario: los términos en palabras simples.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
# Librerías externas (gráficos, números, tablas, interfaz) y los módulos del proyecto en src/.

from __future__ import annotations

import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src import escenarios as esc
from src import exportar
from src import graficos as gr
from src import modelo as mod
from src.config import COBERTURA_PRUDENTE, GRUPOS
from src.limpieza import Parametros
from src.pipeline import AnalisisCafeina

# ---------------------------------------------------------------------------
# Configuración de la página y textos fijos
# ---------------------------------------------------------------------------
# Título e ícono de la pestaña del navegador, y diccionarios que traducen nombres
# internos a textos amigables para la interfaz.

st.set_page_config(
    page_title="Cafeína y sueño · Vida Estudiantil UCR",
    page_icon=":material/coffee:",
    layout="wide",
)

# Nombre con mayúscula de cada tipo de eliminación (para los botones de la barra lateral).
NOMBRE_TIPO = {"rápida": "Rápida", "normal": "Normal", "lenta": "Lenta"}
# Nombre legible de cada parámetro que se mueve en el análisis de sensibilidad.
NOMBRE_PARAMETRO = {
    "k (eliminación)": "Velocidad de eliminación (k)",
    "V (volumen)": "Volumen de distribución (V)",
    "ka (absorción)": "Velocidad de absorción (kₐ)",
    "umbral de efecto": "Cafeína mínima para notar el efecto",
    "umbral de sueño": "Cafeína máxima para dormir bien",
    "hora de dormir": "Hora de acostarse",
}
# Explicación corta de cada escenario, en el mismo orden que esc.escenarios_definidos().
EXPLICACION_ESCENARIO = (
    "Un día cualquiera: no queda cafeína de días anteriores.",
    "El mismo plan varios días seguidos: un poco de cafeína de cada día se acumula.",
    "Te acostás una hora antes, así que hay menos tiempo para eliminarla.",
)


# ---------------------------------------------------------------------------
# Cálculos (con caché)
# ---------------------------------------------------------------------------
# Streamlit vuelve a ejecutar todo el archivo con cada clic. La caché guarda los
# resultados ya calculados para no repetir cuentas pesadas si las entradas no cambian.
# El argumento ``_a`` empieza con guion bajo para que Streamlit no intente "hashearlo";
# en su lugar, ``clave`` (nombre del Excel o "base") identifica qué datos se usaron.


@st.cache_resource(show_spinner="Leyendo la base y ajustando el modelo…")
def cargar(contenido: bytes | None) -> AnalisisCafeina:
    """Análisis completo desde la base incluida o desde un Excel cargado.

    Recibe los bytes del Excel subido (o None para usar la base del proyecto) y devuelve
    un ``AnalisisCafeina``. Se guarda con ``cache_resource``: el objeto se lee y ajusta
    una sola vez por archivo y se comparte entre todas las recargas.
    """
    if contenido is None:
        return AnalisisCafeina.desde_excel()
    return AnalisisCafeina.desde_excel(io.BytesIO(contenido))


@st.cache_data(show_spinner="Calculando planes…")
def evaluar(_a: AnalisisCafeina, clave: str, param: Parametros, cobertura: float) -> dict:
    """Escenarios, recomendación, guía, sensibilidad y planes a la medida.

    Devuelve un diccionario con todas las tablas que usan las páginas. Se guarda con
    ``cache_data`` según la base (``clave``), los ajustes (``param``) y la cobertura:
    solo se recalcula cuando el usuario mueve un control de la barra lateral.
    """
    # 1) Evaluar los seis planes en cada escenario y elegir el mejor (normal y prudente)
    lista = esc.escenarios_definidos(param)
    evaluacion = esc.evaluar_escenarios(lista, _a.planes, _a.modelos, _a.relacion, _a.individuos)
    rec = esc.recomendar(evaluacion)
    prudente = esc.recomendar(evaluacion, cobertura)
    base = rec[rec["escenario"] == lista[0].nombre]
    base_prudente = prudente[prudente["escenario"] == lista[0].nombre]
    # 2) Armar las tablas derivadas: guía, sensibilidad, horas límite y planes a la medida
    return {
        "escenarios": [e.nombre for e in lista],
        "evaluacion": evaluacion,
        "recomendaciones": rec,
        "guia": esc.guia_consumo(base, _a.planes, _a.modelos, param),
        "guia_prudente": esc.guia_consumo(base_prudente, _a.planes, _a.modelos, param),
        "sensibilidad": esc.sensibilidad(_a.planes, _a.modelos, param),
        "limites": esc.tabla_horas_limite(_a.modelos, _a.hojas["Bebidas"], param),
        "a_la_medida": esc.planes_optimizados(
            _a.modelos, _a.individuos, _a.hojas["Bebidas"], param, cobertura
        ),
    }


@st.cache_data(show_spinner="Verificando el modelo…")
def verificar(_a: AnalisisCafeina, clave: str) -> dict:
    """Validación D/(Vk), contraste con los acumulados y comparación de factores.

    Solo depende de la base (``clave``), no de los ajustes, así que se calcula una vez
    por base y se reutiliza aunque el usuario cambie los controles.
    """
    p = _a.param
    return {
        "validacion": mod.validar_auc_modelo(_a.resultados, p.ka, p.dosis_mg),
        "verificacion": mod.verificar_contra_datos(_a.conc_limpio, _a.resultados, p.ka, p.dosis_mg),
        "factores": esc.comparar_factores(_a.clasificados),
    }


# ---------------------------------------------------------------------------
# Utilidades de presentación
# ---------------------------------------------------------------------------
# Funciones pequeñas para dar formato: horas de reloj, números con coma, figuras,
# descargas en CSV y listas de bebidas.


def reloj(h: float) -> str:
    """Hora decimal a hora de reloj: 14.5 -> '14:30', 25 -> '01:00'."""
    return esc.hora_texto(h if np.isnan(h) else h % 24)


def num(x: float, d: int = 1) -> str:
    """Número con coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


def mostrar(fig: plt.Figure, alt: str) -> None:
    """Muestra una figura de matplotlib con texto alternativo y libera su memoria.

    Las figuras de un panel se limitan a un ancho cómodo de lectura; las de
    varios paneles ocupan todo el ancho.
    """
    ancho = "stretch" if len(fig.axes) > 2 or fig.get_figwidth() > 10 else 860
    st.pyplot(fig, alt=alt, width=ancho)
    plt.close(fig)


def csv(df: pd.DataFrame) -> bytes:
    """DataFrame a CSV con ';' y coma decimal: Excel en español lo abre en casillas."""
    return exportar.tabla_csv(df)


def excel(tablas: dict[str, pd.DataFrame]) -> bytes:
    """Varias tablas en un libro .xlsx, una hoja por tabla, con encabezado destacado."""
    return exportar.libro_excel(tablas)


def lista_tomas(descripcion: str, cafeina: pd.Series) -> str:
    """'08:00 Café chorreado + 14:00 Té negro' -> lista Markdown con los mg."""
    lineas = []
    for toma in descripcion.split(" + "):
        hora, bebida = toma.split(" ", 1)
        lineas.append(f"- **{hora}** · {bebida} ({cafeina[bebida]:.0f} mg)")
    return "\n".join(lineas)


def fila_de(tabla: pd.DataFrame, grupo: str) -> pd.Series | None:
    """Fila del grupo en una tabla con columna ``grupo`` (None si no hay plan)."""
    sub = tabla[tabla["grupo"] == grupo]
    return sub.iloc[0] if len(sub) else None


def pistas_tipo(c: pd.DataFrame) -> str:
    """Cómo adivinar el tipo de eliminación con los datos del estudio.

    Recibe la tabla de voluntarios clasificados y devuelve pistas en Markdown según
    si la persona fuma o usa anticonceptivo hormonal.
    """
    lineas = []
    for col, texto in [
        ("fuma", "fumás"),
        ("anticonceptivo_hormonal", "usás anticonceptivo hormonal"),
    ]:
        grupos = c.loc[c[col] == "Sí", "grupo"].value_counts()
        if grupos.sum():
            g = grupos.idxmax()
            lineas.append(
                f"- **Si {texto}:** {grupos.max()} de cada {grupos.sum()} personas así en el "
                f"estudio eliminan de forma **{g}**."
            )
    lineas.append(
        "- **Si no es ninguno de los dos:** podés ser de cualquier tipo. Para ir a lo seguro, "
        "elegí **lenta**."
    )
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Barra lateral: perfil, ajustes y base de datos
# ---------------------------------------------------------------------------
# Aquí el usuario elige su tipo de eliminación, su hora de dormir, los umbrales y,
# si quiere, otra base de Excel. Todo lo que elija se usa en todas las páginas.

# 1) Reservar tres zonas en la barra lateral. Se llenan en otro orden (primero los datos,
#    porque el perfil necesita la base cargada), pero se ven en este orden.
zona_perfil = st.sidebar.container()
zona_ajustes = st.sidebar.container()
zona_datos = st.sidebar.container()

# 2) Carga de datos: Excel subido por el usuario o la base del proyecto
with zona_datos:
    st.subheader("Datos", icon=":material/database:")
    archivo = st.file_uploader(
        "Usar otra base de Excel",
        type=["xlsx"],
        help="Debe tener las mismas hojas y columnas que P02_C-09_VILLALOBOS.xlsx.",
    )
try:
    analisis = cargar(archivo.getvalue() if archivo else None)
except ValueError as error:
    st.error(f"La base cargada no tiene la estructura esperada: {error}", icon=":material/error:")
    st.stop()
zona_datos.caption(
    f"Usando **{archivo.name}**." if archivo else "Usando la base del proyecto (60 voluntarios)."
)
p0 = analisis.param
clave = archivo.name if archivo else "base"

# 3) Perfil: tipo de eliminación y hora de acostarse (de 21:00 a 01:00, cada media hora)
with zona_perfil:
    st.subheader("Tu perfil", icon=":material/person:")
    tipo = st.segmented_control(
        "¿Qué tan rápido eliminás la cafeína?",
        GRUPOS,
        default="normal",
        key="tipo",
        required=True,
        format_func=NOMBRE_TIPO.get,
        help="Depende de cada cuerpo. Las personas de eliminación lenta conservan la cafeína "
        "más horas en la sangre.",
    )
    with st.popover("¿Cómo sé cuál soy?", icon=":material/help:", width="stretch"):
        st.markdown(pistas_tipo(analisis.clasificados))
    horas_dormir = [h / 2 for h in range(42, 51)]
    hora_dormir = st.select_slider(
        "¿A qué hora te acostás?",
        options=horas_dormir,
        value=p0.hora_dormir if p0.hora_dormir in horas_dormir else horas_dormir[4],
        format_func=reloj,
    )

# 4) Ajustes avanzados: umbrales, máximo diario y cobertura (parten de los valores de la base)
with zona_ajustes:
    with st.expander("Ajustes avanzados", icon=":material/tune:"):
        c_efecto = st.slider(
            "Cafeína mínima para notar el efecto (mg/L)",
            0.5,
            3.0,
            p0.c_efecto,
            0.1,
            help="Umbral de efecto. Por encima de esta concentración en la sangre la atención "
            "mejora. Valor de la base: " + num(p0.c_efecto) + " mg/L.",
        )
        c_sueno = st.slider(
            "Cafeína máxima al acostarse (mg/L)",
            0.3,
            2.0,
            p0.c_sueno,
            0.05,
            help="Umbral de sueño. Con más cafeína que esto al acostarse, el sueño empeora. "
            "Valor de la base: " + num(p0.c_sueno) + " mg/L.",
        )
        max_diario = st.slider(
            "Máximo de cafeína por día (mg)",
            100,
            600,
            int(p0.max_diario_mg),
            10,
            help="Límite diario de la base (" + f"{p0.max_diario_mg:.0f}" + " mg).",
        )
        cobertura = st.slider(
            "Opción segura: % del grupo que debe dormir bien",
            50,
            100,
            int(COBERTURA_PRUDENTE),
            5,
            help="El plan recomendado se calcula para la persona típica de cada grupo. La opción "
            "segura exige además que este porcentaje de las personas del grupo duerma bien.",
        )

# 5) Juntar los ajustes en un nuevo Parametros y calcular (o leer de la caché) los resultados.
#    Las variables globales de abajo las comparten todas las páginas.
param = p0.con_cambios(
    c_efecto=c_efecto, c_sueno=c_sueno, hora_dormir=hora_dormir, max_diario_mg=float(max_diario)
)
res = evaluar(analisis, clave, param, float(cobertura))
bebidas = analisis.hojas["Bebidas"]
cafeina = bebidas.set_index("bebida")["cafeina_mg"]
cortes = analisis.clasificados.groupby("grupo", observed=True)["vida_media_h"].agg(["min", "max"])
jornada = f"{reloj(param.inicio)} y las {reloj(param.fin)}"


# ---------------------------------------------------------------------------
# Página: Inicio
# ---------------------------------------------------------------------------
# Resumen de la idea (sube, ayuda, deja dormir) y una tarjeta con el plan
# recomendado para cada tipo de eliminación.


def tarjeta_tipo(g: str) -> None:
    """Tarjeta con el plan recomendado para un tipo de eliminación.

    Recibe el grupo (``"rápida"``, ``"normal"`` o ``"lenta"``) y dibuja el plan, sus horas
    de efecto, la hora límite y si también es la opción segura.
    """
    # 1) Encabezado: nombre del tipo, marca "Tu tipo" y rango de vida media del grupo
    with st.container(border=True, height="stretch"):
        st.subheader(f"Eliminación {g}")
        if g == tipo:
            st.badge("Tu tipo", icon=":material/person:", color="green")
        if g in cortes.index:
            st.caption(
                f"La mitad de la cafeína se va en {num(cortes.loc[g, 'min'])} a "
                f"{num(cortes.loc[g, 'max'])} horas."
            )
        # 2) Plan recomendado para la persona típica del grupo
        fila = fila_de(res["guia"], g)
        if fila is None:
            st.markdown("Ningún plan del catálogo deja dormir bien con estos ajustes.")
            return
        st.markdown(f"**Plan {fila['plan']}**\n\n" + lista_tomas(fila["descripcion"], cafeina))
        st.markdown(
            f":material/schedule: **{num(fila['horas_efecto'])} h** con concentración  \n"
            f":material/bedtime: Última bebida **antes de las "
            f"{reloj(fila['hora_limite_ultima_toma'])}**  \n"
            f":material/local_cafe: Tope con estos horarios: **{fila['maximo_diario_mg']:.0f} mg**"
        )
        # 3) Comparar con la opción segura (la que cubre el % elegido de personas del grupo)
        segura = fila_de(res["guia_prudente"], g)
        pct = fila["pct_personas_duermen_bien"]
        if segura is None:
            st.caption(
                f"Duerme bien el {pct:.0f} % del grupo. Ningún plan del catálogo llega al "
                f"{cobertura} %."
            )
        elif segura["plan"] == fila["plan"]:
            st.caption(f"Duerme bien el {pct:.0f} % del grupo: es también la opción segura.")
        else:
            st.caption(
                f"Duerme bien el {pct:.0f} % del grupo. Para ir a lo seguro (≥ {cobertura} %): "
                f"**plan {segura['plan']}**, {num(segura['horas_efecto'])} h."
            )


def pagina_inicio() -> None:
    """Dibuja la página de inicio: idea general, tarjetas por tipo y enlaces."""
    # 1) Título y tres cajas con la idea del modelo y los dos umbrales
    st.title("¿Cuánta cafeína y hasta qué hora?")
    st.markdown(
        "Guía de la **Coordinación de Vida Estudiantil (UCR, Sede del Sur)** para la semana de "
        f"exámenes: más horas de concentración entre las {jornada} **sin perder el sueño**."
    )
    pasos = st.columns(3)
    textos = [
        (
            ":material/trending_up: La cafeína sube y luego baja",
            "Llega a la sangre en cerca de una hora y después el cuerpo la va eliminando "
            "poco a poco.",
        ),
        (
            f":material/bolt: Ayuda desde {num(param.c_efecto)} mg/L",
            "Con al menos esa cantidad en la sangre la atención mejora: reaccionás unos "
            f"{analisis.relacion.pendiente:.0f} ms más rápido por cada mg/L.",
        ),
        (
            f":material/bedtime: Para dormir, menos de {num(param.c_sueno)} mg/L",
            f"Es lo máximo que debería quedar a la hora de acostarte ({reloj(param.hora_dormir)}).",
        ),
    ]
    for col, (titulo, texto) in zip(pasos, textos, strict=True):
        with col.container(border=True, height="stretch"):
            st.markdown(f"**{titulo}**")
            st.markdown(texto)

    # 2) Una tarjeta de recomendación por cada tipo de eliminación
    st.header("Recomendación por tipo de persona", icon=":material/verified:")
    st.caption(
        "El plan con más horas de concentración que deja dormir bien a la persona típica de cada "
        "grupo y no pasa el máximo diario. Elegí tu tipo en la barra lateral."
    )
    for col, g in zip(st.columns(3), GRUPOS, strict=True):
        with col:
            tarjeta_tipo(g)

    # 3) Enlaces rápidos a las otras páginas
    with st.container(horizontal=True):
        st.page_link(PAGINAS["simulador"], label="Probá tu propio día")
        st.page_link(PAGINAS["planes"], label="Comparar los seis planes")
        st.page_link(PAGINAS["glosario"], label="¿Qué significa cada término?")


# ---------------------------------------------------------------------------
# Página: Simulá tu día
# ---------------------------------------------------------------------------
# El usuario elige hasta cuatro bebidas y sus horas; se calcula la curva de cafeína
# (superposición), las horas con efecto y lo que queda al acostarse.


def cargar_recomendado() -> None:
    """Copia el plan recomendado del tipo elegido a los controles del simulador."""
    fila = fila_de(res["guia"], tipo)
    if fila is None:
        return
    plan = analisis.planes[fila["plan"]]
    st.session_state["n_bebidas"] = len(plan.horas)
    for i, (h, b) in enumerate(zip(plan.horas, plan.bebidas, strict=True)):
        st.session_state[f"bebida_{i}"] = b
        st.session_state[f"hora_{i}"] = h


def pagina_simulador() -> None:
    """Dibuja el simulador: controles de bebidas, veredicto, métricas y gráfico del día."""
    # 1) Título y valores iniciales de los controles (solo la primera vez)
    st.title("Simulá tu día")
    st.markdown(
        f"Elegí qué vas a tomar y a qué hora. Calculamos para eliminación **{tipo}** "
        f"(cambiala en la barra lateral) y acostarte a las **{reloj(param.hora_dormir)}**."
    )
    entrada, salida = st.columns([1, 1.6], gap="large")
    horas = [h / 2 for h in range(12, 45)]
    st.session_state.setdefault("n_bebidas", 2)
    for i in range(4):
        st.session_state.setdefault(f"bebida_{i}", cafeina.index[min(1, len(cafeina) - 1)])
        st.session_state.setdefault(f"hora_{i}", 8.0 + 4 * i)
    # 2) Columna izquierda: elegir bebidas, horas (06:00 a 22:00) y días seguidos
    with entrada, st.container(border=True):
        st.subheader("Tus bebidas", icon=":material/local_cafe:")
        st.button(
            "Usar el plan recomendado",
            icon=":material/auto_awesome:",
            on_click=cargar_recomendado,
            width="stretch",
        )
        n = st.segmented_control("¿Cuántas bebidas?", [1, 2, 3, 4], required=True, key="n_bebidas")
        tomas = []
        for i in range(n):
            c1, c2 = st.columns([1.4, 1], vertical_alignment="bottom")
            bebida = c1.selectbox(
                f"Bebida {i + 1}",
                list(cafeina.index),
                format_func=lambda b: f"{b} · {cafeina[b]:.0f} mg",
                key=f"bebida_{i}",
            )
            hora = c2.select_slider("Hora", horas, format_func=reloj, key=f"hora_{i}")
            tomas.append((hora, bebida))
        dias = st.slider(
            "¿Cuántos días seguidos con este plan?",
            1,
            7,
            1,
            key="dias",
            help="La cafeína que queda de los días anteriores se suma (se acumula).",
        )
    # 3) Armar el plan ordenado por hora y evaluarlo con el modelo del tipo elegido.
    #    dias - 1 = días anteriores cuya cafeína sobrante se acumula.
    tomas.sort()
    plan = esc.PlanConsumo(
        "propio",
        tuple(h for h, _ in tomas),
        tuple(float(cafeina[b]) for _, b in tomas),
        tuple(b for _, b in tomas),
    )
    modelo = analisis.modelos[tipo]
    ind = esc.evaluar_plan(plan, modelo, param, analisis.relacion, dias - 1)
    duerme = ind["c_dormir"] < param.c_sueno
    dentro = plan.total_mg <= param.max_diario_mg

    # 4) Hora límite de la última bebida, contando lo que dejan las anteriores
    previo = (
        esc.PlanConsumo("previo", plan.horas[:-1], plan.dosis_mg[:-1]) if len(tomas) > 1 else None
    )
    limite = esc.hora_limite(modelo, plan.dosis_mg[-1], param, previo, dias - 1)

    # 5) Columna derecha: veredicto (éxito o advertencia con los motivos)
    with salida:
        if duerme and dentro:
            st.success(
                f"Tenés **{num(ind['horas_efecto'])} h** de concentración y a las "
                f"{reloj(param.hora_dormir)} te quedan {num(ind['c_dormir'], 2)} mg/L.",
                title="Buen plan: concentración sin perder el sueño",
                icon=":material/check_circle:",
            )
        else:
            motivos = []
            if not duerme:
                motivos.append(
                    f"al acostarte te quedan {num(ind['c_dormir'], 2)} mg/L (más de "
                    f"{num(param.c_sueno)} mg/L)"
                )
            if not dentro:
                motivos.append(
                    f"tomás {plan.total_mg:.0f} mg (más de {param.max_diario_mg:.0f} mg)"
                )
            st.warning(
                "Ojo: " + " y ".join(motivos) + ". Probá con menos cafeína o tomala más temprano.",
                title="Este plan puede afectar tu sueño",
                icon=":material/warning:",
            )
        # 6) Cuatro métricas: horas con efecto, cafeína al dormir, total del día y reacción
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        m1.metric(
            "Horas con concentración",
            f"{num(ind['horas_efecto'])} h",
            delta=f"de {param.fin - param.inicio:.0f} h de estudio",
            delta_color="off",
            delta_arrow="off",
            border=True,
            help="Horas entre el inicio y el fin de la jornada con la cafeína sobre el umbral de "
            "efecto (área sombreada del gráfico).",
        )
        m2.metric(
            "Cafeína al acostarte",
            f"{num(ind['c_dormir'], 2)} mg/L",
            delta=("✓ " if duerme else "✗ ") + f"límite {num(param.c_sueno)} mg/L",
            delta_color="off",
            delta_arrow="off",
            border=True,
            help="Concentración en la sangre a la hora de acostarte.",
        )
        m3.metric(
            "Cafeína en el día",
            f"{plan.total_mg:.0f} mg",
            delta=("✓ " if dentro else "✗ ") + f"máximo {param.max_diario_mg:.0f} mg",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )
        m4.metric(
            "Reacción más rápida",
            f"{ind['mejora_rt_ms']:.0f} ms",
            delta="en promedio durante la jornada",
            delta_color="off",
            delta_arrow="off",
            border=True,
            help="Mejora del tiempo de reacción estimada con las 480 pruebas de atención.",
        )
        if np.isnan(limite):
            st.caption(
                f":material/schedule: Con tus otras bebidas, la última ({plan.bebidas[-1]}) ya no "
                "cabe sin pasar el límite de sueño."
            )
        else:
            st.caption(
                f":material/schedule: Con tus otras bebidas, la última ({plan.bebidas[-1]}) "
                f"debería ser **antes de las {reloj(limite)}**."
            )
    # 7) Gráfico de la curva del día y guía para leerlo
    mostrar(
        gr.fig_plan(plan, modelo, param, dias - 1, titulo="Tu cafeína en la sangre durante el día"),
        alt="Curva de la concentración de cafeína en la sangre durante el día con el plan elegido.",
    )
    with st.expander("Cómo leer el gráfico", icon=":material/help:", expanded=True):
        st.markdown(
            "- La **curva verde** es la cafeína en tu sangre hora por hora; cada bebida la hace "
            "subir y luego baja sola.\n"
            "- La **zona sombreada** son las horas de estudio en que la cafeína supera la línea "
            "discontinua (umbral de efecto): ahí te ayuda a concentrarte.\n"
            "- El **punto negro** es lo que te queda al acostarte; para dormir bien debe quedar "
            "bajo la línea punteada (umbral de sueño)."
        )


# ---------------------------------------------------------------------------
# Página: Comparar planes
# ---------------------------------------------------------------------------
# Tabla con los seis planes de la campaña, hora límite de cada bebida, gráficos
# de los tres tipos, plan a la medida y descargas.


def pagina_planes() -> None:
    """Dibuja la comparación de planes para el tipo elegido en la barra lateral."""
    # 1) Filtrar la evaluación al escenario base y al tipo del usuario; mostrar el recomendado
    st.title("Comparar los seis planes")
    st.markdown(
        f"Los planes de la campaña evaluados para eliminación **{tipo}** y acostarte a las "
        f"**{reloj(param.hora_dormir)}**."
    )
    ev = res["evaluacion"]
    base = ev[ev["escenario"] == res["escenarios"][0]]
    sub = base[base["grupo"] == tipo]
    rec = fila_de(res["guia"], tipo)
    segura = fila_de(res["guia_prudente"], tipo)
    if rec is not None:
        st.success(
            f"{rec['descripcion'].replace(' + ', ' y ')}: {num(rec['horas_efecto'])} h de "
            f"concentración y {num(rec['c_dormir'], 2)} mg/L al acostarte.",
            title=f"Recomendado para vos: plan {rec['plan']}",
            icon=":material/verified:",
        )
    else:
        st.warning("Ningún plan del catálogo cumple con estos ajustes.", icon=":material/warning:")

    # 2) Tabla de los seis planes con una etiqueta de resultado para cada uno
    def veredicto(f: pd.Series) -> str:
        """Etiqueta de un plan: recomendado, opción segura, cumple o por qué no cumple."""
        if rec is not None and f["plan"] == rec["plan"]:
            return "★ Recomendado"
        if segura is not None and f["plan"] == segura["plan"]:
            return "✓ Opción segura"
        if not f["cumple_sueno"]:
            return "✗ Afecta el sueño"
        if not f["cumple_maximo"]:
            return "✗ Pasa el máximo"
        return "✓ Cumple"

    vista = pd.DataFrame(
        {
            "Plan": sub["plan"],
            "Qué tomar": sub["descripcion"].str.replace(" + ", " · ", regex=False),
            "Resultado": sub.apply(veredicto, axis=1),
            "Horas con concentración": sub["horas_efecto"],
            "Cafeína al acostarte (mg/L)": sub["c_dormir"],
            "Cafeína en el día (mg)": sub["cafeina_mg"],
            "Personas del grupo que duermen bien": sub["pct_personas_duermen_bien"],
        }
    )
    st.dataframe(
        vista,
        hide_index=True,
        alt=f"Comparación de los seis planes para eliminación {tipo}.",
        column_config={
            "Horas con concentración": st.column_config.ProgressColumn(
                format="%.1f h",
                min_value=0,
                max_value=param.fin - param.inicio,
                color="green",
                help="Integral de la función indicadora: horas con la cafeína sobre el umbral.",
            ),
            "Cafeína al acostarte (mg/L)": st.column_config.NumberColumn(
                format="%.2f", help=f"Debe ser menor que {num(param.c_sueno)} mg/L."
            ),
            "Cafeína en el día (mg)": st.column_config.NumberColumn(format="%d"),
            "Personas del grupo que duermen bien": st.column_config.ProgressColumn(
                format="%.0f %%", min_value=0, max_value=100, color="green"
            ),
        },
    )
    st.caption(
        "★ Recomendado: más horas de concentración cumpliendo sueño y máximo para la persona "
        "típica del grupo. ✓ Opción segura: además duerme bien al menos el "
        f"{cobertura} % del grupo."
    )

    # 3) Hora límite de cada bebida si fuera la única del día. ``tope`` (acostarse menos el
    #    tiempo hasta el pico) es la hora más tardía que se revisa; si el límite llega ahí,
    #    la bebida se puede tomar a cualquier hora de la jornada.
    st.header("¿Hasta qué hora puedo tomar cada bebida?", icon=":material/schedule:")
    st.caption(
        f"Si es la única bebida del día, para quedar bajo {num(param.c_sueno)} mg/L a las "
        f"{reloj(param.hora_dormir)}."
    )
    lim = res["limites"]
    tope = param.hora_dormir - analisis.modelos[tipo].tiempo_maximo()

    def texto_limite(h: float) -> str:
        """Hora límite como texto: 'mejor no tomarla', 'a cualquier hora' o 'antes de las …'."""
        if np.isnan(h):
            return "mejor no tomarla"
        if h >= tope - 1e-6:
            return "a cualquier hora"
        return "antes de las " + reloj(h)

    st.dataframe(
        pd.DataFrame(
            {
                "Bebida": lim["bebida"],
                "Cafeína (mg)": lim["cafeina_mg"],
                "Hora límite": [texto_limite(h) for h in lim[tipo]],
            }
        ),
        hide_index=True,
        width="content",
        alt=f"Hora límite de cada bebida para eliminación {tipo}.",
    )

    # 4) Gráficos opcionales con los tres tipos de eliminación
    with st.expander("Ver los tres tipos a la vez", icon=":material/grid_view:"):
        mostrar(
            gr.fig_mapa_planes(base),
            alt="Mapa de horas con concentración de cada plan para los tres tipos.",
        )
        mostrar(
            gr.fig_planes_recomendados(res["guia"], analisis.planes, analisis.modelos, param),
            alt="Curva del plan recomendado para cada tipo de eliminación.",
        )
        mostrar(
            gr.fig_horas_limite(res["limites"], param),
            alt="Hora límite de cada bebida para los tres tipos.",
        )
    # 5) Plan a la medida: la mejor combinación encontrada fuera de los seis planes
    with st.expander("Plan a la medida (fuera del catálogo)", icon=":material/science:"):
        st.markdown(
            "Probamos todas las combinaciones de 1 a 3 bebidas de la base a horas enteras y "
            f"elegimos la de más horas de concentración que deja dormir bien al menos al "
            f"{cobertura} % del grupo. Es exploratorio: muestra el patrón «más cafeína temprano, "
            "poca después»."
        )
        medida = fila_de(res["a_la_medida"], tipo)
        if medida is None:
            st.markdown("No hay combinación que cumpla con estos ajustes.")
        else:
            st.markdown(lista_tomas(medida["descripcion"], cafeina))
            st.markdown(
                f"**{num(medida['horas_efecto'])} h** de concentración · "
                f"{num(medida['c_dormir'], 2)} mg/L al acostarse · "
                f"{medida['cafeina_mg']:.0f} mg · duerme bien el "
                f"{medida['pct_personas_duermen_bien']:.0f} % del grupo"
            )

    # 6) Botones para descargar las tablas: las tres en un Excel o cada una en CSV
    with st.container(horizontal=True):
        st.download_button(
            "Las tres tablas (Excel)",
            excel(
                {
                    "evaluacion_planes": ev,
                    "guia_consumo": res["guia"],
                    "horas_limite": res["limites"],
                }
            ),
            "planes_cafeina.xlsx",
            type="primary",
            icon=":material/table_view:",
        )
        st.download_button(
            "Evaluación de planes (CSV)",
            csv(ev),
            "evaluacion_planes.csv",
            icon=":material/download:",
        )
        st.download_button(
            "Guía de consumo (CSV)",
            csv(res["guia"]),
            "guia_consumo.csv",
            icon=":material/download:",
        )
        st.download_button(
            "Horas límite (CSV)",
            csv(res["limites"]),
            "horas_limite.csv",
            icon=":material/download:",
        )


# ---------------------------------------------------------------------------
# Página: Escenarios
# ---------------------------------------------------------------------------
# El plan recomendado en tres escenarios (base, varios días seguidos, dormir antes)
# y el análisis de sensibilidad: qué dato del modelo cambia más la decisión.


def pagina_escenarios() -> None:
    """Dibuja los tres escenarios y la tabla de sensibilidad para el tipo elegido."""
    # 1) Una caja por escenario con su plan recomendado, y el gráfico comparativo
    st.title("¿Y si cambian las condiciones?")
    st.markdown(
        f"El plan recomendado para eliminación **{tipo}** en el escenario base y en dos "
        "alternativos."
    )
    rec = res["recomendaciones"]
    for col, nombre, texto in zip(
        st.columns(3), res["escenarios"], EXPLICACION_ESCENARIO, strict=True
    ):
        with col.container(border=True, height="stretch"):
            st.subheader(nombre)
            st.caption(texto)
            fila = fila_de(rec[rec["escenario"] == nombre], tipo)
            if fila is None:
                st.markdown("Ningún plan cumple.")
                continue
            st.markdown(f"**Plan {fila['plan']}**\n\n" + lista_tomas(fila["descripcion"], cafeina))
            st.markdown(
                f":material/schedule: **{num(fila['horas_efecto'])} h** con concentración  \n"
                f":material/bedtime: {num(fila['c_dormir'], 2)} mg/L al acostarse"
            )
    mostrar(
        gr.fig_escenarios(res["evaluacion"], rec),
        alt="Horas con concentración del plan recomendado en cada escenario y tipo.",
    )

    # 2) Sensibilidad: contar cuántas veces cambia el plan al mover cada parámetro ±20 %
    st.header("¿Qué dato cambia más la decisión?", icon=":material/tune:")
    st.markdown(
        "Movimos cada dato del modelo un 20 % hacia arriba y hacia abajo (la hora de acostarse, "
        "una hora) y volvimos a buscar el mejor plan."
    )
    sens = res["sensibilidad"]
    conteo = (
        sens.groupby("parametro", sort=False)["cambia_decision"].sum().sort_values(ascending=False)
    )
    importantes = [
        NOMBRE_PARAMETRO.get(p, p)[0].lower() + NOMBRE_PARAMETRO.get(p, p)[1:]
        for p, v in conteo.items()
        if v > 0
    ]
    if importantes:
        st.info(
            "Lo que más mueve la recomendación: " + ", ".join(importantes) + ".",
            icon=":material/lightbulb:",
        )
    # 3) Tabla de sensibilidad del tipo elegido, gráfico de los tres tipos y descargas
    propio = sens[sens["grupo"] == tipo]
    st.dataframe(
        pd.DataFrame(
            {
                "Qué cambia": propio["parametro"].map(NOMBRE_PARAMETRO).fillna(propio["parametro"]),
                "Cuánto": propio["cambio"],
                "Plan recomendado": propio["plan"],
                "Horas con concentración": propio["horas_efecto"],
                "¿Cambia la decisión?": np.where(propio["cambia_decision"], "Sí", "No"),
            }
        ),
        hide_index=True,
        alt=f"Sensibilidad de la recomendación para eliminación {tipo}.",
        column_config={
            "Horas con concentración": st.column_config.NumberColumn(format="%.1f h"),
        },
    )
    with st.expander("Gráfico de sensibilidad (los tres tipos)", icon=":material/bar_chart:"):
        mostrar(
            gr.fig_sensibilidad(sens, res["guia"]),
            alt="Cambio en las horas con concentración al variar cada parámetro.",
        )
    with st.container(horizontal=True):
        st.download_button(
            "Escenarios y sensibilidad (Excel)",
            excel({"escenarios": rec, "sensibilidad": sens}),
            "escenarios_cafeina.xlsx",
            type="primary",
            icon=":material/table_view:",
        )
        st.download_button(
            "Escenarios (CSV)", csv(rec), "escenarios.csv", icon=":material/download:"
        )
        st.download_button(
            "Sensibilidad (CSV)", csv(sens), "sensibilidad.csv", icon=":material/download:"
        )


# ---------------------------------------------------------------------------
# Página: Datos y método
# ---------------------------------------------------------------------------
# Explica el trabajo matemático en cinco secciones: limpieza de datos, modelo
# (AUC, integral impropia, superposición), verificación, factores y atención.


def pagina_metodo() -> None:
    """Dibuja la página de método; un selector elige cuál de las cinco secciones mostrar."""
    # 1) Introducción y selector de sección
    st.title("Datos y método")
    st.markdown(
        "Cómo se llegó a la recomendación, paso a paso, con los datos de "
        f"{len(analisis.clasificados)} voluntarios que tomaron {p0.dosis_mg:.0f} mg de cafeína."
    )
    seccion = st.segmented_control(
        "Sección",
        [
            "Los datos",
            "El modelo",
            "Verificación",
            "Quién elimina más rápido",
            "Cafeína y atención",
        ],
        default="Los datos",
        key="seccion",
        required=True,
        label_visibility="collapsed",
    )
    # 2) Los datos: conteos, perfiles de cada voluntario y bitácora de correcciones
    if seccion == "Los datos":
        bit = analisis.bitacora
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Voluntarios", len(analisis.clasificados), border=True)
        c2.metric("Mediciones de cafeína", len(analisis.conc_limpio), border=True)
        c3.metric("Datos faltantes", int((bit["estado"] == "faltante").sum()), border=True)
        c4.metric("Datos atípicos", int((bit["estado"] == "atípico").sum()), border=True)
        mostrar(
            gr.fig_perfiles(analisis.conc_limpio, analisis.clasificados),
            alt="Concentración de cafeína de cada voluntario durante 24 horas.",
        )
        st.markdown(
            "Cada línea es una persona. La cafeína sube hasta cerca de 1 h después de tomarla y "
            "luego baja. En la escala logarítmica (derecha) la bajada es una recta desde las 6 h: "
            "eso indica decrecimiento exponencial."
        )
        st.subheader("Qué se corrigió y por qué")
        st.dataframe(
            pd.DataFrame(
                {
                    "Voluntario": bit["voluntario"],
                    "Hora de la medición (h)": bit["tiempo_h"],
                    "Problema": bit["estado"].map(
                        {"faltante": "Dato faltante", "atípico": "Dato atípico"}
                    ),
                    "Valor original (mg/L)": bit["valor_original"],
                    "Valor usado (mg/L)": bit["valor_final"],
                    "Cómo se trató": bit["tratamiento"],
                }
            ),
            hide_index=True,
            alt="Bitácora de datos faltantes y atípicos y su tratamiento.",
            column_config={
                "Valor original (mg/L)": st.column_config.NumberColumn(format="%.2f"),
                "Valor usado (mg/L)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.caption(
            "Un dato es atípico si se aleja más de 1,8 veces de lo esperado según sus vecinos. "
            "Los valores corregidos no se usan para calcular la velocidad de eliminación."
        )
    # 3) El modelo: las cuatro fórmulas clave y un ejemplo con un voluntario
    elif seccion == "El modelo":
        st.markdown(
            "**1. Velocidad de eliminación.** Desde las 6 h, ln C baja en línea recta; su "
            "pendiente es −k y la vida media es el tiempo en que la cafeína baja a la mitad."
        )
        st.latex(r"\ln C = \ln C_0 - k\,t \qquad t_{1/2}=\frac{\ln 2}{k}")
        st.markdown(
            "**2. Área bajo la curva (AUC).** Mide la exposición total a la cafeína. Se suma el "
            "área medida hasta las 24 h (regla del trapecio) y la cola que falta hasta el "
            "infinito (integral impropia)."
        )
        st.latex(
            r"AUC=\int_0^{\infty}C\,dt\approx\underbrace{\int_0^{24}C\,dt}_{\text{trapecio}}"
            r"+\underbrace{\frac{C(24)}{k}}_{\text{cola}}=\frac{D}{V\,k}"
        )
        st.markdown(
            "**3. Curva de un día con varias bebidas.** Cada bebida aporta su propia curva y se "
            "suman (principio de superposición)."
        )
        st.latex(
            r"C(t)=\frac{D\,k_a}{V(k_a-k)}\left(e^{-kt}-e^{-k_a t}\right)\qquad "
            r"C_{plan}(t)=\sum_j C(t-t_j;\,D_j)"
        )
        st.markdown(
            "**4. Horas con concentración.** Es la integral de una función que vale 1 cuando la "
            "cafeína supera el umbral y 0 cuando no."
        )
        st.latex(r"H_{ef}=\int_{8}^{20}\mathbf{1}\left[C_{plan}(t)\geq c_{ef}\right]dt")
        st.subheader("Probalo con un voluntario")
        vol = st.selectbox("Voluntario", analisis.resultados.index)
        fila = analisis.clasificados.loc[vol]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tipo", str(fila["grupo"]).capitalize(), border=True)
        c2.metric("Vida media", f"{num(fila['vida_media_h'])} h", border=True)
        c3.metric("AUC total", f"{num(fila['auc_total'])} mg·h/L", border=True)
        c4.metric("Aporte de la cola", f"{num(fila['pct_cola'])} %", border=True)
        mostrar(
            gr.fig_voluntario_desde_tablas(
                analisis.conc_limpio, analisis.resultados, vol, p0.ka, p0.dosis_mg
            ),
            alt=f"Área bajo la curva del voluntario {vol}, con trapecios y cola sombreados.",
        )
        st.download_button(
            "Resultados por voluntario (CSV)",
            csv(analisis.clasificados.reset_index()),
            "resultados_voluntarios.csv",
            icon=":material/download:",
        )
    # 4) Verificación: la integral numérica coincide con D/(Vk) y con los datos medidos
    elif seccion == "Verificación":
        ver = verificar(analisis, clave)
        val, vd = ver["validacion"], ver["verificacion"]
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Validación D/(Vk)",
            f"{100 * val['error_rel'].max():.3f} %",
            delta="error máximo · tolerancia 0,5 %",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )
        c2.metric(
            "Contra los acumulados de la base",
            f"{100 * vd['error_rel_acumulado'].mean():.2f} %",
            delta="error medio de 0 a 24 h",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )
        c3.metric(
            "Ajuste del modelo",
            f"{100 * vd['r2'].median():.0f} %",
            delta="de cada perfil explicado (R² mediano)",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )
        mostrar(
            gr.fig_verificacion(val, vd),
            alt="Acumulado observado contra integral del modelo y error de la validación.",
        )
        st.markdown(
            "Integrando el modelo de cada voluntario hasta 200 h se recupera la fórmula exacta "
            "AUC = D/(Vk) con error menor que 0,5 %. Además, el área medida con los datos coincide "
            "con la integral exacta del modelo."
        )
    # 5) Factores: vida media según tabaquismo y anticonceptivo (prueba de permutaciones)
    elif seccion == "Quién elimina más rápido":
        fac = verificar(analisis, clave)["factores"]
        mostrar(
            gr.fig_vida_media(analisis.clasificados, fac),
            alt="Vida media según tabaquismo y anticonceptivo, y grupos por terciles.",
        )
        st.markdown(
            "Las personas se dividieron en tres grupos del mismo tamaño (terciles) según su vida "
            "media. Fumar acelera la eliminación; el anticonceptivo hormonal la hace más lenta."
        )
        st.dataframe(
            pd.DataFrame(
                {
                    "Factor": fac["factor"].map(
                        {"fuma": "Fuma", "anticonceptivo_hormonal": "Anticonceptivo hormonal"}
                    ),
                    "Respuesta": fac["categoria"],
                    "Personas": fac["n"],
                    "Vida media típica (h)": fac["mediana_t12_h"],
                    "Valor p": fac["p_valor"],
                }
            ),
            hide_index=True,
            width="content",
            alt="Vida media mediana según tabaquismo y anticonceptivo.",
            column_config={
                "Vida media típica (h)": st.column_config.NumberColumn(format="%.1f"),
                "Valor p": st.column_config.NumberColumn(
                    format="%.4f",
                    help="Probabilidad de ver una diferencia así por azar (prueba de "
                    "permutaciones). Menor que 0,05 = diferencia real.",
                ),
            },
        )
    # 6) Cafeína y atención: recta entre concentración y mejora del tiempo de reacción
    else:
        rel = analisis.relacion
        mostrar(
            gr.fig_atencion(analisis.atencion, rel, param.c_efecto),
            alt="Mejora del tiempo de reacción contra la concentración de cafeína.",
        )
        st.markdown(
            f"En las {len(analisis.atencion)} pruebas de tiempo de reacción, cada mg/L de cafeína "
            f"en la sangre hace reaccionar unos **{rel.pendiente:.0f} ms más rápido** "
            f"(la recta explica el {100 * rel.r2:.0f} % de la variación)."
        )


# ---------------------------------------------------------------------------
# Página: Glosario
# ---------------------------------------------------------------------------
# Tabla de términos; algunos muestran los valores actuales de los ajustes.


def pagina_glosario() -> None:
    """Dibuja la tabla del glosario con cada término y su explicación sencilla."""
    st.title("Glosario")
    st.markdown("Los términos de la aplicación, en palabras simples.")
    st.table(
        {
            "Concentración (mg/L)": "Cuánta cafeína hay en la sangre: miligramos por cada litro.",
            "Tipo de eliminación": "Qué tan rápido tu cuerpo saca la cafeína: rápida, normal o "
            "lenta. Se definió dividiendo a los voluntarios en tres grupos iguales (terciles).",
            "Vida media (t½)": "Horas que tarda la cafeína en bajar a la mitad.",
            "Umbral de efecto": f"Cafeína mínima en la sangre ({num(param.c_efecto)} mg/L) para "
            "notar mejor atención.",
            "Umbral de sueño": f"Cafeína máxima a la hora de acostarse ({num(param.c_sueno)} mg/L) "
            "para dormir bien.",
            "Horas con concentración (H_ef)": "Horas de la jornada de estudio con la cafeína "
            "sobre el umbral de efecto.",
            "Hora límite": "Última hora para tomar una bebida sin pasar el umbral de sueño.",
            "Máximo diario": f"Tope de cafeína por día ({p0.max_diario_mg:.0f} mg en la base).",
            "Área bajo la curva (AUC)": "Exposición total a la cafeína: el área bajo la curva de "
            "concentración, en mg·h/L.",
            "Integral impropia": "Integral hasta el infinito; aquí suma la cafeína que queda "
            "después de las 24 h medidas.",
            "Superposición": "Con varias bebidas, la curva total es la suma de la curva de cada "
            "una.",
            "Constante de eliminación (k)": "Qué fracción de la cafeína se elimina por hora (1/h).",
            "Constante de absorción (kₐ)": "Qué tan rápido pasa la cafeína del estómago a la "
            "sangre (1/h).",
            "Volumen de distribución (V)": "Litros en que se reparte la cafeína en el cuerpo.",
            "Depuración (CL)": "Litros de sangre que el cuerpo limpia de cafeína por hora.",
            "Persona típica del grupo": "Persona con los valores medianos de k y V de su grupo.",
            "Opción segura": f"Plan que deja dormir bien al menos al {cobertura} % de las personas "
            "del grupo, no solo a la persona típica.",
        },
        border="horizontal",
        alt="Glosario de términos de la aplicación.",
    )


# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------
# Registra las seis páginas en el menú superior, ejecuta la que eligió el usuario
# y agrega la nota final. PAGINAS también se usa en los enlaces de la página de inicio.

PAGINAS = {
    "inicio": st.Page(pagina_inicio, title="Inicio", icon=":material/home:", default=True),
    "simulador": st.Page(
        pagina_simulador, title="Simulá tu día", icon=":material/local_cafe:", url_path="simulador"
    ),
    "planes": st.Page(
        pagina_planes, title="Comparar planes", icon=":material/checklist:", url_path="planes"
    ),
    "escenarios": st.Page(
        pagina_escenarios,
        title="Escenarios",
        icon=":material/compare_arrows:",
        url_path="escenarios",
    ),
    "metodo": st.Page(
        pagina_metodo, title="Datos y método", icon=":material/query_stats:", url_path="metodo"
    ),
    "glosario": st.Page(
        pagina_glosario, title="Glosario", icon=":material/menu_book:", url_path="glosario"
    ),
}
st.navigation(list(PAGINAS.values()), position="top").run()
st.caption(
    "Proyecto académico MA-0321 (UCR) con datos simulados con fines didácticos; no constituye una "
    "recomendación médica."
)
