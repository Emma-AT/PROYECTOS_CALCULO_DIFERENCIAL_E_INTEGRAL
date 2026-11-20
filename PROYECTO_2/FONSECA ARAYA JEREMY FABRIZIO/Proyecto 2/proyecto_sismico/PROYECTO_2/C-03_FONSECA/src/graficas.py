"""Figuras con unidades, fuente y áreas de integración."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from src.limpieza import BaseDatos
from src.modelo import densidad_eventos, malla_dano, tasa

COLORES = ["#718096", "#087e8b", "#c05c25"]
FUENTE = "Fuente: Excel individual del docente. Datos simulados con fines didácticos."


def preparar(titulo: str, x: str, y: str) -> tuple[Figure, plt.Axes]:
    """Crea figura con título, ejes con unidades y fuente, sin transformar datos."""
    fig, ax = plt.subplots(figsize=(9, 4.2), layout="constrained")
    ax.set(title=titulo, xlabel=x, ylabel=y)
    ax.grid(alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    fig.supxlabel(FUENTE, fontsize=8, color="#555555")
    return fig, ax


def figura_movimiento(resultado: dict, variable: str) -> Figure:
    """Grafica aceleración, velocidad o desplazamiento, con y sin línea base."""
    opciones = {
        "aceleracion": (
            "aceleracion_corregida_cm_s2",
            "aceleracion_interpolada_cm_s2",
            "Aceleración (cm/s²)",
            "Aceleración del suelo",
        ),
        "velocidad": (
            "velocidad_cm_s",
            "velocidad_sin_corregir_cm_s",
            "Velocidad (cm/s)",
            "La primera integral obtiene la velocidad",
        ),
        "desplazamiento": (
            "desplazamiento_cm",
            "desplazamiento_sin_corregir_cm",
            "Desplazamiento (cm)",
            "El sesgo se acumula al integrar dos veces",
        ),
    }
    corregida, original, unidad, titulo = opciones[variable]
    s = resultado["series"]
    fig, ax = preparar(titulo, "Tiempo (s)", unidad)
    ax.plot(s.tiempo_s, s[original], label="Sin corrección", color=COLORES[2], alpha=0.7)
    ax.plot(s.tiempo_s, s[corregida], label="Con corrección", color=COLORES[1])
    if variable != "desplazamiento":
        ax.fill_between(
            s.tiempo_s,
            s[corregida],
            alpha=0.12,
            color=COLORES[1],
            label="Área con signo que se integra",
        )
    ax.legend(fontsize=9)
    return fig


def figura_arias(resultado: dict) -> Figure:
    """Grafica intensidad de Arias acumulada en m/s y su intervalo 5–95 %."""
    s, i = resultado["series"], resultado["indicadores"]
    fig, ax = preparar(
        "La duración significativa concentra el 90 % de Arias",
        "Tiempo (s)",
        "Arias acumulada (m/s)",
    )
    ax.plot(s.tiempo_s, s.arias_acumulada_m_s, color=COLORES[1])
    if i["duracion_s"] is not None:
        ax.axvspan(i["t5_s"], i["t95_s"], alpha=0.16, color=COLORES[1], label="De 5 % a 95 %")
        ax.legend()
    return fig


def figura_recurrencia(base: BaseDatos, resultado: dict) -> Figure:
    """Compara frecuencia anual empírica y modelo Gutenberg–Richter en escala log."""
    mag = base.hojas["Catalogo_sismos"].magnitud_Mw.to_numpy()
    puntos = np.unique(mag)
    emp = np.array([(mag >= m).sum() / base.anos_catalogo for m in puntos])
    x = np.linspace(base.m0, base.hojas["Vulnerabilidad"].magnitud_Mw.max(), 201)
    fig, ax = preparar(
        "Los eventos grandes son menos frecuentes en el modelo",
        "Magnitud (Mw)",
        "Eventos/año con M ≥ m",
    )
    ax.semilogy(
        x,
        tasa(x, resultado["lambda3"], resultado["b"]),
        color=COLORES[1],
        label="Gutenberg–Richter",
    )
    ax.scatter(puntos, emp, color=COLORES[2], s=20, label="Catálogo / años observados")
    ax.axvline(
        mag.max(),
        color=COLORES[0],
        linestyle=":",
        label="Máximo registrado; a la derecha se extrapola",
    )
    ax.legend(fontsize=8)
    return fig


def figura_pae(base: BaseDatos, resultado: dict) -> Figure:
    """Sombrea integrandos de PAE en millones de colones/(año·Mw)."""
    v = base.hojas["Vulnerabilidad"]
    valor = base.parametro("Valor de reposición del pabellón")
    fig, ax = preparar(
        "El área representa la pérdida anual esperada",
        "Magnitud (Mw)",
        "Millones de ₡ / (año · Mw)",
    )
    for color, col, nombre in zip(
        COLORES, v.columns[1:], ["Sin refuerzo", "Opción A", "Opción B"], strict=True
    ):
        x, d = malla_dano(v.magnitud_Mw, v[col] / 100)
        y = valor * d * densidad_eventos(x, resultado["lambda3"], resultado["b"]) / 1e6
        ax.plot(x, y, color=color, label=nombre)
        ax.fill_between(x, y, color=color, alpha=0.12)
    ax.legend()
    return fig


def figura_vpn(resultado: dict) -> Figure:
    """Compara VPN de las tres alternativas en millones de colones."""
    tabla = resultado["escenarios"]
    fig, ax = preparar(
        "Se elige el mayor VPN, incluyendo no invertir", "Alternativa", "VPN (millones de ₡)"
    )
    ax.bar(tabla.escenario, tabla.vpn_colones / 1e6, color=COLORES)
    ax.axhline(0, color="#333333", linewidth=0.7)
    return fig


def figura_descuento(resultado: dict, opcion: str = "Opción A") -> Figure:
    """Muestra el flujo descontado cuyo área, menos costo, produce el VPN."""
    fila = resultado["escenarios"].set_index("escenario").loc[opcion]
    t = np.linspace(0, resultado["H"], 201)
    flujo = fila.ahorro_anual_colones * np.exp(-resultado["r"] * t) / 1e6
    fig, ax = preparar(
        f"El área es el ahorro presente de {opcion}",
        "Tiempo (años)",
        "Ahorro descontado (millones de ₡/año)",
    )
    ax.plot(t, flujo, color=COLORES[1])
    ax.fill_between(t, flujo, color=COLORES[1], alpha=0.2)
    return fig


def figura_exploracion(base: BaseDatos) -> Figure:
    """Muestra conteos anuales y relación magnitud-distancia sin borrar atípicos."""
    c = base.hojas["Catalogo_sismos"]
    conteo = c.groupby(c.fecha_hora.dt.year).size()
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    ax[0].bar(conteo.index, conteo.values, color=COLORES[1])
    ax[0].set(title="Frecuencia anual del catálogo", xlabel="Año", ylabel="Sismos registrados")
    ax[1].scatter(c.distancia_sitio_km, c.magnitud_Mw, s=10, alpha=0.4, color=COLORES[1])
    ax[1].set(
        title="Magnitud y distancia al sitio", xlabel="Distancia (km)", ylabel="Magnitud (Mw)"
    )
    fig.supxlabel(FUENTE, fontsize=8)
    return fig


def figura_sensibilidad(resultado: dict) -> Figure:
    """Grafica VPN frente a b a tasa base y frente a tasa con b base."""
    s = resultado["sensibilidad"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), layout="constrained")
    for ax, mascara, x, titulo in [
        (axes[0], s.delta_r_pp == 0, "b", "Sensibilidad al parámetro b"),
        (axes[1], s.delta_b == 0, "r_pct", "Sensibilidad al descuento"),
    ]:
        for nombre, color in zip(["Opción A", "Opción B"], COLORES[1:], strict=True):
            datos = s[mascara & (s.escenario == nombre)]
            ax.plot(datos[x], datos.vpn_colones / 1e6, "o-", color=color, label=nombre)
        ax.axhline(0, color=COLORES[0], linestyle="--", label="Sin refuerzo")
        ax.set(
            title=titulo,
            xlabel="b (adimensional)" if x == "b" else "Descuento anual (%)",
            ylabel="VPN (millones de ₡)",
        )
        ax.legend(fontsize=8)
    fig.supxlabel(FUENTE, fontsize=8)
    return fig
