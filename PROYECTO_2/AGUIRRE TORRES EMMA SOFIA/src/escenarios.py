"""Energía anual, factor de planta, VPN y comparación de opciones."""

import pandas as pd

from src.limpieza import densidad_aire, leer_parametros, limpiar_viento
from src.modelo import (
    Turbina,
    calibrar_perdidas,
    energia,
    potencia,
    potencia_media,
    turbinas_desde_excel,
    weibull_momentos,
)

HORAS_ANIO = 8760  # h/año (constante de calendario, no es un dato de la base)


def escalar_c(c_ref: float, h: float, h_ref: float, alpha: float) -> float:
    """Ley potencial v(H) = v(H0)·(H/H0)^α aplicada a la escala c de Weibull (m/s)."""
    return c_ref * (h / h_ref) ** alpha


def energia_anual(turbina: Turbina, k, c_ref, h_ref, alpha, rho, rho_ref, perdidas, altura):
    """E_anual = 8760 · N · (1 − L) · P̄ en kWh/año, con c llevada a la altura del buje."""
    c_h = escalar_c(c_ref, altura, h_ref, alpha)
    p_media = potencia_media(turbina, k, c_h, rho, rho_ref)
    return HORAS_ANIO * turbina.n * (1 - perdidas) * p_media


def factor_planta(e_anual_kwh: float, turbina: Turbina) -> float:
    """Factor de planta = energía real / energía a potencia nominal todo el año (fracción)."""
    return e_anual_kwh / (HORAS_ANIO * turbina.n * turbina.p_nom_kw)


def vpn(inversion, delta_e_kwh, precio, delta_m, tasa, anios) -> float:
    """VPN = −I + (ΔE·p − ΔM)·[1 − (1+r)^(−n)] / r, en colones."""
    anualidad = (1 - (1 + tasa) ** (-anios)) / tasa
    return -inversion + (delta_e_kwh * precio - delta_m) * anualidad


def preparar(hojas: dict) -> dict:
    """Limpia el viento, calcula la densidad, calibra L y ajusta Weibull de los 60 días."""
    params = leer_parametros(hojas["Parametros"])
    turbinas = turbinas_desde_excel(hojas)
    df = limpiar_viento(hojas["Viento_horario"])
    presion_pa = params["presion_kpa"] * 1000
    df["rho_kg_m3"] = densidad_aire(df["temperatura_C"], presion_pa, params["r_aire"])
    actual = turbinas[0]
    df["p_planta_kW"] = actual.n * potencia(
        df["v_limpia_m_s"], actual, df["rho_kg_m3"], params["rho_ref"]
    )
    e_teorica = energia(df["p_planta_kW"], 1.0)
    e_medida = df["prod_limpia_MWh"].sum() * 1000  # MWh -> kWh
    k60, c60 = weibull_momentos(df["v_limpia_m_s"])
    return {
        "params": params,
        "turbinas": turbinas,
        "viento": df,
        "e_teorica_kWh": e_teorica,
        "e_medida_kWh": e_medida,
        "L": calibrar_perdidas(e_teorica, e_medida),
        "k60": k60,
        "c60": c60,
        "rho_media": float(df["rho_kg_m3"].mean()),
    }


def comparar(base: dict, alpha: float, precio: float, alturas: dict | None = None):
    """Tabla con energía anual, factor de planta, inversión y VPN de cada opción.

    El VPN es incremental frente a la fila 0 (Mantener); también se calcula con
    el precio 20 % menor que pide el criterio de éxito.
    """
    p = base["params"]
    alturas = alturas or {}
    filas = []
    for t in base["turbinas"]:
        h = alturas.get(t.nombre, t.altura_m)
        e = energia_anual(
            t,
            p["k_anual"],
            p["c_anual_ms"],
            p["h_ref_m"],
            alpha,
            base["rho_media"],
            p["rho_ref"],
            base["L"],
            h,
        )
        filas.append(
            {
                "opcion": t.nombre,
                "turbinas": t.n,
                "altura_m": h,
                "energia_GWh": e / 1e6,
                "factor_planta": factor_planta(e, t),
                "inversion_colones": t.inversion,
                "mantenimiento_colones": t.mantenimiento,
            }
        )
    tabla = pd.DataFrame(filas)
    ref = tabla.iloc[0]
    for columna, precio_i in [("vpn_colones", precio), ("vpn_precio_80_colones", 0.8 * precio)]:
        tabla[columna] = [
            vpn(
                f.inversion_colones,
                (f.energia_GWh - ref.energia_GWh) * 1e6,
                precio_i,
                f.mantenimiento_colones - ref.mantenimiento_colones,
                p["tasa_pct"] / 100,
                p["vida_anios"],
            )
            for f in tabla.itertuples()
        ]
    return tabla


def recomendar(tabla: pd.DataFrame, columna: str = "vpn_colones") -> str:
    """Devuelve la recomendación: la opción con mayor VPN, o mantener si ninguno es > 0."""
    mejor = tabla.loc[tabla[columna].idxmax()]
    if mejor[columna] <= 0:
        return "Mantener las turbinas actuales: ninguna opción tiene VPN positivo."
    return (
        f"Repotenciar con {mejor['opcion']}: VPN de ₡{mejor[columna] / 1e9:,.2f} "
        "mil millones frente a mantener."
    )


def precio_equilibrio(fila, ref, tasa: float, anios: float) -> float:
    """Precio de la energía (colones/kWh) con el que el VPN de una opción vale 0.

    Despejando VPN = 0:  p* = (I / a + ΔM) / ΔE,  con a = [1 − (1+r)^(−n)] / r.
    Entradas: fila y ref son filas de la tabla de comparar() (opción y Mantener).
    """
    anualidad = (1 - (1 + tasa) ** (-anios)) / tasa
    delta_e = (fila["energia_GWh"] - ref["energia_GWh"]) * 1e6
    delta_m = fila["mantenimiento_colones"] - ref["mantenimiento_colones"]
    if delta_e <= 0:
        return float("inf")
    return (fila["inversion_colones"] / anualidad + delta_m) / delta_e
