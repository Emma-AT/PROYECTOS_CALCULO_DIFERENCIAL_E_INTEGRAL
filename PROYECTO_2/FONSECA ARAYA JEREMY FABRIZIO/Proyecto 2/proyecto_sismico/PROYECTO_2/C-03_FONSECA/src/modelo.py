"""Modelo matemático: recurrencia, movimiento del suelo y pérdidas esperadas."""

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from src.limpieza import BaseDatos, corregir_linea_base, interpolar_faltantes
from src.numericos import error_relativo, integral_acumulada, simpson, trapecio, validar_vectores

G = 9.80665  # Constante física: gravedad estándar, m/s²; no es un dato del hospital.


def estimar_b(catalogo: pd.DataFrame, m0: float) -> float:
    """Estima b adimensional con media de magnitudes Mw >=m0 y corrección de 0,05.

    La resolución 0,1 Mw es la indicada por el enunciado y validada al leer la base.
    """
    magnitudes = catalogo["magnitud_Mw"].to_numpy(dtype=float)
    if not np.isfinite(magnitudes).all() or len(magnitudes) < 2 or np.any(magnitudes < m0):
        raise ValueError("Las magnitudes deben ser finitas y mayores o iguales a m0.")
    return float(np.log10(np.e) / (magnitudes.mean() - (m0 - 0.1 / 2)))


def tasa(m: ArrayLike, lambda3: float, b: float) -> NDArray:
    """Devuelve lambda(m), eventos/año con M>=m; m en Mw, b>0, lambda3>=0."""
    m = np.asarray(m, dtype=float)
    if not np.isfinite([lambda3, b]).all() or lambda3 < 0 or b <= 0 or not np.isfinite(m).all():
        raise ValueError("La tasa requiere lambda3>=0, b>0 y magnitudes finitas.")
    return lambda3 * np.power(10.0, -b * (m - 3.0))


def densidad_eventos(m: ArrayLike, lambda3: float, b: float) -> NDArray:
    """Devuelve -lambda'(m), en eventos/(año·Mw); no es una densidad normalizada."""
    return b * np.log(10.0) * tasa(m, lambda3, b)


def probabilidad(m: float, lambda3: float, b: float, horizonte: float) -> float:
    """Probabilidad Poisson de al menos un evento M>=m en horizonte (años)."""
    if not np.isfinite(horizonte) or horizonte < 0:
        raise ValueError("El horizonte debe ser finito y no negativo.")
    return float(-np.expm1(-tasa(m, lambda3, b) * horizonte))


def intensidad_arias(t: ArrayLike, a: ArrayLike) -> float:
    """Recibe t (s), a (cm/s²); convierte a m/s² e integra a² por trapecios.

    Devuelve intensidad de Arias en m/s: pi/(2g) * integral(a_m² dt).
    """
    a_m = np.asarray(a, dtype=float) / 100
    return float(np.pi / (2 * G) * trapecio(t, a_m**2))


def duracion_significativa(t: ArrayLike, a: ArrayLike) -> tuple[float, float, float]:
    """Recibe tiempo (s), aceleración (cm/s²); devuelve t5, t95 y duración (s).

    Interpola los cruces de 5 y 95 % de Arias acumulada. Rechaza energía nula.
    """
    acumulada = integral_acumulada(t, (np.asarray(a, dtype=float) / 100) ** 2)
    if acumulada[-1] <= 0:
        raise ValueError("La duración significativa no está definida para energía nula.")
    t5, t95 = np.interp([0.05, 0.95], acumulada / acumulada[-1], t)
    return float(t5), float(t95), float(t95 - t5)


def analizar_movimiento(base: BaseDatos) -> tuple[pd.DataFrame, dict]:
    """Desde BaseDatos calcula series en s, cm/s², cm/s, cm e indicadores del sismo."""
    acel = base.hojas["Acelerograma"]
    t = acel.tiempo_s.to_numpy(dtype=float)
    a = acel.aceleracion_cm_s2.to_numpy(dtype=float)
    t0 = float(base.hojas["Evento"].segundos_previos_al_sismo.iloc[0])
    original = interpolar_faltantes(t, a)
    corregida = corregir_linea_base(t, a, t0)
    v = integral_acumulada(t, corregida)
    x = integral_acumulada(t, v)
    v_sin = integral_acumulada(t, original)
    x_sin = integral_acumulada(t, v_sin)
    arias = np.pi / (2 * G) * integral_acumulada(t, (corregida / 100) ** 2)
    if arias[-1] > 0:
        t5, t95, duracion = duracion_significativa(t, corregida)
    else:
        t5 = t95 = duracion = None
    indicadores = {
        "linea_base_cm_s2": float(original[t < t0].mean()),
        "PGA_cm_s2": float(np.max(np.abs(corregida))),
        "PGV_cm_s": float(np.max(np.abs(v))),
        "PGD_cm": float(np.max(np.abs(x))),
        "IA_m_s": intensidad_arias(t, corregida),
        "t5_s": t5,
        "t95_s": t95,
        "duracion_s": duracion,
        "desplazamiento_final_cm": float(x[-1]),
        "desplazamiento_final_sin_corregir_cm": float(x_sin[-1]),
    }
    series = pd.DataFrame(
        {
            "tiempo_s": t,
            "aceleracion_original_cm_s2": a,
            "aceleracion_interpolada_cm_s2": original,
            "aceleracion_corregida_cm_s2": corregida,
            "velocidad_cm_s": v,
            "desplazamiento_cm": x,
            "velocidad_sin_corregir_cm_s": v_sin,
            "desplazamiento_sin_corregir_cm": x_sin,
            "arias_acumulada_m_s": arias,
        }
    )
    return series, indicadores


def malla_dano(m: ArrayLike, dano: ArrayLike, subdivisiones: int = 16) -> tuple[NDArray, NDArray]:
    """Interpola linealmente daño fraccionario entre magnitudes Mw.

    Usa subdivisiones pares por tramo para aplicar Simpson sin cruzar los quiebres.
    Es una reconstrucción de la curva, no nuevos datos observados.
    """
    m, dano = validar_vectores(m, dano)
    if not isinstance(subdivisiones, int) or subdivisiones < 2 or subdivisiones % 2:
        raise ValueError("Las subdivisiones deben ser un entero par >=2.")
    if np.any((dano < 0) | (dano > 1)) or not np.allclose(np.diff(m), np.diff(m)[0]):
        raise ValueError("Se requiere daño entre 0 y 1 y magnitudes uniformes.")
    malla = np.linspace(m[0], m[-1], (len(m) - 1) * subdivisiones + 1)
    return malla, np.interp(malla, m, dano)


def perdida_anual(m: ArrayLike, D: ArrayLike, lambda3: float, b: float, V: float) -> float:
    """PAE (colones/año) con Simpson propio sobre daño lineal por tramos refinado.

    Entradas: m en Mw, D como fracción [0,1], lambda3 eventos/año, b, V colones.
    """
    if not np.isfinite(V) or V <= 0:
        raise ValueError("El valor de reposición debe ser positivo y finito.")
    x, dano = malla_dano(m, D)
    return float(V * simpson(x, dano * densidad_eventos(x, lambda3, b)))


def perdida_exacta_lineal(m: ArrayLike, D: ArrayLike, lambda3: float, b: float, V: float) -> float:
    """Integral analítica de daño lineal por tramos por densidad exponencial.

    Entradas y salida como perdida_anual. Ver deducción por partes en docs/MATEMATICA.md.
    """
    m, D = validar_vectores(m, D)
    h = np.diff(m)
    pendiente = np.diff(D) / h
    beta = b * np.log(10)
    integral_uno = -np.expm1(-beta * h)
    integral_u = integral_uno / beta - h * np.exp(-beta * h)
    tramos = tasa(m[:-1], lambda3, b) * (D[:-1] * integral_uno + pendiente * integral_u)
    return float(V * tramos.sum())


def vpn_refuerzo(costo: float, delta_pae: float, r: float, H: float) -> float:
    """VPN exacto (colones), con ahorro anual constante y descuento continuo.

    costo: colones; delta_pae: colones/año; r: fracción/año; H: años.
    """
    if not np.isfinite([costo, delta_pae, r, H]).all() or min(costo, r, H) < 0:
        raise ValueError("Costo, tasa y horizonte deben ser finitos y no negativos.")
    factor = H if r == 0 else -np.expm1(-r * H) / r
    return float(-costo + delta_pae * factor)


def validar_seno() -> pd.DataFrame:
    """Verifica dos integraciones de sin(t) en [0,10], paso 0,01 s.

    Devuelve errores relativos de norma máxima (%) para evitar dividir por ceros.
    """
    t = np.linspace(0, 10, 1001)
    v = integral_acumulada(t, np.sin(t))
    x = integral_acumulada(t, v)
    exactas = [1 - np.cos(t), t - np.sin(t)]
    return pd.DataFrame(
        [
            {
                "variable": nombre,
                "error_relativo_max_pct": float(100 * np.max(abs(calc - ex)) / np.max(abs(ex))),
                "limite_pct": 0.5,
            }
            for nombre, calc, ex in zip(
                ["velocidad", "desplazamiento"], [v, x], exactas, strict=True
            )
        ]
    )


def verificar_integrales(base: BaseDatos, b: float, series: pd.DataFrame) -> pd.DataFrame:
    """Compara métodos propios y fórmulas exactas; entrega valores y errores (%).

    En registros sin valor verdadero, el error relativo es discrepancia entre métodos.
    """
    filas = []
    t = series.tiempo_s.to_numpy()
    a = series.aceleracion_corregida_cm_s2.to_numpy()
    v = series.velocidad_cm_s.to_numpy()
    for nombre, y, unidad in [
        ("Integral a(t)", a, "cm/s"),
        ("Integral v(t)", v, "cm"),
        ("Arias", (a / 100) ** 2 * np.pi / (2 * G), "m/s"),
    ]:
        uno, dos = trapecio(t, y), simpson(t, y)
        filas.append(
            {
                "integral": nombre,
                "metodo": "Trapecio",
                "valor": uno,
                "referencia": "Simpson",
                "valor_referencia": dos,
                "unidad": unidad,
                "error_relativo_pct": error_relativo(uno, dos),
            }
        )
    vul = base.hojas["Vulnerabilidad"]
    m = vul.magnitud_Mw.to_numpy()
    lam = len(base.hojas["Catalogo_sismos"]) / base.anos_catalogo
    valor = base.parametro("Valor de reposición del pabellón")
    for col in vul.columns[1:]:
        D = vul[col].to_numpy() / 100
        x, d = malla_dano(m, D)
        exacta = perdida_exacta_lineal(m, D, lam, b, valor)
        for metodo, integral in [
            ("Simpson refinado", perdida_anual(m, D, lam, b, valor)),
            ("Trapecio refinado", valor * trapecio(x, d * densidad_eventos(x, lam, b))),
            ("Simpson tabla original", valor * simpson(m, D * densidad_eventos(m, lam, b))),
        ]:
            filas.append(
                {
                    "integral": f"PAE {col}",
                    "metodo": metodo,
                    "valor": integral,
                    "referencia": "Exacta D lineal",
                    "valor_referencia": exacta,
                    "unidad": "colones/año",
                    "error_relativo_pct": error_relativo(integral, exacta),
                }
            )
    return pd.DataFrame(filas)
